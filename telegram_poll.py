"""Chạy định kỳ (GitHub Actions): đọc lệnh Telegram, viết bài cho ý tưởng được chọn,
xử lý các bài đã duyệt trên Google Sheet.

Lệnh Telegram:
  /goiy [hướng]            -> AI gợi ý 7 chủ đề, thêm vào Sheet (Ý tưởng)
  /viet <số ID>            -> viết bài cho ý tưởng có ID đó
  /viet <chủ đề | link YouTube> -> viết bài mới (gửi kèm ảnh để dùng ảnh của bạn)
  /duyet <số ID>           -> duyệt bài (không cần mở Sheet)
  /id, /help
"""
import json
import os
import sys
import time

import drafts
import publisher
import sheet
import tele
from tele import reply, tg

SETTLE_SECONDS = 30  # tin quá mới (album đang gửi dở) -> để lần chạy sau
MAX_WRITES_PER_RUN = int(os.environ.get("MAX_WRITES_PER_RUN") or 5)

HELP = (
    "📘 Lệnh:\n"
    "• /goiy — AI gợi ý 7 chủ đề AI-Marketing (thêm hướng: /goiy prompt cho TikTok)\n"
    "• /viet 12 — viết bài cho ý tưởng số 12\n"
    "• /viet <chủ đề> — viết bài theo chủ đề bạn đưa\n"
    "• Gửi ảnh + caption /viet <chủ đề> — dùng ảnh của bạn\n"
    "• /duyet 12 — duyệt bài số 12 → bot gửi bản sẵn sàng đăng\n"
    "Trên Sheet: đổi Trạng thái 'Ý tưởng' → 'Viết' để AI viết, 'Chờ duyệt' → 'Duyệt' để nhận bài.\n"
    "⏱ Bot kiểm tra định kỳ nên phản hồi sau vài phút."
)


def _arg(text):
    parts = text.strip().split(None, 1)
    return parts[1].strip() if len(parts) > 1 else ""


def send_preview(chat_id, d):
    caption = (f"📝 Bản nháp #{d['id']} — trả lời /duyet {d['id']} hoặc đổi Trạng thái trên Sheet thành \"Duyệt\".\n"
               f"{sheet.sheet_url()}")
    if d["notes"]:
        caption += "\n⚠️ " + "; ".join(d["notes"])
    try:
        tele.send_images(chat_id, [d["image"]] if d["image"] else [], caption)
        tele.send_copyable(chat_id, "Nội dung:", d["text"])
    except Exception as e:
        print("Không gửi được bản xem trước:", e)


def cmd_goiy(msg, text):
    focus = _arg(text)
    reply(msg, "💡 Đang tìm ý tưởng…")
    try:
        ideas = drafts.suggest(focus)
    except Exception as e:
        return reply(msg, f"❌ Gợi ý thất bại: {e}")
    lines = "\n".join(f"{i}. {t}" for i, t in ideas)
    reply(msg, f"💡 {len(ideas)} ý tưởng mới (đã thêm vào Sheet):\n\n{lines}\n\n"
               f"Gõ /viet <số> để viết bài, vd /viet {ideas[0][0]}\n{sheet.sheet_url()}")


def cmd_viet(msg, text, msgs):
    arg = _arg(text)
    if arg.isdigit():
        item = sheet.find_by_id(arg)
        if not item:
            return reply(msg, f"Không thấy ý tưởng số {arg} trên Sheet.")
        if not item["source"]:
            return reply(msg, f"Dòng {arg} chưa có chủ đề.")
        reply(msg, f"✍️ Đang viết bài #{arg}…")
        try:
            d = drafts.write_idea(item)
        except Exception as e:
            return reply(msg, f"❌ Viết bài thất bại: {e}")
        return send_preview(msg["chat"]["id"], d)

    user_img = next((img for img in (tele.download_image(m) for m in msgs) if img), None)
    if not arg:
        return reply(msg, "Ví dụ:\n/viet 12 (số ý tưởng trên Sheet)\n/viet 5 prompt viết caption bán hàng")
    reply(msg, "✍️ Đang viết bài và làm ảnh…")
    try:
        d = drafts.create(arg, user_img)
    except Exception as e:
        return reply(msg, f"❌ Tạo bản nháp thất bại: {e}")
    send_preview(msg["chat"]["id"], d)


