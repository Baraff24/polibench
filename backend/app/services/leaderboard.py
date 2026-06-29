from collections import defaultdict
from math import sqrt
from typing import Any
from uuid import UUID

import pymongo
from fastapi import HTTPException

from app.models.metrics import Direction, Metric, Split
from app.schemas.metrics import (
    BestConfigurationGroup,
    BestConfigurationQuery,
    BestConfigurationResponse,
    LeaderboardEntry,
    LeaderboardQuery,
    MultiMetricLeaderboardEntry,
)
from app.services.datasets import get_dataset_by_uuid


def _user_display_name(
    first_name: str | None,
    last_name: str | None,
    email: str | None,
) -> str | None:
    full_name = " ".join([part for part in [first_name, last_name] if part]).strip()
    if full_name:
        return full_name
    return email


def _matches_hyperparam_filters(
    training_config: dict[str, Any] | None,
    filters: dict[str, Any] | None,
) -> bool:
    if not filters:
        return True
    if training_config is None:
        return False

    for key, expected in filters.items():
        if key not in training_config:
            return False
        actual = training_config[key]

        if isinstance(actual, (int, float)) and isinstance(expected, (int, float)):
            if float(actual) != float(expected):
                return False
            continue

        if str(actual) != str(expected):
            return False

    return True


async def _resolve_dataset_version_id(
    dataset_uuid: UUID,
    dataset_version_uuid: UUID | None,
):
    if dataset_version_uuid is None:
        return None

    from app.models.dataset_versions import DatasetVersion

    dataset = await get_dataset_by_uuid(dataset_uuid)
    version = await DatasetVersion.find_one(DatasetVersion.uuid == dataset_version_uuid)
    if version is None:
        raise HTTPException(status_code=404, detail="DatasetVersion non trovata")
    if version.dataset_id != dataset.id:
        raise HTTPException(
            status_code=400,
            detail="DatasetVersion non appartiene al dataset specificato",
        )
    return version.id


async def _resolve_pipeline_id(
    dataset_uuid: UUID,
    dataset_version_uuid: UUID | None,
    pipeline_uuid: UUID | None,
):
    if pipeline_uuid is None:
        return None

    from app.models.dataset_versions import DatasetVersion
    from app.models.pipelines import Pipeline

    dataset = await get_dataset_by_uuid(dataset_uuid)
    pipeline = await Pipeline.find_one(Pipeline.uuid == pipeline_uuid)
    if pipeline is None:
        raise HTTPException(status_code=404, detail="Pipeline non trovata")

    version = await DatasetVersion.get(pipeline.dataset_version_id)
    if version is None:
        raise HTTPException(
            status_code=404,
            detail="DatasetVersion della pipeline non trovata",
        )

    if version.dataset_id != dataset.id:
        raise HTTPException(
            status_code=400,
            detail="Pipeline non appartiene al dataset specificato",
        )

    if dataset_version_uuid is not None and version.uuid != dataset_version_uuid:
        raise HTTPException(
            status_code=400,
            detail="Pipeline non appartiene alla dataset_version specificata",
        )

    return pipeline.id


async def _resolve_model_ids(model_uuids: list[UUID] | None):
    if model_uuids is None:
        return None

    from app.models.ml_models import MLModel

    models = await MLModel.find({"uuid": {"$in": model_uuids}}).to_list()
    return {m.id for m in models}


async def _resolve_author_ids(author_uuids: list[UUID] | None):
    if author_uuids is None:
        return None

    from app.models.users import User

    users = await User.find({"uuid": {"$in": author_uuids}}).to_list()
    return {u.id for u in users}


