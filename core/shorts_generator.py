"""
End-to-End Autonomous Viral Short Generator.
Trims viral segment, formats to 1080x1920 9:16 vertical layout, burns Alex Hormozi captions, and applies audio mastering.
"""

import os
import re
import subprocess
import logging
from typing import Dict, Any, Optional

from core.youtube_service import download_and_trim_youtube
from core.gemini_hook_finder import extract_youtube_video_id, fetch_youtube_transcript
from core.caption_engine import generate_ass_subtitle_file
from core.vertical_formatter import build_vertical_filtergraph
from core.metadata_cleaner import probe_video, get_clean_metadata_args

logger = logging.getLogger("ShortsGenerator")

def generate_viral_short(
    youtube_url: str,
    start_sec: float,
    end_sec: float,
    output_path: str,
    style: str = "blurred_stack",
    burn_captions: bool = True,
    watermark_text: str = "@ViralClips",
    progress_callback = None
) -> Dict[str, Any]:
    """
    Renders an end-to-end 9:16 vertical short ready for YouTube Shorts / Reels.
    """
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    temp_dir = os.path.join(os.path.dirname(output_path), f"tmp_short_{os.path.basename(output_path)}")
    os.makedirs(temp_dir, exist_ok=True)
    
    raw_clip_path = os.path.join(temp_dir, "raw_trimmed.mp4")
    ass_path = os.path.join(temp_dir, "subtitles.ass")

    try:
        # Step 1: Trim clip
        if progress_callback:
            progress_callback(10.0, "Capturing high-energy viral segment from stream...")
            
        download_and_trim_youtube(
            url=youtube_url,
            output_path=raw_clip_path,
            start_sec=start_sec,
            end_sec=end_sec,
            progress_callback=progress_callback
        )

        # Step 2: Generate Hormozi Animated Captions
        has_subtitles = False
        if burn_captions:
            if progress_callback:
                progress_callback(45.0, "Synthesizing dynamic word-by-word animated captions...")
            video_id = extract_youtube_video_id(youtube_url)
            if video_id:
                transcript = fetch_youtube_transcript(video_id)
                if transcript:
                    generate_ass_subtitle_file(
                        transcript_segments=transcript,
                        clip_start=start_sec,
                        clip_end=end_sec,
                        output_ass_path=ass_path
                    )
                    if os.path.exists(ass_path) and os.path.getsize(ass_path) > 100:
                        has_subtitles = True

        # Step 3: Vertical 9:16 Composite + Subtitle Burn
        if progress_callback:
            progress_callback(60.0, "Rendering 1080x1920 portrait canvas with ambient blur...")

        base_vf = build_vertical_filtergraph(style=style)
        
        # Build filter chain
        filter_steps = [base_vf]
        current_pad = "v_out"
        
        # Burn subtitles if generated
        if has_subtitles:
            # Escape path for FFmpeg filter syntax
            escaped_ass = ass_path.replace("\\", "/").replace(":", "\\:").replace("'", "\\'")
            filter_steps.append(f"[{current_pad}]ass='{escaped_ass}'[v_sub]")
            current_pad = "v_sub"
            
        # Optional channel branding watermark
        if watermark_text:
            clean_tag = str(watermark_text).replace("'", "").replace(":", "")
            filter_steps.append(
                f"[{current_pad}]drawtext=text='{clean_tag}':x=(w-tw)/2:y=240:fontsize=38:fontcolor=white@0.75:shadowcolor=black@0.6:shadowx=2:shadowy=2[v_final]"
            )
            current_pad = "v_final"

        full_filter_complex = ";".join(filter_steps)

        cmd = [
            "ffmpeg", "-y",
            "-i", raw_clip_path,
            "-filter_complex", full_filter_complex,
            "-map", f"[{current_pad}]",
            "-map", "0:a:0?",
            "-c:v", "libx264",
            "-preset", "veryfast",
            "-crf", "19",
            "-pix_fmt", "yuv420p",
            "-c:a", "aac",
            "-b:a", "192k",
            "-ar", "44100",
            "-movflags", "+faststart"
        ]
        cmd.extend(get_clean_metadata_args())
        cmd.append(output_path)

        res = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True)
        if res.returncode != 0:
            err = res.stderr[-400:] if res.stderr else "FFmpeg vertical render failed"
            raise RuntimeError(f"Shorts composition error: {err}")

        if progress_callback:
            progress_callback(100.0, "Viral Short generated successfully! Ready to download.")

        probe = probe_video(output_path)
        return {
            "success": True,
            "output_path": output_path,
            "duration": probe.get("duration", 0),
            "width": probe.get("width", 1080),
            "height": probe.get("height", 1920),
            "has_captions": has_subtitles
        }

    finally:
        # Cleanup temporary files
        import shutil
        shutil.rmtree(temp_dir, ignore_errors=True)
