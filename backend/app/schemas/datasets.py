"""
schemas/datasets.py
====================

    DatasetBase       campi condivisi tra Create e Public
         ├── DatasetCreate   quello che il CLIENT manda
         └── DatasetPublic   quello che l'API RITORNA (Base + uuid, metadati server)

    DatasetSummary    FUORI dalla gerarchia — versione ridotta per liste.
                      Non eredita Base perché OMETTE description e splits.

Principio UUID-first (API pubblica):
    - input:   sempre UUID (mai ObjectId)
    - output:  sempre UUID come identificatore primario
    - _id MongoDB:  rimane interno al DB, mai esposto nelle response pubbliche

    Questo rende l'API stabile e DB-agnostic: se il DB cambia,
    i client non devono cambiare nulla.
"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

from app.models.datasets import Splits, TaskType, Visibility


class DatasetBase(BaseModel):
    """Campi condivisi tra Create e Public."""

    name: str
    version: str
    task: TaskType
    description: str | None = None
    visibility: Visibility = Visibility.PUBLIC
    splits: Splits | None = None
    # UUID, non ObjectId: il client non conosce i dettagli interni di Mongo
    team_uuid: UUID | None = None


class DatasetCreate(DatasetBase):
    """
    Quello che il client manda per creare un Dataset.
    Il server calcola: uuid, created_at, created_by_user_uuid.
    """

    pass


class DatasetPublic(DatasetBase):
    """
    Risposta completa per una singola risorsa Dataset.
    uuid è l'unico identificatore esposto: niente _id MongoDB.
    created_by_user_uuid usa UUID coerentemente con il resto dell'API.
    """

    uuid: UUID
    created_by_user_uuid: UUID | None = None
    created_at: datetime


class DatasetSummary(BaseModel):
    """
    Versione compatta per liste e dropdown.
    Solo i campi necessari a identificare il dataset in una tabella.
    uuid è l'identificatore: niente _id MongoDB.
    """

    uuid: UUID
    name: str
    version: str
    task: TaskType
    visibility: Visibility
