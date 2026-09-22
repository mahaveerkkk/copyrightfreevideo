"""
Master Video Transformation Engine.
Supports Dual-Engine Execution:
1. ⚡ Turbo DSP Mode (4-8s fast filtergraph)
2. 🧠 AI Deep Studio Mode (Vocal Isolation, BGM Swap, and 9:16 Split-Screen Canvas)
"""

import os
import re
import subprocess
import threading
import time
from typing import Callable, Optional, Dict, Any

from core.presets import PRESETS
from core.audio_processor import build_audio_filter_graph
from core.video_processor import build_video_filter_graph
from core.metadata_cleaner import get_clean_metadata_args, probe_video
from core.stem_separator import isolate_dialogue_and_swap_bgm
from core.split_canvas import build_split_screen_filter, CANVAS_FILE

ACTIVE_PROCESSES: Dict[str, subprocess.Popen] = {}

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
        progress_callback: Optional[Callable[[float, str], None]] = None,
        job_id: Optional[str] = None
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
        
        # Procedural seed based on job/timestamp to guarantee zero pattern repetition
        seed = int(time.time() * 1000) % 100000
        
        clean_audio_file = None
        
        # 3. AI Stem Separation / Clean Dialogue Isolation
        # Supports both AI Deep mode and Turbo mode with vocal isolation toggle
        isolate_dialogue = ai_options.get("vocal_swap", False) or video_config.get("isolate_dialogue", False)
        
        if isolate_dialogue and has_audio:
            if progress_callback:
                progress_callback(15.0, "Isolating dialogue & muting copyrighted score...")
            clean_audio_file = os.path.join(job_temp_dir, "clean_mix.aac")
            isolate_dialogue_and_swap_bgm(
                input_video=input_path,
                output_audio_path=clean_audio_file,
                temp_dir=job_temp_dir,
                bgm_type=bgm_type,
                duration_sec=duration,
                seed=seed,
                progress_callback=progress_callback
            )
            
        # 4. Construct FFmpeg Command (Inputs MUST come before outputs)
        if progress_callback:
            progress_callback(50.0, "Synthesizing dynamic 5-style motion & acoustic shield...")
            
        video_filters = build_video_filter_graph(video_config, seed=seed)
        
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
            
        # Clean Dialogue / Mixed audio input
        audio_input_idx = None
        if clean_audio_file and os.path.exists(clean_audio_file):
            cmd.extend(["-i", clean_audio_file])
            audio_input_idx = current_input_count
            current_input_count += 1
            
        # Video Filters & Mapping
        if is_ai_deep and use_split_screen and split_input_idx is not None:
            split_vf = build_split_screen_filter(video_filters)
            cmd.extend(["-filter_complex", split_vf, "-map", "[outv]"])
        else:
            cmd.extend(["-vf", video_filters, "-map", "0:v:0"])
            
        # Video encoding parameters — optimized for 1GB RAM & 10-30 min movie streams
        cmd.extend([
            "-c:v", "libx264",
            "-preset", "veryfast",
            "-crf", "20",
            "-pix_fmt", "yuv420p",
            "-threads", "2",
            "-bufsize", "2000k"
        ])
        
        # Audio mapping & filters
        if audio_input_idx is not None:
            # Clean dialogue + BGM track: align PTS with master video & smart cuts
            audio_track_filters = ["aresample=async=1000:min_hard_comp=0.100000:first_pts=0"]
            if video_config.get("smart_cuts", True):
                audio_track_filters.insert(0, "aselect='not(between(mod(t\\,5.5)\\,5.35\\,5.50))',asetpts=N/SR/TB")
            cmd.extend([
                "-map", f"{audio_input_idx}:a:0",
                "-af", ",".join(audio_track_filters),
                "-c:a", "aac",
                "-b:a", "192k",
                "-ar", "44100"
            ])
        elif has_audio:
            audio_filters = build_audio_filter_graph(audio_config)
            # Guarantee audio packets are hard-locked to video frame clock
            if "aresample" not in audio_filters:
                audio_filters += ",aresample=async=1000:min_hard_comp=0.100000:first_pts=0"
            cmd.extend([
                "-af", audio_filters,
                "-map", "0:a:0?",
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
        if job_id:
            ACTIVE_PROCESSES[job_id] = process
        
        try:
            # Drain stderr concurrently in background thread to prevent OS pipe deadlock
            stderr_buffer = []
            def _drain_stderr():
                try:
                    for err_line in process.stderr:
                        stderr_buffer.append(err_line)
                        if len(stderr_buffer) > 200:
                            stderr_buffer.pop(0)
                except Exception:
                    pass

            stderr_thread = threading.Thread(target=_drain_stderr, daemon=True)
            stderr_thread.start()

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
                        
            stderr_thread.join(timeout=2.0)
            retcode = process.poll()
            stderr_text = "".join(stderr_buffer)
        finally:
            if job_id and job_id in ACTIVE_PROCESSES:
                ACTIVE_PROCESSES.pop(job_id, None)
        
        # Clean up intermediate temporary files
        try:
            import shutil
            shutil.rmtree(job_temp_dir, ignore_errors=True)
        except Exception:
            pass
            
        if retcode != 0:
            raise RuntimeError(f"FFmpeg pipeline error (code {retcode}): {stderr_text[-500:]}")
            
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
