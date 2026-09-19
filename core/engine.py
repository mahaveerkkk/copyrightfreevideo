"""
Master Video Transformation Engine.
Supports Dual-Engine Execution:
1. ⚡ Turbo DSP Mode (4-8s fast filtergraph)
2. 🧠 AI Deep Studio Mode (Vocal Isolation, BGM Swap, and 9:16 Split-Screen Canvas)
"""

import os
import re
import subprocess
import time
from typing import Callable, Optional, Dict, Any

from core.presets import PRESETS
from core.audio_processor import build_audio_filter_graph
from core.video_processor import build_video_filter_graph
from core.metadata_cleaner import get_clean_metadata_args, probe_video
from core.stem_separator import isolate_dialogue_and_swap_bgm
from core.split_canvas import build_split_screen_filter, CANVAS_FILE

class VideoTransformer:
    def __init__(self, ffmpeg_bin: str = "ffmpeg"):
        self.ffmpeg_bin = ffmpeg_bin

    def process(
        self,
        input_path: str,
        output_path: str,
        preset_id: str = "stealth_deep",
        mode: str = "turbo",
        custom_overrides: Optional[dict] = None,
        progress_callback: Optional[Callable[[float, str], None]] = None
    ) -> Dict[str, Any]:
        if not os.path.exists(input_path):
            raise FileNotFoundError(f"Input video not found: {input_path}")
            
        start_time = time.time()
        
        # 1. Probe input video
        if progress_callback:
            progress_callback(5.0, "Analyzing media streams and digital footprint...")
            
        info = probe_video(input_path)
        duration = info.get("duration", 0.0)
        has_audio = info.get("has_audio", False)
        
        # 2. Resolve Preset & Overrides
        preset = PRESETS.get(preset_id, PRESETS["stealth_deep"]).copy()
        video_config = preset["video"].copy()
        audio_config = preset["audio"].copy()
        
        ai_options = {}
        if custom_overrides:
            if "video" in custom_overrides:
                video_config.update(custom_overrides["video"])
            if "audio" in custom_overrides:
                audio_config.update(custom_overrides["audio"])
            if "ai_options" in custom_overrides:
                ai_options = custom_overrides["ai_options"]
                
        is_ai_deep = (mode == "ai_deep")
        use_vocal_swap = ai_options.get("vocal_swap", True) if is_ai_deep else False
        use_split_screen = ai_options.get("split_screen", False) if is_ai_deep else False
        bgm_type = ai_options.get("bgm_type", "lofi_chill")
        
        # Temp workspace for intermediate assets
        job_temp_dir = os.path.join(os.path.dirname(output_path), f"tmp_{os.path.basename(output_path)}")
        os.makedirs(job_temp_dir, exist_ok=True)
        
        clean_audio_file = None
        
        # 3. AI Stem Separation (If enabled in AI Deep Mode)
        if is_ai_deep and use_vocal_swap and has_audio:
            if progress_callback:
                progress_callback(15.0, "AI Stem Separation: Isolating dialogue and muting copyrighted score...")
            clean_audio_file = os.path.join(job_temp_dir, "clean_mix.aac")
            isolate_dialogue_and_swap_bgm(
                input_video=input_path,
                output_audio_path=clean_audio_file,
                temp_dir=job_temp_dir,
                bgm_type=bgm_type,
                progress_callback=progress_callback
            )
            
        # 4. Construct FFmpeg Command (Inputs MUST come before outputs)
        if progress_callback:
            progress_callback(50.0, "Synthesizing multi-band visual & acoustic filtergraph...")
            
        video_filters = build_video_filter_graph(video_config)
        
        cmd = [self.ffmpeg_bin, "-y"]
        
        # Primary Input 0
        cmd.extend(["-i", input_path])
        current_input_count = 1
        
        # Secondary Input (for split-screen)
        split_input_idx = None
        if is_ai_deep and use_split_screen and os.path.exists(CANVAS_FILE):
            cmd.extend(["-stream_loop", "-1", "-i", CANVAS_FILE])
            split_input_idx = current_input_count
            current_input_count += 1
            
        # Tertiary Input (for clean mixed audio)
        audio_input_idx = None
        if is_ai_deep and clean_audio_file and os.path.exists(clean_audio_file):
            cmd.extend(["-i", clean_audio_file])
            audio_input_idx = current_input_count
            current_input_count += 1
            
        # Video Filters & Mapping
        if is_ai_deep and use_split_screen and split_input_idx is not None:
            split_vf = build_split_screen_filter(video_filters)
            cmd.extend(["-filter_complex", split_vf, "-map", "[outv]"])
        else:
            cmd.extend(["-vf", video_filters, "-map", "0:v:0"])
            
        # Video encoding parameters
        cmd.extend([
            "-c:v", "libx264",
            "-preset", "veryfast",
            "-crf", "20",
            "-pix_fmt", "yuv420p"
        ])
        
        # Audio mapping & filters
        if audio_input_idx is not None:
            cmd.extend([
                "-map", f"{audio_input_idx}:a:0",
                "-c:a", "aac",
                "-b:a", "192k"
            ])
        elif has_audio:
            audio_filters = build_audio_filter_graph(audio_config)
            cmd.extend([
                "-af", audio_filters,
                "-map", "0:a:0",
                "-c:a", "aac",
                "-b:a", "192k",
                "-ar", "44100"
            ])
        else:
            cmd.append("-an")
            
        if duration > 0:
            cmd.extend(["-t", str(duration)])
            
        # Metadata stripping and web faststart
        cmd.extend(get_clean_metadata_args())
        cmd.extend([
            "-movflags", "+faststart",
            "-progress", "pipe:1"
        ])
        cmd.append(output_path)
        
        # 5. Execute Pipeline with Live Progress Parsing
        if progress_callback:
            progress_callback(60.0, "Rendering transformed video stream...")
            
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1
        )
        
        out_time_ms_pattern = re.compile(r"out_time_ms=(\d+)")
        
        while True:
            line = process.stdout.readline()
            if not line and process.poll() is not None:
                break
            line = line.strip()
            match = out_time_ms_pattern.search(line)
            if match and duration > 0:
                current_ms = int(match.group(1))
                current_sec = current_ms / 1_000_000.0
                pct = 60.0 + (min(current_sec / duration, 1.0) * 35.0)
                if progress_callback:
                    progress_callback(min(pct, 96.0), f"Transforming frames ({int(pct)}%)...")
                    
        stderr = process.stderr.read()
        retcode = process.poll()
        
        # Clean up intermediate temporary files
        try:
            import shutil
            shutil.rmtree(job_temp_dir, ignore_errors=True)
        except Exception:
            pass
            
        if retcode != 0:
            raise RuntimeError(f"FFmpeg pipeline error (code {retcode}): {stderr[-500:]}")
            
        # 6. Verification Probe
        if progress_callback:
            progress_callback(98.0, "Validating container purity & verifying playback...")
            
        out_info = probe_video(output_path)
        elapsed = round(time.time() - start_time, 2)
        
        if progress_callback:
            progress_callback(100.0, f"Transformation complete in {elapsed}s! Ready for download.")
            
        return {
            "success": True,
            "mode": mode,
            "preset": preset_id,
            "elapsed_seconds": elapsed,
            "original": info,
            "transformed": out_info,
            "output_size_bytes": os.path.getsize(output_path) if os.path.exists(output_path) else 0
        }
