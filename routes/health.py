"""Health check endpoint."""

import logging

from flask import Blueprint, jsonify, request

from config import Config

logger = logging.getLogger(__name__)

health_bp = Blueprint("health", __name__)


@health_bp.route("/health", methods=["GET"])
def health_check():
    """Health check endpoint for Docker/Kubernetes."""
    logger.debug(f"[HEALTH] 헬스체크 요청 - IP: {request.remote_addr}")
    return jsonify({
        "status": "healthy",
        "service": Config.DD_SERVICE,
        "mode": "socket" if Config.USE_SOCKET_MODE else "http"
    })
