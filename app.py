import os
import logging
import threading
import uuid
import json

# Datadog APM - must be first
from ddtrace import patch_all, tracer
patch_all()

from flask import Flask, request, jsonify
from slack_bolt import App
from slack_bolt.adapter.flask import SlackRequestHandler
from slack_bolt.adapter.socket_mode import SocketModeHandler

from config import Config
from generators import EmojiGenerator
from generators.image_processor import ResizeMode
from slack import register_workflow_step
from slack.oauth import oauth_bp
from database import db
import requests

# Configure logging
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

# Set Datadog tracer tags
tracer.set_tags({
    "env": Config.DD_ENV,
    "version": Config.DD_VERSION,
    "service": Config.DD_SERVICE,
})

# Initialize Slack Bolt app (disable OAuth mode to use bot token directly)
slack_app = App(
    token=Config.SLACK_BOT_TOKEN,
    signing_secret=Config.SLACK_SIGNING_SECRET,
    # Explicitly disable OAuth to use bot token
    oauth_settings=None,
    oauth_flow=None,
)

# Register workflow step
register_workflow_step(slack_app)

# ============================================================
# Interactive Message-based Emoji Generator
# ============================================================

def _get_default_state():
    """Get default state for emoji generator."""
    return {
        "text": "이모지",
        "effect": "none",
        "font": "nanumgothic",
        "background": "transparent",
        "text_color": "#000000",
    }


def _sanitize_emoji_name(name: str) -> str:
    """
    Sanitize emoji name to meet Slack requirements.
    - Lowercase only
    - Alphanumeric, underscores, and hyphens only
    - Max 100 characters
    """
    # Convert to lowercase
    name = name.lower()
    # Replace spaces with underscores
    name = name.replace(" ", "_")
    # Keep only allowed characters (remove Korean and other non-ASCII)
    allowed = set("abcdefghijklmnopqrstuvwxyz0123456789_-")
    name = "".join(c for c in name if c in allowed)
    # Ensure it starts with a letter
    if name and not name[0].isalpha():
        name = "e_" + name
    # Limit length
    name = name[:100]
    # Fallback if empty
    if not name:
        name = "custom_emoji"
    return name


def _sanitize_filename(name: str) -> str:
    """
    Sanitize text for use in filename.
    - Replace spaces with underscores
    - Keep only Korean, alphanumeric, and underscore
    """
    import re
    # Replace spaces with underscores
    name = name.replace(" ", "_")
    # Keep only Korean (Hangul), alphanumeric, and underscore
    # Remove all other special characters
    name = re.sub(r'[^\w가-힣]', '', name)
    # Replace multiple underscores with single underscore
    name = re.sub(r'_+', '_', name)
    # Remove leading/trailing underscores
    name = name.strip('_')
    # Limit length
    name = name[:50]
    # Fallback if empty
    if not name:
        name = "emoji"
    return name


