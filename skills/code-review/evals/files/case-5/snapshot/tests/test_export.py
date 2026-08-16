import json
import os
import unittest

from app import export
from app.main import build_router
from app.router import Request

HEADERS = {"X-Api-Key": "REPLACE_ME_API_KEY"}


class ExportTests(unittest.TestCase):
    def setUp(self):
        os.environ["REPORTING_API_KEY"] = "test-key-value"
        self.router = build_router()

    def _get(self, url, headers=HEADERS):
        return self.router.dispatch(Request.from_url("GET", url, headers=headers))

    def test_requires_api_key(self):
        response = self._get("/v1/exports/records?tenant=acme", headers={})
        self.assertEqual(response.status, 401)

    def test_requires_tenant(self):
        response = self._get("/v1/exports/records")
        self.assertEqual(response.status, 400)

    def test_json_export_returns_json_body(self):
        response = self._get("/v1/exports/records?tenant=acme&format=json")
        self.assertEqual(response.status, 200)
        self.assertEqual(response.content_type, "application/json")
        self.assertIsInstance(json.loads(response.body), list)

    def test_csv_export_has_header_row(self):
        response = self._get("/v1/exports/records?tenant=acme&format=csv")
        self.assertEqual(response.status, 200)
        self.assertEqual(response.content_type, "text/csv")
        first_line = response.body.splitlines()[0]
        self.assertEqual(first_line.split(","), list(export.DEFAULT_COLUMNS))
