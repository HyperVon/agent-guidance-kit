"""Route registration."""
from __future__ import annotations

import logging

from app import config, export, reports
from app.router import Router


def build_router() -> Router:
    logging.basicConfig(level=config.LOG_LEVEL)
    router = Router()
    router.add("GET", "/v1/tenants", reports.handle_tenant_list)
    router.add("GET", "/v1/reports/summary", reports.handle_tenant_summary)
    router.add("GET", "/v1/exports/records", export.handle_export)
    return router