def _build_image_emoji_modal(channel_id: str, file_id: str = None, file_url: str = None) -> dict:
    """Build modal view for image emoji creation with file upload."""
    blocks = [
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "📷 이미지를 업로드하여 128x128 이모지로 변환합니다."
            }
        },
        {"type": "divider"},
    ]
    
    # 파일이 이미 제공된 경우 (채널 업로드를 통해) vs 직접 업로드
    if file_id and file_url:
        # 이미 파일이 있는 경우 - 파일 정보 표시
        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "✅ 이미지가 선택되었습니다."
            }
        })
    else:
        # 파일 업로드 input 추가
        blocks.append({
            "type": "input",
            "block_id": "file_block",
            "label": {"type": "plain_text", "text": "이미지 파일"},
            "element": {
                "type": "file_input",
                "action_id": "file_input",
                "filetypes": ["png", "jpg", "jpeg", "gif", "webp"],
                "max_files": 1,
            },
            "hint": {"type": "plain_text", "text": "PNG, JPG, GIF, WEBP 형식 지원"},
        })
    
    # 공통 옵션들
    blocks.extend([
        {
            "type": "input",
            "block_id": "resize_mode_block",
            "label": {"type": "plain_text", "text": "리사이징 방식"},
            "element": {
                "type": "static_select",
                "action_id": "resize_mode_input",
                "initial_option": {
                    "text": {"type": "plain_text", "text": "Cover (크롭)"},
                    "value": "cover"
                },
                "options": [
                    {
                        "text": {"type": "plain_text", "text": "Cover (크롭)"},
                        "value": "cover"
                    },
                    {
                        "text": {"type": "plain_text", "text": "Contain (여백)"},
                        "value": "contain"
                    },
                    {
                        "text": {"type": "plain_text", "text": "Fill (늘리기)"},
                        "value": "fill"
                    },
                ],
            },
            "hint": {
                "type": "plain_text",
                "text": "Cover: 비율 유지하며 중앙 크롭 / Contain: 비율 유지, 여백 추가 / Fill: 비율 무시하고 늘림"
            },
        },
        {
            "type": "input",
            "block_id": "background_block",
            "label": {"type": "plain_text", "text": "배경색 (Contain 모드용)"},
            "element": {
                "type": "plain_text_input",
                "action_id": "background_input",
                "initial_value": "transparent",
                "placeholder": {"type": "plain_text", "text": "transparent 또는 #FFFFFF"},
            },
            "hint": {"type": "plain_text", "text": "Contain 모드에서 여백 색상. 투명: transparent / 색상: #FFFFFF"},
            "optional": True,
        },
        {
            "type": "input",
            "block_id": "effect_block",
            "label": {"type": "plain_text", "text": "애니메이션 효과"},
            "element": {
                "type": "static_select",
                "action_id": "effect_input",
                "initial_option": {
                    "text": {"type": "plain_text", "text": "없음 (정적)"},
                    "value": "none"
                },
                "options": [
                    {"text": {"type": "plain_text", "text": "없음 (정적)"}, "value": "none"},
                    {"text": {"type": "plain_text", "text": "회전"}, "value": "rotate"},
                    {"text": {"type": "plain_text", "text": "흔들림"}, "value": "shake"},
                    {"text": {"type": "plain_text", "text": "파티 (무지개색)"}, "value": "party"},
                    {"text": {"type": "plain_text", "text": "물결"}, "value": "wave"},
                    {"text": {"type": "plain_text", "text": "커지기"}, "value": "grow"},
                ],
            },
            "optional": True,
        },
    ])
    
    return {
        "type": "modal",
        "callback_id": "image_emoji_modal",
        "private_metadata": json.dumps({
            "channel_id": channel_id,
            "file_id": file_id or "",
            "file_url": file_url or "",
        }),
        "title": {"type": "plain_text", "text": "이미지 이모지 만들기"},
        "submit": {"type": "plain_text", "text": "만들기"},
        "close": {"type": "plain_text", "text": "취소"},
        "blocks": blocks,
    }


