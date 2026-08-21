"""Reusable route decorators.

Keeps cross-cutting concerns (auth, error handling) out of the view bodies,
following the same decorator pattern used across our other microservices.
"""
import logging
from functools import wraps

from flask import current_app, request
from werkzeug.exceptions import HTTPException

from app.responses import error_response

logger = logging.getLogger(__name__)


def require_api_key(view):
    """Enforce an API key *only if* one is configured (Config.API_KEY).

    Reads a bearer token from the Authorization header, mirroring the
    header-token auth used in our other services. When no API_KEY is set the
    endpoint stays public — which is what the challenge's plain-curl test needs.
    """

    @wraps(view)
    def wrapper(*args, **kwargs):
        expected = current_app.config.get("API_KEY", "")
        if not expected:
            return view(*args, **kwargs)  # auth disabled → public

        auth_header = request.headers.get("Authorization", "")
        token = auth_header.split(" ", 1)[1] if " " in auth_header else auth_header
        if token != expected:
            return error_response(401, "Provide a valid API key.")
        return view(*args, **kwargs)

    return wrapper


def handle_errors(view):
    """Catch any unhandled exception and return a consistent error envelope,
    so a failure never leaks a stack trace to the client.

    Deliberate HTTP errors (e.g. RequestEntityTooLarge from MAX_CONTENT_LENGTH)
    are re-raised so Flask's own error handlers set the right status code —
    swallowing them here would turn a clean 413 into a misleading 500."""

    @wraps(view)
    def wrapper(*args, **kwargs):
        try:
            return view(*args, **kwargs)
        except HTTPException:
            raise
        except Exception as exc:  # noqa: BLE001 - deliberately broad at the edge
            logger.exception("Unhandled error in %s", view.__name__)
            return error_response(500, f"Internal server error: {exc}")

    return wrapper
