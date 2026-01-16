"""Modal view builders for Slack interactions."""

import json


def get_default_state():
    """Get default state for emoji generator."""
    return {
        "text": "이모지",
        "effect": "none",
        "font": "nanumgothic",
        "background": "transparent",
        "text_color": "#000000",
    }


def build_image_emoji_modal(channel_id: str, file_id: str = None, file_url: str = None) -> dict:
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


def build_emoji_modal(channel_id: str, initial_text: str = "") -> dict:
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
