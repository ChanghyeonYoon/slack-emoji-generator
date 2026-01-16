"""
Image processing module for uploaded images.
Supports resize modes similar to CSS object-fit: fill, cover, contain.
"""
import io
import logging
from typing import Tuple, Optional
from PIL import Image

from config import Config

logger = logging.getLogger(__name__)


class ResizeMode:
    """Resize mode constants (similar to CSS object-fit)."""
    FILL = "fill"       # Stretch to fill, may distort aspect ratio
    COVER = "cover"     # Scale and crop to fill, maintains aspect ratio
    CONTAIN = "contain" # Scale to fit inside, maintains aspect ratio (may have padding)


class ImageProcessor:
    """Handles image resizing and cropping for emoji generation."""
    
    def __init__(self, target_size: int = None):
        """
        Initialize processor.
        
        Args:
            target_size: Target emoji size in pixels (default from config)
        """
        self.target_size = target_size or Config.EMOJI_SIZE
    
    def process(
        self,
        image_data: bytes,
        mode: str = ResizeMode.COVER,
        background: str = "transparent",
    ) -> Image.Image:
        """
        Process uploaded image with specified resize mode.
        
        Args:
            image_data: Raw image bytes
            mode: Resize mode (fill, cover, contain)
            background: Background color for contain mode
            
        Returns:
            Processed PIL Image
        """
        # Open image
        img = Image.open(io.BytesIO(image_data))
        
        # Convert to RGBA for transparency support
        if img.mode != "RGBA":
            img = img.convert("RGBA")
        
        logger.info(f"Processing image: original size {img.size}, mode={mode}")
        
        if mode == ResizeMode.FILL:
            return self._resize_fill(img)
        elif mode == ResizeMode.COVER:
            return self._resize_cover(img)
        elif mode == ResizeMode.CONTAIN:
            return self._resize_contain(img, background)
        else:
            # Default to cover
            logger.warning(f"Unknown resize mode: {mode}, using cover")
            return self._resize_cover(img)
    
    def _resize_fill(self, img: Image.Image) -> Image.Image:
        """
        Resize image to fill target size (may distort aspect ratio).
        Similar to CSS object-fit: fill.
        """
        return img.resize(
            (self.target_size, self.target_size),
            Image.Resampling.LANCZOS
        )
    
    def _resize_cover(self, img: Image.Image) -> Image.Image:
        """
        Resize and crop image to cover target size (maintains aspect ratio).
        Similar to CSS object-fit: cover.
        """
        width, height = img.size
        target = self.target_size
        
        # Calculate scale factor to cover the target
        scale = max(target / width, target / height)
        
        # Scale image
        new_width = int(width * scale)
        new_height = int(height * scale)
        img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
        
        # Calculate crop box (center crop)
        left = (new_width - target) // 2
        top = (new_height - target) // 2
        right = left + target
        bottom = top + target
        
        # Crop to target size
        return img.crop((left, top, right, bottom))
    
    def _resize_contain(
        self,
        img: Image.Image,
        background: str = "transparent"
    ) -> Image.Image:
        """
        Resize image to fit inside target size (maintains aspect ratio).
        Similar to CSS object-fit: contain.
        May add padding to fill remaining space.
        """
        width, height = img.size
        target = self.target_size
        
        # Calculate scale factor to fit inside
        scale = min(target / width, target / height)
        
        # Scale image
        new_width = int(width * scale)
        new_height = int(height * scale)
        img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
        
        # Create background canvas
        bg_color = self._parse_background(background)
        canvas = Image.new("RGBA", (target, target), bg_color)
        
        # Calculate position (center)
        x = (target - new_width) // 2
        y = (target - new_height) // 2
        
        # Paste image onto canvas
        canvas.paste(img, (x, y), img)
        
        return canvas
    
    def _parse_background(self, background: str) -> Tuple[int, int, int, int]:
        """Parse background color string to RGBA tuple."""
        if background == "transparent":
            return (0, 0, 0, 0)
        elif background in Config.BACKGROUND_OPTIONS:
            return Config.BACKGROUND_OPTIONS[background]
        elif background.startswith("#"):
            # Parse hex color
            color = background.lstrip("#")
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
        
        # Default to transparent
        return (0, 0, 0, 0)
    
    def to_bytes(self, img: Image.Image, format: str = "PNG") -> Tuple[bytes, str]:
        """
        Convert PIL Image to bytes.
        
        Args:
            img: PIL Image object
            format: Output format (PNG or GIF)
            
        Returns:
            Tuple of (image bytes, file extension)
        """
        buffer = io.BytesIO()
        
        if format.upper() == "GIF":
            # For GIF, need to convert to P mode with transparency
            img.save(buffer, format="GIF", save_all=False)
            ext = "gif"
        else:
            # PNG with transparency
            img.save(buffer, format="PNG", optimize=True)
            ext = "png"
        
        buffer.seek(0)
        return buffer.read(), ext
    
    def process_to_bytes(
        self,
        image_data: bytes,
        mode: str = ResizeMode.COVER,
        background: str = "transparent",
    ) -> Tuple[bytes, str]:
        """
        Process image and return as bytes.
        
        Args:
            image_data: Raw image bytes
            mode: Resize mode
            background: Background color
            
        Returns:
            Tuple of (processed image bytes, file extension)
        """
        img = self.process(image_data, mode, background)
        return self.to_bytes(img)


# Convenience function
def process_image(
    image_data: bytes,
    mode: str = ResizeMode.COVER,
    background: str = "transparent",
    target_size: int = None,
) -> Tuple[bytes, str]:
    """
    Process uploaded image for emoji use.
    
    Args:
        image_data: Raw image bytes
        mode: Resize mode (fill, cover, contain)
        background: Background color
        target_size: Target size in pixels
        
    Returns:
        Tuple of (processed image bytes, file extension)
    """
    processor = ImageProcessor(target_size)
    return processor.process_to_bytes(image_data, mode, background)
