from .datasets import Dataset
from .experiments import Experiment
from .metrics import Metric
from .ml_models import MLModel
from .teams import Team
from .users import User

# Lista di tutti i Document Beanie da passare a init_beanie
DOCUMENT_MODELS = [Dataset, Experiment, Metric, MLModel, Team, User]
