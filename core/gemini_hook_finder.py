"""
AI Viral Hook & Highlight Finder powered by Google Gemini 1.5 Flash.
Analyzes full YouTube transcripts (Hindi, English, Hinglish) to pinpoint high-retention 30-50s viral moments.
"""

import os
import re
import json
import logging
from typing import List, Dict, Any, Optional
import requests
from urllib.parse import urlparse, parse_qs
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger("GeminiHookFinder")

def extract_youtube_video_id(url: str) -> Optional[str]:
    """Extracts 11-char video ID from various YouTube URL formats."""
    parsed = urlparse(url)
    if "youtu.be" in parsed.netloc:
        return parsed.path.strip("/")
    if "youtube.com" in parsed.netloc:
        if parsed.path == "/watch":
            return parse_qs(parsed.query).get("v", [None])[0]
        elif parsed.path.startswith(("/shorts/", "/embed/", "/v/")):
            return parsed.path.split("/")[2]
    return None

def fetch_youtube_transcript(video_id: str) -> List[Dict[str, Any]]:
    """
    Fetches timestamped transcript segments for a YouTube video.
    Tries Hindi (hi), Hinglish, English (en), and auto-generated transcripts.
    """
    from youtube_transcript_api import YouTubeTranscriptApi
    try:
        api = YouTubeTranscriptApi()
        try:
            raw = api.fetch(video_id, languages=['hi', 'en', 'hi-Latn'])
        except Exception:
            raw = api.fetch(video_id)
            
        results = []
        for item in raw:
            text = getattr(item, 'text', None) or (item.get('text') if isinstance(item, dict) else str(item))
            start = getattr(item, 'start', None) if not isinstance(item, dict) else item.get('start')
            dur = getattr(item, 'duration', None) if not isinstance(item, dict) else item.get('duration')
            results.append({
                "text": text,
                "start": float(start or 0.0),
                "duration": float(dur or 2.0)
            })
        return results
    except Exception as e:
        logger.warning(f"youtube-transcript-api failed for {video_id}: {e}")
        return []

def format_timestamp(seconds: float) -> str:
    m = int(seconds // 60)
    s = int(seconds % 60)
    return f"{m:02d}:{s:02d}"

def call_gemini_api(prompt: str, api_key: str) -> str:
    """Invokes Google Gemini REST endpoint with model fallback."""
    models_to_try = ["gemini-3.5-flash", "gemini-3.5-flash-lite"]
    payload = {
        "contents": [{
            "parts": [{"text": prompt}]
        }],
        "generationConfig": {
            "temperature": 0.3,
            "responseMimeType": "application/json"
        }
    }
    last_err = None
    for model in models_to_try:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
        try:
            resp = requests.post(url, json=payload, timeout=30)
            if resp.status_code == 200:
                data = resp.json()
                candidates = data.get("candidates", [])
                if candidates:
                    return candidates[0]["content"]["parts"][0]["text"]
            else:
                last_err = f"Model {model} error {resp.status_code}: {resp.text}"
        except Exception as e:
            last_err = str(e)
            continue

    raise RuntimeError(f"Gemini API error: {last_err}")

def find_gemini_viral_hooks(youtube_url: str, max_hooks: int = 3, api_key: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Extracts video transcript and uses Gemini 1.5 Flash to score and extract the top viral moments.
    Falls back to algorithmic heuristic if API key is not configured.
    """
    video_id = extract_youtube_video_id(youtube_url)
    if not video_id:
        raise ValueError("Invalid YouTube URL provided.")

    gemini_key = api_key or os.getenv("GEMINI_API_KEY")

    # 1. Fetch transcript
    transcript = fetch_youtube_transcript(video_id)
    
    # If transcript is available and Gemini API key is present: use Gemini LLM
    if transcript and gemini_key:
        try:
            transcript_text = "\n".join([
                f"[{item['start']:.1f}s]: {item['text']}"
                for item in transcript[:2500]
            ])
            
            prompt = f"""You are an elite YouTube Shorts and Instagram Reels growth strategist.
Analyze this video transcript and identify the top {max_hooks} MOST VIRAL, SHOCKING, EMOTIONAL, or HIGH-RETENTION segments.

Rules:
1. Each segment MUST be between 30 and 55 seconds long.
2. The segment MUST start with a compelling verbal hook that stops users from scrolling.
3. The segment MUST deliver a complete insight, story, punchline, or realization.
4. Output strict JSON with key "viral_hooks".

Transcript:
{transcript_text}

Required Output JSON Format:
{{
  "viral_hooks": [
    {{
      "title": "Catchy Viral Title with Emojis (e.g., '90% Log Ye Galti Karte Hain ❌')",
      "start_sec": 120.5,
      "end_sec": 165.0,
      "virality_score": 96,
      "hook_line": "The opening punchline sentence",
      "reason": "Why this moment will blow up on Reels/Shorts",
      "hashtags": "#shorts #viral #trending #motivation #money",
      "pinned_affiliate_comment": "👉 Recommended book & tool mentioned in this video: [Click Link for Free Bonus!]"
    }}
  ]
}}
"""
            raw_json = call_gemini_api(prompt, gemini_key)
            data = json.loads(raw_json)
            hooks_data = data.get("viral_hooks", [])
            
            results = []
            for h in hooks_data[:max_hooks]:
                s = float(h.get("start_sec", 0.0))
                e = float(h.get("end_sec", s + 40.0))
                dur = round(e - s, 1)
                results.append({
                    "start": s,
                    "end": e,
                    "start_str": format_timestamp(s),
                    "end_str": format_timestamp(e),
                    "duration_sec": dur,
                    "title": h.get("title", "Viral Highlight"),
                    "hook_line": h.get("hook_line", ""),
                    "reason": h.get("reason", "High-retention emotional hook detected by Gemini."),
                    "score": int(h.get("virality_score", 92)),
                    "hashtags": h.get("hashtags", "#shorts #viral #trending #podcast"),
                    "pinned_affiliate_comment": h.get("pinned_affiliate_comment", "👉 Best book & tool from this clip: [Check Pinned Link]")
                })
            if results:
                return results
        except Exception as e:
            logger.error(f"Gemini AI hook extraction failed, falling back to heuristics: {e}")

    # Fallback heuristic: use hook keywords or golden-ratio chapters
    from core.hook_finder import find_viral_hooks as fallback_finder
    fallback_hooks = fallback_finder(youtube_url, max_hooks=max_hooks)
    for fh in fallback_hooks:
        if not fh.get("hashtags"):
            fh["hashtags"] = "#shorts #viral #trending #podcast #growth"
        if not fh.get("pinned_affiliate_comment"):
            fh["pinned_affiliate_comment"] = "👉 Recommended tool & resources mentioned in this video: [Click link in description for free access]"
    return fallback_hooks
