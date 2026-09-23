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
    Tier 1: Android + Web player client (clean, bypasses JS challenges & bot verification)
    Tier 2: Pure Android client (no cookies, direct CDN playback formats)
    Tier 3: VisionOS / TV client (cookie-less fallback)
    Tier 4: Web Creator & MWeb with cookies (for restricted private videos)
    Tier 5: Standard fallback
    """
    import shutil
    node_bin = shutil.which('node') or ('/home/veer/.nvm/versions/node/v24.16.0/bin/node' if os.path.exists('/home/veer/.nvm/versions/node/v24.16.0/bin/node') else None)

    client_strategies = [
        # Strategy 1: TV Embedded / VisionOS (bypasses bot challenges, gives all resolutions up to 4K)
        ({'extractor_args': {'youtube': {'player_client': ['visionos', 'tv']}}}, False),
        # Strategy 2: Android + Web combo (most reliable on Cloud/Railway datacenter IPs)
        ({'extractor_args': {'youtube': {'player_client': ['android', 'web']}}}, False),
        # Strategy 3: Pure Android client (no cookies)
        ({'extractor_args': {'youtube': {'player_client': ['android']}}}, False),
        # Strategy 4: Web Creator & MWeb with cookies if available
        ({'extractor_args': {'youtube': {'player_client': ['web_creator', 'mweb']}}}, True),
        # Strategy 5: Standard default
        ({}, False)
    ]

    last_err = None
    for strat, use_cookies in client_strategies:
        opts = {
            'quiet': True,
            'no_warnings': True,
            'socket_timeout': 30,
        }
        if node_bin:
            opts['js_runtimes'] = {'node': {'path': node_bin}}

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
    total_sec = max(0, int(seconds))
    hours = total_sec // 3600
    mins = (total_sec % 3600) // 60
    secs = total_sec % 60
    if hours > 0:
        return f"{hours:02d}:{mins:02d}:{secs:02d}"
    return f"{mins:02d}:{secs:02d}"

def is_direct_video_link(url: str) -> bool:
    """Checks if a URL is a direct video download/stream link."""
    clean = url.split("?")[0].lower()
    return (
        clean.endswith(('.mp4', '.mkv', '.webm', '.mov', '.avi', '.m4v')) or
        '/download' in clean or 'cloud' in clean or 'filesdl' in clean or 'gofile' in clean or 'indishare' in clean
    )

def resolve_direct_video_stream(url: str) -> dict:
    """
    Follows HTTP redirects, parses Content-Disposition for the true movie filename,
    and detects if the host CDN returned 403 Forbidden.
    """
    import requests
    from urllib.parse import urlparse, unquote
    import re

    parsed = urlparse(url)
    origin = f"{parsed.scheme}://{parsed.netloc}/"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
        "Referer": origin,
        "Accept": "*/*"
    }

    final_url = url
    real_filename = None
    is_blocked_403 = False

    try:
        resp = requests.get(url, headers=headers, stream=True, allow_redirects=True, timeout=8)
        if resp.status_code == 403:
            is_blocked_403 = True
        else:
            final_url = resp.url
            cd = resp.headers.get("Content-Disposition", "")
            if "filename=" in cd:
                m = re.search(r'filename\*?=(?:UTF-8\'\')?["\']?([^"\';]+)["\']?', cd)
                if m:
                    real_filename = unquote(m.group(1).strip())
        resp.close()
    except Exception:
        pass

    if not real_filename:
        path_name = unquote(urlparse(final_url).path.split("/")[-1])
        if path_name and not path_name.lower().endswith(('.php', '.html', '.htm', '.jsp', '.asp')):
            real_filename = path_name
        else:
            real_filename = "Direct_Movie.mp4"

    return {
        "final_url": final_url,
        "filename": real_filename,
        "origin": origin,
        "is_blocked_403": is_blocked_403
    }

def get_youtube_info(url: str) -> Dict[str, Any]:
    """
    Extracts metadata from YouTube URL or Direct Movie Download URL (9xflix, Filmyfly, etc.).
    """
    if is_direct_video_link(url):
        res_info = resolve_direct_video_stream(url)
        if res_info.get("is_blocked_403"):
            raise ValueError(
                "⚠️ Access Denied (403 Forbidden): Host server ne is link ko block kar diya hai. "
                "Yeh link aapke phone/browser IP ke sath locked hai. "
                "Solution: Browser me movie download shuru karein aur Chrome Downloads se final download link copy karein, ya file direct upload karein."
            )
        resolved_url = res_info.get("final_url") or url
        filename = res_info.get("filename") or "Direct_Movie.mp4"

        # Direct Movie CDN link probe
        from core.metadata_cleaner import probe_video
        try:
            p_info = probe_video(resolved_url)
            duration = float(p_info.get("duration", 0.0) or 0.0)
        except Exception:
            duration = 0.0

        # If probe failed or CDN blocked it, fallback to 3 hours so user can set end time manually
        if duration <= 0:
            duration = 10800.0  # 3 hours max — user will set actual end time

        return {
            "title": f"🎬 {filename}",
            "duration": duration,
            "duration_str": format_time_str(duration),
            "thumbnail": "https://images.unsplash.com/photo-1489599849927-2ee91cede3ba?w=400&q=80",
            "channel": "Direct Cloud CDN Stream",
            "id": "direct_stream",
            "is_direct": True,
            "resolved_url": resolved_url
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

def detect_hindi_or_best_audio_stream(url: str) -> Optional[int]:
    """
    Scans media stream tracks for MKV / Dual-Audio movies (9xflix, Filmyfly, HubCloud).
    Prioritizes Hindi audio track if available, else first audio stream.
    """
    try:
        from urllib.parse import urlparse
        p_u = urlparse(url)
        origin_h = f"Referer: {p_u.scheme}://{p_u.netloc}/\r\n"
        cmd = [
            "ffprobe", "-v", "error",
            "-headers", origin_h,
            "-user_agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
            "-reconnect", "1",
            "-reconnect_streamed", "1",
            "-reconnect_delay_max", "3",
            "-rw_timeout", "8000000",
            "-select_streams", "a",
            "-show_entries", "stream=index:stream_tags=language,title",
            "-of", "json",
            url
        ]
        res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True, timeout=10)
        if res.returncode == 0:
            import json as _json
            data = _json.loads(res.stdout)
            streams = data.get("streams", [])
            for s in streams:
                tags = s.get("tags", {})
                lang = str(tags.get("language", "")).lower()
                title = str(tags.get("title", "")).lower()
                if "hin" in lang or "hindi" in lang or "hindi" in title:
                    return s.get("index")
            if streams:
                return streams[0].get("index")
    except Exception:
        pass
    return None

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
    Supports MKV Dual-Audio track detection and network drop auto-reconnect.
    """
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    if progress_callback:
        progress_callback(10.0, "Resolving direct high-speed stream URLs...")

    # Direct Movie Link or YouTube Stream
    is_direct = is_direct_video_link(url)
    best_audio_idx = None

    if is_direct:
        v_url = url
        a_url = None
        clip_start = max(0.0, float(start_sec))
        if end_sec and end_sec > clip_start:
            clip_duration = min(14400.0, float(end_sec) - clip_start)
        else:
            clip_duration = 60.0
        if progress_callback:
            progress_callback(20.0, "Scanning MKV/MP4 stream tracks for Hindi audio...")
        best_audio_idx = detect_hindi_or_best_audio_stream(v_url)
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
            clip_duration = min(14400.0, float(end_sec) - clip_start)
        else:
            clip_duration = min(14400.0, total_duration) if total_duration > 0 else 45.0

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

    USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
    from urllib.parse import urlparse
    parsed_v = urlparse(v_url)
    origin_header = f"Referer: {parsed_v.scheme}://{parsed_v.netloc}/\r\n"

    # Construct FFmpeg HTTP Seek Command with Reconnect Resilience, Browser UA & Subtitle Suppression
    cmd = [
        "ffmpeg", "-y",
        "-headers", origin_header,
        "-user_agent", USER_AGENT,
        "-reconnect", "1",
        "-reconnect_at_eof", "1",
        "-reconnect_streamed", "1",
        "-reconnect_delay_max", "5",
        "-rw_timeout", "15000000",
        "-threads", "2",
        "-bufsize", "4000k",
        "-ss", str(clip_start),
        "-i", v_url
    ]

    if a_url:
        cmd.extend([
            "-headers", origin_header,
            "-user_agent", USER_AGENT,
            "-reconnect", "1",
            "-reconnect_at_eof", "1",
            "-reconnect_streamed", "1",
            "-reconnect_delay_max", "5",
            "-rw_timeout", "15000000",
            "-ss", str(clip_start),
            "-i", a_url
        ])

    cmd.extend(["-t", str(clip_duration), "-sn"])

    if a_url:
        cmd.extend([
            "-c:v", "libx264", "-preset", "ultrafast", "-crf", "18",
            "-af", "aresample=async=1000:min_hard_comp=0.100000:first_pts=0",
            "-c:a", "aac", "-b:a", "192k",
            "-map", "0:v:0", "-map", "1:a:0?",
            "-avoid_negative_ts", "make_zero"
        ])
    elif is_direct and best_audio_idx is not None:
        cmd.extend([
            "-c:v", "libx264", "-preset", "ultrafast", "-crf", "18",
            "-af", "aresample=async=1000:min_hard_comp=0.100000:first_pts=0",
            "-c:a", "aac", "-b:a", "192k",
            "-map", "0:v:0", "-map", f"0:{best_audio_idx}?",
            "-avoid_negative_ts", "make_zero"
        ])
    else:
        cmd.extend([
            "-c:v", "libx264", "-preset", "ultrafast", "-crf", "18",
            "-af", "aresample=async=1000:min_hard_comp=0.100000:first_pts=0",
            "-c:a", "aac", "-b:a", "192k",
            "-map", "0:v:0", "-map", "0:a:0?",
            "-avoid_negative_ts", "make_zero"
        ])

    # Try Fast Direct Stream Copy first if is_direct (completes 10min clip in 3-5 seconds without re-encode)
    copy_success = False
    if is_direct:
        if progress_callback:
            progress_callback(28.0, "Attempting high-speed zero-loss stream cut...")
        cmd_copy = [
            "ffmpeg", "-y",
            "-headers", origin_header,
            "-user_agent", USER_AGENT,
            "-reconnect", "1",
            "-reconnect_at_eof", "1",
            "-reconnect_streamed", "1",
            "-reconnect_delay_max", "5",
            "-rw_timeout", "15000000",
            "-ss", str(clip_start),
            "-i", v_url,
            "-t", str(clip_duration),
            "-sn",
            "-c", "copy",
            "-avoid_negative_ts", "make_zero",
            "-movflags", "+faststart",
            output_path
        ]
        res_copy = subprocess.run(cmd_copy, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if res_copy.returncode == 0 and os.path.exists(output_path) and os.path.getsize(output_path) > 10000:
            copy_success = True

    if not copy_success:
        cmd.extend(["-progress", "pipe:1", "-movflags", "+faststart", output_path])

        if progress_callback:
            progress_callback(30.0, "Writing trimmed clip container to disk...")

        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, bufsize=1)
        out_time_pattern = re.compile(r"out_time_ms=(\d+)")

        while True:
            line = proc.stdout.readline()
            if not line and proc.poll() is not None:
                break
            line = line.strip()
            match = out_time_pattern.search(line)
            if match and clip_duration > 0:
                current_ms = int(match.group(1))
                current_sec = current_ms / 1_000_000.0
                pct = 30.0 + (min(current_sec / clip_duration, 1.0) * 9.5)
                if progress_callback:
                    progress_callback(min(pct, 39.5), f"Capturing clip: {int(current_sec)}s / {int(clip_duration)}s ({int(min(current_sec/clip_duration, 1.0)*100)}%)...")

        retcode = proc.wait()
        if retcode != 0:
            # Fallback if fast seek failed: try safe re-encode with reconnect headers & subtitle suppression
            cmd_fallback = [
                "ffmpeg", "-y",
                "-headers", origin_header,
                "-user_agent", USER_AGENT,
                "-reconnect", "1",
                "-reconnect_at_eof", "1",
                "-reconnect_streamed", "1",
                "-reconnect_delay_max", "5",
                "-rw_timeout", "15000000",
                "-ss", str(clip_start),
                "-i", v_url,
                "-t", str(clip_duration),
                "-sn",
                "-c:v", "libx264", "-preset", "ultrafast", "-crf", "20",
                "-af", "aresample=async=1000:first_pts=0",
                "-map", "0:v:0", "-map", "0:a:0?",
                "-avoid_negative_ts", "make_zero",
                output_path
            ]
            res_fb = subprocess.run(cmd_fallback, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True)
            if res_fb.returncode != 0:
                err_msg = (res_fb.stderr or "")[-300:]
                raise RuntimeError(f"FFmpeg stream capture error: {err_msg}")

    if not os.path.exists(output_path) or os.path.getsize(output_path) == 0:
        raise RuntimeError("Failed to generate trimmed video file from YouTube stream.")

    if progress_callback:
        progress_callback(40.0, "Trim complete! Entering Anti-Copyright Engine...")

    return output_path

