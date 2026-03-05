"""
schemas/metrics.py
===================

Principio UUID-first:
    - input:   experiment_uuid (mai ObjectId)
    - output:  uuid come identificatore primario
    - I riferimenti denormalizzati (dataset_uuid, model_uuid, experiment_uuid)
      sono esposti come UUID nelle response pubbliche, mai come ObjectId.
    - _id MongoDB: mai esposto nelle response pubbliche.

Note:
    MetricsBatchCreate usa experiment_uuid: il router risolve UUID → Experiment
    e copia dataset_id/model_id internamente (denormalizzazione lato server).

    ExperimentMetrics usa dict[Split, list[MetricPublic]]: flessibile se si
    aggiungono nuovi split in futuro senza cambiare lo schema.
"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.models.metrics import Direction, Split


class MetricCreate(BaseModel):
    """
    Una singola metrica, usata all'interno di MetricsBatchCreate.
    Non include experiment_uuid/dataset_uuid/model_uuid: li fornisce il batch.
    """

    split: Split
    metric: str  # es. "ndcg@10", "recall@20", "rmse"
    k: int | None = None
    value: float
    direction: Direction


class MetricsBatchCreate(BaseModel):
    """
    Input per POST /experiments/{uuid}/metrics.
    Il client manda tutte le metriche di una run in un colpo solo.

    Il router:
    1. risolve experiment_uuid → Experiment (per leggere dataset_id, model_id)
    2. costruisce un Document Metric per ogni MetricCreate con i campi
       denormalizzati (dataset_id, model_id) copiati dall'Experiment
    3. salva tutto in bulk
    """

    experiment_uuid: UUID
    metrics: list[MetricCreate]


class MetricPublic(BaseModel):
    """
    Risposta per una singola metrica (es. nel dettaglio di un experiment).
    uuid è l'identificatore pubblico: niente _id MongoDB.
    I riferimenti denormalizzati sono esposti come UUID.
    """

    uuid: UUID
    experiment_uuid: UUID
    dataset_uuid: UUID
    model_uuid: UUID
    split: Split
    metric: str
    k: int | None = None
    value: float
    direction: Direction
    computed_at: datetime


class LeaderboardEntry(BaseModel):
    """
    Schema appiattito per una riga del leaderboard.
    Tutti i riferimenti sono UUID: niente ObjectId.
    model_name: stringa leggibile, popolata dal router dopo query su MLModel.
    rank: posizione in classifica, calcolata dal router.
    """

    experiment_uuid: UUID
    model_uuid: UUID
    model_name: str | None = None  # popolato dal router
    dataset_uuid: UUID
    split: Split
    metric: str
    k: int | None = None
    value: float
    direction: Direction
    rank: int | None = None  # calcolato dal router (1, 2, 3...)


class ExperimentMetrics(BaseModel):
    """
    Risposta per GET /experiments/{uuid}/metrics.
    experiment_uuid è UUID: niente ObjectId.
    dict[Split, list[MetricPublic]]: flessibile, non hardcoda test/validation.
    """

    experiment_uuid: UUID
    metrics_by_split: dict[Split, list[MetricPublic]] = Field(default_factory=dict)
