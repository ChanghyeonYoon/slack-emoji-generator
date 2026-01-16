"""Slack action handlers for button clicks and interactions."""

import json
import logging

import requests
from ddtrace import tracer
from slack_sdk import WebClient

from config import Config
from generators import EmojiGenerator
from slack.views import build_image_emoji_modal
from slack.emoji_uploader import EmojiUploader
from utils import upload_with_retry, sanitize_filename

logger = logging.getLogger(__name__)


def register(app):
    """Register action handlers to the Slack app."""
    
    @app.action("create_image_emoji")
    @tracer.wrap(service="emoji-generator", resource="action.create_image_emoji")
    def handle_create_image_emoji_button(ack, body, client):
        """Handle create image emoji button click - opens option modal."""
        ack()
        
        user_id = body["user"]["id"]
        value = body["actions"][0]["value"]
        trigger_id = body["trigger_id"]
        
        try:
            data = json.loads(value)
            file_id = data["file_id"]
            file_url = data["file_url"]
            channel_id = data["channel_id"]
        except (json.JSONDecodeError, KeyError) as e:
            logger.error(f"[ACTION] 잘못된 value 형식: {value}, error: {e}")
            return
        
        logger.info(f"[ACTION] 이미지 이모지 생성 버튼 클릭 - user: {user_id}, file: {file_id}")
        
        try:
            modal = build_image_emoji_modal(channel_id, file_id, file_url)
            client.views_open(trigger_id=trigger_id, view=modal)
        except Exception as e:
            logger.error(f"[ACTION] 모달 열기 실패: {e}")

    @app.action("share_emoji")
    @tracer.wrap(service="emoji-generator", resource="action.share")
    def handle_share_emoji(ack, body, client):
        """Handle share emoji button click (legacy)."""
        ack()
        
        user_id = body["user"]["id"]
        value = body["actions"][0]["value"]
        
        try:
            data = json.loads(value)
            channel_id = data["channel_id"]
            text = data["text"]
            effect = data["effect"]
            font = data.get("font", "nanumgothic")
            background = data.get("background", "transparent")
            text_color = data.get("text_color", "#000000")
        except (json.JSONDecodeError, KeyError) as e:
            logger.error(f"[SHARE] 잘못된 value 형식: {value}, error: {e}")
            return
        
        logger.info(f"[SHARE] 채널 공유 요청 - user: {user_id}, channel: {channel_id}, text: '{text}'")
        
        try:
            bot_client = WebClient(token=Config.SLACK_BOT_TOKEN)
            
            # Re-generate and send to channel with user's options
            generator = EmojiGenerator()
            
            if effect == "scroll":
                tiles = generator.generate_scroll_tiles(
                    text=text,
                    text_color=text_color,
                    background=background,
                    font_name=font,
                )
                file_base = sanitize_filename(text)
                file_uploads = []
                for image_bytes, ext, tile_idx in tiles:
                    filename = f"{file_base}_{tile_idx + 1}.{ext}"
                    file_uploads.append({
                        "content": image_bytes,
                        "filename": filename,
                    })
                upload_with_retry(
                    bot_client,
                    file_uploads=file_uploads,
                    channel=channel_id,
                    initial_comment=f"<@{user_id}>님이 생성한 스크롤 이모지입니다! (총 {len(tiles)}개)",
                )
            elif effect == "split":
                # 글자별 생성
                chars = list(text)
                file_base = sanitize_filename(text)
                file_uploads = []
                for idx, char in enumerate(chars[:20]):
                    if char.isspace():
                        continue
                    image_bytes, ext = generator.generate(
                        text=char,
                        effect="none",
                        text_color=text_color,
                        background=background,
                        font_name=font,
                    )
                    filename = f"{file_base}_{char}.{ext}"
                    file_uploads.append({
                        "content": image_bytes,
                        "filename": filename,
                    })
                upload_with_retry(
                    bot_client,
                    file_uploads=file_uploads,
                    channel=channel_id,
                    initial_comment=f"<@{user_id}>님이 생성한 글자별 이모지입니다! (총 {len(file_uploads)}개)",
                )
            else:
                image_bytes, ext = generator.generate(
                    text=text,
                    effect=effect,
                    text_color=text_color,
                    background=background,
                    font_name=font,
                )
                uploader = EmojiUploader(client)
                filename = uploader.generate_unique_filename(text, ext, effect)
                
                upload_with_retry(
                    bot_client,
                    content=image_bytes,
                    filename=filename,
                    channel=channel_id,
                    initial_comment=f"<@{user_id}>님이 생성한 이모지입니다!",
                )
            
            # Update original message
            original_channel = body["channel"]["id"]
            original_ts = body["message"]["ts"]
            
            client.chat_update(
                channel=original_channel,
                ts=original_ts,
                text=f"✅ 채널에 공유되었습니다!",
                blocks=[
                    {
                        "type": "section",
                        "text": {"type": "mrkdwn", "text": "✅ 채널에 공유되었습니다!"},
                    }
                ],
            )
            
            logger.info(f"[SHARE] 채널 공유 완료 - channel: {channel_id}")
            
        except Exception as e:
            logger.error(f"[SHARE] 공유 오류: {e}", exc_info=True)
