from typing import List
from PIL import Image, ImageDraw, ImageFont
import os

from .base_effect import BaseEffect
from config import Config


class GrowEffect(BaseEffect):
    """Growing effect - text starts small and grows larger."""
    
    def generate_frames(self) -> List[Image.Image]:
        """Generate frames with progressively larger text."""
        frames = []
        
        # Get font file path for resizing
        font_path = self._get_font_path()
        
        # Define size range
        min_size = 8
        max_size = self._calculate_max_font_size()
        
        for i in range(self.frame_count):
            # Calculate font size for this frame (ease-out effect)
            progress = i / (self.frame_count - 1) if self.frame_count > 1 else 1
            # Ease-out cubic for natural feel
            eased_progress = 1 - pow(1 - progress, 3)
            
            current_size = int(min_size + (max_size - min_size) * eased_progress)
            
            # Create font at current size
            try:
                sized_font = ImageFont.truetype(font_path, current_size)
            except (OSError, IOError):
                sized_font = ImageFont.load_default()
            
            # Create frame
            img = Image.new("RGBA", (self.size, self.size), self.bg_color)
            draw = ImageDraw.Draw(img)
            
            # Calculate centered position
            bbox = draw.textbbox((0, 0), self.text, font=sized_font)
            text_width = bbox[2] - bbox[0]
            text_height = bbox[3] - bbox[1]
            
            x = (self.size - text_width) // 2
            y = (self.size - text_height) // 2
            
            draw.text((x, y), self.text, font=sized_font, fill=self.text_color)
            frames.append(img)
        
        return frames
    
    def _get_font_path(self) -> str:
        """Get the path to the font file."""
        # Try to get font path from the font object
        if hasattr(self.font, 'path'):
            return self.font.path
        
        # Fallback to default font
        return os.path.join(Config.FONTS_DIR, Config.DEFAULT_FONT)
    
    def _calculate_max_font_size(self) -> int:
        """Calculate maximum font size that fits in canvas."""
        # Start with a reasonable max and adjust
        padding = 10
        target_size = self.size - (padding * 2)
        
        font_path = self._get_font_path()
        
        # Binary search for optimal size
        min_font = 8
        max_font = 128
        optimal_size = min_font
        
        while min_font <= max_font:
            mid = (min_font + max_font) // 2
            try:
                test_font = ImageFont.truetype(font_path, mid)
                temp_img = Image.new("RGBA", (1, 1))
                draw = ImageDraw.Draw(temp_img)
                bbox = draw.textbbox((0, 0), self.text, font=test_font)
                width = bbox[2] - bbox[0]
                height = bbox[3] - bbox[1]
                
                if width <= target_size and height <= target_size:
                    optimal_size = mid
                    min_font = mid + 1
                else:
                    max_font = mid - 1
            except:
                max_font = mid - 1
        
        return optimal_size
