from typing import List, Tuple
from PIL import Image, ImageDraw

from .base_effect import BaseEffect


class ScrollEffect(BaseEffect):
    """
    Scrolling marquee effect - generates multiple emoji tiles.
    When placed side by side, they create a continuous scrolling text effect.
    """
    
    def __init__(self, *args, tile_index: int = 0, total_tiles: int = 1, **kwargs):
        """
        Args:
            tile_index: Which tile this is (0-based)
            total_tiles: Total number of tiles for this text
        """
        super().__init__(*args, **kwargs)
        self.tile_index = tile_index
        self.total_tiles = total_tiles
    
    def generate_frames(self) -> List[Image.Image]:
        """Generate frames with horizontally scrolling text."""
        frames = []
        
        # Get full bounding box for accurate positioning
        temp_img = Image.new("RGBA", (1, 1))
        temp_draw = ImageDraw.Draw(temp_img)
        bbox = temp_draw.textbbox((0, 0), self.text, font=self.font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
        
        # Total width of all tiles combined
        total_canvas_width = self.size * self.total_tiles
        
        # Total scroll distance: text scrolls from right edge to completely off left
        # Start: text at right edge (x = total_canvas_width)
        # End: text completely off left (x = -text_width)
        total_scroll_distance = total_canvas_width + text_width
        
        # Center text vertically, accounting for bbox top offset
        # bbox[1] is the top offset - we subtract it to properly center the actual text
        y = (self.size - text_height) // 2 - bbox[1]
        
        for i in range(self.frame_count):
            img = Image.new("RGBA", (self.size, self.size), self.bg_color)
            draw = ImageDraw.Draw(img)
            
            # Use normalized progress (0.0 to 1.0) for consistent calculation across all tiles
            # This ensures all tiles use exactly the same global_x value
            progress = i / self.frame_count
            
            # global_x: position on the combined canvas (integer for pixel-perfect sync)
            global_x = round(total_canvas_width - (progress * total_scroll_distance))
            
            # local_x: position relative to this tile
            # tile 0 shows x: [0, size), tile 1 shows x: [size, size*2), etc.
            local_x = global_x - (self.tile_index * self.size)
            
            draw.text((local_x, y), self.text, font=self.font, fill=self.text_color)
            frames.append(img)
        
        return frames
    
    @classmethod
    def generate_all_tiles(
        cls,
        text: str,
        font,
        text_color: Tuple[int, int, int, int],
        bg_color: Tuple[int, int, int, int],
        size: int = 128,
        frame_count: int = 60,
        duration: int = 100,
    ) -> List[Tuple[bytes, str, int]]:
        """
        Generate all tiles for the scrolling text.
        
        Returns:
            List of (image_bytes, extension, tile_index) tuples
        """
        # Number of tiles based on text length (minimum 2, maximum 10)
        total_tiles = min(max(len(text), 2), 10)
        
        results = []
        for tile_idx in range(total_tiles):
            effect = cls(
                text=text,
                font=font,
                text_color=text_color,
                bg_color=bg_color,
                size=size,
                frame_count=frame_count,
                duration=duration,
                tile_index=tile_idx,
                total_tiles=total_tiles,
            )
            image_bytes, ext = effect.generate()
            results.append((image_bytes, ext, tile_idx))
        
        return results
