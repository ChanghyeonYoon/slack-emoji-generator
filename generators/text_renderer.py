import os
import logging
from typing import Tuple, Optional
from PIL import Image, ImageDraw, ImageFont

from config import Config

logger = logging.getLogger(__name__)


class TextRenderer:
    """Handles text rendering with fonts and styling."""
    
    def __init__(self):
        self.config = Config
        self._font_cache = {}
    
    def get_font(self, font_name: str, size: Optional[int] = None) -> ImageFont.FreeTypeFont:
        """
        Get a font by name.
        
        Args:
            font_name: Font identifier (e.g., "nanumgothic")
            size: Font size in pixels
            
        Returns:
            PIL ImageFont object
        """
        size = size or self.config.DEFAULT_FONT_SIZE
        cache_key = (font_name, size)
        
        if cache_key in self._font_cache:
            return self._font_cache[cache_key]
        
        # Get font filename
        font_filename = self.config.AVAILABLE_FONTS.get(
            font_name.lower(),
            self.config.DEFAULT_FONT
        )
        
        font_path = os.path.join(self.config.FONTS_DIR, font_filename)
        
        try:
            font = ImageFont.truetype(font_path, size)
        except (OSError, IOError):
            # Fallback to default font
            font = ImageFont.load_default()
        
        self._font_cache[cache_key] = font
        return font
    
    def get_text_size(
        self,
        text: str,
        font: ImageFont.FreeTypeFont
    ) -> Tuple[int, int]:
        """
        Calculate the size of rendered text.
        
        Args:
            text: Text to measure
            font: Font to use
            
        Returns:
            Tuple of (width, height)
        """
        # Create a temporary image for measurement
        temp_img = Image.new("RGBA", (1, 1))
        draw = ImageDraw.Draw(temp_img)
        
        bbox = draw.textbbox((0, 0), text, font=font)
        width = bbox[2] - bbox[0]
        height = bbox[3] - bbox[1]
        
        return (width, height)
    
    def render_text(
        self,
        text: str,
        font: ImageFont.FreeTypeFont,
        text_color: Tuple[int, int, int, int],
        bg_color: Tuple[int, int, int, int],
        size: int,
        x_offset: int = 0,
        y_offset: int = 0,
    ) -> Image.Image:
        """
        Render text onto an image.
        
        Args:
            text: Text to render
            font: Font to use
            text_color: RGBA color tuple for text
            bg_color: RGBA color tuple for background
            size: Canvas size (square)
            x_offset: Horizontal offset from center
            y_offset: Vertical offset from center
            
        Returns:
            PIL Image object
        """
        # Create canvas
        img = Image.new("RGBA", (size, size), bg_color)
        draw = ImageDraw.Draw(img)
        
        # Get full bounding box for accurate positioning
        bbox = draw.textbbox((0, 0), text, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
        
        # Center text with offsets, accounting for bbox offsets
        x = (size - text_width) // 2 - bbox[0] + x_offset
        y = (size - text_height) // 2 - bbox[1] + y_offset
        
        # Draw text
        draw.text((x, y), text, font=font, fill=text_color)
        
        return img
    
    def render_text_with_color(
        self,
        text: str,
        font: ImageFont.FreeTypeFont,
        text_color: Tuple[int, int, int, int],
        bg_color: Tuple[int, int, int, int],
        size: int,
    ) -> Image.Image:
        """
        Render text with specific color (used for color-changing effects).
        """
        return self.render_text(text, font, text_color, bg_color, size)
    
    def calculate_auto_font_size(
        self,
        text: str,
        font_name: str,
        max_size: int,
        padding: int = 10,
    ) -> int:
        """
        Calculate optimal font size to fit text in canvas.
        
        Args:
            text: Text to render
            font_name: Font identifier
            max_size: Maximum canvas size
            padding: Padding from edges
            
        Returns:
            Optimal font size
        """
        target_size = max_size - (padding * 2)
        
        # Binary search for optimal size
        min_font = 8
        max_font = 128
        optimal_size = min_font
        
        while min_font <= max_font:
            mid = (min_font + max_font) // 2
            font = self.get_font(font_name, mid)
            width, height = self.get_text_size(text, font)
            
            if width <= target_size and height <= target_size:
                optimal_size = mid
                min_font = mid + 1
            else:
                max_font = mid - 1
        
        return optimal_size
    
    def calculate_font_size_for_height(
        self,
        text: str,
        font_name: str,
        max_height: int,
        padding: int = 10,
    ) -> int:
        """
        Calculate font size to fit text height only (for scrolling effects).
        
        Args:
            text: Text to render
            font_name: Font identifier
            max_height: Maximum height
            padding: Padding from edges
            
        Returns:
            Optimal font size
        """
        target_height = max_height - (padding * 2)
        
        min_font = 8
        max_font = 128
        optimal_size = min_font
        
        while min_font <= max_font:
            mid = (min_font + max_font) // 2
            font = self.get_font(font_name, mid)
            _, height = self.get_text_size(text, font)
            
            if height <= target_height:
                optimal_size = mid
                min_font = mid + 1
            else:
                max_font = mid - 1
        
        return optimal_size