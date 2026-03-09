"""
services/datasets.py
=====================
Logica di business per Dataset e MLModel.
I router restano sottili: chiamano queste funzioni e restituiscono la risposta.

Responsabilità:
- risoluzione UUID → Document (con HTTPException 404 se non trovato)
- creazione entità con popolamento dei campi server-side
- query per liste
"""

from uuid import UUID

from fastapi import HTTPException

from app.models.datasets import Dataset
from app.models.ml_models import MLModel
from app.models.teams import Team
from app.models.users import User
from app.schemas.datasets import DatasetCreate, DatasetPublic, DatasetSummary
from app.schemas.ml_models import MLModelCreate, MLModelPublic, MLModelSummary

# ---------------------------------------------------------------------------
# Helpers di risoluzione UUID → Document
# ---------------------------------------------------------------------------


async def get_dataset_by_uuid(dataset_uuid: UUID) -> Dataset:
    """Restituisce il Dataset con quel uuid, o 404."""
    dataset = await Dataset.find_one(Dataset.uuid == dataset_uuid)
    if dataset is None:
        raise HTTPException(status_code=404, detail="Dataset non trovato")
    return dataset


async def get_ml_model_by_uuid(model_uuid: UUID) -> MLModel:
    """Restituisce il MLModel con quel uuid, o 404."""
    model = await MLModel.find_one(MLModel.uuid == model_uuid)
    if model is None:
        raise HTTPException(status_code=404, detail="MLModel non trovato")
    return model


async def get_team_by_uuid(team_uuid: UUID) -> Team:
    """Restituisce il Team con quel uuid, o 404."""
    team = await Team.find_one(Team.uuid == team_uuid)
    if team is None:
        raise HTTPException(status_code=404, detail="Team non trovato")
    return team


# ---------------------------------------------------------------------------
# Dataset
# ---------------------------------------------------------------------------


async def create_dataset(data: DatasetCreate, current_user: User) -> DatasetPublic:
    """
    Crea un Dataset.

    Flusso team (risoluzione UUID → ObjectId in scrittura):
    - se data.team_uuid è presente, risolve team_uuid → Team (404 se non esiste)
      e salva team_id (ObjectId interno) sul Document
    - se team_uuid è None, team_id rimane None

    created_by_user_id è popolato con l'ObjectId dell'utente corrente.
    """
    team_doc: Team | None = None
    if data.team_uuid is not None:
        team_doc = await get_team_by_uuid(data.team_uuid)

    dataset = Dataset(
        name=data.name,
        version=data.version,
        task=data.task,
        description=data.description,
        visibility=data.visibility,
        splits=data.splits,
        team_id=team_doc.id if team_doc else None,
        created_by_user_id=current_user.id,
    )
    await dataset.create()
    return _dataset_to_public(dataset, current_user, team_doc)


async def list_datasets() -> list[DatasetSummary]:
    """Restituisce tutti i dataset come lista di summary."""
    datasets = await Dataset.find_all().to_list()
    return [_dataset_to_summary(d) for d in datasets]


async def get_dataset_public(dataset_uuid: UUID) -> DatasetPublic:
    """
    Lettura di un singolo Dataset per UUID con risoluzione completa:
    - team_id (ObjectId interno) → Team → team.uuid
    - created_by_user_id (ObjectId interno) → User → user.uuid
    Usata dal router GET /datasets/{uuid}.
    """
    dataset = await get_dataset_by_uuid(dataset_uuid)

    team: Team | None = None
    if dataset.team_id is not None:
        team = await Team.get(dataset.team_id)

    creator: User | None = None
    if dataset.created_by_user_id is not None:
        creator = await User.get(dataset.created_by_user_id)

    return _dataset_to_public(dataset, creator, team)


def _dataset_to_public(
    dataset: Dataset,
    creator: User | None = None,
    team: Team | None = None,
) -> DatasetPublic:
    """
    Converte un Document Dataset in DatasetPublic (UUID-first).
    Riceve team e creator già risolti — non fa query al DB.
    team_uuid è None se il dataset non è associato a nessun team.
    """
    return DatasetPublic(
        uuid=dataset.uuid,
        name=dataset.name,
        version=dataset.version,
        task=dataset.task,
        description=dataset.description,
        visibility=dataset.visibility,
        splits=dataset.splits,
        team_uuid=team.uuid if team else None,
        created_by_user_uuid=creator.uuid if creator else None,
        created_at=dataset.created_at,
    )


def _dataset_to_summary(dataset: Dataset) -> DatasetSummary:
    return DatasetSummary(
        uuid=dataset.uuid,
        name=dataset.name,
        version=dataset.version,
        task=dataset.task,
        visibility=dataset.visibility,
    )


# ---------------------------------------------------------------------------
# MLModel
# ---------------------------------------------------------------------------


async def create_ml_model(data: MLModelCreate, current_user: User) -> MLModelPublic:
    """Crea un MLModel."""
    model = MLModel(
        name=data.name,
        family=data.family,
        paper_url=data.paper_url,
        implementation=data.implementation,
        hyperparams=data.hyperparams,
        created_by_user_id=current_user.id,
    )
    await model.create()
    return _model_to_public(model, current_user)


async def list_ml_models() -> list[MLModelSummary]:
    """Restituisce tutti i modelli come lista di summary."""
    models = await MLModel.find_all().to_list()
    return [_model_to_summary(m) for m in models]


def get_ml_model_public(model: MLModel, creator: User | None = None) -> MLModelPublic:
    """Versione pubblica di _model_to_public, usabile dal router."""
    return _model_to_public(model, creator)


async def get_ml_model_public_by_uuid(model_uuid: UUID) -> MLModelPublic:
    """
    Lettura di un singolo MLModel per UUID.
    Pattern simmetrico a get_dataset_public.
    """
    model = await get_ml_model_by_uuid(model_uuid)
    return _model_to_public(model)


def _model_to_public(model: MLModel, creator: User | None = None) -> MLModelPublic:
    return MLModelPublic(
        uuid=model.uuid,
        name=model.name,
        family=model.family,
        paper_url=model.paper_url,
        implementation=model.implementation,
        hyperparams=model.hyperparams,
        created_by_user_uuid=creator.uuid if creator else None,
        created_at=model.created_at,
    )


def _model_to_summary(model: MLModel) -> MLModelSummary:
    return MLModelSummary(
        uuid=model.uuid,
        name=model.name,
        family=model.family,
        paper_url=model.paper_url,
    )
