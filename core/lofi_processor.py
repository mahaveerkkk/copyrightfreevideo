"""
Music & Lo-Fi / Slowed + Reverb Audio Scrambler.
Transforms copyrighted songs into copyright-free Lo-Fi, Slowed+Reverb, or 8D audio.
Includes Hardcore Pitch Shifting (-1.5 Semitones), Acoustic Constellation Disruption,
and Android/iOS app client spoofing to prevent bot detection.
"""

import os
import math
import subprocess
from typing import Dict, Any, Optional
import yt_dlp
from core.youtube_service import extract_with_client_fallback

def build_lofi_filtergraph(style: str = "slowed_reverb", speed: float = 0.88, reverb_level: float = 0.5) -> str:
    """
    Constructs high-potency acoustic disruption filters:
    - Pitch Shift (-1.5 semitones) destroys Content ID Shazam constellation graph
    - Multi-band notch filtering removes original harmonic peaks
    - Tempo deceleration (0.85x - 0.88x) scrambles temporal matching
    - Ambient room reverb & warm analog lowpass
    """
    filters = []

    # 1. HARDCORE PITCH SHIFT (-1.5 semitones)
    # Pitch ratio: 2^(-1.5 / 12) ~ 0.9170
    pitch_semitones = -1.5
    pitch_ratio = math.pow(2.0, pitch_semitones / 12.0)
    adjusted_rate = int(44100 * pitch_ratio)

    # 2. TEMPO DECELERATION
    target_tempo = max(0.80, min(0.92, speed))
    tempo_factor = target_tempo / pitch_ratio
    tempo_factor = max(0.5, min(2.0, tempo_factor))

    # Apply Pitch + Tempo
    filters.append(f"asetrate={adjusted_rate}")
    filters.append("aresample=44100")
    filters.append(f"atempo={tempo_factor:.4f}")

    # 3. CONTENT ID NOTCH FILTER (Destroy T-Series / Shazam constellation peaks at 1.2kHz & 3.2kHz)
    filters.append("equalizer=f=3200:t=q:w=1.5:g=-4.0")
    filters.append("equalizer=f=1200:t=q:w=1.5:g=-3.0")

    if style == "slowed_reverb":
        # Deep Ambient Reverb & Warm Analog Lo-Fi
        reverb_in = min(0.85, 0.45 + (reverb_level * 0.3))
        reverb_decay = min(0.92, 0.65 + (reverb_level * 0.25))
        filters.append(f"aecho=0.8:{reverb_in:.2f}:60|120:{reverb_decay:.2f}|{reverb_decay*0.7:.2f}")
        filters.append("lowpass=f=4000")
        filters.append("equalizer=f=90:t=q:w=1.2:g=5.0")  # Sub-bass warmth boost

    elif style == "lofi_chill":
        # Vintage Lo-Fi Vinyl EQ & Warmth
        filters.append("equalizer=f=350:t=q:w=1.0:g=3.0")
        filters.append("lowpass=f=3500")
        filters.append("highpass=f=120")
        filters.append("aecho=0.8:0.4:50:0.35")

    elif style == "eight_d":
        # 8D Circular Spatial Audio Pan + Reverb
        filters.append("apulsator=mode=sine:hz=0.12:amount=0.92")
        filters.append("aecho=0.8:0.35:60:0.4")
        filters.append("lowpass=f=5000")

    # Final studio leveling
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
    Uses Android/iOS client fallback to prevent YouTube bot detection.
    """
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    temp_audio = f"{output_path}.temp.wav"

    if is_youtube:
        if progress_callback:
            progress_callback(15.0, "Resolving YouTube audio stream via Android client...")

        # Use extract_with_client_fallback to bypass bot block
        info = extract_with_client_fallback(
            input_source,
            download=False,
            custom_opts={'format': 'bestaudio/best'}
        )

        # Get direct audio streaming URL
        audio_url = info.get('url')
        if not audio_url and 'requested_formats' in info:
            audio_url = info['requested_formats'][-1].get('url')

        if not audio_url:
            raise RuntimeError("Could not resolve direct audio stream from YouTube.")

        if progress_callback:
            progress_callback(30.0, "Capturing high-fidelity audio stream...")

        # Rapid stream capture with FFmpeg (no full download bottleneck)
        cmd_extract = [
            "ffmpeg", "-y",
            "-i", audio_url,
            "-vn", "-acodec", "pcm_s16le", "-ar", "44100", "-ac", "2",
            temp_audio
        ]
        res = subprocess.run(cmd_extract, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True)
        if res.returncode != 0:
            raise RuntimeError(f"Failed to capture audio stream: {res.stderr[-300:]}")
    else:
        temp_audio = input_source

    if not os.path.exists(temp_audio) or os.path.getsize(temp_audio) == 0:
        raise RuntimeError("Input audio file could not be read.")

    if progress_callback:
        progress_callback(60.0, "Applying Hardcore Pitch Shift (-1.5st) & Shazam Disruption...")

    af = build_lofi_filtergraph(style, speed, reverb_level)

    cmd_filter = [
        "ffmpeg", "-y",
        "-i", temp_audio,
        "-af", af,
        "-c:a", "aac",
        "-b:a", "256k",
        "-ar", "44100",
        output_path
    ]

    subprocess.run(cmd_filter, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)

    # Clean up intermediate wav
    if is_youtube and os.path.exists(temp_audio):
        try:
            os.remove(temp_audio)
        except Exception:
            pass

    if progress_callback:
        progress_callback(100.0, "Copyright-Free Track Complete!")

    return output_path
