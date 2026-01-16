import logging
from typing import Optional, Tuple
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

logger = logging.getLogger(__name__)


class EmojiUploader:
    """
    Handle uploading custom emojis to Slack workspace.
    
    Note: Uploading custom emojis requires admin privileges and
    the admin.emoji:write scope, which is only available to
    Slack Enterprise Grid customers or workspace admins.
    """
    
    MAX_RETRY_COUNT = 10  # Maximum number of retries with incremented suffix
    
    def __init__(self, client: WebClient):
        self.client = client
    
    def upload_emoji(
        self,
        name: str,
        image_bytes: bytes,
        auto_increment: bool = True,
    ) -> Tuple[bool, str, str]:
        """
        Upload an emoji to the Slack workspace.
        If the name is taken and auto_increment is True, try with incremented suffix.
        
        Note: This requires admin.emoji:write scope which is only available for
        Enterprise Grid workspaces. For regular workspaces, this will fail and
        the caller should fallback to file upload with manual registration instructions.
        
        Args:
            name: Emoji name (without colons)
            image_bytes: Image data as bytes
            auto_increment: If True, retry with _1, _2, etc. when name is taken
            
        Returns:
            Tuple of (success, message, final_emoji_name)
        """
        # Sanitize emoji name
        base_name = self._sanitize_emoji_name(name)
        current_name = base_name
        
        # First, check if emoji.list is available to find available name
        try:
            if auto_increment:
                current_name = self.get_available_name(base_name)
        except Exception as e:
            logger.warning(f"Could not check available name: {e}")
            current_name = base_name
        
        # Try to upload using admin.emoji.add API
        # This requires:
        # 1. Enterprise Grid workspace OR
        # 2. Admin privileges with admin.emoji:write scope
        try:
            logger.info(f"Attempting to upload emoji: {current_name}")
            
            # admin.emoji.add requires a publicly accessible URL
            # We need to first upload the file and get a public URL
            # But files.sharedPublicURL requires user token, not bot token
            
            # For now, return failure - Enterprise Grid would need different handling
            # Most workspaces will need manual emoji registration
            return False, "이모지 자동 등록은 Enterprise Grid에서만 지원됩니다.", current_name
                
        except SlackApiError as e:
            error = e.response.get("error", "Unknown error")
            logger.warning(f"Emoji upload not available: {error}")
            
            if error == "missing_scope":
                return False, "이모지 등록 권한이 없습니다 (admin.emoji:write 필요)", current_name
            elif error == "not_allowed_token_type":
                return False, "Bot Token으로는 이모지 등록이 불가능합니다", current_name
            else:
                return False, f"이모지 등록 불가: {error}", current_name
    
    def check_emoji_exists(self, name: str) -> bool:
        """
        Check if an emoji with the given name already exists.
        
        Args:
            name: Emoji name to check
            
        Returns:
            True if exists, False otherwise
        """
        try:
            response = self.client.emoji_list()
            if response["ok"]:
                emoji_dict = response.get("emoji", {})
                safe_name = self._sanitize_emoji_name(name)
                return safe_name in emoji_dict
        except SlackApiError as e:
            logger.warning(f"Could not check emoji existence: {e}")
        return False
    
    def get_available_name(self, base_name: str) -> str:
        """
        Get an available emoji name by checking existing emojis.
        
        Args:
            base_name: Base name to check
            
        Returns:
            Available emoji name (with suffix if needed)
        """
        safe_name = self._sanitize_emoji_name(base_name)
        
        try:
            response = self.client.emoji_list()
            if not response["ok"]:
                return safe_name
            
            emoji_dict = response.get("emoji", {})
            
            # Check if base name is available
            if safe_name not in emoji_dict:
                return safe_name
            
            # Find available name with suffix
            for i in range(1, self.MAX_RETRY_COUNT + 1):
                candidate = f"{safe_name}_{i}"
                if candidate not in emoji_dict:
                    return candidate
            
            # All names taken, return with timestamp
            import time
            return f"{safe_name}_{int(time.time())}"
            
        except SlackApiError as e:
            logger.warning(f"Could not get emoji list: {e}")
            return safe_name
    
    def upload_file_and_share(
        self,
        image_bytes: bytes,
        filename: str,
        channel_id: str,
        title: Optional[str] = None,
        message: Optional[str] = None,
    ) -> Tuple[bool, str]:
        """
        Upload image as a file and share to a channel.
        
        This is an alternative when emoji upload is not available.
        
        Args:
            image_bytes: Image data as bytes
            filename: Filename for the upload
            channel_id: Channel to share the file
            title: Optional title for the file
            message: Optional message to accompany the file
            
        Returns:
            Tuple of (success, file_url or error message)
        """
        try:
            response = self.client.files_upload_v2(
                content=image_bytes,
                filename=filename,
                title=title or filename,
                channel=channel_id,
                initial_comment=message,
            )
            
            if response["ok"]:
                file_info = response.get("file", {})
                file_url = file_info.get("url_private", "")
                return True, file_url
            else:
                return False, f"파일 업로드 실패: {response.get('error', 'Unknown error')}"
                
        except SlackApiError as e:
            logger.error(f"File upload error: {e}", exc_info=True)
            return False, f"파일 업로드 중 오류: {e.response.get('error', 'Unknown error')}"
    
    def generate_unique_filename(
        self,
        base_name: str,
        extension: str,
        effect: str = "none",
    ) -> str:
        """
        Generate a unique filename with auto-increment suffix if needed.
        
        Args:
            base_name: Base name for the file
            extension: File extension (png, gif)
            effect: Effect name to include
            
        Returns:
            Unique filename
        """
        import time
        import hashlib
        
        # Create a short hash for uniqueness
        timestamp = str(time.time())
        hash_input = f"{base_name}{effect}{timestamp}"
        short_hash = hashlib.md5(hash_input.encode()).hexdigest()[:6]
        
        # Sanitize base name
        safe_base = "".join(
            c for c in base_name[:20] 
            if c.isalnum() or c in "가-힣ㄱ-ㅎㅏ-ㅣ_-"
        )
        
        if not safe_base:
            safe_base = "emoji"
        
        return f"{safe_base}_{effect}_{short_hash}.{extension}"
    
    def _sanitize_emoji_name(self, name: str) -> str:
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
        
        # Keep only allowed characters
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
