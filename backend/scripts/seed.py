"""
scripts/seed.py
===============
Popola il database con dati di esempio realistici per sviluppo e demo.

Crea:
  - 1 superuser admin (se non esiste già)
  - 4 Dataset  (MovieLens-1M, Amazon-Books, Yelp2018, LastFM)
  - 6 MLModel  (BPR, LightGCN, SGL, SimGCL, SVD, NeuMF)
  - 12 Experiment (2 per dataset, modelli diversi)
  - ~48 Metric  (test + validation per ogni experiment)

Uso:
  cd backend
  uv run python scripts/seed.py

  # oppure per resettare prima i dati esistenti:
  uv run python scripts/seed.py --reset
"""

import asyncio
import sys
from datetime import UTC, datetime, timedelta
from random import Random

from beanie import init_beanie
from motor.motor_asyncio import AsyncIOMotorClient

sys.path.insert(0, ".")

from app.auth.auth import get_hashed_password
from app.config.config import settings
from app.models import DOCUMENT_MODELS
from app.models.datasets import Dataset, Splits, TaskType, Visibility
from app.models.experiments import Artifacts, CodeInfo, Experiment, Status
from app.models.metrics import Direction, Metric, Split
from app.models.ml_models import MLModel
from app.models.users import User

# Seed fisso per risultati riproducibili
rng = Random(42)


# ---------------------------------------------------------------------------
# Dati di esempio
# ---------------------------------------------------------------------------

DATASETS = [
    {
        "name": "MovieLens-1M",
        "version": "1.0",
        "task": TaskType.RANKING,
        "description": "1 million movie ratings from 6,000 users on 4,000 movies. "
        "Classic collaborative filtering benchmark.",
        "visibility": Visibility.PUBLIC,
        "splits": Splits(train=800_000, validation=100_000, test=100_000),
    },
    {
        "name": "Amazon-Books",
        "version": "2.0",
        "task": TaskType.RANKING,
        "description": "Amazon product reviews dataset filtered to the Books category. "
        "Sparse implicit feedback benchmark.",
        "visibility": Visibility.PUBLIC,
        "splits": Splits(train=2_380_000, validation=52_643, test=52_643),
    },
    {
        "name": "Yelp2018",
        "version": "1.0",
        "task": TaskType.RANKING,
        "description": "Local business reviews from Yelp, 2018 version. "
        "Used in many graph-based recommender papers.",
        "visibility": Visibility.PUBLIC,
        "splits": Splits(train=1_237_259, validation=24_734, test=24_734),
    },
    {
        "name": "MovieLens-100K",
        "version": "1.0",
        "task": TaskType.RATING_PREDICTION,
        "description": "100,000 ratings from 943 users on 1,682 movies. "
        "Standard rating prediction benchmark.",
        "visibility": Visibility.PUBLIC,
        "splits": Splits(train=80_000, validation=10_000, test=10_000),
    },
]

ML_MODELS = [
    {
        "name": "BPR",
        "family": "matrix-factorization",
        "paper_url": "https://arxiv.org/abs/1205.2618",
        "implementation": "https://github.com/guoyang9/BPR-pytorch",
        "hyperparams": {"embedding_dim": 64, "lr": 0.001, "reg": 1e-4},
    },
    {
        "name": "LightGCN",
        "family": "graph-neural-network",
        "paper_url": "https://arxiv.org/abs/2002.02126",
        "implementation": "https://github.com/gusye1234/LightGCN-PyTorch",
        "hyperparams": {"n_layers": 3, "embedding_dim": 64, "lr": 0.001},
    },
    {
        "name": "SGL",
        "family": "graph-neural-network",
        "paper_url": "https://arxiv.org/abs/2010.10783",
        "implementation": "https://github.com/wujcan/SGL-Torch",
        "hyperparams": {"n_layers": 3, "embedding_dim": 64, "ssl_temp": 0.2},
    },
    {
        "name": "SimGCL",
        "family": "graph-neural-network",
        "paper_url": "https://arxiv.org/abs/2112.08679",
        "implementation": "https://github.com/Coder-Yu/QRec",
        "hyperparams": {"n_layers": 3, "embedding_dim": 64, "eps": 0.1},
    },
    {
        "name": "SVD",
        "family": "matrix-factorization",
        "paper_url": "https://dl.acm.org/doi/10.1145/1401890.1401944",
        "implementation": "https://surpriselib.com",
        "hyperparams": {"n_factors": 100, "n_epochs": 20, "lr_all": 0.005},
    },
    {
        "name": "NeuMF",
        "family": "deep-learning",
        "paper_url": "https://arxiv.org/abs/1708.05031",
        "implementation": "https://github.com/hexiangnan/neural_collaborative_filtering",
        "hyperparams": {"layers": [64, 32, 16, 8], "lr": 0.001, "batch_size": 256},
    },
]

