from typing import Any
from uuid import UUID

from fastapi import HTTPException
from pymongo.errors import DuplicateKeyError

from app.models.dataset_versions import DatasetVersion
from app.models.datasets import Dataset
from app.models.resources import Resource
from app.models.sources import Source
from app.schemas.dataset_versions import (
    DatasetVersionCreate,
    DatasetVersionPipelinePublic,
    DatasetVersionPublic,
    DatasetVersionSummary,
    DatasetVersionYamlPublic,
    PipelineBlockPublic,
    ResourcePublic,
    SourcePublic,
)
from app.services.datasets import get_dataset_by_uuid

try:
    import yaml
except ImportError:  # pragma: no cover - fallback unlikely in production
    yaml = None


async def get_dataset_version_by_uuid(version_uuid: UUID) -> DatasetVersion:
    version = await DatasetVersion.find_one(DatasetVersion.uuid == version_uuid)
    if version is None:
        raise HTTPException(status_code=404, detail="DatasetVersion non trovata")
    return version


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
    except Exception as exc:  # noqa: BLE001 - we convert parser errors to HTTP
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


def _as_int(value: Any) -> int | None:
    if value is None:
        return None
    if isinstance(value, bool):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _as_float(value: Any) -> float | None:
    if value is None:
        return None
    if isinstance(value, bool):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _extract_characteristics(
    characteristics_yaml: dict[str, Any] | list[Any] | None,
) -> dict[str, int | float | None]:
    if not isinstance(characteristics_yaml, dict):
        return {
            "n_users": None,
            "n_items": None,
            "n_interactions": None,
            "density": None,
            "gini_user": None,
            "gini_item": None,
        }

    base = characteristics_yaml.get("characteristics")
    if not isinstance(base, dict):
        base = characteristics_yaml

    return {
        "n_users": _as_int(base.get("n_users")),
        "n_items": _as_int(base.get("n_items")),
        "n_interactions": _as_int(base.get("n_interactions")),
        "density": _as_float(base.get("density")),
        "gini_user": _as_float(base.get("gini_user")),
        "gini_item": _as_float(base.get("gini_item")),
    }


def _parse_sources(
    dataset_yaml: dict[str, Any] | list[Any] | None,
) -> list[dict[str, Any]]:
    if not isinstance(dataset_yaml, dict):
        return []
    raw_sources = dataset_yaml.get("sources")
    if not isinstance(raw_sources, list):
        return []

    out: list[dict[str, Any]] = []
    for source in raw_sources:
        if not isinstance(source, dict):
            continue
        inner_paths = source.get("inner_paths")
        if not isinstance(inner_paths, dict):
            inner_paths = None
        out.append(
            {
                "name": str(source.get("name") or "source"),
                "source_type": str(source.get("source_type") or "unknown"),
                "archive": source.get("archive"),
                "downloadable": bool(source.get("downloadable", False)),
                "url": source.get("url"),
                "checksum": source.get("checksum"),
                "checksum_algorithm": source.get("checksum_algorithm"),
                "filename": source.get("filename"),
                "inner_paths": inner_paths,
            }
        )
    return out


def _parse_resources(
    dataset_yaml: dict[str, Any] | list[Any] | None,
) -> list[dict[str, Any]]:
    if not isinstance(dataset_yaml, dict):
        return []
    raw_resources = dataset_yaml.get("resources")
    if not isinstance(raw_resources, list):
        return []

    out: list[dict[str, Any]] = []
    for resource in raw_resources:
        if not isinstance(resource, dict):
            continue
        schema_definition = resource.get("schema_definition")
        if schema_definition is None:
            schema_definition = resource.get("schema")
        if not isinstance(schema_definition, dict):
            schema_definition = None
        out.append(
            {
                "source_name": resource.get("source_name"),
                "name": str(resource.get("name") or "resource"),
                "filename": resource.get("filename"),
                "type": str(resource.get("type") or "unknown"),
                "format": resource.get("format"),
                "required": bool(resource.get("required", True)),
                "about": resource.get("about"),
                "schema_definition": schema_definition,
            }
        )
    return out


