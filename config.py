import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    """Application configuration from environment variables."""
    
    # Slack Configuration
    SLACK_BOT_TOKEN = os.getenv("SLACK_BOT_TOKEN")
    SLACK_SIGNING_SECRET = os.getenv("SLACK_SIGNING_SECRET")
    SLACK_APP_TOKEN = os.getenv("SLACK_APP_TOKEN")  # For Socket Mode
    SLACK_CLIENT_ID = os.getenv("SLACK_CLIENT_ID")
    SLACK_CLIENT_SECRET = os.getenv("SLACK_CLIENT_SECRET")
    
    # Socket Mode (WebSocket)
    USE_SOCKET_MODE = os.getenv("USE_SOCKET_MODE", "true").lower() == "true"
    
    # Database Configuration
    DATABASE_URL = os.getenv(
        "DATABASE_URL",
        "mysql+pymysql://user:password@localhost:3306/slack_emoji"
    )
    
    # Datadog Configuration
    DD_SERVICE = os.getenv("DD_SERVICE", "slack-emoji-bot")
    DD_ENV = os.getenv("DD_ENV", "development")
    DD_VERSION = os.getenv("DD_VERSION", "1.0.0")
    
    # Public URL for serving preview images
    PUBLIC_URL = os.getenv("PUBLIC_URL", "https://your.server.com")
    
    # Application Configuration
    STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")
    FONTS_DIR = os.path.join(os.path.dirname(__file__), "fonts")
    
    # Image Generation Configuration
    EMOJI_SIZE = 128  # Slack emoji size in pixels
    DEFAULT_FONT = "NanumGothic.ttf"
    DEFAULT_FONT_SIZE = 32
    GIF_DURATION = 100  # milliseconds per frame
    GIF_FRAME_COUNT = 12  # number of frames for animations
    
    # Available fonts
    AVAILABLE_FONTS = {
        "nanumgothic": "NanumGothic.ttf",
        "nanumsquare": "NanumSquare.ttf",
        "nanumsquareround": "NanumSquareRoundEB.ttf",
        "nanummyeongjo": "NanumMyeongjoEB.ttf",
        "notosansmono": "NotoSansMonoCJKkr-Bold.otf",
        "ebsjusigyeong": "EBSJusigyeongB.ttf",
        "hoguk": "Hoguk.ttf",
    }
    
    # Available effects
    AVAILABLE_EFFECTS = [
        "none",
        "scroll",
        "party",
        "rotate",
        "shake",
        "wave",
        "typing",
        "grow",
    ]
    
    # Available resize modes for image emoji (similar to CSS object-fit)
    AVAILABLE_RESIZE_MODES = {
        "fill": "비율 무시하고 늘림",
        "cover": "비율 유지하며 중앙 크롭",
        "contain": "비율 유지, 여백 추가",
    }
    
    # Image effects available for uploaded images
    IMAGE_EFFECTS = [
        "none",
        "rotate",
        "shake",
        "party",
        "wave",
        "grow",
    ]
    
    # Background color options
    BACKGROUND_OPTIONS = {
        "transparent": (0, 0, 0, 0),
        "white": (255, 255, 255, 255),
        "black": (0, 0, 0, 255),
    }
