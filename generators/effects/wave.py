import math
from typing import List
from PIL import Image, ImageDraw

from .base_effect import BaseEffect


class WaveEffect(BaseEffect):
    """Wave effect - each character moves up and down in a wave pattern."""
    
    def generate_frames(self) -> List[Image.Image]:
        """Generate frames with wave motion for each character."""
        frames = []
        
        wave_amplitude = 8  # Maximum vertical displacement
        
        for frame_idx in range(self.frame_count):
            img = Image.new("RGBA", (self.size, self.size), self.bg_color)
            draw = ImageDraw.Draw(img)
            
            # Calculate starting x position to center text
            total_width = self._get_total_text_width()
            start_x = (self.size - total_width) // 2
            
            # Draw each character with wave offset
            current_x = start_x
            for char_idx, char in enumerate(self.text):
                if char == "\n":
                    continue
                    
                # Calculate wave phase for this character
                phase = (2 * math.pi * frame_idx / self.frame_count) + (char_idx * 0.5)
                y_offset = int(math.sin(phase) * wave_amplitude)
                
                # Get character width
                char_bbox = draw.textbbox((0, 0), char, font=self.font)
                char_width = char_bbox[2] - char_bbox[0]
                
                # Calculate y position (centered + wave offset)
                text_height = char_bbox[3] - char_bbox[1]
                y = (self.size - text_height) // 2 + y_offset
                
                draw.text((current_x, y), char, font=self.font, fill=self.text_color)
                current_x += char_width
            
            frames.append(img)
        
        return frames
    
    def _get_total_text_width(self) -> int:
        """Calculate total width of text (without newlines)."""
        text_no_newlines = self.text.replace("\n", "")
        temp_img = Image.new("RGBA", (1, 1))
        draw = ImageDraw.Draw(temp_img)
        bbox = draw.textbbox((0, 0), text_no_newlines, font=self.font)
        return bbox[2] - bbox[0]