def _to_dataset_version_summary(
    dataset_uuid: UUID,
    version: DatasetVersion,
) -> DatasetVersionSummary:
    return DatasetVersionSummary(
        uuid=version.uuid,
        dataset_uuid=dataset_uuid,
        version=version.version,
        status=version.status,
        n_users=version.n_users,
        n_items=version.n_items,
        n_interactions=version.n_interactions,
        density=version.density,
        created_at=version.created_at,
    )


def _to_dataset_version_public(
    dataset_uuid: UUID,
    version: DatasetVersion,
) -> DatasetVersionPublic:
    return DatasetVersionPublic(
        uuid=version.uuid,
        dataset_uuid=dataset_uuid,
        version=version.version,
        release_notes=version.release_notes,
        status=version.status,
        pipeline_blocks=[
            PipelineBlockPublic(**block) for block in (version.pipeline_blocks or [])
        ],
        n_users=version.n_users,
        n_items=version.n_items,
        n_interactions=version.n_interactions,
        density=version.density,
        gini_user=version.gini_user,
        gini_item=version.gini_item,
        created_at=version.created_at,
    )


def _to_source_public(source: Source, version_uuid: UUID) -> SourcePublic:
    return SourcePublic(
        uuid=source.uuid,
        dataset_version_uuid=version_uuid,
        name=source.name,
        source_type=source.source_type,
        archive=source.archive,
        downloadable=source.downloadable,
        url=source.url,
        checksum=source.checksum,
        checksum_algorithm=source.checksum_algorithm,
        filename=source.filename,
        inner_paths=source.inner_paths,
        created_at=source.created_at,
    )


async def _source_uuid_by_id(dataset_version_id) -> dict:
    sources = await Source.find(Source.dataset_version_id == dataset_version_id).to_list()
    return {s.id: s.uuid for s in sources}


def _to_resource_public(
    resource: Resource,
    version_uuid: UUID,
    source_uuid: UUID | None = None,
) -> ResourcePublic:
    return ResourcePublic(
        uuid=resource.uuid,
        dataset_version_uuid=version_uuid,
        source_uuid=source_uuid,
        name=resource.name,
        filename=resource.filename,
        type=resource.type,
        format=resource.format,
        required=resource.required,
        about=resource.about,
        schema_definition=resource.schema_definition,
        created_at=resource.created_at,
    )


async def list_dataset_versions(dataset_uuid: UUID) -> list[DatasetVersionSummary]:
    dataset = await get_dataset_by_uuid(dataset_uuid)
    versions = (
        await DatasetVersion.find(DatasetVersion.dataset_id == dataset.id)
        .sort([("created_at", -1)])
        .to_list()
    )
    return [_to_dataset_version_summary(dataset.uuid, v) for v in versions]


async def create_dataset_version(
    dataset_uuid: UUID,
    data: DatasetVersionCreate,
) -> DatasetVersionPublic:
    dataset = await get_dataset_by_uuid(dataset_uuid)

    dataset_yaml = _parse_yaml(data.dataset_yaml_raw, "dataset_yaml_raw")
    pipeline_yaml = _parse_yaml(data.pipeline_yaml_raw, "pipeline_yaml_raw")
    characteristics_yaml = _parse_yaml(
        data.characteristics_yaml_raw,
        "characteristics_yaml_raw",
    )
    pipeline_blocks = _normalize_pipeline_blocks(pipeline_yaml)
    characteristics = _extract_characteristics(characteristics_yaml)

    version = DatasetVersion(
        dataset_id=dataset.id,
        version=data.version,
        release_notes=data.release_notes,
        dataset_yaml_raw=data.dataset_yaml_raw,
        pipeline_yaml_raw=data.pipeline_yaml_raw,
        characteristics_yaml_raw=data.characteristics_yaml_raw,
        pipeline_blocks=pipeline_blocks,
        n_users=characteristics["n_users"],
        n_items=characteristics["n_items"],
        n_interactions=characteristics["n_interactions"],
        density=characteristics["density"],
        gini_user=characteristics["gini_user"],
        gini_item=characteristics["gini_item"],
        status=data.status,
    )
    try:
        await version.create()
    except DuplicateKeyError as exc:
        raise HTTPException(
            status_code=409,
            detail="Versione dataset già esistente per questo dataset",
        ) from exc

    # Parse and materialize sources/resources from dataset YAML.
    parsed_sources = _parse_sources(dataset_yaml)
    source_name_to_id: dict[str, Any] = {}
    for source_data in parsed_sources:
        source = Source(dataset_version_id=version.id, **source_data)
        await source.create()
        source_name_to_id[source.name] = source.id

    parsed_resources = _parse_resources(dataset_yaml)
    for resource_data in parsed_resources:
        source_name = resource_data.pop("source_name", None)
        source_id = source_name_to_id.get(str(source_name)) if source_name else None
        resource = Resource(
            dataset_version_id=version.id,
            source_id=source_id,
            **resource_data,
        )
        await resource.create()

    return _to_dataset_version_public(dataset.uuid, version)


