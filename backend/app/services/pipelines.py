from typing import Any
from uuid import UUID

from fastapi import HTTPException
from pymongo.errors import DuplicateKeyError

from app.models.dataset_versions import DatasetVersion
from app.models.datasets import Dataset
from app.models.experiments import Experiment
from app.models.ml_models import MLModel
from app.models.pipelines import Pipeline
from app.schemas.experiments import ExperimentSummary
from app.schemas.pipelines import (
    PipelineBlockPublic,
    PipelineCreate,
    PipelinePreviewPublic,
    PipelinePublic,
    PipelineSummary,
    PipelineYamlPublic,
)

try:
    import yaml
except ImportError:  # pragma: no cover - fallback unlikely in production
    yaml = None


def _parse_yaml(raw: str | None, field_name: str) -> dict[str, Any] | list[Any] | None:
    if raw is None or raw.strip() == "":
        return None
    if yaml is None:
        raise HTTPException(
            status_code=500,
            detail="Dipendenza PyYAML mancante: impossibile parsare file YAML",
        )
    try:
        parsed = yaml.safe_load(raw)
    except Exception as exc:  # noqa: BLE001 - convert parser errors to HTTP
        raise HTTPException(
            status_code=422,
            detail=f"YAML non valido in {field_name}: {exc}",
        ) from exc
    if parsed is None:
        return None
    if not isinstance(parsed, (dict, list)):
        raise HTTPException(
            status_code=422,
            detail=f"Formato non valido per {field_name}: atteso dict o list",
        )
    return parsed


def _normalize_dataset_name(value: str) -> str:
    return value.strip().lower()


def _same_dataset_name(lhs: str, rhs: str) -> bool:
    return _normalize_dataset_name(lhs) == _normalize_dataset_name(rhs)


def _extract_string(payload: dict[str, Any], keys: tuple[str, ...]) -> str | None:
    for key in keys:
        value = payload.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def _extract_dataset_name(payload: dict[str, Any] | list[Any] | None) -> str | None:
    if not isinstance(payload, dict):
        return None
    direct = _extract_string(payload, ("dataset_name", "name", "dataset"))
    if direct is not None:
        return direct
    for nested_key in ("dataset", "metadata", "info"):
        nested = payload.get(nested_key)
        if not isinstance(nested, dict):
            continue
        nested_name = _extract_string(nested, ("dataset_name", "name"))
        if nested_name is not None:
            return nested_name
    return None


def _extract_version(payload: dict[str, Any] | list[Any] | None) -> str | None:
    if not isinstance(payload, dict):
        return None
    direct = _extract_string(payload, ("version", "dataset_version"))
    if direct is not None:
        return direct
    for nested_key in ("dataset", "metadata", "info"):
        nested = payload.get(nested_key)
        if not isinstance(nested, dict):
            continue
        nested_version = _extract_string(nested, ("version", "dataset_version"))
        if nested_version is not None:
            return nested_version
    return None


def _normalize_pipeline_blocks(
    pipeline_yaml: dict[str, Any] | list[Any] | None,
) -> list[dict[str, Any]]:
    if pipeline_yaml is None:
        return []

    if isinstance(pipeline_yaml, list):
        steps = pipeline_yaml
    elif isinstance(pipeline_yaml, dict):
        steps = pipeline_yaml.get("pipeline") or pipeline_yaml.get("steps") or []
    else:
        steps = []

    blocks: list[dict[str, Any]] = []
    if not isinstance(steps, list):
        return blocks

    for idx, step in enumerate(steps):
        if not isinstance(step, dict):
            continue
        name = step.get("name") or f"step-{idx + 1}"
        operation = step.get("operation") or step.get("op") or ""
        params = step.get("params")
        if not isinstance(params, dict):
            params = {}
        blocks.append(
            {
                "name": str(name),
                "operation": str(operation),
                "params": params,
            }
        )
    return blocks


async def _get_dataset_version_and_dataset(
    dataset_version_uuid: UUID,
) -> tuple[DatasetVersion, Dataset]:
    version = await DatasetVersion.find_one(DatasetVersion.uuid == dataset_version_uuid)
    if version is None:
        raise HTTPException(status_code=404, detail="DatasetVersion non trovata")
    dataset = await Dataset.get(version.dataset_id)
    if dataset is None:
        raise HTTPException(status_code=404, detail="Dataset collegato non trovato")
    return version, dataset


