import json
import os
import unittest

from app.main import build_router
from app.router import Request

HEADERS = {"X-Api-Key": "test-key-value"}


class SummaryTests(unittest.TestCase):
    def setUp(self):
        os.environ["REPORTING_API_KEY"] = "test-key-value"
        self.router = build_router()

    def test_summary_requires_tenant(self):
        response = self.router.dispatch(
            Request.from_url("GET", "/v1/reports/summary", headers=HEADERS)
        )
        self.assertEqual(response.status, 400)

    def test_unknown_tenant_is_404(self):
        response = self.router.dispatch(
            Request.from_url("GET", "/v1/reports/summary?tenant=nope", headers=HEADERS)
        )
        self.assertEqual(response.status, 404)

    def test_summary_totals_only_captured_records(self):
        response = self.router.dispatch(
            Request.from_url("GET", "/v1/reports/summary?tenant=acme", headers=HEADERS)
        )
        self.assertEqual(response.status, 200)
        body = json.loads(response.body)
        self.assertEqual(body["record_count"], 5)
        self.assertEqual(body["captured_count"], 4)
        self.assertEqual(body["captured_total_minor"], 32460)

    def test_tenant_list(self):
        response = self.router.dispatch(Request.from_url("GET", "/v1/tenants", headers=HEADERS))
        self.assertEqual(json.loads(response.body)["tenants"], ["acme", "globex"])
