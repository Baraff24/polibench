"""
schemas/ml_models.py
=====================

    MLModelBase       campi condivisi tra Create e Public
         ├── MLModelCreate   quello che il CLIENT manda
         └── MLModelPublic   quello che l'API RITORNA

    MLModelSummary    FUORI dalla gerarchia — versione ridotta per liste.

Principio UUID-first:
    Le response usano uuid come identificatore primario, mai _id MongoDB.
    created_by_user_uuid è UUID, non ObjectId.

Nota su hyperparams:
    hyperparams appartiene a MLModel, non a Experiment.
    MLModel rappresenta un algoritmo con la sua configurazione canonica
    (es. BPR-MF con factors=64, lr=0.01 come da paper).
    training_config su Experiment cattura variazioni run-specific
    (es. seed diverso, batch size diverso per ablation study).
"""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel


class MLModelBase(BaseModel):
    """Campi condivisi tra Create e Public."""

    name: str
    family: str | None = None
    paper_url: str | None = None
    implementation: str | None = None
    # Configurazione canonica dell'algoritmo (es. dal paper di riferimento)
    hyperparams: dict[str, Any] | None = None


class MLModelCreate(MLModelBase):
    """
    Quello che il client manda per registrare un nuovo algoritmo.
    Il server calcola: uuid, created_at, created_by_user_uuid.
    """

    pass


class MLModelPublic(MLModelBase):
    """
    Risposta completa per un singolo MLModel.
    uuid è l'identificatore pubblico: niente _id MongoDB.
    """

    uuid: UUID
    created_by_user_uuid: UUID | None = None
    created_at: datetime


class MLModelSummary(BaseModel):
    """
    Versione compatta per liste e leaderboard.
    uuid è l'identificatore pubblico: niente _id MongoDB.
    """

    uuid: UUID
    name: str
    family: str | None = None
    paper_url: str | None = None
