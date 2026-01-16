import random
from typing import List
from PIL import Image

from .base_effect import BaseEffect


class ShakeEffect(BaseEffect):
    """Shaking effect - text vibrates randomly."""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Set seed for reproducible random shake
        self._random = random.Random(42)
    
    def generate_frames(self) -> List[Image.Image]:
        """Generate frames with random position offsets."""
        frames = []
        
        shake_intensity = 4  # Maximum pixels to shake
        
        for i in range(self.frame_count):
            # Random offset for shake effect
            x_offset = self._random.randint(-shake_intensity, shake_intensity)
            y_offset = self._random.randint(-shake_intensity, shake_intensity)
            
            frame = self.create_frame(x_offset=x_offset, y_offset=y_offset)
            frames.append(frame)
        
        return frames
