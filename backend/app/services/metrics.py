from uuid import UUID

from fastapi import HTTPException

from app.models.metrics import Metric
from app.schemas.metrics import (
    ExperimentMetrics,
    MetricPublic,
    MetricsBatchCreate,
)


async def create_metrics_batch(data: MetricsBatchCreate) -> None:
    from app.models.dataset_versions import DatasetVersion
    from app.models.datasets import Dataset
    from app.models.pipelines import Pipeline
    from app.services.experiments import get_experiment_by_uuid

    exp = await get_experiment_by_uuid(data.experiment_uuid)
    dataset_version = await DatasetVersion.get(exp.dataset_version_id)
    if dataset_version is None:
        raise HTTPException(
            status_code=404,
            detail="DatasetVersion dell'experiment non trovata",
        )
    dataset = await Dataset.get(dataset_version.dataset_id)
    if dataset is None:
        raise HTTPException(status_code=404, detail="Dataset dell'experiment non trovato")
    if exp.pipeline_id is None:
        raise HTTPException(
            status_code=422,
            detail="Experiment non collegato a nessuna pipeline",
        )
    pipeline = await Pipeline.get(exp.pipeline_id)
    if pipeline is None:
        raise HTTPException(
            status_code=404,
            detail="Pipeline dell'experiment non trovata",
        )

    documents = [
        Metric(
            experiment_id=exp.id,
            dataset_id=dataset.id,
            dataset_version_id=dataset_version.id,
            pipeline_id=pipeline.id,
            model_id=exp.model_id,
            submitted_by_user_id=exp.submitted_by_user_id,
            team_id=exp.team_id,
            split=m.split,
            metric=m.metric,
            k=m.k,
            value=m.value,
            direction=m.direction,
        )
        for m in data.metrics
    ]

    if documents:
        await Metric.insert_many(documents)


async def get_experiment_metrics(experiment_uuid: UUID) -> ExperimentMetrics:
    from app.models.dataset_versions import DatasetVersion
    from app.models.datasets import Dataset
    from app.models.ml_models import MLModel
    from app.models.pipelines import Pipeline
    from app.services.experiments import get_experiment_by_uuid

    exp = await get_experiment_by_uuid(experiment_uuid)
    metrics = await Metric.find(Metric.experiment_id == exp.id).to_list()

    dataset_version = await DatasetVersion.get(exp.dataset_version_id)
    if dataset_version is None:
        raise HTTPException(
            status_code=404,
            detail="DatasetVersion dell'experiment non trovata",
        )

    dataset = await Dataset.get(dataset_version.dataset_id)
    model = await MLModel.get(exp.model_id)
    pipeline = await Pipeline.get(exp.pipeline_id) if exp.pipeline_id else None

    if dataset is None:
        raise HTTPException(status_code=404, detail="Dataset dell'experiment non trovato")
    if model is None:
        raise HTTPException(status_code=404, detail="MLModel dell'experiment non trovato")
    if exp.pipeline_id is not None and pipeline is None:
        raise HTTPException(
            status_code=404,
            detail="Pipeline dell'experiment non trovata",
        )

    by_split: dict = {}
    for m in metrics:
        pub = MetricPublic(
            uuid=m.uuid,
            experiment_uuid=exp.uuid,
            dataset_uuid=dataset.uuid,
            dataset_version_uuid=dataset_version.uuid,
            pipeline_uuid=pipeline.uuid if pipeline else None,
            model_uuid=model.uuid,
            split=m.split,
            metric=m.metric,
            k=m.k,
            value=m.value,
            direction=m.direction,
            computed_at=m.computed_at,
        )
        by_split.setdefault(m.split, []).append(pub)

    return ExperimentMetrics(
        experiment_uuid=exp.uuid,
        metrics_by_split=by_split,
    )
