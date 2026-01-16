"""Slack event handlers."""

import json
import logging

from ddtrace import tracer

logger = logging.getLogger(__name__)


def register(app):
    """Register event handlers to the Slack app."""
    
    @app.event("message")
    @tracer.wrap(service="emoji-generator", resource="event.message")
    def handle_message(event, client, say):
        """Handle message events to detect image uploads."""
        # Only process messages with files
        files = event.get("files", [])
        if not files:
            return
        
        # Check if it's a bot message (avoid loops)
        if event.get("bot_id"):
            return
        
        user_id = event.get("user")
        channel_id = event.get("channel")
        
        # Check for image files
        image_files = [
            f for f in files
            if f.get("mimetype", "").startswith("image/")
        ]
        
        if not image_files:
            return
        
        logger.info(f"[MESSAGE] 이미지 업로드 감지 - user: {user_id}, channel: {channel_id}, files: {len(image_files)}")
        
        # Send action message for each image
        for file_info in image_files:
            file_id = file_info.get("id")
            file_name = file_info.get("name", "image")
            file_url = file_info.get("url_private", "")
            
            try:
                client.chat_postEphemeral(
                    channel=channel_id,
                    user=user_id,
                    blocks=[
                        {
                            "type": "section",
                            "text": {
                                "type": "mrkdwn",
                                "text": f"📷 *{file_name}*\n이 이미지를 이모지로 만들까요?"
                            },
                            "accessory": {
                                "type": "button",
                                "text": {"type": "plain_text", "text": "이모지 만들기"},
                                "action_id": "create_image_emoji",
                                "value": json.dumps({
                                    "file_id": file_id,
                                    "file_url": file_url,
                                    "channel_id": channel_id,
                                }),
                                "style": "primary",
                            }
                        }
                    ],
                    text="이 이미지를 이모지로 만들까요?"
                )
            except Exception as e:
                logger.error(f"[MESSAGE] 액션 메시지 전송 실패: {e}")
