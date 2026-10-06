import logging
import os

from flask import Flask, jsonify
from flask_cors import CORS

from app.limiter import limiter


def create_app() -> Flask:
    logging.basicConfig(level=logging.INFO)

    app = Flask(__name__)
    # Roster screenshots are the only large uploads; phone screenshots run
    # a few MB at most.
    app.config["MAX_CONTENT_LENGTH"] = 10 * 1024 * 1024

    @app.errorhandler(413)
    def too_large(_exc):
        return jsonify({"error": "Screenshot is too large (10 MB max)"}), 413

    # Frontend dev server (Vite) runs on a different origin/port, so it needs
    # CORS to reach Flask. The frontend must never talk to OpenAI directly --
    # only this backend holds the API key. FRONTEND_ORIGIN scopes this down
    # in production; defaults to "*" so local dev needs no extra config.
    allowed_origins = os.environ.get("FRONTEND_ORIGIN", "*")
    CORS(app, resources={r"/api/*": {"origins": allowed_origins}})

    limiter.init_app(app)

    from app.routes import bp as api_bp

    app.register_blueprint(api_bp)

    return app
