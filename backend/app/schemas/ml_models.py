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
    MLModel = algoritmo (es. LightGCN, BPR-MF).
    Gli hyperparams variano per ogni run → appartengono a Experiment.
"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class MLModelBase(BaseModel):
    """Campi condivisi tra Create e Public. Niente hyperparams: vanno su Experiment."""

    name: str
    family: str | None = None
    paper_url: str | None = None
    implementation: str | None = None


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