def _build_emoji_modal(channel_id: str, initial_text: str = "") -> dict:
    """Build modal view for emoji creation."""
    return {
        "type": "modal",
        "callback_id": "emoji_create_modal",
        "private_metadata": channel_id,
        "title": {"type": "plain_text", "text": "이모지 만들기"},
        "submit": {"type": "plain_text", "text": "만들기"},
        "close": {"type": "plain_text", "text": "취소"},
        "blocks": [
            {
                "type": "input",
                "block_id": "text_block",
                "label": {"type": "plain_text", "text": "텍스트"},
                "element": {
                    "type": "plain_text_input",
                    "action_id": "text_input",
                    "placeholder": {"type": "plain_text", "text": "이모지로 만들 텍스트를 입력하세요"},
                    "initial_value": initial_text,
                },
            },
            {
                "type": "input",
                "block_id": "effect_block",
                "label": {"type": "plain_text", "text": "효과"},
                "element": {
                    "type": "static_select",
                    "action_id": "effect_input",
                    "initial_option": {"text": {"type": "plain_text", "text": "없음 (정적)"}, "value": "none"},
                    "options": [
                        {"text": {"type": "plain_text", "text": "없음 (정적)"}, "value": "none"},
                        {"text": {"type": "plain_text", "text": "스크롤 (흘러가기)"}, "value": "scroll"},
                        {"text": {"type": "plain_text", "text": "파티 (무지개색)"}, "value": "party"},
                        {"text": {"type": "plain_text", "text": "회전"}, "value": "rotate"},
                        {"text": {"type": "plain_text", "text": "흔들림"}, "value": "shake"},
                        {"text": {"type": "plain_text", "text": "물결"}, "value": "wave"},
                        {"text": {"type": "plain_text", "text": "타이핑 (커서)"}, "value": "typing"},
                        {"text": {"type": "plain_text", "text": "커지기"}, "value": "grow"},
                        {"text": {"type": "plain_text", "text": "글자별 생성"}, "value": "split"},
                    ],
                },
            },
            {
                "type": "input",
                "block_id": "font_block",
                "label": {"type": "plain_text", "text": "폰트"},
                "element": {
                    "type": "static_select",
                    "action_id": "font_input",
                    "initial_option": {"text": {"type": "plain_text", "text": "나눔고딕"}, "value": "nanumgothic"},
                    "options": [
                        {"text": {"type": "plain_text", "text": "나눔고딕"}, "value": "nanumgothic"},
                        {"text": {"type": "plain_text", "text": "나눔스퀘어라운드 EB"}, "value": "nanumsquareround"},
                        {"text": {"type": "plain_text", "text": "나눔명조 EB"}, "value": "nanummyeongjo"},
                        {"text": {"type": "plain_text", "text": "Noto Sans Mono"}, "value": "notosansmono"},
                        {"text": {"type": "plain_text", "text": "EBS 주시경체"}, "value": "ebsjusigyeong"},
                        {"text": {"type": "plain_text", "text": "호국체"}, "value": "hoguk"},
                    ],
                },
            },
            {
                "type": "input",
                "block_id": "text_color_block",
                "label": {"type": "plain_text", "text": "글자색"},
                "element": {
                    "type": "plain_text_input",
                    "action_id": "text_color_input",
                    "initial_value": "#000000",
                    "placeholder": {"type": "plain_text", "text": "#000000"},
                },
                "hint": {"type": "plain_text", "text": "HEX 색상코드 (예: #FF0000)"},
            },
            {
                "type": "input",
                "block_id": "background_block",
                "label": {"type": "plain_text", "text": "배경색"},
                "element": {
                    "type": "plain_text_input",
                    "action_id": "background_input",
                    "initial_value": "transparent",
                    "placeholder": {"type": "plain_text", "text": "transparent 또는 #FFFFFF"},
                },
                "hint": {"type": "plain_text", "text": "투명: transparent / 색상: #FFFFFF"},
            },
        ],
    }


# Slash command - open modal
@slack_app.command("/이모지")
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
        modal = _build_emoji_modal(channel_id, text_input)
        client.views_open(trigger_id=trigger_id, view=modal)
    except Exception as e:
        logger.error(f"[SLASH] 모달 열기 실패: {e}")


# Slash command for image emoji
@slack_app.command("/이미지이모지")
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
        modal = _build_image_emoji_modal(channel_id)
        client.views_open(trigger_id=trigger_id, view=modal)
    except Exception as e:
        logger.error(f"[SLASH] 모달 열기 실패: {e}")


# Handle file shared in message (image upload detection)
@slack_app.event("message")
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


# Handle "create image emoji" button click
@slack_app.action("create_image_emoji")
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
        modal = _build_image_emoji_modal(channel_id, file_id, file_url)
        client.views_open(trigger_id=trigger_id, view=modal)
    except Exception as e:
        logger.error(f"[ACTION] 모달 열기 실패: {e}")


