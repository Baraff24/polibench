from uuid import UUID

from fastapi import HTTPException

from app.models.dataset_versions import DatasetVersion
from app.models.datasets import Dataset
from app.models.experiments import Experiment, Status
from app.models.ml_models import MLModel
from app.models.pipelines import Pipeline
from app.models.teams import Team
from app.models.users import User
from app.schemas.experiments import ExperimentCreate, ExperimentPublic, ExperimentSummary
from app.services.dataset_versions import (
    get_dataset_version_and_dataset,
    get_latest_dataset_version,
)
from app.services.datasets import get_dataset_by_uuid, get_ml_model_by_uuid
from app.services.pipelines import (
    get_latest_pipeline_for_dataset_version,
    get_pipeline_by_uuid,
)


async def get_experiment_by_uuid(experiment_uuid: UUID) -> Experiment:
    exp = await Experiment.find_one(Experiment.uuid == experiment_uuid)
    if exp is None:
        raise HTTPException(status_code=404, detail="Experiment non trovato")
    return exp


async def _resolve_team_id(team_uuid: UUID | None):
    if team_uuid is None:
        return None
    team = await Team.find_one(Team.uuid == team_uuid)
    if team is None:
        raise HTTPException(status_code=404, detail="Team non trovato")
    return team.id


async def _resolve_pipeline_dataset_and_version(
    data: ExperimentCreate,
) -> tuple[Pipeline, DatasetVersion, Dataset]:
    # Main path: explicit pipeline UUID.
    if data.pipeline_uuid is not None:
        pipeline = await get_pipeline_by_uuid(data.pipeline_uuid)
        dataset_version = await DatasetVersion.get(pipeline.dataset_version_id)
        if dataset_version is None:
            raise HTTPException(
                status_code=404,
                detail="DatasetVersion della pipeline non trovata",
            )
        dataset = await Dataset.get(dataset_version.dataset_id)
        if dataset is None:
            raise HTTPException(
                status_code=404,
                detail="Dataset della pipeline non trovato",
            )

        if (
            data.dataset_version_uuid is not None
            and data.dataset_version_uuid != dataset_version.uuid
        ):
            raise HTTPException(
                status_code=422,
                detail=(
                    "pipeline_uuid non appartiene "
                    "alla dataset_version_uuid specificata"
                ),
            )
        if data.dataset_uuid is not None and data.dataset_uuid != dataset.uuid:
            raise HTTPException(
                status_code=422,
                detail="pipeline_uuid non appartiene al dataset_uuid specificato",
            )
        return pipeline, dataset_version, dataset

    # Transitional compatibility: dataset_version_uuid -> latest pipeline for version.
    if data.dataset_version_uuid is not None:
        dataset_version, dataset = await get_dataset_version_and_dataset(
            data.dataset_version_uuid
        )
        pipeline = await get_latest_pipeline_for_dataset_version(dataset_version.uuid)
        return pipeline, dataset_version, dataset

    # Transitional compatibility: accept dataset_uuid and use latest version.
    if data.dataset_uuid is not None:
        dataset = await get_dataset_by_uuid(data.dataset_uuid)
        version = await get_latest_dataset_version(data.dataset_uuid)
        pipeline = await get_latest_pipeline_for_dataset_version(version.uuid)
        return pipeline, version, dataset

    raise HTTPException(
        status_code=422,
        detail=(
            "pipeline_uuid è obbligatorio "
            "(oppure dataset_version_uuid/dataset_uuid in modalità legacy)"
        ),
    )


