"""
services/leaderboard.py
========================
Query leaderboard: top-N per (dataset_uuid, metric, split) ordinato per value.
Supporta sia single-metric che multi-metric (stile BARS).
"""

from collections import defaultdict
from uuid import UUID

import pymongo

from app.models.metrics import Metric, Split
from app.schemas.metrics import LeaderboardEntry, MultiMetricLeaderboardEntry
from app.services.datasets import get_dataset_by_uuid


async def get_leaderboard(
    dataset_uuid: UUID,
    metric: str,
    split: Split,
    top_n: int = 10,
) -> list[LeaderboardEntry]:
    """
    Flusso:
    1. Risolve dataset_uuid → Dataset (404 se non esiste)
    2. Query Metric per (dataset_id, metric, split) → sort DESC → limit top_n
    3. Batch fetch MLModel e Experiment per nome e uuid
    4. Assembla LeaderboardEntry con rank progressivo
    """
    from app.models.experiments import Experiment
    from app.models.ml_models import MLModel

    dataset = await get_dataset_by_uuid(dataset_uuid)
    rows = await (
        Metric.find(
            Metric.dataset_id == dataset.id,
            Metric.metric == metric,
            Metric.split == split,
        )
        .sort([("value", pymongo.DESCENDING)])
        .limit(top_n)
        .to_list()
    )
    if not rows:
        return []
    # Batch fetch: una sola query per tutti i model_id distinti
    model_ids = list({r.model_id for r in rows})
    models = await MLModel.find({"_id": {"$in": model_ids}}).to_list()
    model_name_by_id = {m.id: m.name for m in models}
    model_uuid_by_id = {m.id: m.uuid for m in models}
    # Batch fetch experiment uuid
    exp_ids = list({r.experiment_id for r in rows})
    experiments = await Experiment.find({"_id": {"$in": exp_ids}}).to_list()
    exp_uuid_by_id = {e.id: e.uuid for e in experiments}
    return [
        LeaderboardEntry(
            experiment_uuid=exp_uuid_by_id[row.experiment_id],
            model_uuid=model_uuid_by_id.get(row.model_id, row.model_id),
            model_name=model_name_by_id.get(row.model_id),
            dataset_uuid=dataset.uuid,
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
) -> list[MultiMetricLeaderboardEntry]:
    """
    Leaderboard multi-metrica ispirata a BARS CTR Leaderboard.

    Flusso:
    1. Risolve dataset_uuid → Dataset (404 se non esiste)
    2. Fetch tutte le Metric per (dataset_id, split) dove metric è in metrics_list
    3. Raggruppa per experiment_id → per ogni experiment raccoglie tutte le metriche
    4. Ordina per sort_by (la metrica primaria) desc o asc in base alla direction
    5. Limit top_n
    6. Batch fetch MLModel e Experiment per nome, uuid, repo_url
    7. Assembla MultiMetricLeaderboardEntry con rank progressivo
    """
    from app.models.experiments import Experiment
    from app.models.ml_models import MLModel

    dataset = await get_dataset_by_uuid(dataset_uuid)

    # Fetch tutte le metriche richieste per questo dataset e split
    rows = await Metric.find(
        Metric.dataset_id == dataset.id,
        Metric.split == split,
        {"metric": {"$in": metrics_list}},
    ).to_list()

    if not rows:
        return []

    # Raggruppa per experiment_id
    by_exp: dict = defaultdict(dict)
    for row in rows:
        by_exp[row.experiment_id][row.metric] = row

    # Determina la direction della metrica di ordinamento
    sort_direction = "max"
    for row in rows:
        if row.metric == sort_by:
            sort_direction = row.direction.value
            break

    # Prepara la lista con il valore della sort_by metrica per ordinare
    aggregated = []
    for exp_id, metric_map in by_exp.items():
        sort_val = metric_map.get(sort_by)
        if sort_val is None:
            continue
        aggregated.append((exp_id, metric_map, sort_val.value))

    # Ordina: max → desc, min → asc
    reverse = sort_direction == "max"
    aggregated.sort(key=lambda x: x[2], reverse=reverse)
    aggregated = aggregated[:top_n]

    if not aggregated:
        return []

    # Batch fetch modelli e esperimenti
    exp_ids = list({a[0] for a in aggregated})
    experiments = await Experiment.find({"_id": {"$in": exp_ids}}).to_list()
    exp_by_id = {e.id: e for e in experiments}

    model_ids = list(
        {e.model_id for e in experiments if e.id in {a[0] for a in aggregated}}
    )
    models = await MLModel.find({"_id": {"$in": model_ids}}).to_list()
    model_name_by_id = {m.id: m.name for m in models}
    model_uuid_by_id = {m.id: m.uuid for m in models}

    result = []
    for rank, (exp_id, metric_map, _) in enumerate(aggregated, start=1):
        exp = exp_by_id.get(exp_id)
        if exp is None:
            continue

        metrics_dict = {}
        directions_dict = {}
        for metric_name in metrics_list:
            m = metric_map.get(metric_name)
            if m is not None:
                metrics_dict[metric_name] = m.value
                directions_dict[metric_name] = m.direction

        repo_url = None
        if exp.code and exp.code.repo_url:
            repo_url = exp.code.repo_url

        result.append(
            MultiMetricLeaderboardEntry(
                experiment_uuid=exp.uuid,
                model_uuid=model_uuid_by_id.get(exp.model_id, exp.uuid),
                model_name=model_name_by_id.get(exp.model_id),
                dataset_uuid=dataset.uuid,
                split=split,
                metrics=metrics_dict,
                directions=directions_dict,
                repo_url=repo_url,
                rank=rank,
            )
        )

    return result
