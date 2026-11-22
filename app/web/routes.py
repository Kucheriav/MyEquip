"""Aggregates every web page router into one.

Pages are split by area; each module only builds forms and calls /api via
app.web.bff. Business rules and role checks stay in the API, so the web
app can never do more than the desktop client.
"""
from fastapi import APIRouter

from app.web import (
    routes_auth, routes_catalog, routes_equipment, routes_operations, routes_people,
)

router = APIRouter(include_in_schema=False)
router.include_router(routes_auth.router)
router.include_router(routes_equipment.router)
router.include_router(routes_operations.router)
router.include_router(routes_people.router)
router.include_router(routes_catalog.router)
