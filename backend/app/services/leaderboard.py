"""
services/leaderboard.py
========================
Query leaderboard: top-N per (dataset_uuid, metric, split) ordinato per value.
"""

from uuid import UUID

import pymongo

from app.models.metrics import Metric, Split
from app.schemas.metrics import LeaderboardEntry
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
