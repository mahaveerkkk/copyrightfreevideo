"""
YouTube Video Stream & Trimmer Service using yt-dlp & FFmpeg.
Enables instant link fetch, thumbnail preview, and stream-trimmed downloading.
"""

import os
import re
import subprocess
from typing import Dict, Any, Optional
import yt_dlp

def format_time_str(seconds: float) -> str:
    mins = int(seconds // 60)
    secs = int(seconds % 60)
    return f"{mins:02d}:{secs:02d}"

def get_youtube_info(url: str) -> Dict[str, Any]:
    """
    Extracts metadata from YouTube URL without downloading the video.
    Returns: title, duration, duration_str, thumbnail, author, channel
    """
    ydl_opts = {
        'quiet': True,
        'no_warnings': True,
        'skip_download': True,
        'extract_flat': False
    }
    
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        try:
            info = ydl.extract_info(url, download=False)
        except Exception as e:
            raise ValueError(f"Could not fetch YouTube video: {str(e)}")
            
        duration = float(info.get('duration', 0) or 0)
        
        # Best available thumbnail
        thumbnail = info.get('thumbnail', '')
        if 'thumbnails' in info and info['thumbnails']:
            # Pick high quality thumbnail
            thumbnail = info['thumbnails'][-1].get('url', thumbnail)
            
        return {
            "title": info.get('title', 'YouTube Video'),
            "duration": duration,
            "duration_str": format_time_str(duration),
            "thumbnail": thumbnail,
            "channel": info.get('uploader') or info.get('channel', 'Unknown Creator'),
            "id": info.get('id', '')
        }

def download_and_trim_youtube(
    url: str,
    output_path: str,
    start_sec: float = 0.0,
    end_sec: Optional[float] = None,
    progress_callback = None
) -> str:
    """
    Downloads only the desired trimmed section of a YouTube video directly to disk.
    If end_sec is None or 0, downloads up to end or 5 minutes max for safety.
    """
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    temp_template = f"{output_path}.raw.%(ext)s"
    
    if progress_callback:
        progress_callback(10.0, "Connecting to YouTube stream...")

    ydl_opts = {
        'format': 'bestvideo[height<=1080][ext=mp4]+bestaudio[ext=m4a]/best[height<=1080][ext=mp4]/best',
        'outtmpl': temp_template,
        'quiet': True,
        'no_warnings': True,
    }

    # If trimming is requested, apply download ranges
    if start_sec > 0 or (end_sec is not None and end_sec > 0):
        target_end = end_sec if (end_sec and end_sec > start_sec) else (start_sec + 60.0)
        ydl_opts['download_ranges'] = yt_dlp.utils.download_range_func(None, [(start_sec, target_end)])
        ydl_opts['force_keyframes_at_cuts'] = True

    if progress_callback:
        progress_callback(25.0, "Extracting trimmed clip from YouTube...")

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])

    # Find the downloaded raw file
    raw_dir = os.path.dirname(output_path)
    base_prefix = f"{os.path.basename(output_path)}.raw."
    downloaded_raw = None
    
    for f in os.listdir(raw_dir):
        if f.startswith(base_prefix):
            downloaded_raw = os.path.join(raw_dir, f)
            break

    if not downloaded_raw or not os.path.exists(downloaded_raw):
        raise RuntimeError("Failed to capture trimmed YouTube stream to disk")

    if progress_callback:
        progress_callback(40.0, "Remuxing to standard MP4 stream...")

    # Fast remux to standard clean MP4 container
    cmd_remux = [
        "ffmpeg", "-y",
        "-i", downloaded_raw,
        "-c", "copy",
        "-movflags", "+faststart",
        output_path
    ]
    subprocess.run(cmd_remux, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)

    # Clean up raw temp file
    try:
        os.remove(downloaded_raw)
    except Exception:
        pass

    return output_path