# (dataset_name, model_name, run_name, seed, status, giorni fa)
EXPERIMENTS_PLAN = [
    ("MovieLens-1M", "LightGCN", "lightgcn-baseline", 42, Status.FINISHED, 10),
    ("MovieLens-1M", "BPR", "bpr-baseline", 42, Status.FINISHED, 9),
    ("MovieLens-1M", "SGL", "sgl-tuned", 7, Status.FINISHED, 5),
    ("Amazon-Books", "LightGCN", "lightgcn-books", 42, Status.FINISHED, 8),
    ("Amazon-Books", "SimGCL", "simgcl-books", 1, Status.FINISHED, 6),
    ("Amazon-Books", "BPR", "bpr-books-v2", 99, Status.FAILED, 4),
    ("Yelp2018", "LightGCN", "lightgcn-yelp", 42, Status.FINISHED, 7),
    ("Yelp2018", "SGL", "sgl-yelp", 0, Status.FINISHED, 3),
    ("Yelp2018", "SimGCL", "simgcl-yelp-v2", 13, Status.RUNNING, 1),
    ("MovieLens-100K", "SVD", "svd-baseline", 42, Status.FINISHED, 6),
    ("MovieLens-100K", "NeuMF", "neumf-baseline", 42, Status.FINISHED, 5),
    ("MovieLens-100K", "BPR", "bpr-ml100k", 7, Status.QUEUED, 0),
]

# Metriche realistiche per dataset di ranking (ndcg, recall, hit)
# Valori calibrati sui paper originali
RANKING_METRICS_BASE = {
    "LightGCN": {
        "MovieLens-1M": {"ndcg@10": 0.4251, "recall@20": 0.3817, "hit@10": 0.7102},
        "Amazon-Books": {"ndcg@10": 0.0411, "recall@20": 0.0682, "hit@10": 0.1023},
        "Yelp2018": {"ndcg@10": 0.0649, "recall@20": 0.1084, "hit@10": 0.1432},
    },
    "BPR": {
        "MovieLens-1M": {"ndcg@10": 0.3812, "recall@20": 0.3401, "hit@10": 0.6521},
        "Amazon-Books": {"ndcg@10": 0.0318, "recall@20": 0.0531, "hit@10": 0.0812},
        "Yelp2018": {"ndcg@10": 0.0421, "recall@20": 0.0732, "hit@10": 0.1011},
    },
    "SGL": {
        "MovieLens-1M": {"ndcg@10": 0.4502, "recall@20": 0.3991, "hit@10": 0.7341},
        "Yelp2018": {"ndcg@10": 0.0721, "recall@20": 0.1193, "hit@10": 0.1612},
    },
    "SimGCL": {
        "Amazon-Books": {"ndcg@10": 0.0489, "recall@20": 0.0801, "hit@10": 0.1211},
        "Yelp2018": {"ndcg@10": 0.0763, "recall@20": 0.1245, "hit@10": 0.1689},
    },
}

# Metriche per rating prediction (rmse, mae)
RATING_METRICS_BASE = {
    "SVD": {"rmse": 0.9341, "mae": 0.7382},
    "NeuMF": {"rmse": 0.9012, "mae": 0.7101},
    "BPR": {"rmse": 0.9721, "mae": 0.7612},
}


def jitter(value: float, pct: float = 0.03) -> float:
    """Aggiunge rumore casuale ±pct% a un valore."""
    return round(value * (1 + rng.uniform(-pct, pct)), 4)


# ---------------------------------------------------------------------------
# Seed
# ---------------------------------------------------------------------------


