import logging
from slack_bolt import App
from slack_bolt.workflows.step import WorkflowStep

from generators import EmojiGenerator
from config import Config

logger = logging.getLogger(__name__)


def register_workflow_step(app: App):
    """
    Register the emoji generator workflow step with the Slack app.
    
    This creates a custom workflow step that can be used in Slack Workflow Builder
    to generate emoji images with various effects.
    """
    
    # Define the workflow step
    emoji_step = WorkflowStep(
        callback_id="emoji_generator_step",
        edit=edit_handler,
        save=save_handler,
        execute=execute_handler,
    )
    
    app.step(emoji_step)
    logger.info("Emoji generator workflow step registered")


def edit_handler(ack, step, configure):
    """
    Handle the workflow step edit event.
    Called when a user adds or edits the step in Workflow Builder.
    """
    ack()
    
    # Get current values if editing existing step
    inputs = step.get("inputs", {})
    
    # Build the configuration form
    blocks = [
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "*이모티콘 제작 설정*\n원하는 옵션을 선택하세요."
            }
        },
        {
            "type": "divider"
        },
        {
            "type": "input",
            "block_id": "text_input",
            "element": {
                "type": "plain_text_input",
                "action_id": "text",
                "placeholder": {
                    "type": "plain_text",
                    "text": "이모지로 만들 텍스트를 입력하세요"
                },
                "initial_value": inputs.get("text", {}).get("value", "")
            },
            "label": {
                "type": "plain_text",
                "text": "텍스트"
            }
        },
        {
            "type": "input",
            "block_id": "effect_input",
            "element": {
                "type": "static_select",
                "action_id": "effect",
                "placeholder": {
                    "type": "plain_text",
                    "text": "효과 선택"
                },
                "options": [
                    {"text": {"type": "plain_text", "text": "없음 (정적)"}, "value": "none"},
                    {"text": {"type": "plain_text", "text": "스크롤 (흘러가기)"}, "value": "scroll"},
                    {"text": {"type": "plain_text", "text": "파티 (무지개색)"}, "value": "party"},
                    {"text": {"type": "plain_text", "text": "회전"}, "value": "rotate"},
                    {"text": {"type": "plain_text", "text": "흔들림"}, "value": "shake"},
                    {"text": {"type": "plain_text", "text": "물결"}, "value": "wave"},
                    {"text": {"type": "plain_text", "text": "타이핑 (커서)"}, "value": "typing"},
                    {"text": {"type": "plain_text", "text": "커지기"}, "value": "grow"},
                ],
                "initial_option": _get_initial_option(inputs, "effect", "none")
            },
            "label": {
                "type": "plain_text",
                "text": "효과"
            }
        },
        {
            "type": "input",
            "block_id": "background_input",
            "element": {
                "type": "plain_text_input",
                "action_id": "background",
                "placeholder": {
                    "type": "plain_text",
                    "text": "transparent 또는 #FFFFFF"
                },
                "initial_value": inputs.get("background", {}).get("value", "transparent")
            },
            "label": {
                "type": "plain_text",
                "text": "배경색 (transparent 또는 HEX)"
            }
        },
        {
            "type": "input",
            "block_id": "text_color_input",
            "element": {
                "type": "plain_text_input",
                "action_id": "text_color",
                "placeholder": {
                    "type": "plain_text",
                    "text": "#000000"
                },
                "initial_value": inputs.get("text_color", {}).get("value", "#000000")
            },
            "label": {
                "type": "plain_text",
                "text": "글씨색 (HEX)"
            }
        },
        {
            "type": "input",
            "block_id": "font_input",
            "element": {
                "type": "static_select",
                "action_id": "font",
                "placeholder": {
                    "type": "plain_text",
                    "text": "폰트 선택"
                },
                "options": [
                    {"text": {"type": "plain_text", "text": "Noto Sans Mono CJK KR Bold"}, "value": "notosansmono"},
                    {"text": {"type": "plain_text", "text": "나눔스퀘어라운드 Extra Bold"}, "value": "nanumsquareround"},
                    {"text": {"type": "plain_text", "text": "나눔명조 Extra Bold"}, "value": "nanummyeongjo"},
                    {"text": {"type": "plain_text", "text": "EBS 주시경체 Bold"}, "value": "ebsjusigyeong"},
                    {"text": {"type": "plain_text", "text": "호국체 Bold"}, "value": "hoguk"},
                    {"text": {"type": "plain_text", "text": "나눔고딕"}, "value": "nanumgothic"},
                    {"text": {"type": "plain_text", "text": "나눔스퀘어"}, "value": "nanumsquare"},
                ],
                "initial_option": _get_initial_option(inputs, "font", "notosansmono")
            },
            "label": {
                "type": "plain_text",
                "text": "폰트"
            }
        },
        {
            "type": "input",
            "block_id": "line_break_input",
            "element": {
                "type": "plain_text_input",
                "action_id": "line_break_at",
                "placeholder": {
                    "type": "plain_text",
                    "text": "0 (줄바꿈 없음)"
                },
                "initial_value": inputs.get("line_break_at", {}).get("value", "0")
            },
            "label": {
                "type": "plain_text",
                "text": "줄바꿈 위치 (N번째 글자)"
            },
            "optional": True
        },
    ]
    
    configure(blocks=blocks)