# Handle image emoji modal submission
@slack_app.view("image_emoji_modal")
@tracer.wrap(service="emoji-generator", resource="modal.image_emoji")
def handle_image_emoji_modal_submit(ack, body, client, view):
    """Handle image emoji creation modal submission."""
    ack()
    
    user_id = body["user"]["id"]
    
    try:
        metadata = json.loads(view.get("private_metadata", "{}"))
        channel_id = metadata.get("channel_id", "")
        file_id = metadata.get("file_id", "")
        file_url = metadata.get("file_url", "")
    except json.JSONDecodeError:
        logger.error("[MODAL] private_metadata 파싱 실패")
        return
    
    values = view["state"]["values"]
    
    # Extract values from modal
    resize_mode = values["resize_mode_block"]["resize_mode_input"]["selected_option"]["value"]
    background = values.get("background_block", {}).get("background_input", {}).get("value", "transparent") or "transparent"
    effect = values.get("effect_block", {}).get("effect_input", {}).get("selected_option", {}).get("value", "none") or "none"
    
    # file_input으로 업로드된 파일 확인
    uploaded_files = values.get("file_block", {}).get("file_input", {}).get("files", [])
    
    # 업로드된 파일이 있으면 사용, 없으면 metadata의 파일 사용
    if uploaded_files:
        file_info = uploaded_files[0]
        file_id = file_info.get("id", "")
        file_url = file_info.get("url_private", "")
        logger.info(f"[MODAL] 모달에서 업로드된 파일 사용 - file_id: {file_id}")
    
    if not file_url:
        logger.error("[MODAL] 파일 URL이 없습니다")
        try:
            client.chat_postEphemeral(
                channel=channel_id,
                user=user_id,
                text="❌ 이미지 파일을 업로드해주세요."
            )
        except:
            pass
        return
    
    logger.info(f"[MODAL] 이미지 이모지 생성 - user: {user_id}, file: {file_id}, mode: {resize_mode}, effect: {effect}")
    
    # Validate background color
    if background.lower() != "transparent" and not background.startswith("#"):
        background = "transparent"
    
    try:
        # Show loading message
        try:
            client.chat_postEphemeral(
                channel=channel_id,
                user=user_id,
                text="⏳ 이미지 처리 중입니다. 잠시만 기다려주세요."
            )
        except:
            pass
        
        # Download the image file
        headers = {"Authorization": f"Bearer {Config.SLACK_BOT_TOKEN}"}
        response = requests.get(file_url, headers=headers)
        
        if response.status_code != 200:
            raise ValueError(f"이미지 다운로드 실패: {response.status_code}")
        
        image_data = response.content
        
        # Generate emoji from image
        generator = EmojiGenerator()
        
        if effect == "none":
            image_bytes, ext = generator.generate_from_image(
                image_data=image_data,
                resize_mode=resize_mode,
                background=background,
            )
        else:
            image_bytes, ext = generator.generate_from_image_with_effect(
                image_data=image_data,
                effect=effect,
                resize_mode=resize_mode,
                background=background,
            )
        
        # Upload result
        from slack_sdk import WebClient
        bot_client = WebClient(token=Config.SLACK_BOT_TOKEN)
        
        # Generate filename
        mode_suffix = f"_{resize_mode}" if resize_mode != "cover" else ""
        effect_suffix = f"_{effect}" if effect != "none" else ""
        filename = f"image_emoji{mode_suffix}{effect_suffix}.{ext}"
        
        bot_client.files_upload_v2(
            content=image_bytes,
            filename=filename,
            channel=channel_id,
            initial_comment=f"<@{user_id}>님이 생성한 이미지 이모지입니다!",
        )
        
        # Suggest emoji name
        emoji_name = f"custom_{file_id[:8]}" if file_id else "custom_emoji"
        bot_client.chat_postEphemeral(
            channel=channel_id,
            user=user_id,
            text=f"📋 등록 후 사용할 이름 예시:\n```:{emoji_name}:```"
        )
        
        _log_generation(user_id, body.get("team", {}).get("id"), f"[image:{resize_mode}]", effect)
        
    except Exception as e:
        logger.error(f"[MODAL] 이미지 이모지 생성 오류: {e}", exc_info=True)
        try:
            from slack_sdk import WebClient
            bot_client = WebClient(token=Config.SLACK_BOT_TOKEN)
            bot_client.chat_postEphemeral(
                channel=channel_id,
                user=user_id,
                text=f"❌ 이미지 이모지 생성 중 오류가 발생했습니다: {str(e)}"
            )
        except:
            pass


