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

    def _calculate_next_india_publish_slot(self) -> Dict[str, Any]:
        """
        Calculates the best India (IST) peak-hour broadcast slot with random creator jitter.
        India Peak Slots:
          - Morning Commute: 09:00 AM - 10:30 AM IST
          - Afternoon Break: 01:30 PM - 03:00 PM IST
          - Evening Prime Time: 07:30 PM - 09:30 PM IST
        Adds an anti-bot random jitter so upload pattern is never mechanical.
        """
        import datetime
        import random

        now_utc = datetime.datetime.now(datetime.timezone.utc)
        ist_offset = datetime.timedelta(hours=5, minutes=30)
        now_ist = now_utc + ist_offset

        # 3 Golden Daily Slots in IST (Hour, Minute)
        golden_slots = [
            (9, 30),   # 09:30 AM IST
            (14, 0),   # 02:00 PM IST
            (19, 45)   # 07:45 PM IST
        ]

        target_slot_utc = None
        for hour, minute in golden_slots:
            jitter_min = random.randint(-20, 35)
            candidate_ist = now_ist.replace(hour=hour, minute=0, second=0, microsecond=0) + datetime.timedelta(minutes=minute + jitter_min)
            candidate_utc = candidate_ist - ist_offset
            # Slot must be at least 30 mins in future so YouTube HD processing finishes cleanly
            if (candidate_utc - now_utc).total_seconds() >= 1800:
                target_slot_utc = candidate_utc
                break

        if not target_slot_utc:
            # All today slots passed; schedule for tomorrow morning
            jitter_min = random.randint(-15, 30)
            tomorrow_ist = (now_ist + datetime.timedelta(days=1)).replace(hour=golden_slots[0][0], minute=golden_slots[0][1] + jitter_min, second=0, microsecond=0)
            target_slot_utc = tomorrow_ist - ist_offset

        delay_minutes = int((target_slot_utc - now_utc).total_seconds() // 60)
        if delay_minutes < 35:
            delay_minutes = random.randint(35, 120)
            target_slot_utc = now_utc + datetime.timedelta(minutes=delay_minutes)

        iso_str = target_slot_utc.strftime("%Y-%m-%dT%H:%M:%S.000Z")
        ist_display = (target_slot_utc + ist_offset).strftime("%I:%M %p IST (%d %b)")
        return {
            "publish_at_iso": iso_str,
            "delay_minutes": delay_minutes,
            "ist_display": ist_display
        }

    def _run_single_cycle(self):
        import datetime
        self.state["last_run_timestamp"] = int(time.time())
        self._save_state()

        # Daily Quota Guard: Exactly 3 Shorts Per Day (IST)
        ist_now = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=5, minutes=30)
        today_ist_str = ist_now.strftime("%Y-%m-%d")

        today_shorts_count = sum(
            1 for s in self.state.get("generated_shorts_history", [])
            if datetime.datetime.fromtimestamp(s.get("generated_at", 0), datetime.timezone.utc).astimezone(datetime.timezone(datetime.timedelta(hours=5, minutes=30))).strftime("%Y-%m-%d") == today_ist_str
        )

        if today_shorts_count >= 3:
            logger.info(f"Daily quota reached ({today_shorts_count}/3 shorts today for IST {today_ist_str}). Waiting for tomorrow.")
            return

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

                # Calculate smart organic India peak hour slot with anti-bot jitter
                schedule_slot = self._calculate_next_india_publish_slot()

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
                    "scheduled_ist": schedule_slot["ist_display"],
                    "scheduled_iso": schedule_slot["publish_at_iso"],
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
                        privacy_status="private",
                        pinned_comment=best_hook.get("pinned_affiliate_comment"),
                        publish_at_iso=schedule_slot["publish_at_iso"]
                    )
                    seo_pack["youtube_url"] = upload_res.get("video_url")
                    seo_pack["youtube_id"] = upload_res.get("video_id")
                    logger.info(f"🚀 Auto-Pilot scheduled for {schedule_slot['ist_display']}: {upload_res.get('video_url')}")
                except Exception as ue:
                    logger.warning(f"YouTube auto-upload failed or skipped: {ue}")
                    seo_pack["youtube_upload_error"] = str(ue)

                with open(seo_filepath, "w", encoding="utf-8") as f:
                    json.dump(seo_pack, f, indent=2)

                self.state["processed_video_ids"].append(vid_id)
                self.state["generated_shorts_history"].append(seo_pack)
                self._save_state()

                logger.info(f"✅ Successfully auto-generated short: {short_filename}")
                # Successfully produced a short for this cycle; yield until next schedule interval
                break

            except Exception as e:
                logger.error(f"Failed to auto-process video {vid_id}: {e}")
                self.state["processed_video_ids"].append(vid_id)
                self._save_state()

            time.sleep(15)

auto_pilot_engine = AutoPilotWorker()
