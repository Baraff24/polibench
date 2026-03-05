"""
schemas/metrics.py
===================

Note:
    (E) MetricCreate + MetricsBatchCreate aggiunti.
        Il batch è la scelta corretta: una run produce decine di metriche,
        mandarle una alla volta sarebbe assurdo.
        Il router "esplode" il batch in Document Metric con i campi
        denormalizzati (dataset_id, model_id) presi dall'Experiment.
        experiment_uuid: UUID — non ObjectId, coerente con il resto dell'API.

    (F) ExperimentMetrics usa dict[Split, list[MetricPublic]] invece di
        campi hardcoded test/validation. Più flessibile se si aggiungono
        nuovi split in futuro (es. train). Lato OpenAPI il tipo è meno
        esplicito, ma il guadagno in flessibilità vale il compromesso.
"""

from datetime import datetime
from uuid import UUID

from beanie import PydanticObjectId
from pydantic import BaseModel, Field

from app.models.metrics import Direction, Split


class MetricCreate(BaseModel):
    """
    Una singola metrica, usata all'interno di MetricsBatchCreate.
    Non include experiment_id/dataset_id/model_id: li fornisce il batch.
    Nessun alias → nessun populate_by_name.
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

    Nessun alias → nessun populate_by_name.
    """

    experiment_uuid: UUID
    metrics: list[MetricCreate]


class MetricPublic(BaseModel):
    """
    Risposta per una singola metrica (es. nel dettaglio di un experiment).
    """

    id: PydanticObjectId = Field(alias="_id")
    uuid: UUID
    experiment_id: PydanticObjectId
    dataset_id: PydanticObjectId
    model_id: PydanticObjectId
    split: Split
    metric: str
    k: int | None = None
    value: float
    direction: Direction
    computed_at: datetime

    model_config = {"populate_by_name": True}


class LeaderboardEntry(BaseModel):
    """
    Schema appiattito per una riga del leaderboard.
    model_name è opzionale: popolato dal router dopo query su MLModel.
    rank è opzionale: calcolato dal router in base alla posizione nella lista.
    Nessun alias → nessun populate_by_name.
    """

    experiment_id: PydanticObjectId
    model_id: PydanticObjectId
    model_name: str | None = None
    dataset_id: PydanticObjectId
    split: Split
    metric: str
    k: int | None = None
    value: float
    direction: Direction
    rank: int | None = None


class ExperimentMetrics(BaseModel):
    """
    Risposta per GET /experiments/{uuid}/metrics.

    Usa dict[Split, list[MetricPublic]] invece di campi hardcoded test/validation:
    se in futuro si aggiunge lo split "train", questo schema non cambia.
    Il frontend itera su metrics_by_split.items() per costruire le tab.
    Nessun alias → nessun populate_by_name.
    """

    experiment_id: PydanticObjectId
    metrics_by_split: dict[Split, list[MetricPublic]] = Field(default_factory=dict)
