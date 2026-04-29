from uuid import UUID

from fastapi import APIRouter, Depends, Response

from app.auth.auth import get_current_verified_user
from app.models.users import User
from app.schemas.dataset_versions import (
    DatasetVersionCreate,
    DatasetVersionPreviewPublic,
    DatasetVersionPublic,
    DatasetVersionSummary,
    DatasetVersionYamlPublic,
    ResourcePublic,
    SourcePublic,
    SourceWithResourcesPublic,
)
from app.schemas.datasets import DatasetCreate, DatasetPublic, DatasetSummary
from app.schemas.experiments import ExperimentSummary
from app.schemas.ml_models import MLModelCreate, MLModelPublic, MLModelSummary
from app.schemas.pipelines import (
    PipelineCreate,
    PipelinePreviewPublic,
    PipelinePublic,
    PipelineSummary,
    PipelineYamlPublic,
)
from app.services.dataset_versions import (
    create_dataset_version,
    get_dataset_version_public,
    get_yaml_for_version,
    list_dataset_versions,
    list_resources_for_version,
    list_sources_for_version,
    list_sources_with_resources_for_version,
    preview_dataset_version_payload,
)
from app.services.datasets import (
    create_dataset,
    create_ml_model,
    get_dataset_public,
    get_ml_model_public_by_uuid,
    list_datasets,
    list_ml_models,
)
from app.services.experiments import list_experiments_for_dataset_version
from app.services.pipelines import (
    create_pipeline_for_version,
    get_pipeline_public,
    get_pipeline_yaml,
    list_experiments_for_pipeline,
    list_pipelines_for_version,
    preview_pipeline_payload,
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


@router.post(
    "/datasets/{dataset_uuid}/versions/preview",
    response_model=DatasetVersionPreviewPublic,
    tags=["datasets"],
)
async def preview_dataset_version_endpoint(
    dataset_uuid: UUID,
    data: DatasetVersionCreate,
    _: User = Depends(get_current_verified_user),
) -> DatasetVersionPreviewPublic:
    return await preview_dataset_version_payload(dataset_uuid, data)


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
    "/dataset-versions/{version_uuid}/sources-with-resources",
    response_model=list[SourceWithResourcesPublic],
    tags=["dataset-versions"],
)
async def get_dataset_version_sources_with_resources_endpoint(
    version_uuid: UUID,
) -> list[SourceWithResourcesPublic]:
    return await list_sources_with_resources_for_version(version_uuid)


@router.get(
    "/dataset-versions/{version_uuid}/pipelines",
    response_model=list[PipelineSummary],
    tags=["dataset-versions"],
)
async def list_pipelines_for_version_endpoint(
    version_uuid: UUID,
) -> list[PipelineSummary]:
    return await list_pipelines_for_version(version_uuid)


@router.post(
    "/dataset-versions/{version_uuid}/pipelines",
    response_model=PipelinePublic,
    tags=["dataset-versions"],
)
async def create_pipeline_for_version_endpoint(
    version_uuid: UUID,
    data: PipelineCreate,
    _: User = Depends(get_current_verified_user),
) -> PipelinePublic:
    return await create_pipeline_for_version(version_uuid, data)


@router.post(
    "/dataset-versions/{version_uuid}/pipelines/preview",
    response_model=PipelinePreviewPublic,
    tags=["dataset-versions"],
)
async def preview_pipeline_for_version_endpoint(
    version_uuid: UUID,
    data: PipelineCreate,
    _: User = Depends(get_current_verified_user),
) -> PipelinePreviewPublic:
    return await preview_pipeline_payload(version_uuid, data)


@router.get(
    "/pipelines/{pipeline_uuid}",
    response_model=PipelinePublic,
    tags=["pipelines"],
)
async def get_pipeline_endpoint(pipeline_uuid: UUID) -> PipelinePublic:
    return await get_pipeline_public(pipeline_uuid)


@router.get(
    "/pipelines/{pipeline_uuid}/yaml",
    response_model=PipelineYamlPublic,
    tags=["pipelines"],
)
async def get_pipeline_yaml_endpoint(pipeline_uuid: UUID) -> PipelineYamlPublic:
    return await get_pipeline_yaml(pipeline_uuid)


@router.get(
    "/pipelines/{pipeline_uuid}/yaml/raw",
    tags=["pipelines"],
    responses={200: {"content": {"text/yaml": {}}}},
)
async def download_pipeline_yaml_raw_endpoint(pipeline_uuid: UUID) -> Response:
    yaml_payload = await get_pipeline_yaml(pipeline_uuid)
    return Response(content=yaml_payload.content, media_type="text/yaml")


@router.get(
    "/pipelines/{pipeline_uuid}/experiments",
    response_model=list[ExperimentSummary],
    tags=["pipelines"],
)
async def list_experiments_for_pipeline_endpoint(
    pipeline_uuid: UUID,
) -> list[ExperimentSummary]:
    return await list_experiments_for_pipeline(pipeline_uuid)


@router.get(
    "/dataset-versions/{version_uuid}/yaml/dataset",
    response_model=DatasetVersionYamlPublic,
    tags=["dataset-versions"],
)
async def get_dataset_yaml_endpoint(version_uuid: UUID) -> DatasetVersionYamlPublic:
    return await get_yaml_for_version(version_uuid, "dataset")


@router.get(
    "/dataset-versions/{version_uuid}/yaml/version",
    response_model=DatasetVersionYamlPublic,
    tags=["dataset-versions"],
)
async def get_version_yaml_endpoint(version_uuid: UUID) -> DatasetVersionYamlPublic:
    return await get_yaml_for_version(version_uuid, "version")


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
    "/dataset-versions/{version_uuid}/yaml/metrics",
    response_model=DatasetVersionYamlPublic,
    tags=["dataset-versions"],
)
async def get_metrics_yaml_endpoint(version_uuid: UUID) -> DatasetVersionYamlPublic:
    return await get_yaml_for_version(version_uuid, "metrics")


@router.get(
    "/dataset-versions/{version_uuid}/yaml/{kind}/raw",
    tags=["dataset-versions"],
    responses={200: {"content": {"text/yaml": {}}}},
)
async def download_yaml_raw_endpoint(version_uuid: UUID, kind: str) -> Response:
    yaml_payload = await get_yaml_for_version(version_uuid, kind)
    return Response(content=yaml_payload.content, media_type="text/yaml")


@router.get(
    "/dataset-versions/{version_uuid}/experiments",
    response_model=list[ExperimentSummary],
    tags=["dataset-versions"],
)
async def list_experiments_for_version_endpoint(
    version_uuid: UUID,
) -> list[ExperimentSummary]:
    return await list_experiments_for_dataset_version(version_uuid)


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
