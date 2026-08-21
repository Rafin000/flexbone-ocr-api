"""Application factory.

`create_app()` builds and configures the Flask app, sets up logging, the
rate limiter and the result cache, wires the Flask-RESTX Api, and registers
the route namespaces.
"""
import logging

from flask import Flask
from flask_restx import Api
from werkzeug.exceptions import HTTPException, RequestEntityTooLarge

from config import Config


def create_app(config_class: type = Config) -> Flask:
    app = Flask(__name__)
    app.config.from_object(config_class)
    app.config["MAX_CONTENT_LENGTH"] = config_class.MAX_CONTENT_LENGTH
    # Keep error bodies to our own envelope — without this Flask-RESTX appends
    # its raw "message" (e.g. the werkzeug 413 text) alongside our "error".
    app.config["ERROR_INCLUDE_MESSAGE"] = False

    _configure_logging(config_class)
    _configure_cache(config_class)

    api = Api(
        app,
        version="1.0.0",
        title="Flexbone OCR API",
        description=(
            "Serverless OCR API — extract text from images using Google Cloud "
            "Vision. Try the endpoints below."
        ),
        doc="/",  # interactive Swagger UI at the root URL
    )

    # Rate limiter (bonus). Initialized against the app; disabled via config.
    from app.extensions import limiter

    limiter.enabled = config_class.RATE_LIMIT_ENABLED
    limiter.init_app(app)

    # Register namespaces (route groups). Imported here to avoid circular imports.
    from app.namespaces.health import health_ns
    from app.namespaces.ocr import ocr_ns

    api.add_namespace(health_ns)
    api.add_namespace(ocr_ns)

    # Registered on the Api (not the app): Flask-RESTX routes errors raised inside
    # a Resource through its own handler, so an app-level handler would be bypassed
    # and the client would get RESTX's {"message": ...} instead of our envelope.
    @api.errorhandler(RequestEntityTooLarge)
    def handle_too_large(_err):
        limit = config_class.MAX_FILE_SIZE_MB
        return {"success": False, "error": f"File exceeds the {limit} MB size limit."}, 413

    @api.errorhandler(HTTPException)
    def handle_http_exception(err):
        # Catch-all so framework-raised errors (429 from the rate limiter, 405,
        # ...) still answer with the same {success, error} envelope as the routes.
        return {"success": False, "error": err.description}, err.code or 500

    return app


def _configure_logging(config_class: type) -> None:
    logging.basicConfig(
        level=getattr(logging, config_class.LOG_LEVEL, logging.INFO),
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    )


def _configure_cache(config_class: type) -> None:
    from app.cache import ocr_cache

    ocr_cache._max = config_class.CACHE_MAX_ENTRIES
