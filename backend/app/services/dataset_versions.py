import re
from dataclasses import dataclass
from typing import Any
from uuid import UUID

from fastapi import HTTPException
from pymongo.errors import DuplicateKeyError

from app.models.dataset_versions import DatasetVersion
from app.models.datasets import Dataset
from app.models.resources import Resource
from app.models.sources import Source
from app.schemas.dataset_versions import (
    DatasetVersionCharacteristicsPreview,
    DatasetVersionCreate,
    DatasetVersionPreviewPublic,
    DatasetVersionPublic,
    DatasetVersionSummary,
    DatasetVersionYamlPublic,
    ResourcePublic,
    SourcePublic,
    SourceWithResourcesPublic,
)
from app.schemas.pipelines import PipelineCreate
from app.services.datasets import get_dataset_by_uuid
from app.services.pipelines import create_pipeline_for_version

try:
    import yaml
except ImportError:  # pragma: no cover - fallback unlikely in production
    yaml = None


@dataclass
class ParsedDatasetVersionPayload:
    dataset_yaml: dict[str, Any] | list[Any] | None
    version_yaml: dict[str, Any] | list[Any] | None
    pipeline_yaml: dict[str, Any] | list[Any] | None
    characteristics_yaml: dict[str, Any] | list[Any] | None
    parsed_sources: list[dict[str, Any]]
    parsed_resources: list[dict[str, Any]]
    pipeline_blocks: list[dict[str, Any]]
    characteristics: dict[str, int | float | None]
    recognized_dataset_name: str | None
    recognized_version: str | None


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


def _normalize_dataset_name(value: str) -> str:
    normalized = value.strip().lower()
    return re.sub(r"[^a-z0-9]+", "", normalized)


def _same_dataset_name(lhs: str, rhs: str) -> bool:
    return _normalize_dataset_name(lhs) == _normalize_dataset_name(rhs)


def _extract_string(
    payload: dict[str, Any],
    keys: tuple[str, ...],
) -> str | None:
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


def _extract_list_from_payload(
    payload: dict[str, Any],
    key: str,
) -> list[Any]:
    def _as_list(value: Any) -> list[Any]:
        if isinstance(value, list):
            return value
        if isinstance(value, dict):
            out: list[Any] = []
            for item_key, item_value in value.items():
                if isinstance(item_value, dict):
                    normalized = dict(item_value)
                    normalized.setdefault("name", str(item_key))
                    out.append(normalized)
                else:
                    out.append(item_value)
            return out
        return []

    direct = payload.get(key)
    direct_list = _as_list(direct)
    if direct_list:
        return direct_list

    for nested_key in ("version", "dataset_version", "registry", "spec"):
        nested = payload.get(nested_key)
        if not isinstance(nested, dict):
            continue
        candidate_list = _as_list(nested.get(key))
        if candidate_list:
            return candidate_list
    return []


def _as_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"1", "true", "yes", "y"}:
            return True
        if normalized in {"0", "false", "no", "n"}:
            return False
    if isinstance(value, (int, float)):
        return bool(value)
    return False


def _validate_dataset_yaml(
    dataset: Dataset,
    requested_version: str,
    dataset_yaml: dict[str, Any] | list[Any] | None,
) -> tuple[str | None, str | None]:
    if dataset_yaml is None:
        return None, None
    if not isinstance(dataset_yaml, dict):
        raise HTTPException(
            status_code=422,
            detail="dataset_yaml_raw deve rappresentare un oggetto YAML",
        )

    dataset_name = _extract_dataset_name(dataset_yaml)
    if dataset_name is not None and not _same_dataset_name(dataset_name, dataset.name):
        raise HTTPException(
            status_code=422,
            detail=(
                "dataset_yaml_raw non coerente: "
                "dataset_name/name="
                f"'{dataset_name}' non corrisponde al dataset '{dataset.name}'"
            ),
        )

    versions = dataset_yaml.get("versions")
    if versions is not None and isinstance(versions, list):
        normalized_versions = {str(v).strip() for v in versions if str(v).strip()}
        if normalized_versions and requested_version not in normalized_versions:
            raise HTTPException(
                status_code=422,
                detail=(
                    "dataset_yaml_raw non coerente: "
                    f"la versione '{requested_version}' non è presente in versions"
                ),
            )

    latest_version = dataset_yaml.get("latest_version")
    if isinstance(latest_version, str) and latest_version.strip():
        return dataset_name, latest_version.strip()
    return dataset_name, None