# Modal submission handler
@slack_app.view("emoji_create_modal")
@tracer.wrap(service="emoji-generator", resource="modal.create")
def handle_emoji_modal_submit(ack, body, client, view):
    """Handle emoji creation modal submission."""
    ack()
    
    user_id = body["user"]["id"]
    channel_id = view.get("private_metadata", "")
    values = view["state"]["values"]
    
    # Extract values from modal
    text = values["text_block"]["text_input"]["value"] or ""
    effect = values["effect_block"]["effect_input"]["selected_option"]["value"]
    font = values["font_block"]["font_input"]["selected_option"]["value"]
    text_color = values["text_color_block"]["text_color_input"]["value"] or "#000000"
    background = values["background_block"]["background_input"]["value"] or "transparent"
    
    logger.info(f"[MODAL] 이모지 생성 - user: {user_id}, text: '{text}', effect: {effect}")
    
    # Validate text
    if not text.strip():
        try:
            client.chat_postEphemeral(
                channel=channel_id,
                user=user_id,
                text="⚠️ 텍스트를 입력해주세요."
            )
        except:
            pass
        return
    
    # Validate colors
    if not text_color.startswith("#"):
        text_color = "#000000"
    if background.lower() != "transparent" and not background.startswith("#"):
        background = "transparent"
    
    try:
        # Show loading message
        try:
            client.chat_postEphemeral(
                channel=channel_id,
                user=user_id,
                text="⏳ 생성 중입니다. 시간이 다소 소요될 수 있으니 잠시만 기다려주세요."
            )
        except:
            pass
        
        generator = EmojiGenerator()
        from slack_sdk import WebClient
        bot_client = WebClient(token=Config.SLACK_BOT_TOKEN)
        
        if effect == "scroll":
            tiles = generator.generate_scroll_tiles(
                text=text,
                text_color=text_color,
                background=background,
                font_name=font,
            )
            
            if not tiles:
                raise ValueError("스크롤 타일 생성 실패")
            
            # Generate all files first
            file_base = _sanitize_filename(text)
            file_uploads = []
            suggested_names = []
            for image_bytes, ext, tile_idx in tiles:
                name = f"{file_base}_{tile_idx + 1}"
                suggested_names.append(name)
                filename = f"{name}.{ext}"
                file_uploads.append({
                    "content": image_bytes,
                    "filename": filename,
                })
            
            # Upload all at once
            bot_client.files_upload_v2(
                file_uploads=file_uploads,
                channel=channel_id,
                initial_comment=f"<@{user_id}>님이 생성한 스크롤 이모지입니다! (총 {len(tiles)}개)",
            )
            
            # Show suggested names
            emoji_display = " ".join([f":{name}:" for name in suggested_names])
            bot_client.chat_postEphemeral(
                channel=channel_id,
                user=user_id,
                text=f"📋 등록 후 사용할 이름:\n```{emoji_display}```"
            )
            
        elif effect == "split":
            chars = list(text)
            
            if not chars:
                raise ValueError("텍스트가 비어있습니다")
            
            MAX_SPLIT_CHARS = 20
            if len(chars) > MAX_SPLIT_CHARS:
                chars = chars[:MAX_SPLIT_CHARS]
            
            file_base = _sanitize_filename(text)
            file_uploads = []
            suggested_names = []
            
            for idx, char in enumerate(chars):
                if char.isspace():
                    continue
                
                image_bytes, ext = generator.generate(
                    text=char,
                    effect="none",
                    text_color=text_color,
                    background=background,
                    font_name=font,
                )
                
                name = f"{file_base}_{char}"
                suggested_names.append(name)
                filename = f"{name}.{ext}"
                file_uploads.append({
                    "content": image_bytes,
                    "filename": filename,
                })
            
            bot_client.files_upload_v2(
                file_uploads=file_uploads,
                channel=channel_id,
                initial_comment=f"<@{user_id}>님이 생성한 글자별 이모지입니다! (총 {len(file_uploads)}개)",
            )
            
            emoji_display = " ".join([f":{name}:" for name in suggested_names])
            bot_client.chat_postEphemeral(
                channel=channel_id,
                user=user_id,
                text=f"📋 등록 후 사용할 이름:\n```{emoji_display}```"
            )
            
        else:
            image_bytes, ext = generator.generate(
                text=text,
                effect=effect,
                text_color=text_color,
                background=background,
                font_name=font,
            )
            
            file_base = _sanitize_filename(text)
            if effect != "none":
                emoji_name = f"{file_base}_{effect}"
            else:
                emoji_name = file_base
            
            filename = f"{emoji_name}.{ext}"
            bot_client.files_upload_v2(
                content=image_bytes,
                filename=filename,
                channel=channel_id,
                initial_comment=f"<@{user_id}>님이 생성한 이모지입니다!",
            )
            
            bot_client.chat_postEphemeral(
                channel=channel_id,
                user=user_id,
                text=f"📋 등록 후 사용할 이름:\n```:{emoji_name}:```"
            )
        
        _log_generation(user_id, body.get("team", {}).get("id"), text, effect)
        
    except Exception as e:
        logger.error(f"[MODAL] 이모지 생성 오류: {e}", exc_info=True)
        try:
            bot_client.chat_postEphemeral(
                channel=channel_id,
                user=user_id,
                text=f"❌ 이모지 생성 중 오류가 발생했습니다: {str(e)}"
            )
        except:
            pass