def get_downloader_info(url: str) -> Dict[str, Any]:
    """
    Extracts video information and available download quality options for the Video Downloader tab.
    Supports YouTube links and direct CDN links.
    """
    is_direct = is_direct_video_link(url)
    if is_direct:
        from core.metadata_cleaner import probe_video
        try:
            p_info = probe_video(url)
            duration = float(p_info.get("duration", 0.0) or 0.0)
        except Exception:
            duration = 0.0
        
        filename = os.path.basename(url.split("?")[0]) or "Direct_Video.mp4"
        return {
            "title": f"🎬 {filename}",
            "channel": "Direct Cloud CDN Link",
            "duration": duration,
            "duration_str": format_time_str(duration) if duration > 0 else "Direct File",
            "thumbnail": "https://images.unsplash.com/photo-1489599849927-2ee91cede3ba?w=400&q=80",
            "is_direct": True,
            "formats": [
                {"id": "direct_original", "label": "Original Direct File", "ext": "mp4", "badge": "Source Quality", "icon": "🎬", "quality": "direct"}
            ]
        }

    # YouTube Video Info & Available Formats
    info = extract_with_client_fallback(url, download=False, custom_opts={'skip_download': True})
    duration = float(info.get('duration', 0) or 0)
    thumbnail = info.get('thumbnail', '')
    if 'thumbnails' in info and info['thumbnails']:
        thumbnail = info['thumbnails'][-1].get('url', thumbnail)

    # Detect available resolutions
    formats_list = info.get('formats', [])
    available_heights = set(f.get('height') for f in formats_list if f.get('height'))

    download_options = []
    
    # 1080p
    if 1080 in available_heights or any(h >= 1080 for h in available_heights):
        download_options.append({
            "id": "1080p",
            "label": "1080p Full HD",
            "ext": "mp4",
            "badge": "1080p Crisp",
            "icon": "🎬",
            "quality": "1080p"
        })
    
    # 720p (default if available or as primary)
    download_options.append({
        "id": "720p",
        "label": "720p HD Video",
        "ext": "mp4",
        "badge": "HD • Recommended",
        "icon": "🎬",
        "quality": "720p"
    })

    # 480p / 360p
    download_options.append({
        "id": "360p",
        "label": "360p / 480p Fast",
        "ext": "mp4",
        "badge": "Fast • Low Data",
        "icon": "⚡",
        "quality": "360p"
    })

    # MP3 Audio
    download_options.append({
        "id": "mp3",
        "label": "Audio Only (MP3)",
        "ext": "mp3",
        "badge": "192kbps High Quality",
        "icon": "🎵",
        "quality": "mp3"
    })

    return {
        "title": info.get('title', 'YouTube Video'),
        "channel": info.get('uploader') or info.get('channel', 'YouTube Creator'),
        "duration": duration,
        "duration_str": format_time_str(duration),
        "thumbnail": thumbnail,
        "is_direct": False,
        "formats": download_options
    }

