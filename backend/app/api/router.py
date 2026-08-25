"""Aggregates every route module into a single router mounted by main.py."""

from fastapi import APIRouter

from app.api.routes import activities, auth, groups, health, recap, telegram, webhooks

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(auth.router)
api_router.include_router(groups.router)
api_router.include_router(activities.router)
api_router.include_router(recap.router)
api_router.include_router(webhooks.router)
api_router.include_router(telegram.router)
