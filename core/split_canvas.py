"""
Transformative Split-Screen Layout Generator (9:16 Vertical Shorts/Reels).
Positions the source clip in top 60% and satisfying dynamic canvas in bottom 40%.
Protects against YouTube's 'Reused Content' monetization rejection.
"""

import os
import subprocess

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CANVAS_FILE = os.path.join(BASE_DIR, "assets", "gameplay", "satisfying_canvas.mp4")

def build_split_screen_filter(top_filter_chain: str = "") -> str:
    """
    Constructs a complex filtergraph combining top source clip (1080x1152)
    and bottom viral canvas (1080x768) with a glowing cyber separator border.
    """
    tf = f"{top_filter_chain}," if top_filter_chain else ""
    
    filtergraph = (
        f"[0:v]{tf}scale=1080:1152:force_original_aspect_ratio=increase,"
        f"crop=1080:1152[top];"
        f"[1:v]scale=1080:768:force_original_aspect_ratio=increase,"
        f"crop=1080:768[bottom];"
        f"[top][bottom]vstack=inputs=2[stacked];"
        f"[stacked]drawbox=y=1150:color=#00f0ff@0.85:width=1080:height=4:t=fill[outv]"
    )
    return filtergraph