def download_media_file(url: str, quality: str, output_path: str) -> str:
    """
    Downloads raw YouTube video or direct CDN video to output_path.
    Quality options: 1080p, 720p, 360p, mp3, direct.
    """
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    is_direct = is_direct_video_link(url)

    if is_direct:
        # Direct stream copy with FFmpeg
        cmd = [
            "ffmpeg", "-y",
            "-reconnect", "1",
            "-reconnect_at_eof", "1",
            "-reconnect_streamed", "1",
            "-reconnect_delay_max", "5",
            "-user_agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
            "-i", url,
            "-c", "copy",
            "-sn",
            "-avoid_negative_ts", "make_zero",
            output_path
        ]
        subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
        return output_path

    # YouTube Download via yt-dlp
    import shutil
    node_bin = shutil.which('node') or ('/home/veer/.nvm/versions/node/v24.16.0/bin/node' if os.path.exists('/home/veer/.nvm/versions/node/v24.16.0/bin/node') else None)

    ydl_opts = {
        'quiet': True,
        'no_warnings': True,
        'outtmpl': output_path,
        'socket_timeout': 45,
        'extractor_args': {'youtube': {'player_client': ['visionos', 'tv', 'android', 'web']}}
    }
    if node_bin:
        ydl_opts['js_runtimes'] = {'node': {'path': node_bin}}

    if quality == "mp3":
        ydl_opts.update({
            'format': 'bestaudio/best',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
        })
        # If output_path ends with .mp3, yt-dlp automatically produces .mp3
        base_no_ext = os.path.splitext(output_path)[0]
        ydl_opts['outtmpl'] = f"{base_no_ext}.%(ext)s"
    elif quality == "1080p":
        ydl_opts['format'] = 'bestvideo[height<=1080]+bestaudio/best[height<=1080]/best'
        ydl_opts['merge_output_format'] = 'mp4'
    elif quality == "720p":
        ydl_opts['format'] = 'bestvideo[height<=720]+bestaudio/best[height<=720]/best'
        ydl_opts['merge_output_format'] = 'mp4'
    else: # 360p / fast
        ydl_opts['format'] = 'best[height<=480]/best[height<=360]/best'
        ydl_opts['merge_output_format'] = 'mp4'

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])

    # Check for actual created file (mp3 post-processing might change extension)
    if os.path.exists(output_path):
        return output_path
    
    mp3_candidate = f"{os.path.splitext(output_path)[0]}.mp3"
    if os.path.exists(mp3_candidate):
        return mp3_candidate

    mp4_candidate = f"{os.path.splitext(output_path)[0]}.mp4"
    if os.path.exists(mp4_candidate):
        return mp4_candidate

    raise RuntimeError("Downloaded file not found on disk.")

