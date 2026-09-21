"""
Production YouTube Video Stream & Trimmer Service.
- Multi-client anti-bot fallback pipeline (Android, iOS, Web Creator).
- Direct HTTP Seek with FFmpeg: Never downloads full movie, trims 30s in 5-8 seconds.
- Cookie file support via environment variable or cookies.txt.
"""

import os
import re
import subprocess
from typing import Dict, Any, Optional, List
import yt_dlp

COOKIES_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'cookies.txt')

def get_base_ydl_opts() -> dict:
    """Returns base yt-dlp configuration with bot-detection bypass."""
    opts = {
        'quiet': True,
        'no_warnings': True,
        'socket_timeout': 30,
    }
    
    # Cookie support if present
    cookies_env = os.environ.get('YOUTUBE_COOKIES')
    if cookies_env:
        c_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'cookies_runtime.txt')
        with open(c_path, 'w', encoding='utf-8') as f:
            f.write(cookies_env)
        opts['cookiefile'] = c_path
    elif os.path.exists(COOKIES_FILE) and os.path.getsize(COOKIES_FILE) > 0:
        opts['cookiefile'] = COOKIES_FILE

    return opts

def extract_with_client_fallback(url: str, download: bool = False, custom_opts: Optional[dict] = None) -> dict:
    """
    Extracts video metadata or direct streaming URLs using multi-tier client fallback.
    Prevents 'The page needs to be reloaded' and 'Sign in to confirm you are not a bot' blocks.
    Tier 1: TV Embedded (best for restricted music/movies, never requires page reload)
    Tier 2: VisionOS & TV (high compatibility, bypasses web JS bot challenges)
    Tier 3: Web Creator & MWeb
    Tier 4: Android & iOS app client
    Tier 5: Clean fallback without cookies (in case cookies are stale)
    """
    client_strategies = [
        # Strategy 1: TV Embedded (most resilient, bypasses reload errors & bot checks)
        ({'extractor_args': {'youtube': {'player_client': ['tv_embedded']}}}, True),
        # Strategy 2: VisionOS & TV
        ({'extractor_args': {'youtube': {'player_client': ['visionos', 'tv']}}}, False),
        # Strategy 3: Web Creator & MWeb
        ({'extractor_args': {'youtube': {'player_client': ['web_creator', 'mweb']}}}, True),
        # Strategy 4: Android & iOS app client (no cookies because android client rejects cookies)
        ({'extractor_args': {'youtube': {'player_client': ['android', 'ios']}}}, False),
        # Strategy 5: Clean TV embedded without cookies
        ({'extractor_args': {'youtube': {'player_client': ['tv_embedded']}}}, False),
        # Strategy 6: Standard default
        ({}, False)
    ]

    last_err = None
    for strat, use_cookies in client_strategies:
        opts = {
            'quiet': True,
            'no_warnings': True,
            'socket_timeout': 30,
        }
        if use_cookies:
            base_cookie_opts = get_base_ydl_opts()
            if 'cookiefile' in base_cookie_opts:
                opts['cookiefile'] = base_cookie_opts['cookiefile']

        opts.update(strat)
        if custom_opts:
            opts.update(custom_opts)

        try:
            with yt_dlp.YoutubeDL(opts) as ydl:
                info = ydl.extract_info(url, download=download)
                if info:
                    return info
        except Exception as e:
            last_err = e
            continue

    if last_err:
        raise last_err
    raise RuntimeError("Unable to extract YouTube video with client fallback.")

