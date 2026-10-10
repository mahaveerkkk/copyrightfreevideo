"""
Autonomous YouTube Channel Watcher & Viral Vault.
Monitors top creators (MrBeast, Raj Shamani, Ranveer, etc.) for both:
1. Latest RSS uploads
2. All-Time Most Popular (10M+ to 100M+ views) legendary viral videos.
"""

import time
from typing import List, Dict, Any, Optional
import feedparser
import yt_dlp

TARGET_CHANNELS = [
    {
        "name": "MrBeast (Viral King ⚡)",
        "category": "World Records & Challenges",
        "channel_id": "UCX6OQ3DkcsbYNE6H8uQQuVA",
        "handle": "MrBeast",
        "avatar": "https://images.unsplash.com/photo-1566492031773-4f4e44671857?w=100&q=80"
    },
    {
        "name": "Raj Shamani",
        "category": "Mindset & Business Secrets",
        "channel_id": "UCn_2XpPzUqA4wPZ8R1X6dTw",
        "handle": "RajShamani",
        "avatar": "https://images.unsplash.com/photo-1534528741775-53994a69daeb?w=100&q=80"
    },
    {
        "name": "The Ranveer Show (BeerBiceps)",
        "category": "Interviews & Mysteries",
        "channel_id": "UCnz-ZXXER4jOvuED5trXfEA",
        "handle": "RanveerAllahbadia",
        "avatar": "https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?w=100&q=80"
    },
    {
        "name": "Samay Raina",
        "category": "Comedy & Roasts",
        "channel_id": "UCAov2BBv1ZJavFTHP_4jzMw",
        "handle": "SamayRainaOfficial",
        "avatar": "https://images.unsplash.com/photo-1500648767791-00dcc994a43e?w=100&q=80"
    },
    {
        "name": "Shark Tank India",
        "category": "Business Pitches & Startups",
        "channel_id": "UC6z8Q_e7Lw2n3j9eU_P06lg",
        "handle": "SonyLIV",
        "avatar": "https://images.unsplash.com/photo-1556761175-5973dc0f32e7?w=100&q=80"
    },
    {
        "name": "Prakhar ke Pravachan",
        "category": "Dark Psychology & Human Mind",
        "channel_id": "UCG1n_QzF1t8QkXgU4X7yqOw",
        "handle": "PrakharkePravachan",
        "avatar": "https://images.unsplash.com/photo-1472099645785-5658abf4ff4e?w=100&q=80"
    }
]

# Simple in-memory cache for fast UI loading
_POPULAR_CACHE = {}
_LAST_CACHE_TIME = {}

def fetch_channel_recent_videos(channel_id: str, limit: int = 4) -> List[Dict[str, Any]]:
    """Pulls recent videos from a channel's public RSS feed without API quota."""
    rss_url = f"https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}"
    feed = feedparser.parse(rss_url)
    videos = []
    
    for entry in feed.entries[:limit]:
        v_id = getattr(entry, "yt_videoid", None)
        if not v_id and "v=" in entry.link:
            v_id = entry.link.split("v=")[1].split("&")[0]
            
        videos.append({
            "title": entry.title,
            "link": entry.link,
            "video_id": v_id,
            "published": getattr(entry, "published", "Recent"),
            "author": getattr(entry, "author", "Channel"),
            "thumbnail": f"https://i.ytimg.com/vi/{v_id}/hqdefault.jpg" if v_id else ""
        })
    return videos

def fetch_channel_popular_videos(handle: str, limit: int = 4) -> List[Dict[str, Any]]:
    """
    Extracts all-time most popular (highest view-count) videos for a channel using yt-dlp flat-playlist.
    Cached for 1 hour for lightning-fast responses.
    """
    now = time.time()
    if handle in _POPULAR_CACHE and (now - _LAST_CACHE_TIME.get(handle, 0)) < 3600:
        return _POPULAR_CACHE[handle]

    url = f"https://www.youtube.com/@{handle}/videos?view=0&sort=p"
    opts = {
        'extract_flat': True,
        'skip_download': True,
        'quiet': True,
        'playlist_items': f"1-{limit}"
    }

    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=False)
            entries = info.get("entries", [])
            videos = []
            for e in entries[:limit]:
                v_id = e.get("id")
                if v_id:
                    videos.append({
                        "title": e.get("title", "Viral Episode"),
                        "link": f"https://www.youtube.com/watch?v={v_id}",
                        "video_id": v_id,
                        "published": "All-Time Viral Hit 🔥",
                        "author": handle,
                        "thumbnail": f"https://i.ytimg.com/vi/{v_id}/hqdefault.jpg"
                    })
            if videos:
                _POPULAR_CACHE[handle] = videos
                _LAST_CACHE_TIME[handle] = now
                return videos
    except Exception:
        pass
        
    return []

def get_watchlist_feed(mode: str = "popular") -> List[Dict[str, Any]]:
    """
    Fetches either All-Time Most Popular (mode='popular') or Recent Uploads (mode='latest').
    """
    watchlist_feed = []
    for ch in TARGET_CHANNELS:
        try:
            if mode == "popular" and ch.get("handle"):
                videos = fetch_channel_popular_videos(ch["handle"], limit=4)
                if not videos:  # Fallback to RSS if flat playlist fails
                    videos = fetch_channel_recent_videos(ch["channel_id"], limit=3)
            else:
                videos = fetch_channel_recent_videos(ch["channel_id"], limit=4)

            watchlist_feed.append({
                "channel": ch["name"],
                "category": ch["category"],
                "channel_id": ch["channel_id"],
                "handle": ch.get("handle", ""),
                "avatar": ch["avatar"],
                "mode": mode,
                "recent_videos": videos
            })
        except Exception:
            pass
    return watchlist_feed