async def create_experiment(
    data: ExperimentCreate,
    current_user: User,
) -> ExperimentPublic:
    pipeline, dataset_version, dataset = await _resolve_pipeline_dataset_and_version(data)
    model = await get_ml_model_by_uuid(data.model_uuid)
    team_id = await _resolve_team_id(data.team_uuid)

    exp = Experiment(
        pipeline_id=pipeline.id,
        dataset_version_id=dataset_version.id,
        dataset_id=dataset.id,
        model_id=model.id,
        submitted_by_user_id=current_user.id,
        team_id=team_id,
        run_name=data.run_name,
        status=Status.QUEUED,
        training_config=data.training_config,
        seed=data.seed,
        notes=data.notes,
        code=data.code,
    )
    await exp.create()
    return ExperimentPublic(
        uuid=exp.uuid,
        dataset_uuid=dataset.uuid,
        dataset_version_uuid=dataset_version.uuid,
        pipeline_uuid=pipeline.uuid,
        model_uuid=model.uuid,
        team_uuid=data.team_uuid,
        submitted_by_user_uuid=current_user.uuid,
        run_name=exp.run_name,
        status=exp.status,
        training_config=exp.training_config,
        seed=exp.seed,
        notes=exp.notes,
        code=exp.code,
        artifacts=exp.artifacts,
        created_at=exp.created_at,
        finished_at=exp.finished_at,
    )


async def get_experiment_public(experiment_uuid: UUID) -> ExperimentPublic:
    exp = await get_experiment_by_uuid(experiment_uuid)

    pipeline: Pipeline | None = None
    if exp.pipeline_id is not None:
        pipeline = await Pipeline.get(exp.pipeline_id)
        if pipeline is None:
            raise HTTPException(
                status_code=404,
                detail="Pipeline dell'experiment non trovata",
            )

    dataset_version = await DatasetVersion.get(exp.dataset_version_id)
    if dataset_version is None:
        raise HTTPException(
            status_code=404,
            detail="DatasetVersion dell'experiment non trovata",
        )

    dataset = await Dataset.get(dataset_version.dataset_id)
    if dataset is None:
        raise HTTPException(status_code=404, detail="Dataset dell'experiment non trovato")

    model = await MLModel.get(exp.model_id)
    if model is None:
        raise HTTPException(status_code=404, detail="MLModel dell'experiment non trovato")

    submitter = await User.get(exp.submitted_by_user_id)

    team_uuid = None
    if exp.team_id is not None:
        team = await Team.get(exp.team_id)
        team_uuid = team.uuid if team else None

    return ExperimentPublic(
        uuid=exp.uuid,
        dataset_uuid=dataset.uuid,
        dataset_version_uuid=dataset_version.uuid,
        pipeline_uuid=pipeline.uuid if pipeline else None,
        model_uuid=model.uuid,
        team_uuid=team_uuid,
        submitted_by_user_uuid=submitter.uuid if submitter else None,
        run_name=exp.run_name,
        status=exp.status,
        training_config=exp.training_config,
        seed=exp.seed,
        notes=exp.notes,
        code=exp.code,
        artifacts=exp.artifacts,
        created_at=exp.created_at,
        finished_at=exp.finished_at,
    )


async def list_experiments_for_dataset_version(
    dataset_version_uuid: UUID,
) -> list[ExperimentSummary]:
    dataset_version, dataset = await get_dataset_version_and_dataset(dataset_version_uuid)
    experiments = (
        await Experiment.find(Experiment.dataset_version_id == dataset_version.id)
        .sort([("created_at", -1)])
        .to_list()
    )
    if not experiments:
        return []

    model_ids = list({e.model_id for e in experiments})
    models = await MLModel.find({"_id": {"$in": model_ids}}).to_list()
    model_by_id = {m.id: m for m in models}
    pipeline_ids = list({e.pipeline_id for e in experiments if e.pipeline_id is not None})
    pipelines = await Pipeline.find({"_id": {"$in": pipeline_ids}}).to_list()
    pipeline_by_id = {p.id: p for p in pipelines}

    out: list[ExperimentSummary] = []
    for exp in experiments:
        model = model_by_id.get(exp.model_id)
        if model is None:
            continue
        pipeline = pipeline_by_id.get(exp.pipeline_id) if exp.pipeline_id else None
        if pipeline is None:
            continue
        out.append(
            ExperimentSummary(
                uuid=exp.uuid,
                dataset_uuid=dataset.uuid,
                dataset_version_uuid=dataset_version.uuid,
                pipeline_uuid=pipeline.uuid,
                pipeline_code=pipeline.code,
                model_uuid=model.uuid,
                model_name=model.name,
                run_name=exp.run_name,
                status=exp.status,
                created_at=exp.created_at,
            )
        )
    return out
