import io
from abc import ABC, abstractmethod
from typing import List, Tuple
from PIL import Image, ImageDraw, ImageFont


class BaseEffect(ABC):
    """Base class for all animation effects."""
    
    def __init__(
        self,
        text: str,
        font: ImageFont.FreeTypeFont,
        text_color: Tuple[int, int, int, int],
        bg_color: Tuple[int, int, int, int],
        size: int = 128,
        frame_count: int = 12,
        duration: int = 100,
    ):
        self.text = text
        self.font = font
        self.text_color = text_color
        self.bg_color = bg_color
        self.size = size
        self.frame_count = frame_count
        self.duration = duration
    
    @abstractmethod
    def generate_frames(self) -> List[Image.Image]:
        """Generate animation frames. Override in subclasses."""
        pass
    
    def generate(self) -> Tuple[bytes, str]:
        """
        Generate the final image or GIF.
        
        Returns:
            Tuple of (image bytes, file extension)
        """
        frames = self.generate_frames()
        
        if len(frames) == 1:
            # Single frame - return PNG
            return self._save_as_png(frames[0]), "png"
        else:
            # Multiple frames - return GIF
            return self._save_as_gif(frames), "gif"
    
    def _save_as_png(self, image: Image.Image) -> bytes:
        """Save image as PNG bytes."""
        buffer = io.BytesIO()
        
        # Check if background is transparent (alpha < 255)
        is_transparent_bg = self.bg_color[3] < 255 if len(self.bg_color) == 4 else False
        
        if image.mode == "RGBA" and not is_transparent_bg:
            # Opaque background: composite onto solid background to ensure no transparency
            bg = Image.new("RGB", image.size, self.bg_color[:3])
            bg.paste(image, mask=image.split()[3])  # Use alpha as mask
            image = bg
        
        image.save(buffer, format="PNG", optimize=True)
        return buffer.getvalue()
    
    def _save_as_gif(self, frames: List[Image.Image]) -> bytes:
        """Save frames as animated GIF bytes."""
        buffer = io.BytesIO()
        
        # Check if background is transparent (alpha < 255)
        is_transparent_bg = self.bg_color[3] < 255 if len(self.bg_color) == 4 else False
        
        # Convert RGBA to P mode for GIF
        converted_frames = []
        for frame in frames:
            if frame.mode == "RGBA":
                if is_transparent_bg:
                    # Transparent background: convert with transparency support
                    alpha = frame.split()[3]
                    frame = frame.convert("RGB").convert("P", palette=Image.ADAPTIVE, colors=255)
                    mask = Image.eval(alpha, lambda a: 255 if a <= 128 else 0)
                    frame.paste(255, mask)
                    frame.info["transparency"] = 255
                else:
                    # Opaque background: composite onto solid background first
                    # This properly handles anti-aliased text edges
                    bg = Image.new("RGB", frame.size, self.bg_color[:3])
                    bg.paste(frame, mask=frame.split()[3])  # Use alpha as mask
                    frame = bg.convert("P", palette=Image.ADAPTIVE, colors=256)
            converted_frames.append(frame)
        
        # Build save options
        save_kwargs = {
            "format": "GIF",
            "save_all": True,
            "append_images": converted_frames[1:],
            "duration": self.duration,
            "loop": 0,
            "optimize": True,
        }
        
        # disposal=2 clears to transparent, which causes issues with opaque backgrounds
        # Only use disposal=2 for transparent backgrounds
        if is_transparent_bg:
            save_kwargs["disposal"] = 2
        
        converted_frames[0].save(buffer, **save_kwargs)
        
        return buffer.getvalue()
    
    def get_text_size(self) -> Tuple[int, int]:
        """Calculate text dimensions."""
        temp_img = Image.new("RGBA", (1, 1))
        draw = ImageDraw.Draw(temp_img)
        bbox = draw.textbbox((0, 0), self.text, font=self.font)
        return (bbox[2] - bbox[0], bbox[3] - bbox[1])
    
    def create_frame(
        self,
        x_offset: int = 0,
        y_offset: int = 0,
        color_override: Tuple[int, int, int, int] = None,
    ) -> Image.Image:
        """
        Create a single frame with text.
        
        Args:
            x_offset: Horizontal offset from center
            y_offset: Vertical offset from center
            color_override: Override text color for this frame
        """
        img = Image.new("RGBA", (self.size, self.size), self.bg_color)
        draw = ImageDraw.Draw(img)
        
        text_width, text_height = self.get_text_size()
        x = (self.size - text_width) // 2 + x_offset
        y = (self.size - text_height) // 2 + y_offset
        
        color = color_override or self.text_color
        draw.text((x, y), self.text, font=self.font, fill=color)
        
        return img
