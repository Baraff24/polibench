"""
services/metrics.py
====================
Logica di business per Metric.

Responsabilità:
- inserimento batch di metriche (denormalizzazione dataset_id/model_id lato server)
- lettura metriche di un experiment raggruppate per split → ExperimentMetrics
"""

from fastapi import HTTPException

from app.models.metrics import Metric
from app.schemas.metrics import (
    ExperimentMetrics,
    MetricPublic,
    MetricsBatchCreate,
)


async def create_metrics_batch(data: MetricsBatchCreate) -> None:
    """
    Inserisce tutte le metriche di una run in bulk.

    Flusso:
    1. Risolve experiment_uuid → Experiment (404 se non esiste)
    2. Per ogni MetricCreate costruisce un Document Metric copiando
       dataset_id e model_id dall'Experiment (denormalizzazione server-side)
    3. Inserisce in bulk con insert_many

    Non ritorna nulla: il chiamante (router) usa get_experiment_metrics
    per costruire la risposta completa con uuid risolti.
    """
    from app.services.experiments import get_experiment_by_uuid

    exp = await get_experiment_by_uuid(data.experiment_uuid)

    documents = [
        Metric(
            experiment_id=exp.id,
            dataset_id=exp.dataset_id,
            model_id=exp.model_id,
            submitted_by_user_id=exp.submitted_by_user_id,
            team_id=exp.team_id,
            split=m.split,
            metric=m.metric,
            k=m.k,
            value=m.value,
            direction=m.direction,
        )
        for m in data.metrics
    ]

    await Metric.insert_many(documents)


async def get_experiment_metrics(experiment_uuid) -> ExperimentMetrics:
    """
    Ritorna tutte le metriche di un experiment raggruppate per split.

    Flusso:
    1. Risolve experiment_uuid → Experiment
    2. Fetch tutte le Metric con experiment_id == exp.id
    3. Risolve dataset_id/model_id → uuid per ciascuna metrica
       (fetch una volta, poi mappa)
    4. Raggruppa per split
    """
    from app.models.datasets import Dataset
    from app.models.ml_models import MLModel
    from app.services.experiments import get_experiment_by_uuid

    exp = await get_experiment_by_uuid(experiment_uuid)
    metrics = await Metric.find(Metric.experiment_id == exp.id).to_list()

    # Fetch uuid dei documenti collegati una sola volta
    dataset = await Dataset.get(exp.dataset_id)
    model = await MLModel.get(exp.model_id)

    if dataset is None:
        raise HTTPException(status_code=404, detail="Dataset dell'experiment non trovato")
    if model is None:
        raise HTTPException(status_code=404, detail="MLModel dell'experiment non trovato")

    # Raggruppa per split
    by_split: dict = {}
    for m in metrics:
        pub = MetricPublic(
            uuid=m.uuid,
            experiment_uuid=exp.uuid,
            dataset_uuid=dataset.uuid,
            model_uuid=model.uuid,
            split=m.split,
            metric=m.metric,
            k=m.k,
            value=m.value,
            direction=m.direction,
            computed_at=m.computed_at,
        )
        by_split.setdefault(m.split, []).append(pub)

    return ExperimentMetrics(
        experiment_uuid=exp.uuid,
        metrics_by_split=by_split,
    )
