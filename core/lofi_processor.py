"""
Music & Lo-Fi / Slowed + Reverb Audio Scrambler.
Transforms copyrighted songs into copyright-free Lo-Fi, Slowed+Reverb, or 8D audio.
"""

import os
import subprocess
from typing import Dict, Any, Optional
import yt_dlp

def build_lofi_filtergraph(style: str = "slowed_reverb", speed: float = 0.88, reverb_level: float = 0.5) -> str:
    """
    Constructs high-potency acoustic disruption filters:
    - Slowed & Reverb
    - 8D Spatial Audio Pan
    - Vinyl Warmth & Sub-bass EQ
    """
    filters = []

    if style == "slowed_reverb":
        # Slow down tempo & lower pitch gracefully
        tempo = max(0.75, min(0.95, speed))
        rate_factor = tempo
        filters.append(f"asetrate=44100*{rate_factor:.4f}")
        filters.append("aresample=44100")
        
        # Deep Ambient Reverb (aecho)
        reverb_in = min(0.8, 0.4 + (reverb_level * 0.3))
        reverb_decay = min(0.9, 0.6 + (reverb_level * 0.25))
        filters.append(f"aecho=0.8:{reverb_in:.2f}:60|120:{reverb_decay:.2f}|{reverb_decay*0.7:.2f}")
        
        # Warm Lo-Fi lowpass filter & sub-bass boost
        filters.append("lowpass=f=4200")
        filters.append("equalizer=f=80:t=q:w=1.2:g=4.5")
        filters.append("equalizer=f=2500:t=q:w=1.5:g=-3.0")

    elif style == "lofi_chill":
        # Lo-Fi acoustic filter + micro pitch shift
        filters.append(f"atempo={speed:.4f}")
        filters.append("equalizer=f=300:t=q:w=1.0:g=2.5")
        filters.append("lowpass=f=3800")
        filters.append("highpass=f=100")
        filters.append("aecho=0.8:0.4:40:0.3")

    elif style == "eight_d":
        # 8D Circular Spatial Audio Pan
        filters.append(f"atempo={speed:.4f}")
        filters.append("apulsator=mode=sine:hz=0.125:amount=0.9")
        filters.append("aecho=0.8:0.3:50:0.4")

    # Output level normalization
    filters.append("dynaudnorm=f=120:g=15")
    return ",".join(filters)

def process_music_lofi(
    input_source: str,
    output_path: str,
    is_youtube: bool = False,
    style: str = "slowed_reverb",
    speed: float = 0.88,
    reverb_level: float = 0.5,
    progress_callback = None
) -> str:
    """
    Takes YouTube URL or local audio file and transforms into copyright-free Lo-Fi track.
    """
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    temp_audio = f"{output_path}.temp.wav"

    if is_youtube:
        if progress_callback:
            progress_callback(15.0, "Extracting audio stream from YouTube...")

        ydl_opts = {
            'format': 'bestaudio/best',
            'outtmpl': f"{output_path}.yt.%(ext)s",
            'quiet': True,
            'no_warnings': True,
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'wav',
                'preferredquality': '192',
            }]
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([input_source])

        # Locate extracted wav
        raw_dir = os.path.dirname(output_path)
        base_prefix = f"{os.path.basename(output_path)}.yt."
        for f in os.listdir(raw_dir):
            if f.startswith(base_prefix) and f.endswith(".wav"):
                temp_audio = os.path.join(raw_dir, f)
                break
    else:
        temp_audio = input_source

    if not os.path.exists(temp_audio):
        raise RuntimeError("Failed to obtain input audio for Lo-Fi processing")

    if progress_callback:
        progress_callback(45.0, f"Synthesizing {style.replace('_', ' ').title()} acoustic matrices...")

    af = build_lofi_filtergraph(style, speed, reverb_level)

    cmd = [
        "ffmpeg", "-y",
        "-i", temp_audio,
        "-af", af,
        "-c:a", "aac",
        "-b:a", "256k",
        "-ar", "44100",
        output_path
    ]

    subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)

    # Clean up temp
    if is_youtube and os.path.exists(temp_audio):
        try:
            os.remove(temp_audio)
        except Exception:
            pass

    return output_path
