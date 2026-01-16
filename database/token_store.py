import logging
from typing import Optional
from .models import db, UserToken

logger = logging.getLogger(__name__)


class TokenStore:
    """Manage user OAuth tokens in the database."""
    
    def save_token(
        self,
        user_id: str,
        team_id: str,
        access_token: str,
        token_type: str = "Bearer",
        scope: str = None,
    ) -> bool:
        """
        Save or update a user's OAuth token.
        
        Args:
            user_id: Slack user ID
            team_id: Slack team/workspace ID
            access_token: OAuth access token
            token_type: Token type (usually "Bearer")
            scope: OAuth scopes granted
            
        Returns:
            True if successful, False otherwise
        """
        try:
            existing = UserToken.query.filter_by(user_id=user_id).first()
            
            if existing:
                # Update existing token
                existing.access_token = access_token
                existing.token_type = token_type
                existing.scope = scope
                existing.team_id = team_id
                logger.info(f"Updated token for user {user_id}")
            else:
                # Create new token
                token = UserToken(
                    user_id=user_id,
                    team_id=team_id,
                    access_token=access_token,
                    token_type=token_type,
                    scope=scope,
                )
                db.session.add(token)
                logger.info(f"Created new token for user {user_id}")
            
            db.session.commit()
            return True
            
        except Exception as e:
            logger.error(f"Error saving token: {e}", exc_info=True)
            db.session.rollback()
            return False
    
    def get_token(self, user_id: str) -> Optional[str]:
        """
        Get a user's access token.
        
        Args:
            user_id: Slack user ID
            
        Returns:
            Access token string or None if not found
        """
        try:
            token = UserToken.query.filter_by(user_id=user_id).first()
            return token.access_token if token else None
        except Exception as e:
            logger.error(f"Error getting token: {e}", exc_info=True)
            return None
    
    def delete_token(self, user_id: str) -> bool:
        """
        Delete a user's token (for logout/revoke).
        
        Args:
            user_id: Slack user ID
            
        Returns:
            True if deleted, False otherwise
        """
        try:
            token = UserToken.query.filter_by(user_id=user_id).first()
            if token:
                db.session.delete(token)
                db.session.commit()
                logger.info(f"Deleted token for user {user_id}")
                return True
            return False
        except Exception as e:
            logger.error(f"Error deleting token: {e}", exc_info=True)
            db.session.rollback()
            return False
    
    def has_token(self, user_id: str) -> bool:
        """Check if a user has a stored token."""
        try:
            return UserToken.query.filter_by(user_id=user_id).first() is not None
        except Exception:
            return False
