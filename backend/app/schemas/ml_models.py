"""
schemas/ml_models.py
=====================

    MLModelBase       campi condivisi tra Create e Public
         ├── MLModelCreate   quello che il CLIENT manda
         └── MLModelPublic   quello che l'API RITORNA

    MLModelSummary    FUORI dalla gerarchia — versione ridotta per liste.

Nota su hyperparams (C):
    MLModel = algoritmo (es. LightGCN, BPR-MF).
    Gli hyperparams variano per ogni run, non per algoritmo.
    Appartengono a Experiment, non a MLModel.
    Rimosso da MLModelBase per evitare confusione semantica.
"""

from datetime import datetime
from uuid import UUID

from beanie import PydanticObjectId
from pydantic import BaseModel, Field


class MLModelBase(BaseModel):
    """Campi condivisi tra Create e Public. Niente hyperparams: vanno su Experiment."""

    name: str
    family: str | None = None
    paper_url: str | None = None
    implementation: str | None = None


class MLModelCreate(MLModelBase):
    """
    Quello che il client manda per registrare un nuovo algoritmo.
    Il server calcola: uuid, created_at, created_by_user_id.
    """

    pass


class MLModelPublic(MLModelBase):
    """Risposta completa per un singolo MLModel."""

    id: PydanticObjectId = Field(alias="_id")
    uuid: UUID
    created_by_user_id: PydanticObjectId | None = None
    created_at: datetime

    model_config = {"populate_by_name": True}


class MLModelSummary(BaseModel):
    """Versione compatta per liste e leaderboard."""

    id: PydanticObjectId = Field(alias="_id")
    uuid: UUID
    name: str
    family: str | None = None
    paper_url: str | None = None

    model_config = {"populate_by_name": True}