async def get_leaderboard(
    dataset_uuid: UUID,
    metric: str,
    split: Split,
    top_n: int = 10,
    dataset_version_uuid: UUID | None = None,
    pipeline_uuid: UUID | None = None,
    model_uuids: list[UUID] | None = None,
    author_uuids: list[UUID] | None = None,
    hyperparam_filters: dict[str, Any] | None = None,
) -> list[LeaderboardEntry]:
    from app.models.dataset_versions import DatasetVersion
    from app.models.experiments import Experiment
    from app.models.ml_models import MLModel
    from app.models.pipelines import Pipeline
    from app.models.users import User

    dataset = await get_dataset_by_uuid(dataset_uuid)
    dataset_version_id = await _resolve_dataset_version_id(
        dataset_uuid,
        dataset_version_uuid,
    )
    pipeline_id = await _resolve_pipeline_id(
        dataset_uuid,
        dataset_version_uuid,
        pipeline_uuid,
    )

    model_ids = await _resolve_model_ids(model_uuids)
    author_ids = await _resolve_author_ids(author_uuids)

    if model_uuids is not None and model_ids is not None and len(model_ids) == 0:
        return []
    if author_uuids is not None and author_ids is not None and len(author_ids) == 0:
        return []

    filters = [
        Metric.dataset_id == dataset.id,
        Metric.metric == metric,
        Metric.split == split,
    ]
    if dataset_version_id is not None:
        filters.append(Metric.dataset_version_id == dataset_version_id)
    if pipeline_id is not None:
        filters.append(Metric.pipeline_id == pipeline_id)
    if model_ids is not None:
        filters.append({"model_id": {"$in": list(model_ids)}})
    if author_ids is not None:
        filters.append({"submitted_by_user_id": {"$in": list(author_ids)}})

    sample_row = await Metric.find(*filters).limit(1).to_list()
    if not sample_row:
        return []

    sort_direction = (
        pymongo.DESCENDING
        if sample_row[0].direction.value == "max"
        else pymongo.ASCENDING
    )

    query = Metric.find(*filters).sort([("value", sort_direction)])
    if not hyperparam_filters:
        query = query.limit(top_n)
    rows = await query.to_list()
    if not rows:
        return []

    model_ids_from_rows = list({r.model_id for r in rows})
    models = await MLModel.find({"_id": {"$in": model_ids_from_rows}}).to_list()
    model_name_by_id = {m.id: m.name for m in models}
    model_uuid_by_id = {m.id: m.uuid for m in models}

    exp_ids = list({r.experiment_id for r in rows})
    experiments = await Experiment.find({"_id": {"$in": exp_ids}}).to_list()
    exp_by_id = {e.id: e for e in experiments}

    version_ids = list({r.dataset_version_id for r in rows})
    versions = await DatasetVersion.find({"_id": {"$in": version_ids}}).to_list()
    version_uuid_by_id = {v.id: v.uuid for v in versions}

    pipeline_ids = list({r.pipeline_id for r in rows if r.pipeline_id is not None})
    pipelines = await Pipeline.find({"_id": {"$in": pipeline_ids}}).to_list()
    pipeline_uuid_by_id = {p.id: p.uuid for p in pipelines}
    pipeline_code_by_id = {p.id: p.code for p in pipelines}

    submitted_user_ids = list(
        {
            e.submitted_by_user_id
            for e in experiments
            if e.submitted_by_user_id is not None
        }
    )
    users = await User.find({"_id": {"$in": submitted_user_ids}}).to_list()
    user_by_id = {u.id: u for u in users}

    candidates: list[tuple[Metric, Experiment]] = []
    for row in rows:
        exp = exp_by_id.get(row.experiment_id)
        if exp is None:
            continue
        if not _matches_hyperparam_filters(exp.training_config, hyperparam_filters):
            continue
        candidates.append((row, exp))

    if not candidates:
        return []

    candidates = candidates[:top_n]

    entries: list[LeaderboardEntry] = []
    for rank, (row, exp) in enumerate(candidates, start=1):
        submitter = user_by_id.get(exp.submitted_by_user_id)
        model_uuid = model_uuid_by_id.get(row.model_id)
        if model_uuid is None:
            continue

        entries.append(
            LeaderboardEntry(
                experiment_uuid=exp.uuid,
                model_uuid=model_uuid,
                model_name=model_name_by_id.get(row.model_id),
                dataset_uuid=dataset.uuid,
                dataset_version_uuid=version_uuid_by_id[row.dataset_version_id],
                pipeline_uuid=(
                    pipeline_uuid_by_id.get(row.pipeline_id)
                    if row.pipeline_id is not None
                    else None
                ),
                pipeline_code=(
                    pipeline_code_by_id.get(row.pipeline_id)
                    if row.pipeline_id is not None
                    else None
                ),
                submitted_by_user_uuid=submitter.uuid if submitter else None,
                submitted_by_display_name=(
                    _user_display_name(
                        submitter.first_name if submitter else None,
                        submitter.last_name if submitter else None,
                        submitter.email if submitter else None,
                    )
                ),
                submitted_by_email=submitter.email if submitter else None,
                training_config=exp.training_config,
                status=exp.status.value,
                run_name=exp.run_name,
                seed=exp.seed,
                created_at=exp.created_at,
                split=row.split,
                metric=row.metric,
                k=row.k,
                value=row.value,
                direction=row.direction,
                rank=rank,
            )
        )

    return entries


