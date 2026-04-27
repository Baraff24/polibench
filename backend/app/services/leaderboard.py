from collections import defaultdict
from uuid import UUID

import pymongo
from fastapi import HTTPException

from app.models.metrics import Metric, Split
from app.schemas.metrics import LeaderboardEntry, MultiMetricLeaderboardEntry
from app.services.datasets import get_dataset_by_uuid


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


async def get_leaderboard(
    dataset_uuid: UUID,
    metric: str,
    split: Split,
    top_n: int = 10,
    dataset_version_uuid: UUID | None = None,
    pipeline_uuid: UUID | None = None,
) -> list[LeaderboardEntry]:
    from app.models.dataset_versions import DatasetVersion
    from app.models.experiments import Experiment
    from app.models.ml_models import MLModel
    from app.models.pipelines import Pipeline

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

    filters = [
        Metric.dataset_id == dataset.id,
        Metric.metric == metric,
        Metric.split == split,
    ]
    if dataset_version_id is not None:
        filters.append(Metric.dataset_version_id == dataset_version_id)
    if pipeline_id is not None:
        filters.append(Metric.pipeline_id == pipeline_id)

    rows = await (
        Metric.find(*filters)
        .sort([("value", pymongo.DESCENDING)])
        .limit(top_n)
        .to_list()
    )
    if not rows:
        return []

    model_ids = list({r.model_id for r in rows})
    models = await MLModel.find({"_id": {"$in": model_ids}}).to_list()
    model_name_by_id = {m.id: m.name for m in models}
    model_uuid_by_id = {m.id: m.uuid for m in models}

    exp_ids = list({r.experiment_id for r in rows})
    experiments = await Experiment.find({"_id": {"$in": exp_ids}}).to_list()
    exp_uuid_by_id = {e.id: e.uuid for e in experiments}

    version_ids = list({r.dataset_version_id for r in rows})
    versions = await DatasetVersion.find({"_id": {"$in": version_ids}}).to_list()
    version_uuid_by_id = {v.id: v.uuid for v in versions}
    pipeline_ids = list({r.pipeline_id for r in rows if r.pipeline_id is not None})
    pipelines = await Pipeline.find({"_id": {"$in": pipeline_ids}}).to_list()
    pipeline_uuid_by_id = {p.id: p.uuid for p in pipelines}
    pipeline_code_by_id = {p.id: p.code for p in pipelines}

    return [
        LeaderboardEntry(
            experiment_uuid=exp_uuid_by_id[row.experiment_id],
            model_uuid=model_uuid_by_id.get(row.model_id, row.model_id),
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
            split=row.split,
            metric=row.metric,
            k=row.k,
            value=row.value,
            direction=row.direction,
            rank=rank,
        )
        for rank, row in enumerate(rows, start=1)
    ]


async def get_multi_metric_leaderboard(
    dataset_uuid: UUID,
    metrics_list: list[str],
    split: Split,
    sort_by: str,
    top_n: int = 20,
    dataset_version_uuid: UUID | None = None,
    pipeline_uuid: UUID | None = None,
) -> list[MultiMetricLeaderboardEntry]:
    from app.models.dataset_versions import DatasetVersion
    from app.models.experiments import Experiment
    from app.models.ml_models import MLModel
    from app.models.pipelines import Pipeline

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

    filters = [
        Metric.dataset_id == dataset.id,
        Metric.split == split,
        {"metric": {"$in": metrics_list}},
    ]
    if dataset_version_id is not None:
        filters.append(Metric.dataset_version_id == dataset_version_id)
    if pipeline_id is not None:
        filters.append(Metric.pipeline_id == pipeline_id)

    rows = await Metric.find(*filters).to_list()
    if not rows:
        return []

    by_exp: dict = defaultdict(dict)
    for row in rows:
        by_exp[row.experiment_id][row.metric] = row

    sort_direction = "max"
    for row in rows:
        if row.metric == sort_by:
            sort_direction = row.direction.value
            break

    aggregated = []
    for exp_id, metric_map in by_exp.items():
        sort_val = metric_map.get(sort_by)
        if sort_val is None:
            continue
        aggregated.append((exp_id, metric_map, sort_val.value))

    reverse = sort_direction == "max"
    aggregated.sort(key=lambda x: x[2], reverse=reverse)
    aggregated = aggregated[:top_n]
    if not aggregated:
        return []

    exp_ids = list({a[0] for a in aggregated})
    experiments = await Experiment.find({"_id": {"$in": exp_ids}}).to_list()
    exp_by_id = {e.id: e for e in experiments}

    model_ids = list(
        {e.model_id for e in experiments if e.id in {a[0] for a in aggregated}}
    )
    models = await MLModel.find({"_id": {"$in": model_ids}}).to_list()
    model_name_by_id = {m.id: m.name for m in models}
    model_uuid_by_id = {m.id: m.uuid for m in models}

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

    result = []
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

        repo_url = exp.code.repo_url if exp.code else None

        result.append(
            MultiMetricLeaderboardEntry(
                experiment_uuid=exp.uuid,
                model_uuid=model_uuid_by_id.get(exp.model_id, exp.uuid),
                model_name=model_name_by_id.get(exp.model_id),
                dataset_uuid=dataset.uuid,
                dataset_version_uuid=row_dataset_version_uuid,
                pipeline_uuid=row_pipeline_uuid,
                pipeline_code=row_pipeline_code,
                split=split,
                metrics=metrics_dict,
                directions=directions_dict,
                repo_url=repo_url,
                rank=rank,
            )
        )

    return result
