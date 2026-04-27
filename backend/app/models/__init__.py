from .dataset_versions import DatasetVersion
from .datasets import Dataset
from .experiments import Experiment
from .metric_import_jobs import MetricImportJob
from .metrics import ExperimentMetric, Metric
from .ml_models import MLModel
from .pipelines import Pipeline
from .resources import Resource
from .sources import Source
from .teams import Team
from .users import User

# Lista di tutti i Document Beanie da passare a init_beanie
DOCUMENT_MODELS = [
    Dataset,
    DatasetVersion,
    Pipeline,
    Source,
    Resource,
    Experiment,
    MetricImportJob,
    ExperimentMetric,
    MLModel,
    Team,
    User,
]