async def get_multi_metric_leaderboard(
    dataset_uuid: UUID,
    metrics_list: list[str],
    split: Split,
    sort_by: str,
    top_n: int = 20,
    dataset_version_uuid: UUID | None = None,
    pipeline_uuid: UUID | None = None,
    model_uuids: list[UUID] | None = None,
    author_uuids: list[UUID] | None = None,
    hyperparam_filters: dict[str, Any] | None = None,
) -> list[MultiMetricLeaderboardEntry]:
    from app.models.dataset_versions import DatasetVersion
    from app.models.experiments import Experiment
    from app.models.ml_models import MLModel
    from app.models.pipelines import Pipeline
    from app.models.users import User

    dataset = await get_dataset_by_uuid(dataset_uuid)
    dataset_version_id = await _resolve_dataset_version_id(
        dataset_uuid,
        dataset_version_uuid,
    )
    pipeline_id = await _resolve_pipeline_id(
        dataset_uuid,
        dataset_version_uuid,
        pipeline_uuid,
    )

    model_ids = await _resolve_model_ids(model_uuids)
    author_ids = await _resolve_author_ids(author_uuids)

    if model_uuids is not None and model_ids is not None and len(model_ids) == 0:
        return []
    if author_uuids is not None and author_ids is not None and len(author_ids) == 0:
        return []

    filters = [
        Metric.dataset_id == dataset.id,
        Metric.split == split,
        {"metric": {"$in": metrics_list}},
    ]
    if dataset_version_id is not None:
        filters.append(Metric.dataset_version_id == dataset_version_id)
    if pipeline_id is not None:
        filters.append(Metric.pipeline_id == pipeline_id)
    if model_ids is not None:
        filters.append({"model_id": {"$in": list(model_ids)}})
    if author_ids is not None:
        filters.append({"submitted_by_user_id": {"$in": list(author_ids)}})

    rows = await Metric.find(*filters).to_list()
    if not rows:
        return []

    by_exp: dict = defaultdict(dict)
    for row in rows:
        by_exp[row.experiment_id][row.metric] = row

    exp_ids = list(by_exp.keys())
    experiments = await Experiment.find({"_id": {"$in": exp_ids}}).to_list()
    exp_by_id = {e.id: e for e in experiments}

    sort_direction = "max"
    for row in rows:
        if row.metric == sort_by:
            sort_direction = row.direction.value
            break

    aggregated = []
    for exp_id, metric_map in by_exp.items():
        exp = exp_by_id.get(exp_id)
        if exp is None:
            continue
        if not _matches_hyperparam_filters(exp.training_config, hyperparam_filters):
            continue

        sort_val = metric_map.get(sort_by)
        if sort_val is None:
            continue
        aggregated.append((exp_id, metric_map, sort_val.value))

    reverse = sort_direction == "max"
    aggregated.sort(key=lambda x: x[2], reverse=reverse)
    aggregated = aggregated[:top_n]
    if not aggregated:
        return []

    target_exp_ids = list({a[0] for a in aggregated})
    experiments = await Experiment.find({"_id": {"$in": target_exp_ids}}).to_list()
    exp_by_id = {e.id: e for e in experiments}

    model_ids = list(
        {e.model_id for e in experiments if e.id in {a[0] for a in aggregated}}
    )
    models = await MLModel.find({"_id": {"$in": model_ids}}).to_list()
    model_name_by_id = {m.id: m.name for m in models}
    model_uuid_by_id = {m.id: m.uuid for m in models}

    submitted_user_ids = list(
        {
            e.submitted_by_user_id
            for e in experiments
            if e.submitted_by_user_id is not None
        }
    )
    users = await User.find({"_id": {"$in": submitted_user_ids}}).to_list()
    user_by_id = {u.id: u for u in users}

    version_ids = list(
        {
            metric_row.dataset_version_id
            for _, metric_map, _ in aggregated
            for metric_row in metric_map.values()
        }
    )
    versions = await DatasetVersion.find({"_id": {"$in": version_ids}}).to_list()
    version_uuid_by_id = {v.id: v.uuid for v in versions}

    pipeline_ids = list(
        {
            metric_row.pipeline_id
            for _, metric_map, _ in aggregated
            for metric_row in metric_map.values()
            if metric_row.pipeline_id is not None
        }
    )
    pipelines = await Pipeline.find({"_id": {"$in": pipeline_ids}}).to_list()
    pipeline_uuid_by_id = {p.id: p.uuid for p in pipelines}
    pipeline_code_by_id = {p.id: p.code for p in pipelines}

    result: list[MultiMetricLeaderboardEntry] = []
    for rank, (exp_id, metric_map, _) in enumerate(aggregated, start=1):
        exp = exp_by_id.get(exp_id)
        if exp is None:
            continue

        metrics_dict = {}
        directions_dict = {}
        row_dataset_version_uuid = None
        row_pipeline_uuid = None
        row_pipeline_code = None
        for metric_name in metrics_list:
            m = metric_map.get(metric_name)
            if m is not None:
                metrics_dict[metric_name] = m.value
                directions_dict[metric_name] = m.direction
                if row_dataset_version_uuid is None:
                    row_dataset_version_uuid = version_uuid_by_id.get(
                        m.dataset_version_id
                    )
                if row_pipeline_uuid is None and m.pipeline_id is not None:
                    row_pipeline_uuid = pipeline_uuid_by_id.get(m.pipeline_id)
                    row_pipeline_code = pipeline_code_by_id.get(m.pipeline_id)

        if row_dataset_version_uuid is None:
            continue

        submitter = user_by_id.get(exp.submitted_by_user_id)
        repo_url = exp.code.repo_url if exp.code else None
        model_uuid = model_uuid_by_id.get(exp.model_id)
        if model_uuid is None:
            continue

        result.append(
            MultiMetricLeaderboardEntry(
                experiment_uuid=exp.uuid,
                model_uuid=model_uuid,
                model_name=model_name_by_id.get(exp.model_id),
                dataset_uuid=dataset.uuid,
                dataset_version_uuid=row_dataset_version_uuid,
                pipeline_uuid=row_pipeline_uuid,
                pipeline_code=row_pipeline_code,
                submitted_by_user_uuid=submitter.uuid if submitter else None,
                submitted_by_display_name=(
                    _user_display_name(
                        submitter.first_name if submitter else None,
                        submitter.last_name if submitter else None,
                        submitter.email if submitter else None,
                    )
                ),
                submitted_by_email=submitter.email if submitter else None,
                training_config=exp.training_config,
                status=exp.status.value,
                run_name=exp.run_name,
                seed=exp.seed,
                created_at=exp.created_at,
                split=split,
                metrics=metrics_dict,
                directions=directions_dict,
                repo_url=repo_url,
                rank=rank,
            )
        )

    return result


