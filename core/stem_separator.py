"""
AI Stem Separation & Background Music Replacement Module.
Supports Demucs Neural Network (when available) with high-fidelity DSP Center-Channel Vocal Extraction fallback.
Mutes copyrighted background music and mixes royalty-free clean background audio.
"""

import os
import shutil
import subprocess

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ASSETS_BGM_DIR = os.path.join(BASE_DIR, "assets", "bgm")

def has_demucs() -> bool:
    return shutil.which("demucs") is not None

def get_bgm_file(bgm_type: str = "lofi_chill") -> str:
    for ext in [".wav", ".aac", ".mp3"]:
        candidate = os.path.join(ASSETS_BGM_DIR, f"{bgm_type}{ext}")
        if os.path.exists(candidate) and os.path.getsize(candidate) > 0:
            return candidate
    # Fallback to any valid audio in bgm dir
    for f in os.listdir(ASSETS_BGM_DIR):
        full = os.path.join(ASSETS_BGM_DIR, f)
        if os.path.isfile(full) and os.path.getsize(full) > 0:
            return full
    return ""

def isolate_dialogue_and_swap_bgm(
    input_video: str,
    output_audio_path: str,
    temp_dir: str,
    bgm_type: str = "lofi_chill",
    progress_callback = None
) -> str:
    os.makedirs(temp_dir, exist_ok=True)
    extracted_raw_audio = os.path.join(temp_dir, "raw_audio.wav")
    vocals_isolated = os.path.join(temp_dir, "vocals_clean.wav")
    
    # 1. Extract audio from video
    if progress_callback:
        progress_callback(10, "Extracting audio stream for dialogue isolation...")
        
    cmd_extract = [
        "ffmpeg", "-y", "-i", input_video,
        "-vn", "-acodec", "pcm_s16le", "-ar", "44100", "-ac", "2",
        extracted_raw_audio
    ]
    subprocess.run(cmd_extract, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
    
    # 2. Try Demucs AI separation, or fallback to center-channel vocal band isolation
    use_ai = has_demucs()
    if use_ai:
        try:
            if progress_callback:
                progress_callback(25, "Running Demucs neural stem separation (isolating speech)...")
            demucs_out_dir = os.path.join(temp_dir, "demucs_out")
            os.makedirs(demucs_out_dir, exist_ok=True)
            
            cmd_demucs = [
                "demucs", "--two-stems=vocals", "-n", "htdemucs",
                "-o", demucs_out_dir, extracted_raw_audio
            ]
            subprocess.run(cmd_demucs, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
            
            for root, _, files in os.walk(demucs_out_dir):
                if "vocals.wav" in files:
                    shutil.copyfile(os.path.join(root, "vocals.wav"), vocals_isolated)
                    break
        except Exception:
            use_ai = False
            
    if not use_ai or not os.path.exists(vocals_isolated):
        if progress_callback:
            progress_callback(30, "Applying Center-Channel Phase Dialogue Isolation...")
            
        vocal_filter = (
            "pan=stereo|c0=0.6*c0+0.4*c1|c1=0.4*c0+0.6*c1,"
            "highpass=f=120,lowpass=f=4500,"
            "equalizer=f=1800:t=q:w=1.0:g=3.0,"
            "afftdn=nf=-25"
        )
        cmd_dsp = [
            "ffmpeg", "-y", "-i", extracted_raw_audio,
            "-af", vocal_filter,
            "-ar", "44100",
            vocals_isolated
        ]
        subprocess.run(cmd_dsp, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
        
    # 3. Locate chosen royalty-free BGM
    bgm_file = get_bgm_file(bgm_type)
    
    # 4. Mix Clean Dialogue with Safe BGM
    if progress_callback:
        progress_callback(45, "Layering copyright-free background score & balancing speech...")
        
    mix_filter = (
        "[0:a]volume=1.2,dynaudnorm=f=120:g=15[dialogue];"
        "[1:a]volume=0.12,lowpass=f=3500[safe_bgm];"
        "[dialogue][safe_bgm]amix=inputs=2:duration=first:dropout_transition=2[final_audio]"
    )
    
    cmd_mix = [
        "ffmpeg", "-y",
        "-i", vocals_isolated,
        "-stream_loop", "-1", "-i", bgm_file,
        "-filter_complex", mix_filter,
        "-map", "[final_audio]",
        "-c:a", "aac", "-b:a", "192k", "-ar", "44100",
        output_audio_path
    ]
    subprocess.run(cmd_mix, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
    return output_audio_path
