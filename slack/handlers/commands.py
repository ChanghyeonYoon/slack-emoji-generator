"""Slash command handlers for Slack."""

import logging

from ddtrace import tracer

from slack.views import build_emoji_modal, build_image_emoji_modal

logger = logging.getLogger(__name__)


def register(app):
    """Register slash command handlers to the Slack app."""
    
    @app.command("/이모지")
    @tracer.wrap(service="emoji-generator", resource="slash.emoji")
    def handle_emoji_command(ack, command, client):
        """Handle /이모지 slash command - opens modal for emoji creation."""
        ack()
        
        user_id = command.get("user_id")
        channel_id = command.get("channel_id")
        trigger_id = command.get("trigger_id")
        text_input = command.get("text", "").strip()
        
        logger.info(f"[SLASH] /이모지 명령어 수신 - user: {user_id}, channel: {channel_id}, text: '{text_input}'")
        
        # Open modal
        try:
            modal = build_emoji_modal(channel_id, text_input)
            client.views_open(trigger_id=trigger_id, view=modal)
        except Exception as e:
            logger.error(f"[SLASH] 모달 열기 실패: {e}")

    @app.command("/이미지이모지")
    @tracer.wrap(service="emoji-generator", resource="slash.image_emoji")
    def handle_image_emoji_command(ack, command, client):
        """Handle /이미지이모지 slash command - opens modal for image upload."""
        ack()
        
        user_id = command.get("user_id")
        channel_id = command.get("channel_id")
        trigger_id = command.get("trigger_id")
        
        logger.info(f"[SLASH] /이미지이모지 명령어 수신 - user: {user_id}, channel: {channel_id}")
        
        try:
            # 파일 업로드를 포함한 모달 열기
            modal = build_image_emoji_modal(channel_id)
            client.views_open(trigger_id=trigger_id, view=modal)
        except Exception as e:
            logger.error(f"[SLASH] 모달 열기 실패: {e}")
