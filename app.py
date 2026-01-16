"""
Slack Emoji Bot - Main Application Entry Point

This module initializes and runs the Slack Emoji Bot application.
It sets up logging, Datadog APM, Flask, and Slack Bolt app.
"""

import logging
import threading

# Datadog APM - must be first
from ddtrace import patch_all, tracer
patch_all()

from flask import Flask, request, jsonify
from slack_bolt import App
from slack_bolt.adapter.flask import SlackRequestHandler
from slack_bolt.adapter.socket_mode import SocketModeHandler

from config import Config
from database import db
from slack import register_workflow_step
from slack.oauth import oauth_bp
from slack.handlers import register_all_handlers
from routes import register_routes

# ============================================================
# Logging Configuration
# ============================================================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(),  # Console output
    ]
)

# Set log levels for different modules
logging.getLogger("slack_bolt").setLevel(logging.INFO)
logging.getLogger("slack_sdk").setLevel(logging.INFO)
logging.getLogger("urllib3").setLevel(logging.WARNING)
logging.getLogger("werkzeug").setLevel(logging.INFO)

# Suppress ddtrace verbose logging
logging.getLogger("ddtrace").setLevel(logging.WARNING)
logging.getLogger("ddtrace.tracer").setLevel(logging.WARNING)
logging.getLogger("ddtrace.span").setLevel(logging.WARNING)
logging.getLogger("ddtrace.internal").setLevel(logging.WARNING)
logging.getLogger("ddtrace.propagation").setLevel(logging.WARNING)

logger = logging.getLogger(__name__)
logger.info("=" * 50)
logger.info("Slack Emoji Bot - Starting up...")
logger.info("=" * 50)

# ============================================================
# Datadog Tracer Configuration
# ============================================================

tracer.set_tags({
    "env": Config.DD_ENV,
    "version": Config.DD_VERSION,
    "service": Config.DD_SERVICE,
})

# ============================================================
# Slack Bolt App Initialization
# ============================================================

slack_app = App(
    token=Config.SLACK_BOT_TOKEN,
    signing_secret=Config.SLACK_SIGNING_SECRET,
    # Explicitly disable OAuth to use bot token
    oauth_settings=None,
    oauth_flow=None,
)

# Register workflow step
register_workflow_step(slack_app)

# Register all Slack handlers (commands, events, actions, modals, home)
register_all_handlers(slack_app)

# ============================================================
# Flask App Initialization
# ============================================================

app = Flask(__name__, static_folder=Config.STATIC_DIR, static_url_path="/static")
app.config["SQLALCHEMY_DATABASE_URI"] = Config.DATABASE_URL
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_recycle": 300,
    "pool_pre_ping": True,
}

# Initialize database
db.init_app(app)

# Register blueprints
app.register_blueprint(oauth_bp)
register_routes(app)

# Slack request handler for HTTP mode
handler = SlackRequestHandler(slack_app)


# ============================================================
# Slack Event Routes (HTTP Mode)
# ============================================================

@app.route("/slack/events", methods=["POST"])
def slack_events():
    """Handle Slack events (HTTP mode only)."""
    return handler.handle(request)


@app.route("/slack/interactions", methods=["POST"])
def slack_interactions():
    """Handle Slack interactions."""
    return handler.handle(request)


# ============================================================
# Error Handlers
# ============================================================

@app.errorhandler(404)
def not_found(error):
    return jsonify({"error": "Not found"}), 404


@app.errorhandler(500)
def internal_error(error):
    logger.error(f"Internal error: {error}", exc_info=True)
    return jsonify({"error": "Internal server error"}), 500


# ============================================================
# Socket Mode
# ============================================================

def run_socket_mode():
    """Run the app in Socket Mode (WebSocket)."""
    logger.info("=" * 50)
    logger.info("[SOCKET] Socket Mode 시작...")
    logger.info(f"[SOCKET] App Token: {Config.SLACK_APP_TOKEN[:20]}..." if Config.SLACK_APP_TOKEN else "[SOCKET] App Token: 없음!")
    logger.info("=" * 50)
    
    try:
        socket_handler = SocketModeHandler(slack_app, Config.SLACK_APP_TOKEN)
        logger.info("[SOCKET] WebSocket 연결 시도 중...")
        socket_handler.start()
    except Exception as e:
        logger.error(f"[SOCKET] Socket Mode 오류: {e}", exc_info=True)


def create_tables():
    """Create database tables."""
    with app.app_context():
        db.create_all()
        logger.info("Database tables created")


# ============================================================
# Main Entry Point
# ============================================================

if __name__ == "__main__":
    # Create tables
    create_tables()
    
    if Config.USE_SOCKET_MODE:
        # Socket Mode: Run WebSocket in background, Flask for health checks
        logger.info(f"Starting {Config.DD_SERVICE} with Socket Mode")
        
        # Start Socket Mode in background thread
        socket_thread = threading.Thread(target=run_socket_mode, daemon=True)
        socket_thread.start()
        
        # Run Flask for health checks and OAuth
        app.run(host="0.0.0.0", port=5000, debug=False)
    else:
        # HTTP Mode: Flask handles everything
        logger.info(f"Starting {Config.DD_SERVICE} in HTTP mode")
        app.run(host="0.0.0.0", port=5000, debug=True)
