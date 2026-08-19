"""WSGI entry point for gunicorn (production) and `python wsgi.py` (local dev)."""
from app import app
from config import Config

if __name__ == "__main__":
    # Local development server. Production uses gunicorn (see Dockerfile).
    app.run(host="0.0.0.0", port=Config.PORT, debug=True)