async def query_leaderboard(data: LeaderboardQuery) -> list[MultiMetricLeaderboardEntry]:
    if data.dataset_version_uuid is not None and data.pipeline_uuid is None:
        raise HTTPException(
            status_code=422,
            detail=(
                "pipeline_uuid è obbligatorio quando viene specificata "
                "dataset_version_uuid"
            ),
        )
    if not data.metrics:
        raise HTTPException(status_code=422, detail="metrics non può essere vuoto")

    sort_by = data.sort_by or data.metrics[0]

    return await get_multi_metric_leaderboard(
        dataset_uuid=data.dataset_uuid,
        metrics_list=data.metrics,
        split=data.split,
        sort_by=sort_by,
        top_n=data.top_n,
        dataset_version_uuid=data.dataset_version_uuid,
        pipeline_uuid=data.pipeline_uuid,
        model_uuids=data.model_uuids,
        author_uuids=data.author_uuids,
        hyperparam_filters=data.hyperparam_filters,
    )


async def get_best_configuration(
    data: BestConfigurationQuery,
) -> BestConfigurationResponse:
    from app.models.experiments import Experiment
    from app.models.ml_models import MLModel
    from app.models.pipelines import Pipeline
    from app.models.users import User

    dataset = await get_dataset_by_uuid(data.dataset_uuid)
    dataset_version_id = await _resolve_dataset_version_id(
        data.dataset_uuid,
        data.dataset_version_uuid,
    )
    pipeline_id = await _resolve_pipeline_id(
        data.dataset_uuid,
        data.dataset_version_uuid,
        data.pipeline_uuid,
    )

    model_ids = await _resolve_model_ids(data.model_uuids)
    author_ids = await _resolve_author_ids(data.author_uuids)
    requested_metrics = list(dict.fromkeys([data.target_metric, *data.metrics]))

    def empty_response(
        direction: Direction = data.direction,
    ) -> BestConfigurationResponse:
        return BestConfigurationResponse(
            dataset_uuid=data.dataset_uuid,
            dataset_version_uuid=data.dataset_version_uuid,
            pipeline_uuid=data.pipeline_uuid,
            split=data.split,
            metrics=requested_metrics,
            target_metric=data.target_metric,
            direction=direction,
            group_by_hyperparams=data.group_by_hyperparams,
            best_group=None,
            groups=[],
        )

    if data.model_uuids is not None and model_ids is not None and len(model_ids) == 0:
        return empty_response()
    if data.author_uuids is not None and author_ids is not None and len(author_ids) == 0:
        return empty_response()

    filters = [
        Metric.dataset_id == dataset.id,
        Metric.dataset_version_id == dataset_version_id,
        Metric.pipeline_id == pipeline_id,
        Metric.split == data.split,
        Metric.metric == data.target_metric,
    ]
    if model_ids is not None:
        filters.append({"model_id": {"$in": list(model_ids)}})
    if author_ids is not None:
        filters.append({"submitted_by_user_id": {"$in": list(author_ids)}})

    rows = await Metric.find(*filters).to_list()
    if not rows:
        return empty_response()
    selected_direction = data.direction

    exp_ids = list({r.experiment_id for r in rows})
    experiments = await Experiment.find({"_id": {"$in": exp_ids}}).to_list()
    exp_by_id = {e.id: e for e in experiments}

    rows_with_exp: list[tuple[Metric, Experiment]] = []
    for row in rows:
        exp = exp_by_id.get(row.experiment_id)
        if exp is None:
            continue
        if not _matches_hyperparam_filters(exp.training_config, data.hyperparam_filters):
            continue
        rows_with_exp.append((row, exp))

    if not rows_with_exp:
        return empty_response(selected_direction)

    model_ids = list({exp.model_id for _, exp in rows_with_exp})
    models = await MLModel.find({"_id": {"$in": model_ids}}).to_list()
    model_by_id = {m.id: m for m in models}

    user_ids = list(
        {
            exp.submitted_by_user_id
            for _, exp in rows_with_exp
            if exp.submitted_by_user_id is not None
        }
    )
    users = await User.find({"_id": {"$in": user_ids}}).to_list()
    user_by_id = {u.id: u for u in users}

    grouped: dict[tuple, dict[str, Any]] = {}

    for row, exp in rows_with_exp:
        hyperparams = {}
        for key in data.group_by_hyperparams:
            hyperparams[key] = (exp.training_config or {}).get(key)

        group_key = (
            exp.model_id,
            tuple((k, hyperparams.get(k)) for k in data.group_by_hyperparams),
        )

        if group_key not in grouped:
            grouped[group_key] = {
                "model_id": exp.model_id,
                "hyperparams": hyperparams,
                "values": [],
                "best_row": row,
                "best_exp": exp,
            }

        group = grouped[group_key]
        group["values"].append(row.value)

        current_best_row = group["best_row"]
        if selected_direction.value == "max":
            if row.value > current_best_row.value:
                group["best_row"] = row
                group["best_exp"] = exp
        else:
            if row.value < current_best_row.value:
                group["best_row"] = row
                group["best_exp"] = exp

    best_exp_ids = list({payload["best_exp"].id for payload in grouped.values()})
    best_metric_filters: list[Any] = [
        Metric.dataset_id == dataset.id,
        Metric.dataset_version_id == dataset_version_id,
        Metric.pipeline_id == pipeline_id,
        Metric.split == data.split,
        {"experiment_id": {"$in": best_exp_ids}},
        {"metric": {"$in": requested_metrics}},
    ]

    best_metric_rows = await Metric.find(*best_metric_filters).to_list()
    best_metrics_by_exp: dict[Any, dict[str, float]] = defaultdict(dict)
    directions_by_exp: dict[Any, dict[str, Any]] = defaultdict(dict)
    for metric_row in best_metric_rows:
        best_metrics_by_exp[metric_row.experiment_id][metric_row.metric] = (
            metric_row.value
        )
        directions_by_exp[metric_row.experiment_id][metric_row.metric] = (
            metric_row.direction
        )

    best_pipeline_ids = list(
        {
            payload["best_row"].pipeline_id
            for payload in grouped.values()
            if payload["best_row"].pipeline_id is not None
        }
    )
    pipelines = await Pipeline.find({"_id": {"$in": best_pipeline_ids}}).to_list()
    pipeline_uuid_by_id = {pipeline.id: pipeline.uuid for pipeline in pipelines}
    pipeline_code_by_id = {pipeline.id: pipeline.code for pipeline in pipelines}

    groups: list[BestConfigurationGroup] = []
    for payload in grouped.values():
        values = payload["values"]
        count = len(values)
        mean_value = sum(values) / count
        std_value = None
        if count > 1:
            variance = sum((v - mean_value) ** 2 for v in values) / count
            std_value = sqrt(variance)

        best_exp = payload["best_exp"]
        best_row = payload["best_row"]
        model = model_by_id.get(payload["model_id"])
        if model is None:
            continue
        submitter = user_by_id.get(best_exp.submitted_by_user_id)

        groups.append(
            BestConfigurationGroup(
                model_uuid=model.uuid,
                model_name=model.name,
                submitted_by_user_uuid=submitter.uuid if submitter else None,
                submitted_by_display_name=(
                    _user_display_name(
                        submitter.first_name if submitter else None,
                        submitter.last_name if submitter else None,
                        submitter.email if submitter else None,
                    )
                ),
                submitted_by_email=submitter.email if submitter else None,
                hyperparams=payload["hyperparams"],
                best_value=best_row.value,
                mean_value=mean_value,
                count=count,
                std=std_value,
                best_metrics=dict(best_metrics_by_exp.get(best_exp.id, {})),
                directions=dict(directions_by_exp.get(best_exp.id, {})),
                best_pipeline_uuid=(
                    pipeline_uuid_by_id.get(best_row.pipeline_id)
                    if best_row.pipeline_id is not None
                    else None
                ),
                best_pipeline_code=(
                    pipeline_code_by_id.get(best_row.pipeline_id)
                    if best_row.pipeline_id is not None
                    else None
                ),
                best_experiment_uuid=best_exp.uuid,
                best_run_name=best_exp.run_name,
                best_training_config=best_exp.training_config,
            )
        )

    groups.sort(
        key=lambda g: g.best_value,
        reverse=selected_direction.value == "max",
    )

    return BestConfigurationResponse(
        dataset_uuid=data.dataset_uuid,
        dataset_version_uuid=data.dataset_version_uuid,
        pipeline_uuid=data.pipeline_uuid,
        split=data.split,
        metrics=requested_metrics,
        target_metric=data.target_metric,
        direction=selected_direction,
        group_by_hyperparams=data.group_by_hyperparams,
        best_group=groups[0] if groups else None,
        groups=groups,
    )
