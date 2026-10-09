"""
Autonomous YouTube Channel RSS Watcher.
Monitors target podcast/interview channels for new uploads without requiring YouTube API quota.
"""

from typing import List, Dict, Any
import feedparser

TARGET_CHANNELS = [
    {
        "name": "Raj Shamani",
        "category": "Mindset & Business",
        "channel_id": "UCn_2XpPzUqA4wPZ8R1X6dTw",
        "avatar": "https://images.unsplash.com/photo-1534528741775-53994a69daeb?w=100&q=80"
    },
    {
        "name": "The Ranveer Show (BeerBiceps)",
        "category": "Spirituality & Interviews",
        "channel_id": "UCnz-ZXXER4jOvuED5trXfEA",
        "avatar": "https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?w=100&q=80"
    },
    {
        "name": "Samay Raina",
        "category": "Comedy & Roasts",
        "channel_id": "UCAov2BBv1ZJavFTHP_4jzMw",
        "avatar": "https://images.unsplash.com/photo-1500648767791-00dcc994a43e?w=100&q=80"
    },
    {
        "name": "Shark Tank India",
        "category": "Business & Startups",
        "channel_id": "UC6z8Q_e7Lw2n3j9eU_P06lg",
        "avatar": "https://images.unsplash.com/photo-1556761175-5973dc0f32e7?w=100&q=80"
    },
    {
        "name": "Prakhar ke Pravachan",
        "category": "Dark Psychology & Philosophy",
        "channel_id": "UCG1n_QzF1t8QkXgU4X7yqOw",
        "avatar": "https://images.unsplash.com/photo-1472099645785-5658abf4ff4e?w=100&q=80"
    }
]

def fetch_channel_recent_videos(channel_id: str, limit: int = 5) -> List[Dict[str, Any]]:
    """
    Pulls recent videos from a channel's public RSS feed.
    Zero API keys or quota required.
    """
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

def get_watchlist_feed() -> List[Dict[str, Any]]:
    """Fetches the latest videos across all monitored channels."""
    watchlist_feed = []
    for ch in TARGET_CHANNELS:
        try:
            recent = fetch_channel_recent_videos(ch["channel_id"], limit=3)
            watchlist_feed.append({
                "channel": ch["name"],
                "category": ch["category"],
                "channel_id": ch["channel_id"],
                "avatar": ch["avatar"],
                "recent_videos": recent
            })
        except Exception:
            pass
    return watchlist_feed
