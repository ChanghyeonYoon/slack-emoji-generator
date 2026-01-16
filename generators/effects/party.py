import colorsys
from typing import List, Tuple
from PIL import Image

from .base_effect import BaseEffect


class PartyEffect(BaseEffect):
    """Party parrot style - rainbow color cycling effect."""
    
    def generate_frames(self) -> List[Image.Image]:
        """Generate frames with cycling rainbow colors."""
        frames = []
        
        for i in range(self.frame_count):
            # Calculate hue for this frame (0-1 range)
            hue = i / self.frame_count
            
            # Convert HSV to RGB
            r, g, b = colorsys.hsv_to_rgb(hue, 1.0, 1.0)
            color = (
                int(r * 255),
                int(g * 255),
                int(b * 255),
                255
            )
            
            frame = self.create_frame(color_override=color)
            frames.append(frame)
        
        return frames
