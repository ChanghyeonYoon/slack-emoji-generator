"""Modal submission handlers for Slack."""

import json
import logging

import requests
from ddtrace import tracer
from slack_sdk import WebClient

from config import Config
from database import db
from database.models import GenerationLog
from generators import EmojiGenerator
from slack.emoji_uploader import EmojiUploader
from utils import upload_with_retry, sanitize_filename

logger = logging.getLogger(__name__)


def _log_generation(user_id, team_id, text, effect):
    """Log generation to database for analytics."""
    try:
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


def register(app):
    """Register modal submission handlers to the Slack app."""
    
    @app.view("image_emoji_modal")
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
            bot_client = WebClient(token=Config.SLACK_BOT_TOKEN)
            
            # Generate filename
            mode_suffix = f"_{resize_mode}" if resize_mode != "cover" else ""
            effect_suffix = f"_{effect}" if effect != "none" else ""
            filename = f"image_emoji{mode_suffix}{effect_suffix}.{ext}"
            
            upload_with_retry(
                bot_client,
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
                bot_client = WebClient(token=Config.SLACK_BOT_TOKEN)
                bot_client.chat_postEphemeral(
                    channel=channel_id,
                    user=user_id,
                    text=f"❌ 이미지 이모지 생성 중 오류가 발생했습니다: {str(e)}"
                )
            except:
                pass

    @app.view("emoji_create_modal")
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
                file_base = sanitize_filename(text)
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
                
                # Upload all at once with retry
                upload_with_retry(
                    bot_client,
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
                
                file_base = sanitize_filename(text)
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
                
                upload_with_retry(
                    bot_client,
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
                
                file_base = sanitize_filename(text)
                if effect != "none":
                    emoji_name = f"{file_base}_{effect}"
                else:
                    emoji_name = file_base
                
                filename = f"{emoji_name}.{ext}"
                upload_with_retry(
                    bot_client,
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

    @app.view("slash_emoji_modal")
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
                file_base = sanitize_filename(text)
                file_uploads = []
                for image_bytes, ext, tile_idx in tiles:
                    filename = f"{file_base}_{tile_idx + 1}.{ext}"
                    file_uploads.append({
                        "content": image_bytes,
                        "filename": filename,
                    })
                
                # Upload all at once with retry
                upload_with_retry(
                    bot_client,
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
                file_base = sanitize_filename(text)
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
                
                # Upload all at once with retry
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
            
            _log_generation(user_id, body.get("team", {}).get("id"), text, effect)
            
        except Exception as e:
            logger.error(f"[MODAL] 이모지 생성 오류: {e}", exc_info=True)
            bot_client.chat_postEphemeral(
                channel=channel_id,
                user=user_id,
                text=f"이모지 생성 중 오류가 발생했습니다: {str(e)}"
            )
