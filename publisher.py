"""Xử lý các dòng 'Duyệt' trên Google Sheet.

PUBLISH_MODE=telegram (mặc định, cho Facebook CÁ NHÂN): gửi ảnh + nội dung sẵn sàng qua Telegram
    để bạn lưu ảnh, copy chữ và tự đăng.
PUBLISH_MODE=page: tự đăng lên Fanpage qua Graph API.
"""
import os
import re

import requests

import drafts
import sheet
import tele

MODE = (os.environ.get("PUBLISH_MODE") or "telegram").lower()
DRIVE_RE = re.compile(r"drive\.google\.com/(?:file/d/|open\?id=|uc\?.*id=)([\w-]+)")


def load_image(url):
    """URL ảnh -> bytes (ảnh trong repo, link Google Drive, link ảnh thường)."""
    local = drafts.local_path_for(url)
    if local:
        return local.read_bytes()
    m = DRIVE_RE.search(url)
    if m:
        url = f"https://drive.google.com/uc?export=download&id={m.group(1)}"
    r = requests.get(url, timeout=60, headers={"User-Agent": "Mozilla/5.0"})
    r.raise_for_status()
    if not r.headers.get("content-type", "").startswith("image/"):
        raise ValueError(f"Link không phải ảnh (hoặc chưa chia sẻ công khai): {url[:80]}")
    return r.content


def _send_to_telegram(item, images):
    chat = tele.owner_chat()
    if not chat:
        raise RuntimeError("Thiếu TELEGRAM_ALLOWED_CHAT_IDS để gửi bài")
    tele.send_images(chat, images)
    tele.send_copyable(chat, f"📣 Bài #{item['id']} sẵn sàng đăng Facebook cá nhân\n"
                             "1) Giữ vào ảnh → Lưu  2) Bấm khung chữ bên dưới để copy  3) Dán lên Facebook", item["text"])


def publish_approved():
    """Trả về số bài đã xử lý."""
    count = 0
    for item in sheet.approved_rows():
        row = item["row"]
        sheet.set_status(row, sheet.WORKING)  # khoá dòng, tránh xử lý trùng
        try:
            if not item["text"] and not item["images"]:
                raise ValueError("Dòng trống nội dung và ảnh")
            images = [load_image(u) for u in item["images"]]
            if MODE == "page":
                import fb
                post_id = fb.post_photos(item["text"], images) if images else fb.post_text(item["text"])
                link = fb.post_link(post_id)
                sheet.set_status(row, sheet.POSTED, link=link, note="")
                tele.notify(f"✅ Đã đăng bài #{item['id']} lên Fanpage\n{link}")
            else:
                _send_to_telegram(item, images)
                sheet.set_status(row, sheet.SENT, note=f"Đã gửi Telegram {sheet.now():%d/%m %H:%M}. "
                                                       "Đăng xong: dán link bài vào cột I, chọn 'Đã đăng'")
        except Exception as e:
            print(f"Dòng {row} lỗi:", e)
            sheet.set_status(row, sheet.ERROR, note=f"{sheet.now():%d/%m %H:%M} {e}")
            tele.notify(f"❌ Bài #{item['id']} lỗi: {e}\n{sheet.sheet_url()}")
            continue
        count += 1
    return count
