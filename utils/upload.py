"""Upload utilities with retry logic for Slack API."""

import logging
import threading
import time

from slack_sdk.errors import SlackApiError

logger = logging.getLogger(__name__)

# Semaphore to limit concurrent file uploads to Slack
# Slack API can have issues with too many concurrent uploads
_upload_semaphore = threading.Semaphore(3)  # Allow max 3 concurrent uploads


def upload_with_retry(bot_client, max_retries=3, **upload_kwargs):
    """
    Upload file to Slack with retry logic for transient errors.
    
    This handles 'internal_error' and other transient failures by retrying
    with exponential backoff. Uses semaphore to limit concurrent uploads.
    
    Args:
        bot_client: Slack WebClient instance
        max_retries: Maximum number of retry attempts
        **upload_kwargs: Arguments to pass to files_upload_v2
    
    Returns:
        The response from files_upload_v2
    
    Raises:
        SlackApiError: If all retries fail
    """
    last_error = None
    
    # Acquire semaphore to limit concurrent uploads
    with _upload_semaphore:
        for attempt in range(max_retries):
            try:
                response = bot_client.files_upload_v2(**upload_kwargs)
                return response
            except SlackApiError as e:
                last_error = e
                error_code = e.response.get("error", "") if e.response else ""
                
                # Only retry on transient errors
                retryable_errors = ["internal_error", "fatal_error", "request_timeout", "service_unavailable"]
                
                if error_code in retryable_errors and attempt < max_retries - 1:
                    # Exponential backoff: 1s, 2s, 4s...
                    wait_time = (2 ** attempt)
                    logger.warning(
                        f"[UPLOAD] Slack API error '{error_code}' on attempt {attempt + 1}/{max_retries}. "
                        f"Retrying in {wait_time}s..."
                    )
                    time.sleep(wait_time)
                else:
                    # Non-retryable error or max retries reached
                    raise
    
    # This should not be reached, but just in case
    if last_error:
        raise last_error
