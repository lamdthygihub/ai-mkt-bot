"""Lấy thông tin + thumbnail video YouTube (không tốn token AI)."""
import os
import re

import requests

ID_RE = re.compile(r"(?:youtu\.be/|youtube\.com/(?:watch\?(?:.*&)?v=|shorts/|live/|embed/))([\w-]{11})")


def find_video(text):
    """Trả về (video_id, url) nếu text có link YouTube."""
    m = ID_RE.search(text or "")
    return (m.group(1), m.group(0)) if m else (None, None)


def video_info(video_id):
    url = f"https://www.youtube.com/watch?v={video_id}"
    info = {"id": video_id, "url": f"https://youtu.be/{video_id}", "title": "", "description": "", "tags": [], "channel": ""}
    key = os.environ.get("YOUTUBE_API_KEY", "").strip()
    if key:  # có API key -> lấy được cả mô tả + tags
        r = requests.get("https://www.googleapis.com/youtube/v3/videos",
                         params={"part": "snippet", "id": video_id, "key": key}, timeout=30).json()
        items = r.get("items") or []
        if items:
            s = items[0]["snippet"]
            info.update(title=s.get("title", ""), description=s.get("description", "")[:2000],
                        tags=s.get("tags", [])[:15], channel=s.get("channelTitle", ""))
    if not info["title"]:
        r = requests.get("https://www.youtube.com/oembed", params={"url": url, "format": "json"}, timeout=30)
        if r.ok:
            d = r.json()
            info.update(title=d.get("title", ""), channel=d.get("author_name", ""))
    return info


def thumbnail(video_id):
    for name in ("maxresdefault", "sddefault", "hqdefault"):
        r = requests.get(f"https://i.ytimg.com/vi/{video_id}/{name}.jpg", timeout=30)
        if r.ok and len(r.content) > 5000:  # ảnh "không có" của YouTube rất nhỏ
            return r.content
    return None
