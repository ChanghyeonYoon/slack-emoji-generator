"""
Image-based animation effects.
Applies animation effects to uploaded images.
"""
import io
import math
from typing import Tuple, List
from PIL import Image


def apply_effect_to_image(
    img: Image.Image,
    effect: str,
    frame_count: int = 12,
    duration: int = 100,
) -> Tuple[bytes, str]:
    """
    Apply animation effect to an image.
    
    Args:
        img: PIL Image (processed to emoji size)
        effect: Effect name
        frame_count: Number of animation frames
        duration: Duration per frame in milliseconds
        
    Returns:
        Tuple of (animated GIF bytes, file extension)
    """
    if effect == "none":
        # No animation, return as PNG
        buffer = io.BytesIO()
        img.save(buffer, format="PNG", optimize=True)
        buffer.seek(0)
        return buffer.read(), "png"
    
    effect_func = EFFECT_FUNCTIONS.get(effect, _effect_none)
    frames = effect_func(img, frame_count)
    
    return _create_gif(frames, duration)


def _create_gif(frames: List[Image.Image], duration: int) -> Tuple[bytes, str]:
    """Create animated GIF from frames."""
    buffer = io.BytesIO()
    
    # Convert frames to P mode with transparency for GIF
    processed_frames = []
    for frame in frames:
        if frame.mode == "RGBA":
            # Convert RGBA to P with transparency
            alpha = frame.split()[3]
            p_frame = frame.convert("P", palette=Image.Palette.ADAPTIVE, colors=255)
            mask = Image.eval(alpha, lambda a: 255 if a <= 128 else 0)
            p_frame.paste(255, mask)
            processed_frames.append(p_frame)
        else:
            processed_frames.append(frame.convert("P", palette=Image.Palette.ADAPTIVE))
    
    processed_frames[0].save(
        buffer,
        format="GIF",
        save_all=True,
        append_images=processed_frames[1:],
        duration=duration,
        loop=0,
        disposal=2,
        transparency=255,
    )
    
    buffer.seek(0)
    return buffer.read(), "gif"


def _effect_none(img: Image.Image, frame_count: int) -> List[Image.Image]:
    """No animation - single frame."""
    return [img]


def _effect_rotate(img: Image.Image, frame_count: int) -> List[Image.Image]:
    """Rotate image 360 degrees."""
    frames = []
    for i in range(frame_count):
        angle = (360 / frame_count) * i
        # Rotate around center
        rotated = img.rotate(-angle, resample=Image.Resampling.BICUBIC, expand=False)
        frames.append(rotated)
    return frames


def _effect_shake(img: Image.Image, frame_count: int) -> List[Image.Image]:
    """Shake image left and right."""
    frames = []
    size = img.size[0]
    max_offset = size // 10  # 10% of size
    
    for i in range(frame_count):
        # Sine wave movement
        offset = int(max_offset * math.sin(2 * math.pi * i / frame_count))
        
        # Create new canvas and paste shifted image
        canvas = Image.new("RGBA", img.size, (0, 0, 0, 0))
        canvas.paste(img, (offset, 0), img)
        frames.append(canvas)
    
    return frames


def _effect_party(img: Image.Image, frame_count: int) -> List[Image.Image]:
    """Rainbow color cycling effect."""
    frames = []
    
    for i in range(frame_count):
        hue_shift = int((360 / frame_count) * i)
        
        # Convert to HSV, shift hue, convert back
        if img.mode != "RGBA":
            rgba_img = img.convert("RGBA")
        else:
            rgba_img = img.copy()
        
        # Simple color overlay with hue shift
        r, g, b, a = rgba_img.split()
        
        # Create hue color
        hue_color = _hue_to_rgb(hue_shift)
        
        # Blend with original (tint effect)
        from PIL import ImageEnhance
        
        # Create a colored overlay
        overlay = Image.new("RGBA", img.size, (*hue_color, 128))
        
        # Composite with original
        result = Image.alpha_composite(rgba_img, overlay)
        
        # Restore original alpha
        result.putalpha(a)
        frames.append(result)
    
    return frames


def _effect_wave(img: Image.Image, frame_count: int) -> List[Image.Image]:
    """Wave distortion effect."""
    frames = []
    size = img.size[0]
    amplitude = size // 16  # Wave amplitude
    
    for i in range(frame_count):
        phase = (2 * math.pi * i) / frame_count
        
        # Create distorted image
        result = Image.new("RGBA", img.size, (0, 0, 0, 0))
        
        for y in range(size):
            # Calculate x offset based on sine wave
            offset = int(amplitude * math.sin(2 * math.pi * y / size + phase))
            
            # Copy row with offset
            row = img.crop((0, y, size, y + 1))
            
            # Wrap around
            if offset != 0:
                result.paste(row, (offset, y), row)
        
        frames.append(result)
    
    return frames


def _effect_grow(img: Image.Image, frame_count: int) -> List[Image.Image]:
    """Pulsing size effect."""
    frames = []
    size = img.size[0]
    min_scale = 0.7
    max_scale = 1.0
    
    for i in range(frame_count):
        # Sine wave for smooth pulsing
        t = (math.sin(2 * math.pi * i / frame_count) + 1) / 2  # 0 to 1
        scale = min_scale + (max_scale - min_scale) * t
        
        new_size = int(size * scale)
        
        # Resize image
        resized = img.resize(
            (new_size, new_size),
            Image.Resampling.LANCZOS
        )
        
        # Center on canvas
        canvas = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        offset = (size - new_size) // 2
        canvas.paste(resized, (offset, offset), resized)
        
        frames.append(canvas)
    
    return frames


def _hue_to_rgb(hue: int) -> Tuple[int, int, int]:
    """Convert hue (0-360) to RGB."""
    h = hue / 360.0
    s = 1.0
    v = 1.0
    
    i = int(h * 6)
    f = (h * 6) - i
    p = v * (1 - s)
    q = v * (1 - f * s)
    t = v * (1 - (1 - f) * s)
    
    i = i % 6
    
    if i == 0:
        r, g, b = v, t, p
    elif i == 1:
        r, g, b = q, v, p
    elif i == 2:
        r, g, b = p, v, t
    elif i == 3:
        r, g, b = p, q, v
    elif i == 4:
        r, g, b = t, p, v
    else:
        r, g, b = v, p, q
    
    return (int(r * 255), int(g * 255), int(b * 255))


# Effect function mapping
EFFECT_FUNCTIONS = {
    "none": _effect_none,
    "rotate": _effect_rotate,
    "shake": _effect_shake,
    "party": _effect_party,
    "wave": _effect_wave,
    "grow": _effect_grow,
}
