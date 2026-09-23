"""
Container metadata cleaner and probe utility.
Strips digital footprints, camera tags, EXIF, and encoder signatures.
"""

import json
import subprocess
from typing import Dict, Any

def get_clean_metadata_args() -> list:
    """
    Returns standard FFmpeg CLI flags to strip all container tags and inject clean synthetic atoms.
    """
    return [
        "-map_metadata", "-1",
        "-map_chapters", "-1",
        "-fflags", "+bitexact+genpts",
        "-metadata", "title=",
        "-metadata", "artist=",
        "-metadata", "album=",
        "-metadata", "comment=",
        "-metadata", "encoder=MediaEngine Pro"
    ]

def probe_video(file_path: str) -> Dict[str, Any]:
    """
    Uses ffprobe to extract stream information, duration, resolution, and audio channels.
    Supports remote CDN URLs (Gofile, HubCloud, FileDL) with User-Agent and timeout.
    """
    is_remote = file_path.startswith("http://") or file_path.startswith("https://")

    cmd = [
        "ffprobe",
        "-v", "quiet",
        "-print_format", "json",
        "-show_format",
        "-show_streams",
    ]

    if is_remote:
        cmd.extend([
            "-user_agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
            "-timeout", "10000000",
            "-rw_timeout", "10000000",
            "-reconnect", "1",
            "-reconnect_streamed", "1",
            "-reconnect_delay_max", "3",
        ])

    cmd.append(file_path)

    try:
        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=True, timeout=15)
        data = json.loads(result.stdout)
        
        video_stream = next((s for s in data.get("streams", []) if s.get("codec_type") == "video"), None)
        audio_stream = next((s for s in data.get("streams", []) if s.get("codec_type") == "audio"), None)
        
        format_info = data.get("format", {})
        duration = float(format_info.get("duration", 0.0))
        
        return {
            "has_video": video_stream is not None,
            "has_audio": audio_stream is not None,
            "duration": duration,
            "width": int(video_stream.get("width", 0)) if video_stream else 0,
            "height": int(video_stream.get("height", 0)) if video_stream else 0,
            "codec_video": video_stream.get("codec_name", "unknown") if video_stream else None,
            "codec_audio": audio_stream.get("codec_name", "unknown") if audio_stream else None,
            "fps": eval(video_stream.get("r_frame_rate", "30/1")) if video_stream and "/" in video_stream.get("r_frame_rate", "") else 30.0,
            "format_name": format_info.get("format_name", "mp4"),
            "size_bytes": int(format_info.get("size", 0))
        }
    except Exception as e:
        return {
            "error": str(e),
            "has_video": False,
            "has_audio": False,
            "duration": 0.0
        }