def _validate_version_yaml(
    dataset: Dataset,
    requested_version: str,
    version_yaml: dict[str, Any] | list[Any] | None,
) -> tuple[str | None, str | None]:
    if version_yaml is None:
        return None, None
    if not isinstance(version_yaml, dict):
        raise HTTPException(
            status_code=422,
            detail="version_yaml_raw deve rappresentare un oggetto YAML",
        )

    dataset_name = _extract_dataset_name(version_yaml)
    if dataset_name is not None and not _same_dataset_name(dataset_name, dataset.name):
        raise HTTPException(
            status_code=422,
            detail=(
                "version_yaml_raw non coerente: "
                "dataset_name/name="
                f"'{dataset_name}' non corrisponde al dataset '{dataset.name}'"
            ),
        )

    version_in_yaml = _extract_version(version_yaml)
    if version_in_yaml is not None and version_in_yaml != requested_version:
        raise HTTPException(
            status_code=422,
            detail=(
                "version_yaml_raw non coerente: "
                f"version='{version_in_yaml}' non corrisponde "
                f"alla versione richiesta '{requested_version}'"
            ),
        )

    return dataset_name, version_in_yaml


def _validate_characteristics_yaml(
    dataset: Dataset,
    requested_version: str,
    characteristics_yaml: dict[str, Any] | list[Any] | None,
) -> tuple[str | None, str | None]:
    if characteristics_yaml is None:
        return None, None
    if not isinstance(characteristics_yaml, dict):
        raise HTTPException(
            status_code=422,
            detail="characteristics_yaml_raw deve rappresentare un oggetto YAML",
        )

    dataset_name = _extract_dataset_name(characteristics_yaml)
    if dataset_name is not None and not _same_dataset_name(dataset_name, dataset.name):
        raise HTTPException(
            status_code=422,
            detail=(
                "characteristics_yaml_raw non coerente: "
                "dataset_name/name="
                f"'{dataset_name}' non corrisponde al dataset '{dataset.name}'"
            ),
        )

    version_in_yaml = _extract_version(characteristics_yaml)
    if version_in_yaml is not None and version_in_yaml != requested_version:
        raise HTTPException(
            status_code=422,
            detail=(
                "characteristics_yaml_raw non coerente: "
                f"version='{version_in_yaml}' non corrisponde "
                f"alla versione richiesta '{requested_version}'"
            ),
        )
    return dataset_name, version_in_yaml


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
        base = characteristics_yaml.get("metrics")
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
    version_yaml: dict[str, Any] | list[Any] | None,
) -> list[dict[str, Any]]:
    if not isinstance(version_yaml, dict):
        return []
    raw_sources = _extract_list_from_payload(version_yaml, "sources")

    out: list[dict[str, Any]] = []
    seen_names: set[str] = set()
    for source in raw_sources:
        if not isinstance(source, dict):
            continue

        source_name = str(source.get("name") or "source").strip()
        if source_name in seen_names:
            raise HTTPException(
                status_code=422,
                detail=f"source duplicata nel version YAML: '{source_name}'",
            )
        seen_names.add(source_name)

        args = source.get("args")
        if not isinstance(args, dict):
            args = {}

        downloadable = _as_bool(
            source.get("downloadable", args.get("downloadable", False))
        )
        url = source.get("url", args.get("url"))
        if downloadable and (not isinstance(url, str) or not url.strip()):
            raise HTTPException(
                status_code=422,
                detail=(
                    f"source '{source_name}': url obbligatorio quando downloadable=true"
                ),
            )

        checksum = source.get("checksum", args.get("checksum"))
        checksum_algorithm = source.get(
            "checksum_algorithm",
            args.get("checksum_algorithm"),
        )
        if checksum is not None and checksum_algorithm in (None, ""):
            raise HTTPException(
                status_code=422,
                detail=(
                    f"source '{source_name}': checksum_algorithm "
                    "obbligatorio quando è presente checksum"
                ),
            )

        inner_paths = source.get("inner_paths", args.get("inner_paths"))
        if not isinstance(inner_paths, dict):
            inner_paths = None
        out.append(
            {
                "name": source_name,
                "source_type": str(source.get("source_type") or "unknown"),
                "archive": source.get("archive", args.get("archive")),
                "downloadable": downloadable,
                "url": url.strip() if isinstance(url, str) else None,
                "checksum": checksum,
                "checksum_algorithm": checksum_algorithm,
                "filename": source.get("filename", args.get("filename")),
                "inner_paths": inner_paths,
            }
        )
    return out


