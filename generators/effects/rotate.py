import math
from typing import List
from PIL import Image, ImageDraw

from .base_effect import BaseEffect


class RotateEffect(BaseEffect):
    """Circular rotation effect - text moves in a circle."""
    
    def generate_frames(self) -> List[Image.Image]:
        """Generate frames with text moving in circular path."""
        frames = []
        
        text_width, text_height = self.get_text_size()
        
        # Radius of circular motion
        radius_x = 10  # Horizontal radius
        radius_y = 5   # Vertical radius (elliptical motion)
        
        for i in range(self.frame_count):
            # Calculate angle for this frame
            angle = (2 * math.pi * i) / self.frame_count
            
            # Calculate offset using sin/cos for circular motion
            x_offset = int(math.sin(angle) * radius_x)
            y_offset = int(math.cos(angle) * radius_y)
            
            frame = self.create_frame(x_offset=x_offset, y_offset=y_offset)
            frames.append(frame)
        
        return frames