def cmd_duyet(msg, text):
    ids = [x for x in _arg(text).replace(",", " ").split() if x.isdigit()]
    if not ids:
        return reply(msg, "Ví dụ: /duyet 12  (hoặc nhiều bài: /duyet 12 13)")
    done = []
    for i in ids:
        item = sheet.find_by_id(i)
        if item and item["status"] in (sheet.PENDING, sheet.ERROR) and item["text"]:
            sheet.set_status(item["row"], sheet.APPROVED)
            done.append(i)
    reply(msg, f"👍 Đã duyệt: {', '.join(done)}. Bài sẽ được gửi ngay sau đây." if done
          else "Không có bài nào ở trạng thái 'Chờ duyệt' với số đó.")


def handle_group(msgs):
    first = msgs[0]
    chat_id = str(first["chat"]["id"])
    text = next((m.get("caption") or m.get("text") for m in msgs if m.get("caption") or m.get("text")), "")
    cmd = text.strip().split(None, 1)[0].split("@")[0].lower() if text.strip() else ""

    if cmd == "/id":
        return reply(first, f"Chat ID của bạn: {chat_id}")
    if not tele.ALLOWED:
        return reply(first, f"⚙️ Bot chưa cấu hình. Chat ID của bạn là {chat_id} — lưu vào secret TELEGRAM_ALLOWED_CHAT_IDS.")
    if chat_id not in tele.ALLOWED:
        return reply(first, "⛔ Bạn không có quyền dùng bot này.")
    if cmd in ("/goiy", "/ideas"):
        return cmd_goiy(first, text)
    if cmd in ("/viet", "/draft"):
        return cmd_viet(first, text, msgs)
    if cmd in ("/duyet", "/approve"):
        return cmd_duyet(first, text)
    reply(first, HELP)


def process_telegram():
    updates = tg("getUpdates", timeout=0, allowed_updates=json.dumps(["message"]))
    if not updates:
        print("Không có tin nhắn mới.")
        return
    now = time.time()
    ready = []
    for u in sorted(updates, key=lambda u: u["update_id"]):
        msg = u.get("message")
        if msg and now - msg.get("date", 0) < SETTLE_SECONDS:
            break
        ready.append(u)
    if not ready:
        return
    # Xác nhận TRƯỚC khi xử lý để không bao giờ xử lý trùng
    tg("getUpdates", offset=ready[-1]["update_id"] + 1, timeout=0, limit=1)

    groups, index = [], {}
    for u in ready:
        msg = u.get("message")
        if not msg:
            continue
        gid = msg.get("media_group_id")
        if gid and gid in index:
            groups[index[gid]].append(msg)
        else:
            if gid:
                index[gid] = len(groups)
            groups.append([msg])
    print(f"Xử lý {len(groups)} yêu cầu Telegram.")
    for g in groups:
        handle_group(g)


def process_write_requests():
    """Dòng được đổi sang 'Viết' trên Sheet -> AI viết bài."""
    chat = tele.owner_chat()
    for item in sheet.rows_by_status(sheet.WRITE)[:MAX_WRITES_PER_RUN]:
        if not item["source"]:
            sheet.set_status(item["row"], sheet.ERROR, note="Chưa có chủ đề ở cột C")
            continue
        try:
            d = drafts.write_idea(item)
        except Exception as e:
            tele.notify(f"❌ Viết bài #{item['id']} lỗi: {e}")
            continue
        if chat:
            send_preview(chat, d)


def main():
    if tele.TOKEN:
        process_telegram()
    if os.environ.get("SHEET_ID", "").strip():
        process_write_requests()
        print(f"Đã xử lý {publisher.publish_approved()} bài được duyệt.")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print("Lỗi:", e)
        sys.exit(1)
