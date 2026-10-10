"""
Autonomous Auto-Pilot Engine.
Scans target channels (MrBeast, Raj Shamani, etc.) in the background, selects unclipped high-retention videos,
runs Gemini 3.5 AI to pinpoint viral hooks, and auto-renders 9:16 Shorts with Alex Hormozi animated captions.
Saves completed ready-to-upload shorts to `storage/outputs/auto_shorts/` along with `.seo.json` pack.
"""

import os
import json
import time
import uuid
import logging
import threading
from typing import List, Dict, Any, Optional

from api.config import OUTPUT_DIR
from core.channel_watcher import TARGET_CHANNELS, fetch_channel_popular_videos, fetch_channel_recent_videos
from core.gemini_hook_finder import find_gemini_viral_hooks
from core.shorts_generator import generate_viral_short

logger = logging.getLogger("AutoPilotEngine")

AUTO_SHORTS_DIR = os.path.join(OUTPUT_DIR, "auto_shorts")
os.makedirs(AUTO_SHORTS_DIR, exist_ok=True)

STATE_FILE = os.path.join(OUTPUT_DIR, "auto_pilot_state.json")

class AutoPilotWorker:
    def __init__(self):
        self.is_running = False
        self.interval_seconds = 3600  # Check every 1 hour by default
        self.max_daily_shorts = 5
        self.active_thread: Optional[threading.Thread] = None
        self.state = self._load_state()

    def _load_state(self) -> Dict[str, Any]:
        if os.path.exists(STATE_FILE):
            try:
                with open(STATE_FILE, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return {
            "processed_video_ids": [],
            "generated_shorts_history": [],
            "last_run_timestamp": 0,
            "auto_pilot_enabled": False,
            "selected_channels": [c["name"] for c in TARGET_CHANNELS]
        }

    def _save_state(self):
        try:
            with open(STATE_FILE, "w", encoding="utf-8") as f:
                json.dump(self.state, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save auto pilot state: {e}")

    def get_status(self) -> Dict[str, Any]:
        return {
            "is_running": self.is_running,
            "enabled": self.state.get("auto_pilot_enabled", False),
            "last_run": self.state.get("last_run_timestamp", 0),
            "total_processed_source_videos": len(self.state.get("processed_video_ids", [])),
            "total_shorts_generated": len(self.state.get("generated_shorts_history", [])),
            "recent_generated_shorts": self.state.get("generated_shorts_history", [])[-10:],
            "selected_channels": self.state.get("selected_channels", [])
        }

    def start(self, interval_seconds: int = 3600):
        if self.is_running:
            return
        self.interval_seconds = interval_seconds
        self.state["auto_pilot_enabled"] = True
        self._save_state()
        self.is_running = True
        self.active_thread = threading.Thread(target=self._run_loop, daemon=True)
        self.active_thread.start()
        logger.info("Autonomous Auto-Pilot Worker started.")

    def stop(self):
        self.is_running = False
        self.state["auto_pilot_enabled"] = False
        self._save_state()
        logger.info("Autonomous Auto-Pilot Worker stopped.")

    def _run_loop(self):
        while self.is_running:
            try:
                logger.info("Auto-Pilot cycle starting...")
                self._run_single_cycle()
            except Exception as e:
                logger.error(f"Error during Auto-Pilot cycle: {e}")
            
            # Sleep in increments of 10s so stop() responds immediately
            for _ in range(int(self.interval_seconds // 10)):
                if not self.is_running:
                    break
                time.sleep(10)

    def _run_single_cycle(self):
        self.state["last_run_timestamp"] = int(time.time())
        self._save_state()

        selected_names = self.state.get("selected_channels", [])
        channels_to_scan = [c for c in TARGET_CHANNELS if c["name"] in selected_names or not selected_names]

        for channel in channels_to_scan:
            if not self.is_running:
                break

            logger.info(f"Scanning channel for new clips: {channel['name']}")
            videos = []
            if channel.get("handle"):
                videos = fetch_channel_popular_videos(channel["handle"], limit=5)
            if not videos and channel.get("channel_id"):
                videos = fetch_channel_recent_videos(channel["channel_id"], limit=5)

            target_video = None
            for v in videos:
                vid_id = v.get("video_id") or v.get("id")
                if vid_id and vid_id not in self.state["processed_video_ids"]:
                    target_video = v
                    break

            if not target_video:
                continue

            vid_id = target_video.get("video_id") or target_video.get("id")
            video_url = target_video.get("link") or f"https://www.youtube.com/watch?v={vid_id}"

            logger.info(f"Auto-Pilot selected video: {target_video.get('title')} ({vid_id})")
            
            try:
                hooks = find_gemini_viral_hooks(video_url, max_hooks=1)
                if not hooks:
                    self.state["processed_video_ids"].append(vid_id)
                    self._save_state()
                    continue

                best_hook = hooks[0]
                short_id = str(uuid.uuid4())[:8]
                short_filename = f"Short_{vid_id}_{short_id}.mp4"
                short_filepath = os.path.join(AUTO_SHORTS_DIR, short_filename)
                seo_filepath = os.path.join(AUTO_SHORTS_DIR, f"Short_{vid_id}_{short_id}.seo.json")

                logger.info(f"Auto-Pilot rendering short: {best_hook['title']}")
                generate_viral_short(
                    youtube_url=video_url,
                    start_sec=float(best_hook["start"]),
                    end_sec=float(best_hook["end"]),
                    output_path=short_filepath,
                    style="blurred_stack",
                    burn_captions=True,
                    watermark_text="@ViralClips"
                )

                # 3. Create SEO & Monetization Pack
                seo_pack = {
                    "short_id": short_id,
                    "source_channel": channel["name"],
                    "source_video_title": target_video.get("title"),
                    "source_url": video_url,
                    "short_filename": short_filename,
                    "title": best_hook.get("title"),
                    "hook_line": best_hook.get("hook_line"),
                    "virality_score": best_hook.get("score"),
                    "hashtags": best_hook.get("hashtags"),
                    "pinned_affiliate_comment": best_hook.get("pinned_affiliate_comment"),
                    "generated_at": int(time.time()),
                    "download_url": f"/api/auto-shorts/download/{short_filename}"
                }

                # 4. Direct Autonomous YouTube Upload
                upload_res = None
                try:
                    from core.youtube_uploader import upload_short_to_youtube
                    raw_tags = [t.strip() for t in str(best_hook.get("hashtags", "")).split() if t.strip()]
                    upload_res = upload_short_to_youtube(
                        video_path=short_filepath,
                        title=best_hook.get("title", "Viral Highlight"),
                        description=f"{best_hook.get('hook_line', '')}\n\nClip from: {target_video.get('title')}",
                        tags=raw_tags,
                        privacy_status=self.state.get("youtube_privacy", "public"),
                        pinned_comment=best_hook.get("pinned_affiliate_comment")
                    )
                    seo_pack["youtube_url"] = upload_res.get("video_url")
                    seo_pack["youtube_id"] = upload_res.get("video_id")
                    logger.info(f"🚀 Auto-Pilot published directly to YouTube: {upload_res.get('video_url')}")
                except Exception as ue:
                    logger.warning(f"YouTube auto-upload failed or skipped: {ue}")
                    seo_pack["youtube_upload_error"] = str(ue)

                with open(seo_filepath, "w", encoding="utf-8") as f:
                    json.dump(seo_pack, f, indent=2)

                self.state["processed_video_ids"].append(vid_id)
                self.state["generated_shorts_history"].append(seo_pack)
                self._save_state()

                logger.info(f"✅ Successfully auto-generated short: {short_filename}")

            except Exception as e:
                logger.error(f"Failed to auto-process video {vid_id}: {e}")
                self.state["processed_video_ids"].append(vid_id)
                self._save_state()

            time.sleep(15)

auto_pilot_engine = AutoPilotWorker()