def _get_initial_option(inputs, field, default):
    """Get initial option for select elements."""
    value = inputs.get(field, {}).get("value", default)
    
    option_labels = {
        "effect": {
            "none": "없음 (정적)",
            "scroll": "스크롤 (흘러가기)",
            "party": "파티 (무지개색)",
            "rotate": "회전",
            "shake": "흔들림",
            "wave": "물결",
            "typing": "타이핑 (커서)",
            "grow": "커지기",
        },
        "background": {
            "transparent": "투명",
            "white": "흰색",
            "black": "검정",
        },
        "font": {
            "notosansmono": "Noto Sans Mono CJK KR Bold",
            "nanumsquareround": "나눔스퀘어라운드 Extra Bold",
            "nanummyeongjo": "나눔명조 Extra Bold",
            "ebsjusigyeong": "EBS 주시경체 Bold",
            "hoguk": "호국체 Bold",
            "nanumgothic": "나눔고딕",
            "nanumsquare": "나눔스퀘어",
        }
    }
    
    labels = option_labels.get(field, {})
    label = labels.get(value, value)
    
    return {"text": {"type": "plain_text", "text": label}, "value": value}


def save_handler(ack, view, update):
    """
    Handle the workflow step save event.
    Called when user saves the step configuration.
    """
    values = view["state"]["values"]
    
    # Extract values from form
    inputs = {
        "text": {"value": values["text_input"]["text"]["value"]},
        "effect": {"value": values["effect_input"]["effect"]["selected_option"]["value"]},
        "background": {"value": values["background_input"]["background"]["value"]},
        "text_color": {"value": values["text_color_input"]["text_color"]["value"]},
        "font": {"value": values["font_input"]["font"]["selected_option"]["value"]},
        "line_break_at": {"value": values["line_break_input"]["line_break_at"]["value"] or "0"},
    }
    
    # Define outputs
    outputs = [
        {
            "type": "text",
            "name": "emoji_url",
            "label": "생성된 이모지 URL",
        },
        {
            "type": "text",
            "name": "emoji_filename",
            "label": "파일명",
        },
    ]
    
    update(inputs=inputs, outputs=outputs)
    ack()


def execute_handler(step, complete, fail, client):
    """
    Handle the workflow step execution.
    Called when the workflow runs and reaches this step.
    """
    try:
        inputs = step["inputs"]
        
        # Extract input values
        text = inputs["text"]["value"]
        effect = inputs["effect"]["value"]
        background = inputs["background"]["value"]
        text_color = inputs["text_color"]["value"]
        font = inputs["font"]["value"]
        line_break_at = int(inputs["line_break_at"]["value"])
        
        logger.info(f"Generating emoji: text='{text}', effect='{effect}'")
        
        # Generate emoji
        generator = EmojiGenerator()
        image_bytes, ext = generator.generate(
            text=text,
            effect=effect,
            text_color=text_color,
            background=background,
            font_name=font,
            line_break_at=line_break_at,
        )
        
        # Create unique filename to avoid conflicts
        from slack.emoji_uploader import EmojiUploader
        uploader = EmojiUploader(client)
        filename = uploader.generate_unique_filename(text, ext, effect)
        
        # Upload file to Slack
        response = client.files_upload_v2(
            content=image_bytes,
            filename=filename,
            title=f"{text} ({effect})",
        )
        
        # Get file URL
        file_info = response.get("file", {})
        file_url = file_info.get("url_private", "")
        
        logger.info(f"Emoji generated successfully: {filename}")
        
        # Complete the step with outputs
        complete(outputs={
            "emoji_url": file_url,
            "emoji_filename": filename,
        })
        
    except Exception as e:
        logger.error(f"Error generating emoji: {e}", exc_info=True)
        fail(error={"message": f"이모지 생성 중 오류가 발생했습니다: {str(e)}"})
