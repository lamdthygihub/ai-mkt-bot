"""Tạo bản nháp: AI viết bài + ảnh -> lưu ảnh vào repo -> ghi lên Google Sheet."""
import os
import uuid
from pathlib import Path

import gemini
import image_card
import sheet
import youtube

ROOT = Path(__file__).parent
DRAFT_DIR = ROOT / "drafts"
PROMPT_FILE = ROOT / "prompt.md"
IDEAS_PROMPT_FILE = ROOT / "prompt_ideas.md"
# card = thẻ nội dung vẽ bằng Pillow (miễn phí) | ai = Gemini vẽ ảnh nền (tốn phí nhỏ, lỗi thì tự quay về card)
IMAGE_MODE = (os.environ.get("IMAGE_MODE") or "card").lower()
OVERLAY_ON_THUMBNAIL = (os.environ.get("OVERLAY_ON_THUMBNAIL") or "false").lower() == "true"


def raw_url(rel_path):
    repo = os.environ.get("GITHUB_REPOSITORY", "")
    branch = os.environ.get("GITHUB_REF_NAME") or "main"
    return f"https://raw.githubusercontent.com/{repo}/{branch}/{rel_path}"


def local_path_for(url):
    """Nếu url là ảnh trong chính repo này -> file trên máy chạy."""
    prefix = raw_url("")
    if url.startswith(prefix):
        p = ROOT / url[len(prefix):]
        if p.is_file():
            return p
    return None


def _save(image_bytes, key):
    DRAFT_DIR.mkdir(exist_ok=True)
    name = f"{sheet.now():%Y%m%d-%H%M}-{key}-{uuid.uuid4().hex[:6]}.jpg"
    (DRAFT_DIR / name).write_bytes(image_bytes)
    return raw_url(f"drafts/{name}")


def generate(request_text, user_image=None):
    """Viết bài + làm ảnh. Trả về dict: source, text, image (bytes|None), notes, key."""
    notes = []
    video_id, _ = youtube.find_video(request_text)
    if video_id:
        v = youtube.video_info(video_id)
        extra = youtube.ID_RE.sub("", request_text).replace("https://", "").replace("www.", "").strip()
        source = f"YouTube: {v['title'] or video_id}"
        info = (f"LOẠI BÀI: giới thiệu/bình luận video YouTube\nLink video (đặt cuối bài): {v['url']}\n"
                f"Tiêu đề: {v['title']}\nKênh: {v['channel']}\nTags: {', '.join(v['tags'])}\n"
                f"Mô tả video:\n{v['description']}")
        if extra:
            info += f"\n\nYêu cầu thêm: {extra}"
    else:
        source = request_text[:200]
        info = f"CHỦ ĐỀ BÀI VIẾT: {request_text}"

    result = gemini.write_post(PROMPT_FILE.read_text(encoding="utf-8"), info)
    text = result["post"].strip()
    title, points = result.get("image_title", ""), result.get("card_points") or []

    image = None
    if user_image:
        image = image_card.watermark(user_image)
    elif video_id and (thumb := youtube.thumbnail(video_id)):
        image = image_card.add_title(thumb, title) if OVERLAY_ON_THUMBNAIL else image_card.watermark(thumb)
    elif IMAGE_MODE == "ai":
        try:
            raw = gemini.make_image(result["image_prompt"] + ". No text, no letters, no watermark.")
            image = image_card.add_title(raw, title)
        except Exception as e:
            notes.append(f"Ảnh AI lỗi, dùng thẻ nội dung thay thế ({e})")
    if image is None:
        image = image_card.make_card(title or source, points)
    return {"source": source, "text": text, "image": image, "notes": notes, "key": video_id or "post"}


def create(request_text, user_image=None):
    """Tạo bản nháp mới (dòng mới trên Sheet)."""
    d = generate(request_text, user_image)
    urls = [_save(d["image"], d["key"])] if d["image"] else []
    d["id"], d["row"] = sheet.add_draft(d["source"], d["text"], urls, note="; ".join(d["notes"]))
    return d


def write_idea(item):
    """Viết bài cho một dòng ý tưởng có sẵn (item từ sheet.all_rows())."""
    sheet.set_status(item["row"], sheet.WORKING)
    try:
        d = generate(item["source"])
    except Exception as e:
        sheet.set_status(item["row"], sheet.ERROR, note=f"Viết bài lỗi: {e}")
        raise
    urls = [_save(d["image"], d["key"])] if d["image"] else []
    sheet.fill_draft(item["row"], d["text"], urls, note="; ".join(d["notes"]))
    d["id"], d["row"] = item["id"], item["row"]
    return d


def suggest(focus="", n=7):
    """AI gợi ý n chủ đề -> thêm vào Sheet trạng thái 'Ý tưởng'."""
    use_search = (os.environ.get("IDEAS_USE_SEARCH") or "true").lower() == "true"
    ideas = gemini.suggest_topics(IDEAS_PROMPT_FILE.read_text(encoding="utf-8"),
                                  sheet.recent_topics(), focus=focus, n=n, use_search=use_search)
    return sheet.add_ideas(ideas)