async def seed(reset: bool = False) -> None:
    client = AsyncIOMotorClient(
        settings.MONGO_HOST,
        settings.MONGO_PORT,
        username=settings.MONGO_USER,
        password=settings.MONGO_PASSWORD,
    )
    await init_beanie(
        database=client[settings.MONGO_DB],
        document_models=DOCUMENT_MODELS,
    )

    if reset:
        print("⚠️  Reset: elimino dataset, modelli, esperimenti e metriche esistenti...")
        await Dataset.delete_all()
        await MLModel.delete_all()
        await Experiment.delete_all()
        await Metric.delete_all()
        print("   Fatto.\n")

    # Admin user (owner dei dati)
    admin = await User.find_one({"email": settings.FIRST_SUPERUSER})
    if not admin:
        admin = User(
            email=settings.FIRST_SUPERUSER,
            hashed_password=get_hashed_password(settings.FIRST_SUPERUSER_PASSWORD),
            is_superuser=True,
            is_verified=True,
        )
        await admin.create()
        print(f"✓ Admin creato: {admin.email}")
    else:
        print(f"✓ Admin già presente: {admin.email}")

    # ---- Dataset ----
    print("\n📦 Dataset...")
    dataset_map: dict[str, Dataset] = {}
    for d in DATASETS:
        existing = await Dataset.find_one({"name": d["name"], "version": d["version"]})
        if existing:
            dataset_map[d["name"]] = existing
            print(f"   · {d['name']} v{d['version']} (già presente)")
            continue
        doc = Dataset(**d, created_by_user_id=admin.id)
        await doc.create()
        dataset_map[d["name"]] = doc
        print(f"   + {d['name']} v{d['version']}")

    # ---- MLModel ----
    print("\n🤖 Modelli...")
    model_map: dict[str, MLModel] = {}
    for m in ML_MODELS:
        existing = await MLModel.find_one({"name": m["name"]})
        if existing:
            model_map[m["name"]] = existing
            print(f"   · {m['name']} (già presente)")
            continue
        doc = MLModel(**m, created_by_user_id=admin.id)
        await doc.create()
        model_map[m["name"]] = doc
        print(f"   + {m['name']}")

    # ---- Experiment + Metric ----
    print("\n🧪 Esperimenti e metriche...")
    for ds_name, model_name, run_name, seed_val, status, days_ago in EXPERIMENTS_PLAN:
        ds = dataset_map.get(ds_name)
        ml = model_map.get(model_name)
        if not ds or not ml:
            print(f"   ⚠ skip {run_name}: dataset o modello mancante")
            continue

        existing_exp = await Experiment.find_one({"run_name": run_name})
        if existing_exp:
            print(f"   · {run_name} (già presente)")
            continue

        created = datetime.now(UTC) - timedelta(days=days_ago, hours=rng.randint(0, 8))
        finished = (
            created + timedelta(hours=rng.randint(1, 6))
            if status == Status.FINISHED
            else None
        )

        exp = Experiment(
            dataset_id=ds.id,
            model_id=ml.id,
            submitted_by_user_id=admin.id,
            run_name=run_name,
            status=status,
            seed=seed_val,
            training_config=ml.hyperparams,
            code=CodeInfo(
                repo_url="https://github.com/polibench/experiments",
                git_commit=rng.randbytes(4).hex(),
            ),
            artifacts=Artifacts(logs_url=f"https://logs.polibench.local/{run_name}"),
            created_at=created,
            finished_at=finished,
            notes=f"Seed {seed_val} — run automatica via CLI.",
        )
        await exp.create()

        # Metriche solo per esperimenti finiti
        if status != Status.FINISHED:
            print(f"   + {run_name} [{status.value}] (nessuna metrica)")
            continue

        # Scegli il set di metriche giusto in base al task
        ds_task = ds.task
        metrics_to_insert: list[Metric] = []

        if ds_task == TaskType.RANKING:
            base = RANKING_METRICS_BASE.get(model_name, {}).get(ds_name, {})
            if not base:
                # fallback generico
                base = {"ndcg@10": 0.04, "recall@20": 0.07, "hit@10": 0.12}

            for split in (Split.TEST, Split.VALIDATION):
                for metric_name, base_val in base.items():
                    k_val = int(metric_name.split("@")[1]) if "@" in metric_name else None
                    metrics_to_insert.append(
                        Metric(
                            experiment_id=exp.id,
                            dataset_id=ds.id,
                            model_id=ml.id,
                            submitted_by_user_id=admin.id,
                            split=split,
                            metric=metric_name,
                            k=k_val,
                            value=jitter(base_val),
                            direction=Direction.MAX,
                        )
                    )

        else:  # rating prediction
            base = RATING_METRICS_BASE.get(model_name, {"rmse": 1.0, "mae": 0.8})
            for split in (Split.TEST, Split.VALIDATION):
                for metric_name, base_val in base.items():
                    metrics_to_insert.append(
                        Metric(
                            experiment_id=exp.id,
                            dataset_id=ds.id,
                            model_id=ml.id,
                            submitted_by_user_id=admin.id,
                            split=split,
                            metric=metric_name,
                            k=None,
                            value=jitter(base_val),
                            direction=Direction.MIN,
                        )
                    )

        await Metric.insert_many(metrics_to_insert)
        print(f"   + {run_name} [{status.value}] → {len(metrics_to_insert)} metriche")

    print("\n✅ Seed completato.")
    client.close()


if __name__ == "__main__":
    reset_flag = "--reset" in sys.argv
    asyncio.run(seed(reset=reset_flag))
