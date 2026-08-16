"""Minimal request/response plumbing and dispatch."""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from typing import Callable, Dict, Optional
from urllib.parse import parse_qs, urlparse

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class Request:
    method: str
    path: str
    query: Dict[str, str] = field(default_factory=dict)
    headers: Dict[str, str] = field(default_factory=dict)

    @classmethod
    def from_url(cls, method: str, url: str, headers: Optional[Dict[str, str]] = None) -> "Request":
        parsed = urlparse(url)
        query = {
            key: values[-1]
            for key, values in parse_qs(parsed.query, keep_blank_values=True).items()
        }
        return cls(
            method=method.upper(),
            path=parsed.path,
            query=query,
            headers={k: v for k, v in (headers or {}).items()},
        )


@dataclass(frozen=True)
class Response:
    status: int
    body: str = ""
    content_type: str = "application/json"

    @classmethod
    def error(cls, status: int, code: str, detail: Optional[str] = None) -> "Response":
        payload = {"error": code}
        if detail:
            payload["detail"] = detail
        return cls(status=status, body=json.dumps(payload), content_type="application/json")


class Router:
    def __init__(self) -> None:
        self._routes: Dict[tuple, Callable[[Request], Response]] = {}

    def add(self, method: str, path: str, handler: Callable[[Request], Response]) -> None:
        self._routes[(method.upper(), path)] = handler

    def dispatch(self, request: Request) -> Response:
        handler = self._routes.get((request.method, request.path))
        if handler is None:
            return Response.error(404, "not_found")
        try:
            return handler(request)
        except Exception:
            logger.exception("unhandled error serving %s %s", request.method, request.path)
            return Response.error(500, "internal_error")

    @property
    def routes(self) -> tuple:
        return tuple(sorted(self._routes))
