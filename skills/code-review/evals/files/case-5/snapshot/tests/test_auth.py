import os
import unittest

from app.auth import require_api_key
from app.router import Request


class ApiKeyTests(unittest.TestCase):
    def setUp(self):
        self._previous = os.environ.get("REPORTING_API_KEY")
        os.environ["REPORTING_API_KEY"] = "test-key-value"

    def tearDown(self):
        if self._previous is None:
            os.environ.pop("REPORTING_API_KEY", None)
        else:
            os.environ["REPORTING_API_KEY"] = self._previous

    def test_missing_header_is_rejected(self):
        response = require_api_key(Request.from_url("GET", "/v1/tenants"))
        self.assertIsNotNone(response)
        self.assertEqual(response.status, 401)

    def test_wrong_key_is_rejected(self):
        request = Request.from_url("GET", "/v1/tenants", headers={"X-Api-Key": "wrong"})
        response = require_api_key(request)
        self.assertEqual(response.status, 401)

    def test_matching_key_is_accepted(self):
        request = Request.from_url("GET", "/v1/tenants", headers={"X-Api-Key": "test-key-value"})
        self.assertIsNone(require_api_key(request))

    def test_unconfigured_key_fails_closed(self):
        os.environ.pop("REPORTING_API_KEY", None)
        request = Request.from_url("GET", "/v1/tenants", headers={"X-Api-Key": "anything"})
        response = require_api_key(request)
        self.assertEqual(response.status, 503)