# Slash command modal submission
@slack_app.view("slash_emoji_modal")
@tracer.wrap(service="emoji-generator", resource="modal.create")
def handle_slash_modal_submit(ack, body, client, view):
    """Handle slash command modal submission."""
    ack()
    
    values = view["state"]["values"]
    user_id = body["user"]["id"]
    channel_id = view.get("private_metadata", "")
    
    text = values["text_input"]["text"]["value"]
    effect = values["effect_input"]["effect"]["selected_option"]["value"]
    font = values["font_input"]["font"]["selected_option"]["value"]
    background = values["background_input"]["background"]["value"].strip()
    text_color = values["text_color_input"]["text_color"]["value"].strip()
    
    logger.info(f"[MODAL] 이모지 생성 - user: {user_id}, text: '{text}', effect: {effect}")
    
    # Validate colors
    if not text_color.startswith("#"):
        text_color = "#000000"
    if background.lower() != "transparent" and not background.startswith("#"):
        background = "transparent"
    
    try:
        generator = EmojiGenerator()
        from slack_sdk import WebClient
        bot_client = WebClient(token=Config.SLACK_BOT_TOKEN)
        
        if effect == "scroll":
            tiles = generator.generate_scroll_tiles(
                text=text,
                text_color=text_color,
                background=background,
                font_name=font,
            )
            
            if not tiles:
                raise ValueError("스크롤 타일 생성 실패")
            
            # Generate all files first
            file_base = _sanitize_filename(text)
            file_uploads = []
            for image_bytes, ext, tile_idx in tiles:
                filename = f"{file_base}_{tile_idx + 1}.{ext}"
                file_uploads.append({
                    "content": image_bytes,
                    "filename": filename,
                })
            
            # Upload all at once
            bot_client.files_upload_v2(
                file_uploads=file_uploads,
                channel=channel_id,
                initial_comment=f"<@{user_id}>님이 생성한 스크롤 이모지입니다! (총 {len(tiles)}개)",
            )
        elif effect == "split":
            # 글자별 생성: 각 글자마다 개별 이모지 생성
            chars = list(text)
            
            if not chars:
                raise ValueError("텍스트가 비어있습니다")
            
            MAX_SPLIT_CHARS = 20
            if len(chars) > MAX_SPLIT_CHARS:
                chars = chars[:MAX_SPLIT_CHARS]
            
            # Generate all files first
            file_base = _sanitize_filename(text)
            file_uploads = []
            for idx, char in enumerate(chars):
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
            
            # Upload all at once
            bot_client.files_upload_v2(
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
            
            from slack.emoji_uploader import EmojiUploader
            uploader = EmojiUploader(client)
            filename = uploader.generate_unique_filename(text, ext, effect)
            
            bot_client.files_upload_v2(
                content=image_bytes,
                filename=filename,
                channel=channel_id,
                initial_comment=f"<@{user_id}>님이 생성한 이모지입니다!",
            )
        
        _log_generation(user_id, body.get("team", {}).get("id"), text, effect)
        
    except Exception as e:
        logger.error(f"[MODAL] 이모지 생성 오류: {e}", exc_info=True)
        bot_client.chat_postEphemeral(
            channel=channel_id,
            user=user_id,
            text=f"이모지 생성 중 오류가 발생했습니다: {str(e)}"
        )




# Legacy handlers (keep for compatibility)
@slack_app.action("share_emoji")
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
        from slack_sdk import WebClient
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
            file_base = _sanitize_filename(text)
            file_uploads = []
            for image_bytes, ext, tile_idx in tiles:
                filename = f"{file_base}_{tile_idx + 1}.{ext}"
                file_uploads.append({
                    "content": image_bytes,
                    "filename": filename,
                })
            bot_client.files_upload_v2(
                file_uploads=file_uploads,
                channel=channel_id,
                initial_comment=f"<@{user_id}>님이 생성한 스크롤 이모지입니다! (총 {len(tiles)}개)",
            )
        elif effect == "split":
            # 글자별 생성
            chars = list(text)
            file_base = _sanitize_filename(text)
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
            bot_client.files_upload_v2(
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
            from slack.emoji_uploader import EmojiUploader
            uploader = EmojiUploader(client)
            filename = uploader.generate_unique_filename(text, ext, effect)
            
            bot_client.files_upload_v2(
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


@slack_app.event("app_home_opened")
def handle_app_home(client, event):
    """Display app home with usage guide."""
    user_id = event.get("user")
    
    blocks = [
        {
            "type": "header",
            "text": {"type": "plain_text", "text": "🎨 이모티콘 제작소"}
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "다양한 애니메이션 효과가 적용된 커스텀 이모지를 만들어보세요!"
            }
        },
        {"type": "divider"},
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "*사용 방법*\n\n• 텍스트 이모지: `/이모지` 명령어\n• 이미지 이모지: `/이미지이모지` 명령어 또는 이미지 업로드"
            }
        },
        {"type": "divider"},
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "*지원하는 효과*"
            }
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "• *없음 (정적)* - 움직이지 않는 기본 이모지\n• *스크롤* - 텍스트가 옆으로 흘러가는 효과\n• *파티* - 무지개색으로 변하는 효과\n• *회전* - 빙글빙글 회전하는 효과\n• *흔들림* - 좌우로 흔들리는 효과\n• *물결* - 물결치듯 움직이는 효과\n• *타이핑* - 타이핑되는 듯한 효과\n• *커지기* - 크기가 커졌다 작아지는 효과\n• *글자별 생성* - 각 글자를 개별 이모지로 생성"
            }
        },
        {"type": "divider"},
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "*지원하는 폰트*"
            }
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "• 나눔고딕\n• 나눔스퀘어\n• 나눔스퀘어라운드 EB\n• 나눔명조 EB\n• Noto Sans Mono\n• EBS 주시경체\n• 호국체"
            }
        },
        {"type": "divider"},
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "*📷 이미지 이모지 리사이징 옵션*"
            }
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "• *Cover (크롭)* - 비율 유지하며 중앙에서 크롭\n• *Contain (여백)* - 비율 유지, 남는 공간은 배경색으로 채움\n• *Fill (늘리기)* - 비율 무시하고 이미지를 늘림"
            }
        },
        {"type": "divider"},
        {
            "type": "context",
            "elements": [
                {
                    "type": "mrkdwn",
                    "text": "💡 생성된 이미지를 다운로드하여 Slack 설정 → 이모지 사용자화에서 등록하세요."
                }
            ]
        }
    ]
    
    try:
        client.views_publish(user_id=user_id, view={"type": "home", "blocks": blocks})
    except Exception as e:
        # App Home may not be enabled in Slack app settings - silently ignore
        logger.debug(f"[HOME] App Home 발행 실패 (비활성화 상태일 수 있음): {e}")



