"""
routers/experiments.py
=======================
Router per Experiment e Metric (submission + read-side + leaderboard).
I router sono sottili: delegano tutta la logica ai services.
"""

from uuid import UUID

from fastapi import APIRouter, Depends

from app.auth.auth import get_current_active_user, get_current_verified_user
from app.models.metrics import Split
from app.models.users import User
from app.schemas.experiments import ExperimentCreate, ExperimentPublic
from app.schemas.metrics import ExperimentMetrics, LeaderboardEntry, MetricsBatchCreate
from app.services import experiments as exp_service
from app.services import leaderboard as lb_service
from app.services import metrics as metric_service

router = APIRouter()


# ---------------------------------------------------------------------------
# Experiments
# ---------------------------------------------------------------------------


@router.post("/experiments", response_model=ExperimentPublic, tags=["experiments"])
async def submit_experiment(
    data: ExperimentCreate,
    current_user: User = Depends(get_current_verified_user),
) -> ExperimentPublic:
    """
    Sottomette un nuovo Experiment.
    - dataset_uuid e model_uuid vengono risolti → ObjectId internamente
    - submitted_by_user_uuid viene estratto dal token JWT
    - status parte sempre da QUEUED
    """
    return await exp_service.create_experiment(data, current_user)


@router.get(
    "/experiments/{experiment_uuid}",
    response_model=ExperimentPublic,
    tags=["experiments"],
)
async def get_experiment(
    experiment_uuid: UUID,
    _: User = Depends(get_current_active_user),
) -> ExperimentPublic:
    """Dettaglio di un singolo Experiment per UUID."""
    return await exp_service.get_experiment_public(experiment_uuid)


# ---------------------------------------------------------------------------
# Metrics (submission batch + lettura raggruppata)
# ---------------------------------------------------------------------------


@router.post(
    "/experiments/{experiment_uuid}/metrics",
    response_model=ExperimentMetrics,
    tags=["metrics"],
)
async def submit_metrics(
    experiment_uuid: UUID,
    data: MetricsBatchCreate,
    current_user: User = Depends(get_current_verified_user),
) -> ExperimentMetrics:
    """
    Sottomette tutte le metriche di una run in batch.
    Il server denormalizza dataset_id e model_id dall'Experiment.
    Ritorna le metriche già raggruppate per split.
    """
    # Forza la coerenza: experiment_uuid nel path == quello nel body
    data.experiment_uuid = experiment_uuid
    await metric_service.create_metrics_batch(data)
    return await metric_service.get_experiment_metrics(experiment_uuid)


@router.get(
    "/experiments/{experiment_uuid}/metrics",
    response_model=ExperimentMetrics,
    tags=["metrics"],
)
async def get_experiment_metrics(experiment_uuid: UUID) -> ExperimentMetrics:
    """Ritorna tutte le metriche di un Experiment raggruppate per split."""
    return await metric_service.get_experiment_metrics(experiment_uuid)


# ---------------------------------------------------------------------------
# Leaderboard
# ---------------------------------------------------------------------------


@router.get("/leaderboard", response_model=list[LeaderboardEntry], tags=["leaderboard"])
async def get_leaderboard(
    dataset_uuid: UUID,
    metric: str,
    split: Split,
    top_n: int = 10,
) -> list[LeaderboardEntry]:
    """
    Ritorna i top_n risultati per (dataset, metric, split) ordinati per value DESC.

    Query params:
    - dataset_uuid: UUID del dataset
    - metric: nome della metrica (es. "ndcg@10")
    - split: "test" o "validation"
    - top_n: numero di risultati (default 10)
    """
    return await lb_service.get_leaderboard(dataset_uuid, metric, split, top_n)
