"""App Home handler for Slack."""

import logging

logger = logging.getLogger(__name__)


def register(app):
    """Register App Home handler to the Slack app."""
    
    @app.event("app_home_opened")
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