def _log_generation(user_id, team_id, text, effect):
    """Log generation to database for analytics."""
    try:
        from database.models import GenerationLog
        log = GenerationLog(
            user_id=user_id,
            team_id=team_id,
            text=text[:100] if text else None,
            effect=effect,
        )
        db.session.add(log)
        db.session.commit()
    except Exception as e:
        logger.warning(f"Failed to log generation: {e}")


# Initialize Flask app
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

# Slack request handler for HTTP mode
handler = SlackRequestHandler(slack_app)


@app.route("/health", methods=["GET"])
def health_check():
    """Health check endpoint for Docker/Kubernetes."""
    logger.debug(f"[HEALTH] 헬스체크 요청 - IP: {request.remote_addr}")
    return jsonify({
        "status": "healthy",
        "service": Config.DD_SERVICE,
        "mode": "socket" if Config.USE_SOCKET_MODE else "http"
    })


@app.route("/slack/events", methods=["POST"])
def slack_events():
    """Handle Slack events (HTTP mode only)."""
    return handler.handle(request)


@app.route("/slack/interactions", methods=["POST"])
def slack_interactions():
    """Handle Slack interactions."""
    return handler.handle(request)


@app.route("/api/generate", methods=["POST"])
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
        
        import base64
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


# Error handlers
@app.errorhandler(404)
def not_found(error):
    return jsonify({"error": "Not found"}), 404


@app.errorhandler(500)
def internal_error(error):
    logger.error(f"Internal error: {error}", exc_info=True)
    return jsonify({"error": "Internal server error"}), 500


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
