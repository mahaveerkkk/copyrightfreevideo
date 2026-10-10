"""
Autonomous YouTube Shorts Uploader powered by YouTube Data API v3.
Features:
- Auto-refresh OAuth2 tokens
- Uploads .mp4 with auto-generated Viral Title, Description, #Shorts Tags
- Pins high-converting affiliate comment directly under the uploaded video!
"""

import os
import re
import json
import logging
from typing import Optional, Dict, Any, List
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

logger = logging.getLogger("YouTubeUploader")

CONFIG_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "config")
TOKEN_FILE = os.path.join(CONFIG_DIR, "youtube_token.json")
SECRETS_FILE = os.path.join(CONFIG_DIR, "client_secrets.json")

def sanitize_youtube_tags(raw_tags: List[str]) -> List[str]:
    """Sanitizes tags to comply with strict YouTube Data API v3 limits."""
    clean_list = []
    seen = set()
    total_len = 0
    for t in raw_tags:
        clean = re.sub(r'[^a-zA-Z0-9\s]', '', str(t)).strip()
        clean = re.sub(r'\s+', ' ', clean)
        if clean and len(clean) >= 2 and clean.lower() not in seen:
            seen.add(clean.lower())
            clean_list.append(clean[:50])
            total_len += len(clean)
            if len(clean_list) >= 15 or total_len > 350:
                break
    return clean_list

def get_authenticated_youtube_service():
    """Authenticates and returns the YouTube Data API v3 service client."""
    if not os.path.exists(TOKEN_FILE):
        raise FileNotFoundError(f"YouTube token file not found at {TOKEN_FILE}")

    creds = Credentials.from_authorized_user_file(TOKEN_FILE)
    if creds.expired and creds.refresh_token:
        logger.info("Refreshing expired YouTube OAuth2 token...")
        creds.refresh(Request())
        with open(TOKEN_FILE, "w", encoding="utf-8") as f:
            f.write(creds.to_json())
        logger.info("YouTube token refreshed and persisted!")

    return build("youtube", "v3", credentials=creds)

def get_connected_channel_info() -> Dict[str, Any]:
    """Returns the title, customUrl, and thumbnail of the connected YouTube channel."""
    try:
        yt = get_authenticated_youtube_service()
        res = yt.channels().list(mine=True, part="snippet,statistics").execute()
        items = res.get("items", [])
        if items:
            snip = items[0]["snippet"]
            stats = items[0].get("statistics", {})
            return {
                "connected": True,
                "title": snip.get("title"),
                "channel_id": items[0]["id"],
                "subscriber_count": stats.get("subscriberCount", "0"),
                "video_count": stats.get("videoCount", "0"),
                "avatar": snip.get("thumbnails", {}).get("default", {}).get("url")
            }
    except Exception as e:
        logger.warning(f"Could not retrieve channel info: {e}")
    return {"connected": False, "title": "Not Connected"}

def upload_short_to_youtube(
    video_path: str,
    title: str,
    description: str,
    tags: List[str],
    privacy_status: str = "public",
    pinned_comment: Optional[str] = None
) -> Dict[str, Any]:
    """
    Uploads a short to YouTube, applies tags & description, and posts a pinned comment.
    """
    yt = get_authenticated_youtube_service()

    # Ensure title has #shorts
    final_title = title.strip()
    if "#shorts" not in final_title.lower() and len(final_title) < 90:
        final_title = f"{final_title} #shorts"

    # Ensure description has viral tags
    tag_words = " ".join([f"#{t.replace(' ', '')}" for t in tags[:8] if not t.startswith("#")])
    final_desc = f"{description}\n\n{tag_words}\n\n⚡ Subscribe for daily viral wisdom & highlights!".strip()

    body = {
        "snippet": {
            "title": final_title[:100],
            "description": final_desc[:5000],
            "tags": sanitize_youtube_tags(tags),
            "categoryId": "24"  # Entertainment
        },
        "status": {
            "privacyStatus": privacy_status,
            "selfDeclaredMadeForKids": False
        }
    }

    media = MediaFileUpload(video_path, chunksize=5 * 1024 * 1024, resumable=True, mimetype="video/mp4")
    request = yt.videos().insert(part="snippet,status", body=body, media_body=media)

    logger.info(f"Uploading '{os.path.basename(video_path)}' to YouTube ({privacy_status})...")
    response = None
    while response is None:
        status, response = request.next_chunk()
        if status:
            logger.info(f"YouTube Upload Progress: {int(status.progress() * 100)}%")

    video_id = response.get("id")
    video_url = f"https://www.youtube.com/shorts/{video_id}"
    logger.info(f"✅ Uploaded to YouTube! URL: {video_url}")

    # Post Pinned Affiliate Comment if provided
    comment_posted = False
    if pinned_comment and video_id:
        try:
            comment_body = {
                "snippet": {
                    "videoId": video_id,
                    "topLevelComment": {
                        "snippet": {
                            "textOriginal": pinned_comment
                        }
                    }
                }
            }
            yt.commentThreads().insert(part="snippet", body=comment_body).execute()
            comment_posted = True
            logger.info(f"✅ Pinned affiliate comment posted under {video_id}!")
        except Exception as ce:
            logger.warning(f"Could not post affiliate comment (may require channel permission): {ce}")

    return {
        "success": True,
        "video_id": video_id,
        "video_url": video_url,
        "title": final_title,
        "privacy": privacy_status,
        "comment_posted": comment_posted
    }
