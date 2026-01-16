from .base_effect import BaseEffect
from .none import NoneEffect
from .billboard import BillboardEffect
from .scroll import ScrollEffect
from .party import PartyEffect
from .rotate import RotateEffect
from .shake import ShakeEffect
from .wave import WaveEffect
from .typing import TypingEffect
from .grow import GrowEffect

EFFECTS = {
    "none": NoneEffect,
    "billboard": BillboardEffect,
    "scroll": ScrollEffect,
    "party": PartyEffect,
    "rotate": RotateEffect,
    "shake": ShakeEffect,
    "wave": WaveEffect,
    "typing": TypingEffect,
    "grow": GrowEffect,
}


def get_effect(effect_name: str):
    """Get effect class by name."""
    return EFFECTS.get(effect_name, NoneEffect)


__all__ = [
    "NoneEffect",
    "BillboardEffect",
    "ScrollEffect",
    "PartyEffect",
    "RotateEffect",
    "ShakeEffect",
    "WaveEffect",
    "TypingEffect",
    "GrowEffect",
    "EFFECTS",
    "get_effect",
]
