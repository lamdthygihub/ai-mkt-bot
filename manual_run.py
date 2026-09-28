"""Chạy từ nút Run workflow trên GitHub.

ACTION=suggest  -> AI gợi ý chủ đề (INPUT = hướng ưu tiên, có thể trống)
ACTION=write    -> viết bài (INPUT = số ID ý tưởng, hoặc chủ đề, hoặc link YouTube)
"""
import os
import sys
from pathlib import Path

import drafts
import sheet
import tele

action = (os.environ.get("ACTION") or "suggest").strip().lower()
arg = os.environ.get("INPUT", "").strip()
summary = []

try:
    if action.startswith("suggest") or action.startswith("gợi"):
        ideas = drafts.suggest(arg, n=int(os.environ.get("IDEAS_COUNT") or 7))
        lines = "\n".join(f"{i}. {t}" for i, t in ideas)
        msg = f"💡 {len(ideas)} ý tưởng mới trên Sheet:\n\n{lines}\n\nGõ /viet <số> để viết.\n{sheet.sheet_url()}"
        tele.notify(msg)
        summary.append(msg)
    else:
        if not arg:
            sys.exit("Cần nhập số ID ý tưởng hoặc chủ đề.")
        if arg.isdigit():
            item = sheet.find_by_id(arg)
            if not item:
                sys.exit(f"Không thấy ID {arg}")
            d = drafts.write_idea(item)
        else:
            d = drafts.create(arg)
        msg = f"📝 Bản nháp #{d['id']} đã lên Sheet. Trả lời /duyet {d['id']} trên Telegram hoặc chọn 'Duyệt'.\n{sheet.sheet_url()}"
        tele.notify(msg)
        summary.append(f"{msg}\n\n```\n{d['text']}\n```")
except Exception as e:
    tele.notify(f"❌ [GitHub] Lỗi: {e}")
    sys.exit(f"Lỗi: {e}")

print("\n".join(summary))
if os.environ.get("GITHUB_STEP_SUMMARY"):
    with open(os.environ["GITHUB_STEP_SUMMARY"], "a", encoding="utf-8") as f:
        f.write("\n".join(summary) + "\n")
