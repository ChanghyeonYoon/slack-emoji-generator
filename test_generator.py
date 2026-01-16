#!/usr/bin/env python3
"""
Test script for emoji generator.
Run this locally to test image generation without Slack integration.
"""

import os
import sys

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from generators import EmojiGenerator
from config import Config


def test_all_effects():
    """Test all animation effects."""
    generator = EmojiGenerator()
    
    # Ensure static directory exists
    os.makedirs(Config.STATIC_DIR, exist_ok=True)
    
    test_text = "테스트"
    effects = Config.AVAILABLE_EFFECTS
    
    print(f"Testing {len(effects)} effects with text: '{test_text}'")
    print("-" * 50)
    
    for effect in effects:
        try:
            image_bytes, ext = generator.generate(
                text=test_text,
                effect=effect,
                text_color="#FF5733",
                background="transparent",
                font_name="nanumgothic",
                line_break_at=0,
            )
            
            # Save to file
            filename = f"test_{effect}.{ext}"
            filepath = os.path.join(Config.STATIC_DIR, filename)
            
            with open(filepath, "wb") as f:
                f.write(image_bytes)
            
            size_kb = len(image_bytes) / 1024
            print(f"  [OK] {effect:12} -> {filename} ({size_kb:.1f} KB)")
            
        except Exception as e:
            print(f"  [FAIL] {effect:12} -> {e}")
    
    print("-" * 50)
    print(f"Generated files saved to: {Config.STATIC_DIR}")


def test_line_break():
    """Test line break functionality."""
    generator = EmojiGenerator()
    
    test_text = "안녕하세요반갑습니다"
    
    print("\nTesting line break functionality:")
    print(f"Original text: '{test_text}'")
    print("-" * 50)
    
    for break_at in [0, 2, 5]:
        try:
            image_bytes, ext = generator.generate(
                text=test_text,
                effect="none",
                text_color="#000000",
                background="white",
                font_name="nanumgothic",
                line_break_at=break_at,
            )
            
            filename = f"test_linebreak_{break_at}.{ext}"
            filepath = os.path.join(Config.STATIC_DIR, filename)
            
            with open(filepath, "wb") as f:
                f.write(image_bytes)
            
            print(f"  [OK] break_at={break_at} -> {filename}")
            
        except Exception as e:
            print(f"  [FAIL] break_at={break_at} -> {e}")


def test_colors():
    """Test different color combinations."""
    generator = EmojiGenerator()
    
    print("\nTesting color combinations:")
    print("-" * 50)
    
    color_tests = [
        ("#FF0000", "transparent", "red_transparent"),
        ("#00FF00", "black", "green_black"),
        ("#0000FF", "white", "blue_white"),
        ("#FFFF00", "#333333", "yellow_gray"),
    ]
    
    for text_color, bg, name in color_tests:
        try:
            image_bytes, ext = generator.generate(
                text="색상",
                effect="none",
                text_color=text_color,
                background=bg,
                font_name="nanumgothic",
            )
            
            filename = f"test_color_{name}.{ext}"
            filepath = os.path.join(Config.STATIC_DIR, filename)
            
            with open(filepath, "wb") as f:
                f.write(image_bytes)
            
            print(f"  [OK] {name:20} -> {filename}")
            
        except Exception as e:
            print(f"  [FAIL] {name:20} -> {e}")


if __name__ == "__main__":
    print("=" * 50)
    print("Slack Emoji Generator - Test Suite")
    print("=" * 50)
    
    # Check for fonts
    font_path = os.path.join(Config.FONTS_DIR, Config.DEFAULT_FONT)
    if not os.path.exists(font_path):
        print(f"\n[WARNING] Font not found: {font_path}")
        print("Using default system font. For best results, add fonts to fonts/ directory.")
        print("Download from: https://hangeul.naver.com/font\n")
    
    test_all_effects()
    test_line_break()
    test_colors()
    
    print("\n" + "=" * 50)
    print("Tests completed! Check static/ directory for generated images.")
    print("=" * 50)
