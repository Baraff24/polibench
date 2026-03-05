"""
services/experiments.py
========================
Logica di business per Experiment.

Responsabilità:
- risoluzione UUID → Document (con HTTPException 404)
- creazione Experiment con:
    - submitted_by_user_id dal token (non dal client)
    - status iniziale QUEUED
    - risoluzione dataset_uuid / model_uuid → ObjectId
- lettura singolo Experiment → ExperimentPublic
"""

from uuid import UUID

from fastapi import HTTPException

from app.models.experiments import Experiment, Status
from app.models.users import User
from app.schemas.experiments import ExperimentCreate, ExperimentPublic
from app.services.datasets import get_dataset_by_uuid, get_ml_model_by_uuid

# ---------------------------------------------------------------------------
# Helper di risoluzione UUID → Document
# ---------------------------------------------------------------------------


async def get_experiment_by_uuid(experiment_uuid: UUID) -> Experiment:
    """Restituisce l'Experiment con quel uuid, o 404."""
    exp = await Experiment.find_one(Experiment.uuid == experiment_uuid)
    if exp is None:
        raise HTTPException(status_code=404, detail="Experiment non trovato")
    return exp


# ---------------------------------------------------------------------------
# Creazione
# ---------------------------------------------------------------------------


async def create_experiment(
    data: ExperimentCreate,
    current_user: User,
) -> ExperimentPublic:
    """
    Crea un Experiment.

    Flusso:
    1. Risolve data.dataset_uuid → Dataset (404 se non esiste)
    2. Risolve data.model_uuid   → MLModel (404 se non esiste)
    3. Crea Experiment con ObjectId interni e submitted_by dal token
    4. Ritorna ExperimentPublic (solo UUID, niente ObjectId)
    """
    dataset = await get_dataset_by_uuid(data.dataset_uuid)
    model = await get_ml_model_by_uuid(data.model_uuid)

    exp = Experiment(
        dataset_id=dataset.id,
        model_id=model.id,
        submitted_by_user_id=current_user.id,
        run_name=data.run_name,
        status=Status.QUEUED,
        training_config=data.training_config,
        seed=data.seed,
        notes=data.notes,
        code=data.code,
    )
    await exp.create()
    return _experiment_to_public(exp, data, current_user)


# ---------------------------------------------------------------------------
# Lettura
# ---------------------------------------------------------------------------


async def get_experiment_public(experiment_uuid: UUID) -> ExperimentPublic:
    """
    Ritorna ExperimentPublic dato un uuid.
    Risolve tutti gli ObjectId interni in UUID:
    - dataset_id → dataset.uuid
    - model_id   → model.uuid
    - submitted_by_user_id → user.uuid
    - team_id    → team.uuid (None se non associato)
    """
    from app.models.datasets import Dataset
    from app.models.ml_models import MLModel
    from app.models.teams import Team

    exp = await get_experiment_by_uuid(experiment_uuid)

    dataset = await Dataset.get(exp.dataset_id)
    if dataset is None:
        raise HTTPException(status_code=404, detail="Dataset dell'experiment non trovato")

    model = await MLModel.get(exp.model_id)
    if model is None:
        raise HTTPException(status_code=404, detail="MLModel dell'experiment non trovato")

    submitter = await User.get(exp.submitted_by_user_id)

    team_uuid = None
    if exp.team_id is not None:
        team = await Team.get(exp.team_id)
        team_uuid = team.uuid if team else None

    return ExperimentPublic(
        uuid=exp.uuid,
        dataset_uuid=dataset.uuid,
        model_uuid=model.uuid,
        team_uuid=team_uuid,
        submitted_by_user_uuid=submitter.uuid if submitter else exp.uuid,
        run_name=exp.run_name,
        status=exp.status,
        training_config=exp.training_config,
        seed=exp.seed,
        notes=exp.notes,
        code=exp.code,
        artifacts=exp.artifacts,
        created_at=exp.created_at,
        finished_at=exp.finished_at,
    )


# ---------------------------------------------------------------------------
# Helpers interni
# ---------------------------------------------------------------------------


def _experiment_to_public(
    exp: Experiment,
    data: ExperimentCreate,
    current_user: User,
) -> ExperimentPublic:
    """
    Conversione rapida post-creazione: riusa i UUID già noti dal payload
    invece di fare ulteriori query al DB.
    """
    return ExperimentPublic(
        uuid=exp.uuid,
        dataset_uuid=data.dataset_uuid,
        model_uuid=data.model_uuid,
        team_uuid=data.team_uuid,
        submitted_by_user_uuid=current_user.uuid,
        run_name=exp.run_name,
        status=exp.status,
        training_config=exp.training_config,
        seed=exp.seed,
        notes=exp.notes,
        code=exp.code,
        artifacts=exp.artifacts,
        created_at=exp.created_at,
        finished_at=exp.finished_at,
    )