def _to_pipeline_public(
    pipeline: Pipeline,
    dataset_version_uuid: UUID,
) -> PipelinePublic:
    return PipelinePublic(
        uuid=pipeline.uuid,
        dataset_version_uuid=dataset_version_uuid,
        code=pipeline.code,
        status=pipeline.status,
        blocks=[PipelineBlockPublic(**block) for block in (pipeline.blocks or [])],
        created_at=pipeline.created_at,
    )


def _to_pipeline_summary(
    pipeline: Pipeline,
    dataset_version_uuid: UUID,
) -> PipelineSummary:
    return PipelineSummary(
        uuid=pipeline.uuid,
        dataset_version_uuid=dataset_version_uuid,
        code=pipeline.code,
        status=pipeline.status,
        steps_count=len(pipeline.blocks or []),
        created_at=pipeline.created_at,
    )


def _extract_numeric_code_suffix(code: str) -> int | None:
    code = code.strip().upper()
    if not code.startswith("P"):
        return None
    suffix = code[1:]
    if not suffix.isdigit():
        return None
    return int(suffix)


async def _generate_next_pipeline_code(dataset_version_id) -> str:
    pipelines = await Pipeline.find(
        Pipeline.dataset_version_id == dataset_version_id
    ).to_list()
    max_suffix = 0
    for pipeline in pipelines:
        parsed = _extract_numeric_code_suffix(pipeline.code)
        if parsed is not None:
            max_suffix = max(max_suffix, parsed)
    return f"P{max_suffix + 1:03d}"


def _normalize_pipeline_code(code: str | None) -> str | None:
    if code is None:
        return None
    normalized = code.strip().upper()
    if normalized == "":
        return None
    return normalized


def _validate_pipeline_yaml_consistency(
    dataset: Dataset,
    dataset_version: DatasetVersion,
    pipeline_yaml: dict[str, Any] | list[Any] | None,
) -> tuple[str | None, str | None]:
    dataset_name = _extract_dataset_name(pipeline_yaml)
    if dataset_name is not None and not _same_dataset_name(dataset_name, dataset.name):
        raise HTTPException(
            status_code=422,
            detail=(
                "pipeline yaml non coerente: dataset_name/name="
                f"'{dataset_name}' non corrisponde al dataset '{dataset.name}'"
            ),
        )

    version_in_yaml = _extract_version(pipeline_yaml)
    if (
        version_in_yaml is not None
        and version_in_yaml.strip() != ""
        and version_in_yaml != dataset_version.version
    ):
        raise HTTPException(
            status_code=422,
            detail=(
                "pipeline yaml non coerente: "
                f"version='{version_in_yaml}' non corrisponde "
                f"alla versione target '{dataset_version.version}'"
            ),
        )
    return dataset_name, version_in_yaml


async def create_pipeline_for_version(
    dataset_version_uuid: UUID,
    data: PipelineCreate,
) -> PipelinePublic:
    dataset_version, dataset = await _get_dataset_version_and_dataset(
        dataset_version_uuid
    )
    pipeline_yaml = _parse_yaml(data.yaml_raw, "pipeline_yaml_raw")
    _validate_pipeline_yaml_consistency(dataset, dataset_version, pipeline_yaml)
    blocks = _normalize_pipeline_blocks(pipeline_yaml)
    pipeline_code = _normalize_pipeline_code(data.code)
    if pipeline_code is None:
        pipeline_code = await _generate_next_pipeline_code(dataset_version.id)

    pipeline = Pipeline(
        dataset_version_id=dataset_version.id,
        code=pipeline_code,
        yaml_raw=data.yaml_raw,
        blocks=blocks,
        status=data.status,
    )
    try:
        await pipeline.create()
    except DuplicateKeyError as exc:
        raise HTTPException(
            status_code=409,
            detail="Pipeline code già esistente per questa DatasetVersion",
        ) from exc

    return _to_pipeline_public(pipeline, dataset_version.uuid)


