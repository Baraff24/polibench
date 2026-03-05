"""
schemas/experiments.py
=======================

    ExperimentBase    campi che il CLIENT può scegliere
         ├── ExperimentCreate   il server popola status e submitted_by
         └── ExperimentPublic   aggiunge uuid, status, submitted_by, timestamps

    ExperimentSummary FUORI dalla gerarchia — omette training_config, hyperparams e code.

Principio UUID-first:
    - input:   dataset_uuid, model_uuid, team_uuid (mai ObjectId)
    - output:  uuid come identificatore primario, tutti i riferimenti come UUID
    - _id MongoDB: mai esposto nelle response pubbliche

    submitted_by_user_uuid e status NON sono in Base:
        - submitted_by_user_uuid → estratto dal token JWT nel router
        - status                 → parte sempre da QUEUED
"""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel

from app.models.experiments import Artifacts, CodeInfo, Status


class ExperimentBase(BaseModel):
    """Campi che il client sceglie. Solo UUID per i riferimenti, mai ObjectId."""

    dataset_uuid: UUID
    model_uuid: UUID
    team_uuid: UUID | None = None
    run_name: str | None = None
    seed: int | None = None
    notes: str | None = None
    # hyperparams specifici di questa run (non dell'algoritmo)
    hyperparams: dict[str, Any] | None = None
    training_config: dict[str, Any] | None = None
    code: CodeInfo | None = None


class ExperimentCreate(ExperimentBase):
    """
    Quello che il client manda per sottomettere un experiment.
    Il server popola: uuid, submitted_by_user_uuid, status, created_at.
    """

    pass


class ExperimentPublic(ExperimentBase):
    """
    Risposta completa per un singolo Experiment.
    uuid è l'identificatore pubblico: niente _id MongoDB.
    Tutti i riferimenti ad altre entità usano UUID.
    """

    uuid: UUID
    submitted_by_user_uuid: UUID
    status: Status
    artifacts: Artifacts | None = None
    created_at: datetime
    finished_at: datetime | None = None


class ExperimentSummary(BaseModel):
    """
    Versione compatta per liste di run.
    Omette hyperparams, training_config e code.
    uuid è l'identificatore pubblico: niente _id MongoDB.
    """

    uuid: UUID
    dataset_uuid: UUID
    model_uuid: UUID
    run_name: str | None = None
    status: Status
    created_at: datetime
