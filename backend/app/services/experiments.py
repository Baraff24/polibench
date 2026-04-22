from uuid import UUID

from fastapi import HTTPException

from app.models.experiments import Experiment, Status
from app.models.teams import Team
from app.models.users import User
from app.schemas.experiments import ExperimentCreate, ExperimentPublic
from app.services.dataset_versions import (
    get_dataset_version_and_dataset,
    get_latest_dataset_version,
)
from app.services.datasets import get_dataset_by_uuid, get_ml_model_by_uuid


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


async def _resolve_dataset_version(data: ExperimentCreate):
    if data.dataset_version_uuid is not None:
        return await get_dataset_version_and_dataset(data.dataset_version_uuid)

    # Transitional compatibility: accept dataset_uuid and use latest version.
    if data.dataset_uuid is not None:
        dataset = await get_dataset_by_uuid(data.dataset_uuid)
        version = await get_latest_dataset_version(data.dataset_uuid)
        return version, dataset

    raise HTTPException(
        status_code=422,
        detail="dataset_version_uuid è obbligatorio (oppure dataset_uuid legacy)",
    )


async def create_experiment(
    data: ExperimentCreate,
    current_user: User,
) -> ExperimentPublic:
    dataset_version, dataset = await _resolve_dataset_version(data)
    model = await get_ml_model_by_uuid(data.model_uuid)
    team_id = await _resolve_team_id(data.team_uuid)

    exp = Experiment(
        dataset_version_id=dataset_version.id,
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
    from app.models.dataset_versions import DatasetVersion
    from app.models.datasets import Dataset
    from app.models.ml_models import MLModel

    exp = await get_experiment_by_uuid(experiment_uuid)

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
