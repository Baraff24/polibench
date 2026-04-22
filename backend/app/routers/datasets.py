from uuid import UUID

from fastapi import APIRouter, Depends, Response

from app.auth.auth import get_current_verified_user
from app.models.users import User
from app.schemas.dataset_versions import (
    DatasetVersionCreate,
    DatasetVersionPipelinePublic,
    DatasetVersionPublic,
    DatasetVersionSummary,
    DatasetVersionYamlPublic,
    ResourcePublic,
    SourcePublic,
)
from app.schemas.datasets import DatasetCreate, DatasetPublic, DatasetSummary
from app.schemas.ml_models import MLModelCreate, MLModelPublic, MLModelSummary
from app.services.dataset_versions import (
    create_dataset_version,
    get_dataset_version_public,
    get_pipeline_for_version,
    get_yaml_for_version,
    list_dataset_versions,
    list_resources_for_version,
    list_sources_for_version,
)
from app.services.datasets import (
    create_dataset,
    create_ml_model,
    get_dataset_public,
    get_ml_model_public_by_uuid,
    list_datasets,
    list_ml_models,
)

router = APIRouter()


@router.post("/datasets", response_model=DatasetPublic, tags=["datasets"])
async def create_dataset_endpoint(
    data: DatasetCreate,
    current_user: User = Depends(get_current_verified_user),
) -> DatasetPublic:
    return await create_dataset(data, current_user)


@router.get("/datasets", response_model=list[DatasetSummary], tags=["datasets"])
async def list_datasets_endpoint() -> list[DatasetSummary]:
    return await list_datasets()


@router.get(
    "/datasets/{dataset_uuid}",
    response_model=DatasetPublic,
    tags=["datasets"],
)
async def get_dataset_endpoint(dataset_uuid: UUID) -> DatasetPublic:
    return await get_dataset_public(dataset_uuid)


@router.get(
    "/datasets/{dataset_uuid}/versions",
    response_model=list[DatasetVersionSummary],
    tags=["datasets"],
)
async def list_dataset_versions_endpoint(
    dataset_uuid: UUID,
) -> list[DatasetVersionSummary]:
    return await list_dataset_versions(dataset_uuid)


@router.post(
    "/datasets/{dataset_uuid}/versions",
    response_model=DatasetVersionPublic,
    tags=["datasets"],
)
async def create_dataset_version_endpoint(
    dataset_uuid: UUID,
    data: DatasetVersionCreate,
    _: User = Depends(get_current_verified_user),
) -> DatasetVersionPublic:
    return await create_dataset_version(dataset_uuid, data)


@router.get(
    "/dataset-versions/{version_uuid}",
    response_model=DatasetVersionPublic,
    tags=["dataset-versions"],
)
async def get_dataset_version_endpoint(version_uuid: UUID) -> DatasetVersionPublic:
    return await get_dataset_version_public(version_uuid)


@router.get(
    "/dataset-versions/{version_uuid}/sources",
    response_model=list[SourcePublic],
    tags=["dataset-versions"],
)
async def get_dataset_version_sources_endpoint(
    version_uuid: UUID,
) -> list[SourcePublic]:
    return await list_sources_for_version(version_uuid)


@router.get(
    "/dataset-versions/{version_uuid}/resources",
    response_model=list[ResourcePublic],
    tags=["dataset-versions"],
)
async def get_dataset_version_resources_endpoint(
    version_uuid: UUID,
) -> list[ResourcePublic]:
    return await list_resources_for_version(version_uuid)


@router.get(
    "/dataset-versions/{version_uuid}/pipeline",
    response_model=DatasetVersionPipelinePublic,
    tags=["dataset-versions"],
)
async def get_dataset_version_pipeline_endpoint(
    version_uuid: UUID,
) -> DatasetVersionPipelinePublic:
    return await get_pipeline_for_version(version_uuid)


@router.get(
    "/dataset-versions/{version_uuid}/yaml/dataset",
    response_model=DatasetVersionYamlPublic,
    tags=["dataset-versions"],
)
async def get_dataset_yaml_endpoint(version_uuid: UUID) -> DatasetVersionYamlPublic:
    return await get_yaml_for_version(version_uuid, "dataset")


@router.get(
    "/dataset-versions/{version_uuid}/yaml/pipeline",
    response_model=DatasetVersionYamlPublic,
    tags=["dataset-versions"],
)
async def get_pipeline_yaml_endpoint(version_uuid: UUID) -> DatasetVersionYamlPublic:
    return await get_yaml_for_version(version_uuid, "pipeline")


@router.get(
    "/dataset-versions/{version_uuid}/yaml/characteristics",
    response_model=DatasetVersionYamlPublic,
    tags=["dataset-versions"],
)
async def get_characteristics_yaml_endpoint(
    version_uuid: UUID,
) -> DatasetVersionYamlPublic:
    return await get_yaml_for_version(version_uuid, "characteristics")


@router.get(
    "/dataset-versions/{version_uuid}/yaml/{kind}/raw",
    tags=["dataset-versions"],
    responses={200: {"content": {"text/yaml": {}}}},
)
async def download_yaml_raw_endpoint(version_uuid: UUID, kind: str) -> Response:
    yaml_payload = await get_yaml_for_version(version_uuid, kind)
    return Response(content=yaml_payload.content, media_type="text/yaml")


@router.post("/ml-models", response_model=MLModelPublic, tags=["ml-models"])
async def create_ml_model_endpoint(
    data: MLModelCreate,
    current_user: User = Depends(get_current_verified_user),
) -> MLModelPublic:
    return await create_ml_model(data, current_user)


@router.get("/ml-models", response_model=list[MLModelSummary], tags=["ml-models"])
async def list_ml_models_endpoint() -> list[MLModelSummary]:
    return await list_ml_models()


@router.get(
    "/ml-models/{model_uuid}",
    response_model=MLModelPublic,
    tags=["ml-models"],
)
async def get_ml_model_endpoint(model_uuid: UUID) -> MLModelPublic:
    return await get_ml_model_public_by_uuid(model_uuid)