def _parse_resources(
    version_yaml: dict[str, Any] | list[Any] | None,
) -> list[dict[str, Any]]:
    if not isinstance(version_yaml, dict):
        return []
    raw_resources = _extract_list_from_payload(version_yaml, "resources")

    out: list[dict[str, Any]] = []
    for resource in raw_resources:
        if not isinstance(resource, dict):
            continue
        schema_definition = resource.get("schema_definition")
        if schema_definition is None:
            schema_definition = resource.get("schema")
        if not isinstance(schema_definition, dict):
            schema_definition = None
        source_name = resource.get("source_name")
        if source_name is None:
            source_name = resource.get("source")
        if not isinstance(source_name, str):
            source_name = None
        out.append(
            {
                "source_name": source_name.strip() if source_name else None,
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


def _validate_resource_source_names(
    parsed_sources: list[dict[str, Any]],
    parsed_resources: list[dict[str, Any]],
) -> None:
    source_names = {str(source["name"]) for source in parsed_sources}
    for resource in parsed_resources:
        source_name = resource.get("source_name")
        if source_name is None:
            continue
        if source_name not in source_names:
            raise HTTPException(
                status_code=422,
                detail=(
                    "resource non valida: "
                    f"source_name='{source_name}' non presente nella lista sources"
                ),
            )


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


def _prepare_dataset_version_payload(
    dataset: Dataset,
    data: DatasetVersionCreate,
) -> ParsedDatasetVersionPayload:
    dataset_yaml = _parse_yaml(data.dataset_yaml_raw, "dataset_yaml_raw")
    version_yaml = _parse_yaml(data.version_yaml_raw, "version_yaml_raw")
    pipeline_yaml = _parse_yaml(data.pipeline_yaml_raw, "pipeline_yaml_raw")
    characteristics_yaml = _parse_yaml(
        data.characteristics_yaml_raw,
        "characteristics_yaml_raw",
    )

    dataset_name_from_dataset_yaml, version_from_dataset_yaml = _validate_dataset_yaml(
        dataset,
        data.version,
        dataset_yaml,
    )
    dataset_name_from_version_yaml, version_from_version_yaml = _validate_version_yaml(
        dataset,
        data.version,
        version_yaml,
    )
    dataset_name_from_characteristics_yaml, version_from_characteristics_yaml = (
        _validate_characteristics_yaml(
            dataset,
            data.version,
            characteristics_yaml,
        )
    )

    # New contract: sources/resources come from version YAML.
    # Backward compatibility: if version YAML is not provided, fallback to dataset YAML.
    source_of_truth_yaml = version_yaml if version_yaml is not None else dataset_yaml
    parsed_sources = _parse_sources(source_of_truth_yaml)
    parsed_resources = _parse_resources(source_of_truth_yaml)
    _validate_resource_source_names(parsed_sources, parsed_resources)

    return ParsedDatasetVersionPayload(
        dataset_yaml=dataset_yaml,
        version_yaml=version_yaml,
        pipeline_yaml=pipeline_yaml,
        characteristics_yaml=characteristics_yaml,
        parsed_sources=parsed_sources,
        parsed_resources=parsed_resources,
        pipeline_blocks=_normalize_pipeline_blocks(pipeline_yaml),
        characteristics=_extract_characteristics(characteristics_yaml),
        recognized_dataset_name=(
            dataset_name_from_version_yaml
            or dataset_name_from_dataset_yaml
            or dataset_name_from_characteristics_yaml
            or dataset.name
        ),
        recognized_version=(
            version_from_version_yaml
            or version_from_characteristics_yaml
            or version_from_dataset_yaml
            or data.version
        ),
    )


async def preview_dataset_version_payload(
    dataset_uuid: UUID,
    data: DatasetVersionCreate,
) -> DatasetVersionPreviewPublic:
    dataset = await get_dataset_by_uuid(dataset_uuid)
    parsed = _prepare_dataset_version_payload(dataset, data)

    return DatasetVersionPreviewPublic(
        dataset_uuid=dataset.uuid,
        requested_version=data.version,
        recognized_dataset_name=parsed.recognized_dataset_name,
        recognized_version=parsed.recognized_version,
        source_count=len(parsed.parsed_sources),
        resource_count=len(parsed.parsed_resources),
        pipeline_steps_count=len(parsed.pipeline_blocks),
        characteristics=DatasetVersionCharacteristicsPreview(**parsed.characteristics),
    )


async def create_dataset_version(
    dataset_uuid: UUID,
    data: DatasetVersionCreate,
) -> DatasetVersionPublic:
    dataset = await get_dataset_by_uuid(dataset_uuid)
    parsed = _prepare_dataset_version_payload(dataset, data)

    version = DatasetVersion(
        dataset_id=dataset.id,
        version=data.version,
        release_notes=data.release_notes,
        dataset_yaml_raw=data.dataset_yaml_raw,
        version_yaml_raw=data.version_yaml_raw,
        pipeline_yaml_raw=None,
        characteristics_yaml_raw=data.characteristics_yaml_raw,
        pipeline_blocks=None,
        n_users=parsed.characteristics["n_users"],
        n_items=parsed.characteristics["n_items"],
        n_interactions=parsed.characteristics["n_interactions"],
        density=parsed.characteristics["density"],
        gini_user=parsed.characteristics["gini_user"],
        gini_item=parsed.characteristics["gini_item"],
        status=data.status,
    )
    try:
        await version.create()
    except DuplicateKeyError as exc:
        raise HTTPException(
            status_code=409,
            detail="Versione dataset già esistente per questo dataset",
        ) from exc

    source_name_to_id: dict[str, Any] = {}
    for source_data in parsed.parsed_sources:
        source = Source(dataset_version_id=version.id, **source_data)
        await source.create()
        source_name_to_id[source.name] = source.id

    for resource_data in parsed.parsed_resources:
        source_name = resource_data.pop("source_name", None)
        source_id = source_name_to_id.get(str(source_name)) if source_name else None
        resource = Resource(
            dataset_version_id=version.id,
            source_id=source_id,
            **resource_data,
        )
        await resource.create()

    # Transitional compatibility: if pipeline YAML is provided during DatasetVersion
    # creation, create a first Pipeline entity and keep that as source of truth.
    if data.pipeline_yaml_raw is not None and data.pipeline_yaml_raw.strip() != "":
        await create_pipeline_for_version(
            version.uuid,
            PipelineCreate(
                yaml_raw=data.pipeline_yaml_raw,
                status=data.status.value,
            ),
        )

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


async def list_sources_with_resources_for_version(
    version_uuid: UUID,
) -> list[SourceWithResourcesPublic]:
    version = await get_dataset_version_by_uuid(version_uuid)
    sources = await Source.find(Source.dataset_version_id == version.id).to_list()
    resources = await Resource.find(Resource.dataset_version_id == version.id).to_list()
    resources_by_source_id: dict[Any, list[ResourcePublic]] = {}

    for resource in resources:
        if resource.source_id is None:
            continue
        resources_by_source_id.setdefault(resource.source_id, []).append(
            _to_resource_public(resource, version.uuid)
        )

    out: list[SourceWithResourcesPublic] = []
    for source in sources:
        source_public = _to_source_public(source, version.uuid)
        out.append(
            SourceWithResourcesPublic(
                **source_public.model_dump(),
                resources=resources_by_source_id.get(source.id, []),
            )
        )

    return out


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


async def get_yaml_for_version(version_uuid: UUID, kind: str) -> DatasetVersionYamlPublic:
    version = await get_dataset_version_by_uuid(version_uuid)
    normalized_kind = "characteristics" if kind == "metrics" else kind
    field_map = {
        "dataset": version.dataset_yaml_raw,
        "version": version.version_yaml_raw,
        "characteristics": version.characteristics_yaml_raw,
    }
    if normalized_kind not in field_map:
        raise HTTPException(status_code=404, detail="Tipo YAML non supportato")

    content = field_map[normalized_kind]
    if content is None:
        raise HTTPException(status_code=404, detail="YAML non disponibile")

    return DatasetVersionYamlPublic(
        dataset_version_uuid=version.uuid,
        kind=normalized_kind,
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