def format_time_str(seconds: float) -> str:
    mins = int(seconds // 60)
    secs = int(seconds % 60)
    return f"{mins:02d}:{secs:02d}"

def is_direct_video_link(url: str) -> bool:
    """Checks if a URL is a direct video download/stream link."""
    clean = url.split("?")[0].lower()
    return clean.endswith(('.mp4', '.mkv', '.webm', '.mov', '.avi', '.m4v')) or '/download' in clean

def get_youtube_info(url: str) -> Dict[str, Any]:
    """
    Extracts metadata from YouTube URL or Direct Movie Download URL (9xflix, Filmyfly, etc.).
    """
    if is_direct_video_link(url):
        # Direct Movie CDN link probe
        from core.metadata_cleaner import probe_video
        try:
            p_info = probe_video(url)
            duration = float(p_info.get("duration", 0.0) or 0.0)
        except Exception:
            duration = 3600.0 # fallback duration if server blocks probe

        filename = os.path.basename(url.split("?")[0]) or "Direct_Movie.mp4"
        return {
            "title": f"🎬 {filename}",
            "duration": duration,
            "duration_str": format_time_str(duration),
            "thumbnail": "https://images.unsplash.com/photo-1489599849927-2ee91cede3ba?w=400&q=80",
            "channel": "Direct Cloud CDN Stream",
            "id": "direct_stream",
            "is_direct": True
        }

    info = extract_with_client_fallback(url, download=False, custom_opts={'skip_download': True})
    duration = float(info.get('duration', 0) or 0)
    
    thumbnail = info.get('thumbnail', '')
    if 'thumbnails' in info and info['thumbnails']:
        thumbnail = info['thumbnails'][-1].get('url', thumbnail)

    return {
        "title": info.get('title', 'YouTube Video'),
        "duration": duration,
        "duration_str": format_time_str(duration),
        "thumbnail": thumbnail,
        "channel": info.get('uploader') or info.get('channel', 'Unknown Creator'),
        "id": info.get('id', ''),
        "is_direct": False
    }

def download_and_trim_youtube(
    url: str,
    output_path: str,
    start_sec: float = 0.0,
    end_sec: Optional[float] = None,
    progress_callback = None
) -> str:
    """
    Direct HTTP Seek Trimmer:
    Obtains the direct streaming CDN URLs from yt-dlp and uses FFmpeg -ss to capture
    ONLY the target segment. Completes in 4-8s without downloading the rest of the video.
    """
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    if progress_callback:
        progress_callback(10.0, "Resolving direct high-speed stream URLs...")

    # Direct Movie Link or YouTube Stream
    if is_direct_video_link(url):
        v_url = url
        a_url = None
        clip_start = max(0.0, float(start_sec))
        if end_sec and end_sec > clip_start:
            clip_duration = min(600.0, float(end_sec) - clip_start)
        else:
            clip_duration = 60.0
        if progress_callback:
            progress_callback(25.0, f"Capturing {int(clip_duration)}s clip from direct movie stream...")
    else:
        # Extract direct video and audio streaming URLs from YouTube
        custom_opts = {
            'format': 'bestvideo[height<=1080][ext=mp4]+bestaudio[ext=m4a]/best[height<=1080][ext=mp4]/best',
            'skip_download': True
        }
        info = extract_with_client_fallback(url, download=False, custom_opts=custom_opts)

        # Calculate trim duration
        total_duration = float(info.get('duration', 0) or 0)
        clip_start = max(0.0, float(start_sec))
        if end_sec and end_sec > clip_start:
            clip_duration = min(600.0, float(end_sec) - clip_start)
        else:
            clip_duration = 45.0 # default 45s clip if unspecified

        if progress_callback:
            progress_callback(25.0, f"Capturing direct {int(clip_duration)}s clip from stream...")

        # Check if stream has separate video and audio URLs
        v_url = None
        a_url = None

        if 'requested_formats' in info and len(info['requested_formats']) >= 2:
            v_url = info['requested_formats'][0].get('url')
            a_url = info['requested_formats'][1].get('url')
        elif 'url' in info:
            v_url = info.get('url')
            a_url = None

        if not v_url:
            raise RuntimeError("Could not resolve streaming URL from YouTube.")

    # Construct FFmpeg HTTP Seek Command
    # Placing -ss before -i enables rapid seek without downloading earlier parts
    # -avoid_negative_ts make_zero ensures video and audio PTS start synchronously from timestamp 0.000
    cmd = ["ffmpeg", "-y"]
    cmd.extend(["-ss", str(clip_start)])
    cmd.extend(["-i", v_url])

    if a_url:
        cmd.extend(["-ss", str(clip_start)])
        cmd.extend(["-i", a_url])

    cmd.extend(["-t", str(clip_duration)])

    if a_url:
        cmd.extend([
            "-c:v", "libx264", "-preset", "ultrafast", "-crf", "18",
            "-af", "aresample=async=1000:min_hard_comp=0.100000:first_pts=0",
            "-c:a", "aac", "-b:a", "192k",
            "-map", "0:v:0", "-map", "1:a:0",
            "-avoid_negative_ts", "make_zero"
        ])
    else:
        cmd.extend([
            "-c:v", "libx264", "-preset", "ultrafast", "-crf", "18",
            "-af", "aresample=async=1000:min_hard_comp=0.100000:first_pts=0",
            "-c:a", "aac", "-b:a", "192k",
            "-avoid_negative_ts", "make_zero"
        ])

    cmd.extend(["-movflags", "+faststart", output_path])

    if progress_callback:
        progress_callback(35.0, "Writing trimmed clip container to disk...")

    res = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True)
    if res.returncode != 0:
        # Fallback if fast seek failed: try safe re-encode with zero timestamp alignment
        cmd_fallback = [
            "ffmpeg", "-y",
            "-ss", str(clip_start), "-i", v_url,
            "-t", str(clip_duration),
            "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
            "-af", "aresample=async=1000:first_pts=0",
            "-avoid_negative_ts", "make_zero",
            output_path
        ]
        subprocess.run(cmd_fallback, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)

    if not os.path.exists(output_path) or os.path.getsize(output_path) == 0:
        raise RuntimeError("Failed to generate trimmed video file from YouTube stream.")

    if progress_callback:
        progress_callback(40.0, "Trim complete! Entering Anti-Copyright Engine...")

    return output_path
