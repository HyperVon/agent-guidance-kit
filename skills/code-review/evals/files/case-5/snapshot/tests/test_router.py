import json
import unittest

from app.router import Request, Response, Router


class RequestParsingTests(unittest.TestCase):
    def test_parses_path_and_query(self):
        request = Request.from_url("get", "/v1/reports/summary?tenant=acme&limit=10")
        self.assertEqual(request.method, "GET")
        self.assertEqual(request.path, "/v1/reports/summary")
        self.assertEqual(request.query["tenant"], "acme")
        self.assertEqual(request.query["limit"], "10")

    def test_keeps_blank_values(self):
        request = Request.from_url("GET", "/v1/reports/summary?tenant=")
        self.assertEqual(request.query["tenant"], "")


class DispatchTests(unittest.TestCase):
    def test_unknown_route_returns_404(self):
        router = Router()
        response = router.dispatch(Request.from_url("GET", "/nope"))
        self.assertEqual(response.status, 404)
        self.assertEqual(json.loads(response.body)["error"], "not_found")

    def test_handler_exception_becomes_500(self):
        router = Router()

        def boom(request):
            raise RuntimeError("boom")

        router.add("GET", "/boom", boom)
        with self.assertLogs("app.router", level="ERROR"):
            response = router.dispatch(Request.from_url("GET", "/boom"))
        self.assertEqual(response.status, 500)

    def test_error_response_includes_detail(self):
        response = Response.error(400, "invalid_request", "tenant is required")
        self.assertEqual(json.loads(response.body)["detail"], "tenant is required")