async def preview_pipeline_payload(
    dataset_version_uuid: UUID,
    data: PipelineCreate,
) -> PipelinePreviewPublic:
    dataset_version, dataset = await _get_dataset_version_and_dataset(
        dataset_version_uuid
    )
    pipeline_yaml = _parse_yaml(data.yaml_raw, "pipeline_yaml_raw")
    recognized_dataset_name, recognized_version = _validate_pipeline_yaml_consistency(
        dataset,
        dataset_version,
        pipeline_yaml,
    )
    blocks = _normalize_pipeline_blocks(pipeline_yaml)

    return PipelinePreviewPublic(
        dataset_version_uuid=dataset_version.uuid,
        requested_code=_normalize_pipeline_code(data.code),
        recognized_dataset_name=recognized_dataset_name or dataset.name,
        recognized_version=recognized_version or dataset_version.version,
        pipeline_steps_count=len(blocks),
    )


async def list_pipelines_for_version(
    dataset_version_uuid: UUID,
) -> list[PipelineSummary]:
    dataset_version, _ = await _get_dataset_version_and_dataset(dataset_version_uuid)
    pipelines = (
        await Pipeline.find(Pipeline.dataset_version_id == dataset_version.id)
        .sort([("created_at", -1)])
        .to_list()
    )
    return [_to_pipeline_summary(p, dataset_version.uuid) for p in pipelines]


async def get_pipeline_by_uuid(pipeline_uuid: UUID) -> Pipeline:
    pipeline = await Pipeline.find_one(Pipeline.uuid == pipeline_uuid)
    if pipeline is None:
        raise HTTPException(status_code=404, detail="Pipeline non trovata")
    return pipeline


async def get_pipeline_public(pipeline_uuid: UUID) -> PipelinePublic:
    pipeline = await get_pipeline_by_uuid(pipeline_uuid)
    dataset_version = await DatasetVersion.get(pipeline.dataset_version_id)
    if dataset_version is None:
        raise HTTPException(
            status_code=404,
            detail="DatasetVersion della pipeline non trovata",
        )
    return _to_pipeline_public(pipeline, dataset_version.uuid)


async def get_pipeline_yaml(pipeline_uuid: UUID) -> PipelineYamlPublic:
    pipeline = await get_pipeline_by_uuid(pipeline_uuid)
    if pipeline.yaml_raw is None:
        raise HTTPException(status_code=404, detail="YAML pipeline non disponibile")
    return PipelineYamlPublic(pipeline_uuid=pipeline.uuid, content=pipeline.yaml_raw)


async def list_experiments_for_pipeline(
    pipeline_uuid: UUID,
) -> list[ExperimentSummary]:
    pipeline = await get_pipeline_by_uuid(pipeline_uuid)
    dataset_version = await DatasetVersion.get(pipeline.dataset_version_id)
    if dataset_version is None:
        raise HTTPException(
            status_code=404,
            detail="DatasetVersion della pipeline non trovata",
        )
    dataset = await Dataset.get(dataset_version.dataset_id)
    if dataset is None:
        raise HTTPException(status_code=404, detail="Dataset della pipeline non trovato")

    experiments = (
        await Experiment.find(Experiment.pipeline_id == pipeline.id)
        .sort([("created_at", -1)])
        .to_list()
    )
    if not experiments:
        return []

    model_ids = list({e.model_id for e in experiments})
    models = await MLModel.find({"_id": {"$in": model_ids}}).to_list()
    model_by_id = {m.id: m for m in models}

    out: list[ExperimentSummary] = []
    for exp in experiments:
        model = model_by_id.get(exp.model_id)
        if model is None:
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


async def get_latest_pipeline_for_dataset_version(
    dataset_version_uuid: UUID,
) -> Pipeline:
    dataset_version, _ = await _get_dataset_version_and_dataset(dataset_version_uuid)
    pipeline = (
        await Pipeline.find(Pipeline.dataset_version_id == dataset_version.id)
        .sort([("created_at", -1)])
        .first_or_none()
    )
    if pipeline is None:
        raise HTTPException(
            status_code=400,
            detail="La DatasetVersion non ha pipeline. Crea prima una Pipeline.",
        )
    return pipeline