async def get_dataset_version_public(version_uuid: UUID) -> DatasetVersionPublic:
    version = await get_dataset_version_by_uuid(version_uuid)
    dataset = await Dataset.get(version.dataset_id)
    if dataset is None:
        raise HTTPException(status_code=404, detail="Dataset collegato non trovato")
    return _to_dataset_version_public(dataset.uuid, version)


async def list_sources_for_version(version_uuid: UUID) -> list[SourcePublic]:
    version = await get_dataset_version_by_uuid(version_uuid)
    sources = await Source.find(Source.dataset_version_id == version.id).to_list()
    return [_to_source_public(s, version.uuid) for s in sources]


async def list_resources_for_version(version_uuid: UUID) -> list[ResourcePublic]:
    version = await get_dataset_version_by_uuid(version_uuid)
    resources = await Resource.find(Resource.dataset_version_id == version.id).to_list()
    source_uuid_map = await _source_uuid_by_id(version.id)
    return [
        _to_resource_public(
            r,
            version.uuid,
            source_uuid_map.get(r.source_id) if r.source_id else None,
        )
        for r in resources
    ]


async def get_pipeline_for_version(version_uuid: UUID) -> DatasetVersionPipelinePublic:
    version = await get_dataset_version_by_uuid(version_uuid)
    return DatasetVersionPipelinePublic(
        dataset_version_uuid=version.uuid,
        blocks=[
            PipelineBlockPublic(**block) for block in (version.pipeline_blocks or [])
        ],
    )


async def get_yaml_for_version(version_uuid: UUID, kind: str) -> DatasetVersionYamlPublic:
    version = await get_dataset_version_by_uuid(version_uuid)
    field_map = {
        "dataset": version.dataset_yaml_raw,
        "pipeline": version.pipeline_yaml_raw,
        "characteristics": version.characteristics_yaml_raw,
    }
    if kind not in field_map:
        raise HTTPException(status_code=404, detail="Tipo YAML non supportato")

    content = field_map[kind]
    if content is None:
        raise HTTPException(status_code=404, detail="YAML non disponibile")

    return DatasetVersionYamlPublic(
        dataset_version_uuid=version.uuid,
        kind=kind,
        content=content,
    )


async def get_latest_dataset_version(dataset_uuid: UUID) -> DatasetVersion:
    dataset = await get_dataset_by_uuid(dataset_uuid)
    latest = (
        await DatasetVersion.find(DatasetVersion.dataset_id == dataset.id)
        .sort([("created_at", -1)])
        .first_or_none()
    )
    if latest is None:
        raise HTTPException(
            status_code=400,
            detail="Il dataset non ha versioni. Crea prima una DatasetVersion.",
        )
    return latest


async def get_dataset_version_and_dataset(
    dataset_version_uuid: UUID,
) -> tuple[DatasetVersion, Dataset]:
    version = await get_dataset_version_by_uuid(dataset_version_uuid)
    dataset = await Dataset.get(version.dataset_id)
    if dataset is None:
        raise HTTPException(status_code=404, detail="Dataset collegato non trovato")
    return version, dataset
