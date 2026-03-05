"""
routers/datasets.py
====================
Router per Dataset e MLModel (listing + creation).
I router sono sottili: delegano tutta la logica ai services.
"""

from uuid import UUID

from fastapi import APIRouter, Depends

from app.auth.auth import get_current_active_user
from app.models.users import User
from app.schemas.datasets import DatasetCreate, DatasetPublic, DatasetSummary
from app.schemas.ml_models import MLModelCreate, MLModelPublic, MLModelSummary
from app.services.datasets import (
    create_dataset,
    create_ml_model,
    get_dataset_public,
    get_ml_model_public_by_uuid,
    list_datasets,
    list_ml_models,
)

router = APIRouter()


# ---------------------------------------------------------------------------
# Datasets
# ---------------------------------------------------------------------------


@router.post("/datasets", response_model=DatasetPublic, tags=["datasets"])
async def create_dataset_endpoint(
    data: DatasetCreate,
    current_user: User = Depends(get_current_active_user),
) -> DatasetPublic:
    """Crea un nuovo Dataset. Richiede autenticazione."""
    return await create_dataset(data, current_user)


@router.get("/datasets", response_model=list[DatasetSummary], tags=["datasets"])
async def list_datasets_endpoint() -> list[DatasetSummary]:
    """Restituisce la lista di tutti i dataset. Pubblico."""
    return await list_datasets()


@router.get(
    "/datasets/{dataset_uuid}",
    response_model=DatasetPublic,
    tags=["datasets"],
)
async def get_dataset_endpoint(dataset_uuid: UUID) -> DatasetPublic:
    """Dettaglio di un singolo Dataset per UUID. Risolve team_id → team.uuid."""
    return await get_dataset_public(dataset_uuid)


# ---------------------------------------------------------------------------
# MLModels
# ---------------------------------------------------------------------------


@router.post("/ml-models", response_model=MLModelPublic, tags=["ml-models"])
async def create_ml_model_endpoint(
    data: MLModelCreate,
    current_user: User = Depends(get_current_active_user),
) -> MLModelPublic:
    """Registra un nuovo algoritmo. Richiede autenticazione."""
    return await create_ml_model(data, current_user)


@router.get("/ml-models", response_model=list[MLModelSummary], tags=["ml-models"])
async def list_ml_models_endpoint() -> list[MLModelSummary]:
    """Restituisce la lista di tutti i modelli. Pubblico."""
    return await list_ml_models()


@router.get(
    "/ml-models/{model_uuid}",
    response_model=MLModelPublic,
    tags=["ml-models"],
)
async def get_ml_model_endpoint(model_uuid: UUID) -> MLModelPublic:
    """Dettaglio di un singolo MLModel per UUID."""
    return await get_ml_model_public_by_uuid(model_uuid)
