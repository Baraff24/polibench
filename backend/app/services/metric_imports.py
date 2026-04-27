import csv
import io
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID, uuid4

from beanie import PydanticObjectId
from fastapi import HTTPException, UploadFile

from app.models.experiments import Experiment
from app.models.metric_import_jobs import ImportStatus, MetricImportJob
from app.models.metrics import Direction, Metric, Split
from app.models.pipelines import Pipeline
from app.models.users import User
from app.schemas.metric_imports import MetricImportPublic
from app.services.experiments import get_experiment_by_uuid

IMPORT_STORAGE_DIR = Path("/tmp/polibench_metric_imports")


def _sanitize_filename(filename: str) -> str:
    safe = "".join(ch for ch in filename if ch.isalnum() or ch in {"-", "_", "."})
    return safe or "metrics.csv"


async def _read_csv_content(file: UploadFile) -> tuple[str, bytes]:
    if file.filename is None:
        raise HTTPException(status_code=422, detail="Nome file CSV mancante")

    content = await file.read()
    if not content:
        raise HTTPException(status_code=422, detail="CSV vuoto")

    return _sanitize_filename(file.filename), content


async def _save_csv_file(filename: str, content: bytes) -> Path:
    IMPORT_STORAGE_DIR.mkdir(parents=True, exist_ok=True)
    storage_name = f"{uuid4()}_{filename}"
    path = IMPORT_STORAGE_DIR / storage_name
    path.write_bytes(content)
    return path


def _to_metric_import_public(
    job: MetricImportJob,
    experiment_uuid: UUID,
    uploaded_by_user_uuid: UUID | None = None,
) -> MetricImportPublic:
    return MetricImportPublic(
        uuid=job.uuid,
        experiment_uuid=experiment_uuid,
        uploaded_by_user_uuid=uploaded_by_user_uuid,
        status=job.status,
        csv_filename=job.csv_filename,
        error_message=job.error_message,
        created_at=job.created_at,
        started_at=job.started_at,
        finished_at=job.finished_at,
    )


async def create_metric_import_job(
    experiment_uuid: UUID,
    file: UploadFile,
    current_user: User,
) -> MetricImportPublic:
    experiment = await get_experiment_by_uuid(experiment_uuid)
    filename, content = await _read_csv_content(file)
    path = await _save_csv_file(filename, content)

    job = MetricImportJob(
        experiment_id=experiment.id,
        uploaded_by_user_id=current_user.id,
        status=ImportStatus.QUEUED,
        csv_filename=filename,
        csv_storage_path=str(path),
    )
    await job.create()
    return _to_metric_import_public(job, experiment.uuid, current_user.uuid)


async def get_metric_import_job_by_uuid(job_uuid: UUID) -> MetricImportJob:
    job = await MetricImportJob.find_one(MetricImportJob.uuid == job_uuid)
    if job is None:
        raise HTTPException(status_code=404, detail="MetricImportJob non trovato")
    return job


async def list_metric_import_jobs_for_experiment(
    experiment_uuid: UUID,
) -> list[MetricImportPublic]:
    experiment = await get_experiment_by_uuid(experiment_uuid)
    jobs = (
        await MetricImportJob.find(MetricImportJob.experiment_id == experiment.id)
        .sort([("created_at", -1)])
        .to_list()
    )

    uploader_ids = [job.uploaded_by_user_id for job in jobs if job.uploaded_by_user_id]
    uploader_uuid_by_id: dict[PydanticObjectId, UUID] = {}
    if uploader_ids:
        users = await User.find({"_id": {"$in": uploader_ids}}).to_list()
        uploader_uuid_by_id = {u.id: u.uuid for u in users}

    return [
        _to_metric_import_public(
            job,
            experiment.uuid,
            uploader_uuid_by_id.get(job.uploaded_by_user_id),
        )
        for job in jobs
    ]


def _parse_split(value: str | None) -> Split:
    if value is None or value.strip() == "":
        return Split.TEST
    norm = value.strip().lower()
    if norm == "validation":
        return Split.VALIDATION
    if norm == "test":
        return Split.TEST
    raise ValueError(f"split non valido: {value}")


def _parse_direction(value: str | None) -> Direction:
    if value is None or value.strip() == "":
        return Direction.MAX
    norm = value.strip().lower()
    if norm == "min":
        return Direction.MIN
    if norm == "max":
        return Direction.MAX
    raise ValueError(f"direction non valida: {value}")


def _parse_k(value: str | None) -> int | None:
    if value is None:
        return None
    stripped = value.strip()
    if stripped == "":
        return None
    return int(stripped)


async def process_metric_import_job(job_uuid: UUID) -> None:
    job = await MetricImportJob.find_one(MetricImportJob.uuid == job_uuid)
    if job is None:
        return

    try:
        job.status = ImportStatus.PROCESSING
        job.started_at = datetime.now(UTC)
        job.error_message = None
        await job.save()

        experiment = await Experiment.get(job.experiment_id)
        if experiment is None:
            raise ValueError("Experiment associato non trovato")

        from app.models.dataset_versions import DatasetVersion
        from app.models.datasets import Dataset

        dataset_version = await DatasetVersion.get(experiment.dataset_version_id)
        if dataset_version is None:
            raise ValueError("DatasetVersion associata non trovata")

        dataset = await Dataset.get(dataset_version.dataset_id)
        if dataset is None:
            raise ValueError("Dataset associato non trovato")
        pipeline = (
            await Pipeline.get(experiment.pipeline_id)
            if experiment.pipeline_id
            else None
        )
        if experiment.pipeline_id is not None and pipeline is None:
            raise ValueError("Pipeline associata non trovata")

        csv_content = Path(job.csv_storage_path).read_text(encoding="utf-8")
        reader = csv.DictReader(io.StringIO(csv_content))
        if reader.fieldnames is None:
            raise ValueError("CSV senza header")

        # Replace existing metrics to keep imports idempotent per experiment.
        await Metric.find(Metric.experiment_id == experiment.id).delete()

        metrics_to_insert: list[Metric] = []
        for row_idx, row in enumerate(reader, start=2):
            metric_name = (row.get("metric") or "").strip()
            raw_value = (row.get("value") or "").strip()

            if metric_name == "":
                raise ValueError(f"riga {row_idx}: campo metric mancante")
            if raw_value == "":
                raise ValueError(f"riga {row_idx}: campo value mancante")

            try:
                split = _parse_split(row.get("split"))
                direction = _parse_direction(row.get("direction"))
                k = _parse_k(row.get("k"))
                value = float(raw_value)
            except ValueError as exc:
                raise ValueError(f"riga {row_idx}: {exc}") from exc

            metrics_to_insert.append(
                Metric(
                    experiment_id=experiment.id,
                    dataset_id=dataset.id,
                    dataset_version_id=dataset_version.id,
                    pipeline_id=pipeline.id if pipeline else None,
                    model_id=experiment.model_id,
                    submitted_by_user_id=experiment.submitted_by_user_id,
                    team_id=experiment.team_id,
                    split=split,
                    metric=metric_name,
                    k=k,
                    value=value,
                    direction=direction,
                )
            )

        if metrics_to_insert:
            await Metric.insert_many(metrics_to_insert)

        job.status = ImportStatus.COMPLETED
        job.finished_at = datetime.now(UTC)
        await job.save()

    except Exception as exc:  # noqa: BLE001 - persist failure details
        job.status = ImportStatus.FAILED
        job.finished_at = datetime.now(UTC)
        job.error_message = str(exc)
        await job.save()
