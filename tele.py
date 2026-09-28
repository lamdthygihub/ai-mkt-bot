"""Hàm gửi tin Telegram dùng chung."""
import html
import json
import os

import requests

TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
TG = f"https://api.telegram.org/bot{TOKEN}"
TG_FILE = f"https://api.telegram.org/file/bot{TOKEN}"
ALLOWED = {c.strip() for c in os.environ.get("TELEGRAM_ALLOWED_CHAT_IDS", "").split(",") if c.strip()}
NO_PREVIEW = json.dumps({"is_disabled": True})


def tg(method, files=None, **params):
    r = requests.post(f"{TG}/{method}", data=params, files=files, timeout=60)
    body = r.json()
    if not body.get("ok"):
        raise RuntimeError(f"Telegram {method}: {body.get('description')}")
    return body["result"]


def owner_chat():
    return sorted(ALLOWED)[0] if ALLOWED else None


def reply(msg, text):
    try:
        tg("sendMessage", chat_id=msg["chat"]["id"], text=text, link_preview_options=NO_PREVIEW,
           reply_parameters=json.dumps({"message_id": msg["message_id"], "allow_sending_without_reply": True}))
    except Exception as e:  # không để lỗi trả lời làm hỏng cả lượt
        print("Không gửi được tin trả lời:", e)


def notify(text, chat_id=None):
    chat_id = chat_id or owner_chat()
    if TOKEN and chat_id:
        try:
            tg("sendMessage", chat_id=chat_id, text=text, link_preview_options=NO_PREVIEW)
        except Exception as e:
            print("Không gửi được thông báo:", e)


def send_images(chat_id, images, caption=None):
    """images: list[bytes]. 1 ảnh -> sendPhoto, nhiều ảnh -> album."""
    if not images:
        return
    if len(images) == 1:
        params = {"caption": caption[:1024]} if caption else {}
        return tg("sendPhoto", chat_id=chat_id, files={"photo": ("image.jpg", images[0])}, **params)
    media = [{"type": "photo", "media": f"attach://p{i}"} for i in range(len(images[:10]))]
    if caption:
        media[0]["caption"] = caption[:1024]
    files = {f"p{i}": (f"p{i}.jpg", img) for i, img in enumerate(images[:10])}
    return tg("sendMediaGroup", chat_id=chat_id, media=json.dumps(media), files=files)


def send_copyable(chat_id, header, text):
    """Gửi nội dung trong khung <pre> -> bấm 'Copy' 1 chạm trên Telegram."""
    body = f"{html.escape(header)}\n<pre>{html.escape(text)}</pre>"
    if len(body) > 4000:  # quá dài -> gửi thường
        tg("sendMessage", chat_id=chat_id, text=header, link_preview_options=NO_PREVIEW)
        return tg("sendMessage", chat_id=chat_id, text=text, link_preview_options=NO_PREVIEW)
    return tg("sendMessage", chat_id=chat_id, text=body, parse_mode="HTML", link_preview_options=NO_PREVIEW)


def download_image(msg):
    """Bytes ảnh trong tin nhắn, hoặc None."""
    file_id = None
    if msg.get("photo"):
        file_id = msg["photo"][-1]["file_id"]
    elif msg.get("document", {}).get("mime_type", "").startswith("image/"):
        file_id = msg["document"]["file_id"]
    if not file_id:
        return None
    path = tg("getFile", file_id=file_id)["file_path"]
    r = requests.get(f"{TG_FILE}/{path}", timeout=120)
    r.raise_for_status()
    return r.content
