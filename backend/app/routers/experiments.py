from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, UploadFile

from app.auth.auth import get_current_active_user, get_current_verified_user
from app.models.metrics import Split
from app.models.users import User
from app.schemas.experiments import ExperimentCreate, ExperimentPublic
from app.schemas.metric_imports import MetricImportPublic
from app.schemas.metrics import (
    BestConfigurationQuery,
    BestConfigurationResponse,
    ExperimentMetrics,
    LeaderboardEntry,
    LeaderboardQuery,
    MetricsBatchCreate,
    MultiMetricLeaderboardEntry,
)
from app.services import experiments as exp_service
from app.services import leaderboard as lb_service
from app.services import metrics as metric_service
from app.services.metric_imports import (
    create_metric_import_job,
    list_metric_import_jobs_for_experiment,
    process_metric_import_job,
)

router = APIRouter()


@router.post("/experiments", response_model=ExperimentPublic, tags=["experiments"])
async def submit_experiment(
    data: ExperimentCreate,
    current_user: User = Depends(get_current_verified_user),
) -> ExperimentPublic:
    return await exp_service.create_experiment(data, current_user)


@router.get(
    "/experiments/{experiment_uuid}",
    response_model=ExperimentPublic,
    tags=["experiments"],
)
async def get_experiment(
    experiment_uuid: UUID,
    _: User = Depends(get_current_active_user),
) -> ExperimentPublic:
    return await exp_service.get_experiment_public(experiment_uuid)


# Legacy endpoint kept during migration: direct metrics submission.
@router.post(
    "/experiments/{experiment_uuid}/metrics",
    response_model=ExperimentMetrics,
    tags=["metrics"],
)
async def submit_metrics(
    experiment_uuid: UUID,
    data: MetricsBatchCreate,
    _: User = Depends(get_current_verified_user),
) -> ExperimentMetrics:
    data.experiment_uuid = experiment_uuid
    await metric_service.create_metrics_batch(data)
    return await metric_service.get_experiment_metrics(experiment_uuid)


@router.get(
    "/experiments/{experiment_uuid}/metrics",
    response_model=ExperimentMetrics,
    tags=["metrics"],
)
async def get_experiment_metrics(experiment_uuid: UUID) -> ExperimentMetrics:
    return await metric_service.get_experiment_metrics(experiment_uuid)


@router.post(
    "/experiments/{experiment_uuid}/metric-import",
    response_model=MetricImportPublic,
    tags=["metric-imports"],
)
async def upload_metric_import(
    experiment_uuid: UUID,
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_verified_user),
) -> MetricImportPublic:
    job = await create_metric_import_job(experiment_uuid, file, current_user)
    background_tasks.add_task(process_metric_import_job, job.uuid)
    return job


@router.get(
    "/experiments/{experiment_uuid}/metric-imports",
    response_model=list[MetricImportPublic],
    tags=["metric-imports"],
)
async def list_metric_imports(
    experiment_uuid: UUID,
    _: User = Depends(get_current_active_user),
) -> list[MetricImportPublic]:
    return await list_metric_import_jobs_for_experiment(experiment_uuid)


@router.get("/leaderboard", response_model=list[LeaderboardEntry], tags=["leaderboard"])
async def get_leaderboard(
    dataset_uuid: UUID,
    metric: str,
    split: Split,
    top_n: int = 10,
    dataset_version_uuid: UUID | None = None,
    pipeline_uuid: UUID | None = None,
    model_uuids: str | None = None,
    author_uuids: str | None = None,
) -> list[LeaderboardEntry]:
    if dataset_version_uuid is not None and pipeline_uuid is None:
        raise HTTPException(
            status_code=422,
            detail=(
                "pipeline_uuid è obbligatorio quando viene specificata "
                "dataset_version_uuid"
            ),
        )
    try:
        parsed_model_uuids = (
            [UUID(item.strip()) for item in model_uuids.split(",") if item.strip()]
            if model_uuids
            else None
        )
        parsed_author_uuids = (
            [UUID(item.strip()) for item in author_uuids.split(",") if item.strip()]
            if author_uuids
            else None
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail="UUID non valido nei filtri") from exc
    return await lb_service.get_leaderboard(
        dataset_uuid,
        metric,
        split,
        top_n,
        dataset_version_uuid=dataset_version_uuid,
        pipeline_uuid=pipeline_uuid,
        model_uuids=parsed_model_uuids,
        author_uuids=parsed_author_uuids,
    )


@router.get(
    "/leaderboard/multi",
    response_model=list[MultiMetricLeaderboardEntry],
    tags=["leaderboard"],
)
async def get_multi_metric_leaderboard(
    dataset_uuid: UUID,
    metrics: str,
    split: Split,
    sort_by: str,
    top_n: int = 20,
    dataset_version_uuid: UUID | None = None,
    pipeline_uuid: UUID | None = None,
    model_uuids: str | None = None,
    author_uuids: str | None = None,
) -> list[MultiMetricLeaderboardEntry]:
    if dataset_version_uuid is not None and pipeline_uuid is None:
        raise HTTPException(
            status_code=422,
            detail=(
                "pipeline_uuid è obbligatorio quando viene specificata "
                "dataset_version_uuid"
            ),
        )
    metrics_list = [m.strip() for m in metrics.split(",") if m.strip()]
    try:
        parsed_model_uuids = (
            [UUID(item.strip()) for item in model_uuids.split(",") if item.strip()]
            if model_uuids
            else None
        )
        parsed_author_uuids = (
            [UUID(item.strip()) for item in author_uuids.split(",") if item.strip()]
            if author_uuids
            else None
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail="UUID non valido nei filtri") from exc
    return await lb_service.get_multi_metric_leaderboard(
        dataset_uuid,
        metrics_list,
        split,
        sort_by,
        top_n,
        dataset_version_uuid=dataset_version_uuid,
        pipeline_uuid=pipeline_uuid,
        model_uuids=parsed_model_uuids,
        author_uuids=parsed_author_uuids,
    )


@router.post(
    "/leaderboard/query",
    response_model=list[MultiMetricLeaderboardEntry],
    tags=["leaderboard"],
)
async def query_leaderboard(data: LeaderboardQuery) -> list[MultiMetricLeaderboardEntry]:
    return await lb_service.query_leaderboard(data)


@router.post(
    "/leaderboard/best-configuration",
    response_model=BestConfigurationResponse,
    tags=["leaderboard"],
)
async def best_configuration(data: BestConfigurationQuery) -> BestConfigurationResponse:
    return await lb_service.get_best_configuration(data)
