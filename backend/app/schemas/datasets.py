"""
schemas/datasets.py
====================

    DatasetBase       campi condivisi tra Create e Public
         ├── DatasetCreate   quello che il CLIENT manda
         └── DatasetPublic   quello che l'API RITORNA (Base + id, uuid, metadati server)

    DatasetSummary    FUORI dalla gerarchia — versione ridotta per liste.
                      Non eredita Base perché OMETTE description e splits.

Nota su UUID vs ObjectId negli input (B):
    DatasetCreate non espone PydanticObjectId al client.
    team_uuid: UUID | None  →  il router risolve UUID → ObjectId internamente.
    Questo rende l'API stabile e indipendente dal DB.
"""

from datetime import datetime
from uuid import UUID

from beanie import PydanticObjectId
from pydantic import BaseModel, Field

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
    Il server calcola: uuid, created_at, created_by_user_id.
    Nessun alias → nessun populate_by_name necessario.
    """

    pass


class DatasetPublic(DatasetBase):
    """
    Risposta completa per una singola risorsa Dataset.
    Qui torniamo a esporre anche gli ObjectId interni perché
    il client potrebbe averne bisogno per join lato frontend.
    populate_by_name serve perché id ha alias="_id".
    """

    id: PydanticObjectId = Field(alias="_id")
    uuid: UUID
    team_id: PydanticObjectId | None = None
    created_by_user_id: PydanticObjectId | None = None
    created_at: datetime

    model_config = {"populate_by_name": True}


class DatasetSummary(BaseModel):
    """
    Versione compatta per liste e dropdown.
    populate_by_name serve perché id ha alias="_id".
    """

    id: PydanticObjectId = Field(alias="_id")
    uuid: UUID
    name: str
    version: str
    task: TaskType
    visibility: Visibility

    model_config = {"populate_by_name": True}
