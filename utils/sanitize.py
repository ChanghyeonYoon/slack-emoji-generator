"""Text sanitization utilities for emoji names and filenames."""

import re


def sanitize_emoji_name(name: str) -> str:
    """
    Sanitize emoji name to meet Slack requirements.
    - Lowercase only
    - Alphanumeric, underscores, and hyphens only
    - Max 100 characters
    
    Args:
        name: The raw emoji name
        
    Returns:
        Sanitized emoji name safe for Slack
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


def sanitize_filename(name: str) -> str:
    """
    Sanitize text for use in filename.
    - Replace spaces with underscores
    - Keep only Korean, alphanumeric, and underscore
    
    Args:
        name: The raw filename text
        
    Returns:
        Sanitized filename
    """
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
