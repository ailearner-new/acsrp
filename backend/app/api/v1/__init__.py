"""API v1 router initialization."""

from fastapi import APIRouter

from backend.app.api.v1.health import router as health_router
from backend.app.api.v1.auth import router as auth_router
from backend.app.api.v1.tickets import router as tickets_router
from backend.app.api.v1.customers import router as customers_router
from backend.app.api.v1.articles import router as articles_router
from backend.app.api.v1.ws import router as ws_router

api_v1_router = APIRouter(prefix="/api/v1")
api_v1_router.include_router(health_router)
api_v1_router.include_router(auth_router)
api_v1_router.include_router(tickets_router)
api_v1_router.include_router(customers_router)
api_v1_router.include_router(articles_router)
api_v1_router.include_router(ws_router)