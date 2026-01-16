from typing import List
from PIL import Image

from .base_effect import BaseEffect


class NoneEffect(BaseEffect):
    """No animation - generates a static PNG image."""
    
    def generate_frames(self) -> List[Image.Image]:
        """Generate a single static frame."""
        return [self.create_frame()]
