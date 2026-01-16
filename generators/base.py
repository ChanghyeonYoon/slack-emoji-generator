import io
import os
from typing import Optional, Tuple, List
from PIL import Image

from config import Config
from .text_renderer import TextRenderer
from .effects import get_effect
from .image_processor import ImageProcessor, ResizeMode


class EmojiGenerator:
    """Main emoji generator that combines text rendering with effects."""
    
    def __init__(self):
        self.text_renderer = TextRenderer()
        self.config = Config
    
    def generate(
        self,
        text: str,
        effect: str = "none",
        text_color: str = "#000000",
        background: str = "transparent",
        font_name: str = "nanumgothic",
        line_break_at: int = 0,
    ) -> Tuple[bytes, str]:
        """
        Generate an emoji image or GIF.
        
        Args:
            text: Text to render
            effect: Animation effect name
            text_color: Hex color code for text (e.g., "#FF0000")
            background: Background color name or hex code
            font_name: Font name (e.g., "nanumgothic")
            line_break_at: Insert line break after N characters (0 = no break)
            
        Returns:
            Tuple of (image bytes, file extension)
        """
        # Parse colors
        text_color_tuple = self._parse_color(text_color)
        bg_color_tuple = self._parse_background(background)
        
        # Apply line breaks
        processed_text = self._apply_line_breaks(text, line_break_at)
        
        # Get font with auto-size to fit text in canvas
        # Use larger padding (16px) for better top/bottom margins
        optimal_size = self.text_renderer.calculate_auto_font_size(
            processed_text,
            font_name,
            self.config.EMOJI_SIZE,
            padding=16
        )
        font = self.text_renderer.get_font(font_name, optimal_size)
        
        # Get effect class and generate
        effect_class = get_effect(effect)
        effect_instance = effect_class(
            text=processed_text,
            font=font,
            text_color=text_color_tuple,
            bg_color=bg_color_tuple,
            size=self.config.EMOJI_SIZE,
            frame_count=self.config.GIF_FRAME_COUNT,
            duration=self.config.GIF_DURATION,
        )
        
        return effect_instance.generate()
    
    def _parse_color(self, color: str) -> Tuple[int, int, int, int]:
        """Parse hex color code to RGBA tuple."""
        color = color.lstrip("#")
        if len(color) == 6:
            r = int(color[0:2], 16)
            g = int(color[2:4], 16)
            b = int(color[4:6], 16)
            return (r, g, b, 255)
        elif len(color) == 8:
            r = int(color[0:2], 16)
            g = int(color[2:4], 16)
            b = int(color[4:6], 16)
            a = int(color[6:8], 16)
            return (r, g, b, a)
        else:
            # Default to black
            return (0, 0, 0, 255)
    
    def _parse_background(self, background: str) -> Tuple[int, int, int, int]:
        """Parse background color."""
        if background in self.config.BACKGROUND_OPTIONS:
            return self.config.BACKGROUND_OPTIONS[background]
        else:
            # Treat as hex color
            return self._parse_color(background)
    
    def _apply_line_breaks(self, text: str, line_break_at: int) -> str:
        """Apply line breaks at specified character positions."""
        if line_break_at <= 0:
            return text
        
        lines = []
        for i in range(0, len(text), line_break_at):
            lines.append(text[i:i + line_break_at])
        return "\n".join(lines)
    
    def generate_scroll_tiles(
        self,
        text: str,
        text_color: str = "#000000",
        background: str = "transparent",
        font_name: str = "nanumgothic",
    ) -> List[Tuple[bytes, str, int]]:
        """
        Generate multiple scroll tiles for marquee effect.
        
        Args:
            text: Text to render
            text_color: Hex color code for text
            background: Background color name or hex code
            font_name: Font name
            
        Returns:
            List of (image_bytes, extension, tile_index) tuples
        """
        from .effects.scroll import ScrollEffect
        
        text_color_tuple = self._parse_color(text_color)
        bg_color_tuple = self._parse_background(background)
        
        # For scroll, use height-based font size (text can be wider than canvas)
        # Use minimal padding so text fills vertical space
        optimal_size = self.text_renderer.calculate_font_size_for_height(
            text,
            font_name,
            self.config.EMOJI_SIZE,
            padding=4  # Minimal padding for maximum text size
        )
        font = self.text_renderer.get_font(font_name, optimal_size)
        
        # Generate all tiles with smooth animation
        # Higher fps (20fps) for buttery smooth scrolling
        # 100 frames x 50ms = 5 seconds total animation
        return ScrollEffect.generate_all_tiles(
            text=text,
            font=font,
            text_color=text_color_tuple,
            bg_color=bg_color_tuple,
            size=self.config.EMOJI_SIZE,
            frame_count=100,  # More frames for smoother scroll (was 60)
            duration=50,      # 20fps for smooth animation (was 150ms = 6.67fps)
        )
    
    def generate_from_image(
        self,
        image_data: bytes,
        resize_mode: str = "cover",
        background: str = "transparent",
    ) -> Tuple[bytes, str]:
        """
        Generate emoji from uploaded image.
        
        Args:
            image_data: Raw image bytes
            resize_mode: Resize mode - 'fill', 'cover', or 'contain'
            background: Background color for contain mode
            
        Returns:
            Tuple of (image bytes, file extension)
        """
        processor = ImageProcessor(self.config.EMOJI_SIZE)
        return processor.process_to_bytes(image_data, resize_mode, background)
    
    def generate_from_image_with_effect(
        self,
        image_data: bytes,
        effect: str = "none",
        resize_mode: str = "cover",
        background: str = "transparent",
    ) -> Tuple[bytes, str]:
        """
        Generate emoji from uploaded image with animation effect.
        
        Args:
            image_data: Raw image bytes
            effect: Animation effect name
            resize_mode: Resize mode - 'fill', 'cover', or 'contain'
            background: Background color
            
        Returns:
            Tuple of (image bytes, file extension)
        """
        # First process the image
        processor = ImageProcessor(self.config.EMOJI_SIZE)
        processed_img = processor.process(image_data, resize_mode, background)
        
        # If no effect, just return the processed image
        if effect == "none":
            return processor.to_bytes(processed_img)
        
        # Apply animation effect to the processed image
        from .effects.image_effects import apply_effect_to_image
        return apply_effect_to_image(
            processed_img,
            effect=effect,
            frame_count=self.config.GIF_FRAME_COUNT,
            duration=self.config.GIF_DURATION,
        )
    
    def save_to_file(
        self,
        text: str,
        filename: str,
        **kwargs
    ) -> str:
        """Generate and save emoji to file."""
        image_bytes, ext = self.generate(text, **kwargs)
        
        # Ensure static directory exists
        os.makedirs(self.config.STATIC_DIR, exist_ok=True)
        
        # Save file
        filepath = os.path.join(self.config.STATIC_DIR, f"{filename}.{ext}")
        with open(filepath, "wb") as f:
            f.write(image_bytes)
        
        return filepath
