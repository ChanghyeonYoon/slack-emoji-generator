from typing import List, Tuple
from PIL import Image, ImageDraw

from .base_effect import BaseEffect


class BillboardEffect(BaseEffect):
    """Billboard effect - characters appear one by one like LED display."""
    
    def generate_frames(self) -> List[Image.Image]:
        """Generate frames where characters appear sequentially."""
        frames = []
        text_len = len(self.text)
        
        if text_len == 0:
            return [self.create_frame()]
        
        # Calculate character positions
        text_width, text_height = self.get_text_size()
        start_x = (self.size - text_width) // 2
        start_y = (self.size - text_height) // 2
        
        # Generate frame for each character appearing
        for i in range(text_len + 1):
            img = Image.new("RGBA", (self.size, self.size), self.bg_color)
            draw = ImageDraw.Draw(img)
            
            # Draw characters up to index i
            visible_text = self.text[:i]
            if visible_text:
                draw.text((start_x, start_y), visible_text, font=self.font, fill=self.text_color)
            
            frames.append(img)
        
        # Add a few frames showing full text (hold)
        for _ in range(3):
            frames.append(frames[-1].copy())
        
        return frames
