"""WSGI entry point.

`app` is what gunicorn serves (see Dockerfile). Running this file directly
starts Flask's dev server for local use.
"""
from app import create_app
from config import Config

app = create_app()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=Config.PORT, debug=True)
