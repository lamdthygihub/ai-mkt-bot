"""Đăng bài lên Facebook Fanpage qua Graph API."""
import json
import os
import re

import requests

GRAPH_VERSION = os.environ.get("GRAPH_VERSION", "v23.0")
GRAPH = f"https://graph.facebook.com/{GRAPH_VERSION}"
URL_RE = re.compile(r"https?://\S+")


class FBError(Exception):
    pass


def _cfg():
    page_id = os.environ.get("FB_PAGE_ID", "").strip()
    token = os.environ.get("FB_PAGE_TOKEN", "").strip()
    if not page_id or not token:
        raise FBError("Thiếu secret FB_PAGE_ID hoặc FB_PAGE_TOKEN")
    return page_id, token


def _call(path, data=None, files=None):
    page_id, token = _cfg()
    data = dict(data or {})
    data["access_token"] = token
    r = requests.post(f"{GRAPH}/{path.format(page=page_id)}", data=data, files=files, timeout=120)
    try:
        body = r.json()
    except ValueError:
        raise FBError(f"HTTP {r.status_code}: {r.text[:300]}")
    if "error" in body:
        err = body["error"]
        raise FBError(f"{err.get('message')} (code {err.get('code')})")
    return body


def _upload_photo(image, caption=None, published=True):
    """image: bytes (nội dung ảnh) hoặc str (URL công khai)."""
    data = {"published": "true" if published else "false"}
    if caption:
        data["caption"] = caption
    if isinstance(image, (bytes, bytearray)):
        return _call("{page}/photos", data, files={"source": ("image.jpg", image)})
    return _call("{page}/photos", {**data, "url": image})


def post_text(message):
    data = {"message": message}
    m = URL_RE.search(message)
    if m:  # có link (vd link YouTube) -> để Facebook tạo khung xem trước
        data["link"] = m.group(0)
    return _call("{page}/feed", data)["id"]


def post_photos(message, images):
    """Đăng 1 hoặc nhiều ảnh kèm caption. Trả về post_id."""
    if not images:
        return post_text(message)
    if len(images) == 1:
        res = _upload_photo(images[0], caption=message)
        return res.get("post_id") or res["id"]
    ids = [_upload_photo(img, published=False)["id"] for img in images]
    data = {"attached_media": json.dumps([{"media_fbid": i} for i in ids])}
    if message:
        data["message"] = message
    return _call("{page}/feed", data)["id"]


def post_link(post_id):
    return f"https://www.facebook.com/{post_id}"
