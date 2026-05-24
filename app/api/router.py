"""Aggregate API routers."""

from fastapi import APIRouter
from app.api.v1 import etl as etl_v1
from app.api.v1 import llm as llm_v1
from app.api.v1 import health as health_v1
from app.api.v1 import scraping as scraping_v1
from app.api.v1 import exchange as exchange_v1

api_router = APIRouter()

api_router.include_router(health_v1.router, tags=["Health"])
api_router.include_router(etl_v1.router)
api_router.include_router(exchange_v1.router)
api_router.include_router(scraping_v1.router)
api_router.include_router(llm_v1.router)
