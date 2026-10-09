"""
9:16 Vertical Shorts & Reels Layout Engine.
Transforms standard 16:9 widescreen footage into high-retention 1080x1920 portrait formats.
"""

from typing import Dict, Any

def build_vertical_filtergraph(style: str = "blurred_stack", contrast: float = 1.04, saturation: float = 1.05) -> str:
    """
    Constructs an FFmpeg filter_complex graph to format video into 1080x1920 9:16 vertical portrait.
    
    Styles:
    - blurred_stack: 16:9 main video crisp in center; background filled with zoomed, blurred ambient footage.
    - smart_crop: Centers the video and crops into a full-height 9:16 frame.
    """
    if style == "smart_crop":
        # Full-height vertical crop
        return (
            f"[0:v]scale=-2:1920,crop=1080:1920:(iw-1080)/2:0,"
            f"eq=contrast={contrast}:saturation={saturation},format=yuv420p[v_out]"
        )
    
    # Default: blurred_stack (Classic Podcast Short look)
    # Background: scaled & cropped to 1080x1920, blurred with boxblur
    # Foreground: scaled to 1080px width, centered vertically at (1920 - h) / 2
    return (
        f"[0:v]split=2[bg_src][fg_src];"
        f"[bg_src]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,boxblur=25:8[bg_blur];"
        f"[fg_src]scale=1080:-2,eq=contrast={contrast}:saturation={saturation}[fg_crisp];"
        f"[bg_blur][fg_crisp]overlay=0:(1920-overlay_h)/2,format=yuv420p[v_out]"
    )
