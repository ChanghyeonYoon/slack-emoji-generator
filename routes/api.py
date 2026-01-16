"""REST API endpoints."""

import base64
import logging

from flask import Blueprint, jsonify, request
from ddtrace import tracer

from generators import EmojiGenerator

logger = logging.getLogger(__name__)

api_bp = Blueprint("api", __name__)


@api_bp.route("/api/generate", methods=["POST"])
@tracer.wrap(service="emoji-generator", resource="api.generate")
def api_generate():
    """REST API endpoint for generating emojis."""
    logger.info(f"[API] /api/generate 요청 수신 - IP: {request.remote_addr}")
    
    try:
        data = request.get_json()
        logger.debug(f"[API] 요청 데이터: {data}")
        
        if not data or "text" not in data:
            logger.warning("[API] 잘못된 요청 - text 필드 누락")
            return jsonify({"error": "text is required"}), 400
        
        text = data["text"]
        effect = data.get("effect", "none")
        
        logger.info(f"[API] 이모지 생성 시작 - text: '{text}', effect: {effect}")
        
        span = tracer.current_span()
        if span:
            span.set_tag("emoji.text", text[:50])
            span.set_tag("emoji.effect", effect)
        
        generator = EmojiGenerator()
        image_bytes, ext = generator.generate(
            text=text,
            effect=effect,
            text_color=data.get("text_color", "#000000"),
            background=data.get("background", "transparent"),
            font_name=data.get("font", "nanumgothic"),
            line_break_at=data.get("line_break_at", 0),
        )
        
        logger.info(f"[API] 이모지 생성 완료 - format: {ext}, size: {len(image_bytes)} bytes")
        
        image_base64 = base64.b64encode(image_bytes).decode("utf-8")
        
        logger.info(f"[API] 응답 전송 - text: '{text}', effect: {effect}")
        
        return jsonify({
            "success": True,
            "image": image_base64,
            "format": ext,
        })
        
    except Exception as e:
        logger.error(f"[API] 이모지 생성 오류: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500
