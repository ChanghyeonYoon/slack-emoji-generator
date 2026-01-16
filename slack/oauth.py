import logging
from flask import Blueprint, request, redirect, url_for
from slack_sdk import WebClient
from slack_sdk.oauth import AuthorizeUrlGenerator
from slack_sdk.oauth.installation_store import Installation

from config import Config
from database import TokenStore

logger = logging.getLogger(__name__)

oauth_bp = Blueprint("oauth", __name__, url_prefix="/oauth")

# OAuth scopes required for user token
USER_SCOPES = [
    "chat:write",      # Send messages as user
    "users:read",      # Read user info
]


@oauth_bp.route("/install")
def oauth_install():
    """
    Redirect to Slack OAuth authorization page.
    Users visit this URL to grant permissions.
    """
    authorize_url_generator = AuthorizeUrlGenerator(
        client_id=Config.SLACK_CLIENT_ID,
        user_scopes=USER_SCOPES,
        redirect_uri=_get_redirect_uri(),
    )
    
    url = authorize_url_generator.generate("")
    return redirect(url)


@oauth_bp.route("/callback")
def oauth_callback():
    """
    Handle OAuth callback from Slack.
    Exchange authorization code for user token and store it.
    """
    # Check for errors
    error = request.args.get("error")
    if error:
        logger.error(f"OAuth error: {error}")
        return f"권한 승인이 거부되었습니다: {error}", 400
    
    # Get authorization code
    code = request.args.get("code")
    if not code:
        return "인증 코드가 없습니다.", 400
    
    try:
        # Exchange code for token
        client = WebClient()
        response = client.oauth_v2_access(
            client_id=Config.SLACK_CLIENT_ID,
            client_secret=Config.SLACK_CLIENT_SECRET,
            code=code,
            redirect_uri=_get_redirect_uri(),
        )
        
        if not response["ok"]:
            logger.error(f"OAuth exchange failed: {response}")
            return "토큰 발급에 실패했습니다.", 500
        
        # Extract user token info
        authed_user = response.get("authed_user", {})
        user_id = authed_user.get("id")
        access_token = authed_user.get("access_token")
        scope = authed_user.get("scope", "")
        team_id = response.get("team", {}).get("id")
        
        if not user_id or not access_token:
            return "유저 토큰 정보가 없습니다.", 500
        
        # Store token in database
        token_store = TokenStore()
        success = token_store.save_token(
            user_id=user_id,
            team_id=team_id,
            access_token=access_token,
            scope=scope,
        )
        
        if success:
            logger.info(f"OAuth successful for user {user_id}")
            return """
            <html>
            <head><meta charset="utf-8"></head>
            <body style="font-family: sans-serif; text-align: center; padding: 50px;">
                <h1>✅ 권한 승인 완료!</h1>
                <p>이제 슬랙 이모티콘 제작소에서 본인 이름으로 메시지를 보낼 수 있습니다.</p>
                <p>이 창을 닫아도 됩니다.</p>
            </body>
            </html>
            """
        else:
            return "토큰 저장에 실패했습니다.", 500
            
    except Exception as e:
        logger.error(f"OAuth callback error: {e}", exc_info=True)
        return f"오류가 발생했습니다: {str(e)}", 500


def _get_redirect_uri():
    """Get OAuth redirect URI from environment or construct it."""
    import os
    redirect_uri = os.getenv("OAUTH_REDIRECT_URI")
    if redirect_uri:
        return redirect_uri
    
    # Fallback to constructed URI (may not work in all environments)
    return url_for("oauth.oauth_callback", _external=True)
