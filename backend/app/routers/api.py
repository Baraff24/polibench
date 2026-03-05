from fastapi import APIRouter

from . import datasets, experiments, login, users

api_router = APIRouter()
api_router.include_router(login.router, prefix="/login", tags=["login"])
api_router.include_router(users.router, prefix="/users", tags=["users"])
api_router.include_router(datasets.router, tags=["datasets"])
api_router.include_router(experiments.router, tags=["experiments"])


@api_router.get("/")
async def root():
    return {"message": "Backend API for Polibench operational !"}
