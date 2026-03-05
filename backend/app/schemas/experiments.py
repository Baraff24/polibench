"""
schemas/experiments.py
=======================

    ExperimentBase    campi che il CLIENT può scegliere
         ├── ExperimentCreate   il server popola status e submitted_by
         └── ExperimentPublic   aggiunge id, uuid, status, submitted_by, timestamps

    ExperimentSummary FUORI dalla gerarchia — omette training_config, hyperparams e code.

Note:
    (B) dataset_uuid / model_uuid: UUID invece di ObjectId — il client
        non conosce gli _id interni di Mongo. Il router risolve UUID → ObjectId.

    (D) hyperparams aggiunto in ExperimentBase: è uno dei campi principali
        che il client manda (configurazione della run), non appartiene a MLModel.

    submitted_by_user_id e status NON sono in Base:
        - submitted_by_user_id → estratto dal token JWT nel router
        - status               → parte sempre da QUEUED
"""

from datetime import datetime
from typing import Any
from uuid import UUID

from beanie import PydanticObjectId
from pydantic import BaseModel, Field

from app.models.experiments import Artifacts, CodeInfo, Status


class ExperimentBase(BaseModel):
    """Campi che il client sceglie. Usa UUID per i riferimenti — non ObjectId."""

    dataset_uuid: UUID
    model_uuid: UUID
    team_uuid: UUID | None = None
    run_name: str | None = None
    seed: int | None = None
    notes: str | None = None
    # hyperparams appartiene qui, non su MLModel (che rappresenta l'algoritmo)
    hyperparams: dict[str, Any] | None = None
    training_config: dict[str, Any] | None = None
    code: CodeInfo | None = None


class ExperimentCreate(ExperimentBase):
    """
    Quello che il client manda per sottomettere un experiment.
    Il server popola: uuid, submitted_by_user_id, status, created_at.
    Nessun alias → nessun populate_by_name necessario.
    """

    pass


class ExperimentPublic(ExperimentBase):
    """
    Risposta completa per un singolo Experiment.
    Aggiunge i campi gestiti dal server.
    """

    id: PydanticObjectId = Field(alias="_id")
    uuid: UUID
    submitted_by_user_id: PydanticObjectId
    status: Status
    artifacts: Artifacts | None = None
    created_at: datetime
    finished_at: datetime | None = None

    model_config = {"populate_by_name": True}


class ExperimentSummary(BaseModel):
    """
    Versione compatta per liste di run.
    Omette hyperparams, training_config e code — troppo pesanti per una tabella.
    """

    id: PydanticObjectId = Field(alias="_id")
    uuid: UUID
    dataset_uuid: UUID
    model_uuid: UUID
    run_name: str | None = None
    status: Status
    created_at: datetime

    model_config = {"populate_by_name": True}
