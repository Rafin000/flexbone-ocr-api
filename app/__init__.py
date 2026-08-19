"""Application factory.

`create_app()` builds and configures the Flask app, wires up the Flask-RESTX
Api, and registers the route namespaces. Keeping construction in a factory
makes the app easy to configure per-environment and to instantiate in tests.
"""
from flask import Flask
from flask_restx import Api
from werkzeug.exceptions import RequestEntityTooLarge

from config import Config


def create_app(config_class: type = Config) -> Flask:
    app = Flask(__name__)
    app.config.from_object(config_class)
    # Enforce the upload cap at the framework level (Flask returns 413).
    app.config["MAX_CONTENT_LENGTH"] = config_class.MAX_CONTENT_LENGTH

    api = Api(
        app,
        version="1.0.0",
        title="Flexbone OCR API",
        description=(
            "Serverless OCR API — extract text from JPG images using "
            "Google Cloud Vision. Interactive docs below."
        ),
        doc="/",  # interactive Swagger UI served at the root URL
    )

    # Register namespaces (route groups). Imported here to avoid circular imports.
    from app.namespaces.health import health_ns
    from app.namespaces.ocr import ocr_ns

    api.add_namespace(health_ns)
    api.add_namespace(ocr_ns)

    @app.errorhandler(RequestEntityTooLarge)
    def handle_too_large(_err):
        limit = config_class.MAX_FILE_SIZE_MB
        return {"success": False, "error": f"File exceeds the {limit} MB size limit."}, 413

    return app
