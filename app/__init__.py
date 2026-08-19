"""Application package.

Mirrors the microservice convention: create the Flask app here, load the
`Config`, then import the views so their routes register on import.
"""
from flask import Flask

from config import Config

app = Flask(__name__)
app.config.from_object(Config)

# Enforce the max upload size at the framework level too (Flask returns 413
# automatically if the body exceeds this).
app.config["MAX_CONTENT_LENGTH"] = Config.MAX_CONTENT_LENGTH

# Import views last so their @app.route decorators bind to the app above.
from app import views  # noqa: E402,F401
