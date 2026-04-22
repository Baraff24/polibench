from collections import defaultdict
from uuid import UUID

from fastapi import HTTPException

from app.models.dataset_versions import DatasetVersion
from app.models.datasets import Dataset
from app.models.ml_models import MLModel
from app.models.teams import Team
from app.models.users import User
from app.schemas.datasets import DatasetCreate, DatasetPublic, DatasetSummary
from app.schemas.ml_models import MLModelCreate, MLModelPublic, MLModelSummary


async def get_dataset_by_uuid(dataset_uuid: UUID) -> Dataset:
    dataset = await Dataset.find_one(Dataset.uuid == dataset_uuid)
    if dataset is None:
        raise HTTPException(status_code=404, detail="Dataset non trovato")
    return dataset


async def get_ml_model_by_uuid(model_uuid: UUID) -> MLModel:
    model = await MLModel.find_one(MLModel.uuid == model_uuid)
    if model is None:
        raise HTTPException(status_code=404, detail="MLModel non trovato")
    return model


async def get_team_by_uuid(team_uuid: UUID) -> Team:
    team = await Team.find_one(Team.uuid == team_uuid)
    if team is None:
        raise HTTPException(status_code=404, detail="Team non trovato")
    return team


async def _build_versions_lookup(
    datasets: list[Dataset],
) -> tuple[dict, dict]:
    dataset_ids = [d.id for d in datasets]
    if not dataset_ids:
        return {}, {}

    versions = await DatasetVersion.find({"dataset_id": {"$in": dataset_ids}}).to_list()
    count_by_dataset_id: dict = defaultdict(int)
    latest_by_dataset_id: dict = {}
    for v in versions:
        count_by_dataset_id[v.dataset_id] += 1
        current = latest_by_dataset_id.get(v.dataset_id)
        if current is None or v.created_at > current.created_at:
            latest_by_dataset_id[v.dataset_id] = v
    return count_by_dataset_id, latest_by_dataset_id


async def create_dataset(data: DatasetCreate, current_user: User) -> DatasetPublic:
    team_doc: Team | None = None
    if data.team_uuid is not None:
        team_doc = await get_team_by_uuid(data.team_uuid)

    dataset = Dataset(
        name=data.name,
        task=data.task,
        description=data.description,
        visibility=data.visibility,
        team_id=team_doc.id if team_doc else None,
        created_by_user_id=current_user.id,
    )
    await dataset.create()
    return _dataset_to_public(dataset, current_user, team_doc)


async def list_datasets() -> list[DatasetSummary]:
    datasets = await Dataset.find_all().to_list()
    count_by_dataset_id, latest_by_dataset_id = await _build_versions_lookup(datasets)
    return [
        _dataset_to_summary(
            d,
            versions_count=count_by_dataset_id.get(d.id, 0),
            latest_version=getattr(latest_by_dataset_id.get(d.id), "version", None),
        )
        for d in datasets
    ]


async def get_dataset_public(dataset_uuid: UUID) -> DatasetPublic:
    dataset = await get_dataset_by_uuid(dataset_uuid)

    team: Team | None = None
    if dataset.team_id is not None:
        team = await Team.get(dataset.team_id)

    creator: User | None = None
    if dataset.created_by_user_id is not None:
        creator = await User.get(dataset.created_by_user_id)

    versions_count = await DatasetVersion.find(
        DatasetVersion.dataset_id == dataset.id
    ).count()
    latest = (
        await DatasetVersion.find(DatasetVersion.dataset_id == dataset.id)
        .sort([("created_at", -1)])
        .first_or_none()
    )

    return _dataset_to_public(
        dataset,
        creator,
        team,
        versions_count=versions_count,
        latest_version=latest.version if latest else None,
    )


def _dataset_to_public(
    dataset: Dataset,
    creator: User | None = None,
    team: Team | None = None,
    versions_count: int = 0,
    latest_version: str | None = None,
) -> DatasetPublic:
    return DatasetPublic(
        uuid=dataset.uuid,
        name=dataset.name,
        task=dataset.task,
        description=dataset.description,
        visibility=dataset.visibility,
        team_uuid=team.uuid if team else None,
        created_by_user_uuid=creator.uuid if creator else None,
        created_at=dataset.created_at,
        versions_count=versions_count,
        latest_version=latest_version,
    )


def _dataset_to_summary(
    dataset: Dataset,
    versions_count: int = 0,
    latest_version: str | None = None,
) -> DatasetSummary:
    return DatasetSummary(
        uuid=dataset.uuid,
        name=dataset.name,
        task=dataset.task,
        visibility=dataset.visibility,
        versions_count=versions_count,
        latest_version=latest_version,
    )


async def create_ml_model(data: MLModelCreate, current_user: User) -> MLModelPublic:
    model = MLModel(
        name=data.name,
        family=data.family,
        paper_url=data.paper_url,
        implementation=data.implementation,
        hyperparams=data.hyperparams,
        created_by_user_id=current_user.id,
    )
    await model.create()
    return _model_to_public(model, current_user)


async def list_ml_models() -> list[MLModelSummary]:
    models = await MLModel.find_all().to_list()
    return [_model_to_summary(m) for m in models]


def get_ml_model_public(model: MLModel, creator: User | None = None) -> MLModelPublic:
    return _model_to_public(model, creator)


async def get_ml_model_public_by_uuid(model_uuid: UUID) -> MLModelPublic:
    model = await get_ml_model_by_uuid(model_uuid)
    return _model_to_public(model)


def _model_to_public(model: MLModel, creator: User | None = None) -> MLModelPublic:
    return MLModelPublic(
        uuid=model.uuid,
        name=model.name,
        family=model.family,
        paper_url=model.paper_url,
        implementation=model.implementation,
        hyperparams=model.hyperparams,
        created_by_user_uuid=creator.uuid if creator else None,
        created_at=model.created_at,
    )


def _model_to_summary(model: MLModel) -> MLModelSummary:
    return MLModelSummary(
        uuid=model.uuid,
        name=model.name,
        family=model.family,
        paper_url=model.paper_url,
    )
