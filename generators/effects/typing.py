from typing import List
from PIL import Image, ImageDraw

from .base_effect import BaseEffect


class TypingEffect(BaseEffect):
    """Typing effect - characters appear one by one."""
    
    def generate_frames(self) -> List[Image.Image]:
        """Generate frames with progressively appearing text."""
        frames = []
        
        text_length = len(self.text.replace("\n", ""))
        
        # Calculate how many characters to show per frame
        if text_length <= self.frame_count:
            chars_per_frame = 1
            actual_frames = text_length + 2  # Extra frames at the end
        else:
            chars_per_frame = max(1, text_length // self.frame_count)
            actual_frames = self.frame_count
        
        for i in range(actual_frames):
            # Calculate how many characters to show
            chars_to_show = min((i + 1) * chars_per_frame, text_length)
            
            # Get the substring to display
            display_text = self._get_chars(chars_to_show)
            
            img = Image.new("RGBA", (self.size, self.size), self.bg_color)
            draw = ImageDraw.Draw(img)
            
            # Calculate position (left-aligned for typing effect)
            text_bbox = self._get_text_bbox(display_text)
            text_width = text_bbox[2] - text_bbox[0]
            text_height = text_bbox[3] - text_bbox[1]
            
            full_bbox = self._get_full_text_bbox()
            x = (self.size - (full_bbox[2] - full_bbox[0])) // 2 - full_bbox[0]
            y = (self.size - text_height) // 2 - text_bbox[1]
            
            draw.text((x, y), display_text, font=self.font, fill=self.text_color)
            
            # Add cursor blink
            if i < actual_frames - 1:
                cursor_x = x + text_width
                draw.text((cursor_x, y), "|", font=self.font, fill=self.text_color)
            
            frames.append(img)
        
        # Add final frame without cursor
        final_frame = self.create_frame()
        frames.append(final_frame)
        
        return frames
    
    def _get_chars(self, count: int) -> str:
        """Get first N characters (excluding newlines from count)."""
        result = []
        char_count = 0
        for char in self.text:
            if char == "\n":
                result.append(char)
            else:
                if char_count < count:
                    result.append(char)
                    char_count += 1
        return "".join(result)
    
    def _get_text_bbox(self, text: str):
        """Get bounding box of specific text."""
        temp_img = Image.new("RGBA", (1, 1))
        draw = ImageDraw.Draw(temp_img)
        return draw.textbbox((0, 0), text, font=self.font)
    
    def _get_text_size(self, text: str):
        """Get size of specific text."""
        bbox = self._get_text_bbox(text)
        return (bbox[2] - bbox[0], bbox[3] - bbox[1])
    
    def _get_full_text_bbox(self):
        """Get bounding box of full text."""
        temp_img = Image.new("RGBA", (1, 1))
        draw = ImageDraw.Draw(temp_img)
        return draw.textbbox((0, 0), self.text, font=self.font)
    
    def _get_full_text_width(self) -> int:
        """Get width of full text."""
        bbox = self._get_full_text_bbox()
        return bbox[2] - bbox[0]
