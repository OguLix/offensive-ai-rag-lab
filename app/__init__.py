"""Flask application factory for the demo UI.

The UI is only a window onto the pipeline: no retrieval or prompt logic lives here.
"""

from __future__ import annotations

from flask import Flask

from ragbot.config import load_settings


def create_app() -> Flask:
    """Build the app and load settings once, so routes never re-read YAML per request."""
    settings = load_settings()

    app = Flask(__name__)
    app.config["RAGBOT_SETTINGS"] = settings

    # Diimpor di dalam fungsi untuk menghindari impor melingkar saat paket app dimuat.
    from app.routes import bp

    app.register_blueprint(bp)
    return app
