"""Gọi Gemini API (Google AI Studio) để viết bài và tạo ảnh."""
import base64
import json
import os
import time

import requests

API = "https://generativelanguage.googleapis.com/v1beta/models"
TEXT_MODEL = os.environ.get("GEMINI_TEXT_MODEL") or "gemini-flash-latest"
IMAGE_MODEL = os.environ.get("GEMINI_IMAGE_MODEL") or "gemini-3.1-flash-lite-image"


class GeminiError(Exception):
    pass


def _generate(model, body):
    key = os.environ.get("GEMINI_API_KEY", "").strip()
    if not key:
        raise GeminiError("Thiếu secret GEMINI_API_KEY")
    for attempt in range(4):
        r = requests.post(f"{API}/{model}:generateContent", json=body,
                          headers={"x-goog-api-key": key}, timeout=180)
        if r.status_code in (429, 500, 503) and attempt < 3:
            time.sleep(10 * (attempt + 1))  # quá tải / hết lượt miễn phí tạm thời
            continue
        data = r.json()
        if "error" in data:
            raise GeminiError(f"{model}: {data['error'].get('message')}")
        cands = data.get("candidates") or []
        if not cands:
            raise GeminiError(f"{model}: không có kết quả ({data.get('promptFeedback')})")
        return cands[0].get("content", {}).get("parts", [])
    raise GeminiError(f"{model}: quá tải, thử lại sau")


def write_post(instructions, source_info):
    """Trả về dict: post, image_title, image_prompt."""
    schema = {
        "type": "OBJECT",
        "properties": {
            "post": {"type": "STRING", "description": "Nội dung bài Facebook hoàn chỉnh"},
            "image_title": {"type": "STRING", "description": "Tiêu đề ngắn (tối đa 10 từ) để in lên ảnh"},
            "card_points": {"type": "ARRAY", "items": {"type": "STRING"},
                            "description": "3 ý chính cực ngắn (mỗi ý tối đa 9 từ) để in lên ảnh"},
            "image_prompt": {"type": "STRING", "description": "Mô tả ảnh bằng tiếng Anh để AI vẽ, ảnh chụp chân thực, không có chữ"},
        },
        "required": ["post", "image_title", "card_points", "image_prompt"],
    }
    parts = _generate(TEXT_MODEL, {
        "contents": [{"role": "user", "parts": [{"text": f"{instructions}\n\n---\n{source_info}"}]}],
        "generationConfig": {"responseMimeType": "application/json", "responseSchema": schema,
                             "temperature": 0.9},
    })
    text = "".join(p.get("text", "") for p in parts)
    try:
        return json.loads(text)
    except ValueError:
        raise GeminiError(f"Kết quả không đúng JSON: {text[:200]}")


def make_image(prompt, aspect_ratio="4:5"):
    """Trả về bytes ảnh. Cần bật thanh toán (billing) cho API key."""
    parts = _generate(IMAGE_MODEL, {
        "contents": [{"role": "user", "parts": [{"text": prompt}]}],
        "generationConfig": {"responseModalities": ["TEXT", "IMAGE"],
                             "imageConfig": {"aspectRatio": aspect_ratio}},
    })
    for p in parts:
        inline = p.get("inlineData") or p.get("inline_data")
        if inline and inline.get("data"):
            return base64.b64decode(inline["data"])
    raise GeminiError("Gemini không trả về ảnh")


def _json_from_text(text):
    start, end = text.find("["), text.rfind("]")
    if start < 0 or end < start:
        raise GeminiError(f"Không đọc được danh sách ý tưởng: {text[:200]}")
    return json.loads(text[start:end + 1])


def suggest_topics(instructions, recent, focus="", n=7, use_search=True):
    """Trả về list[str] ý tưởng. use_search: dùng Google Search để bám tin mới."""
    ask = (f"{instructions}\n\n---\nHôm nay: {time.strftime('%d/%m/%Y')}\n"
           f"Hãy đề xuất đúng {n} ý tưởng bài viết.\n"
           + (f"Hướng ưu tiên lần này: {focus}\n" if focus else "")
           + "Các chủ đề ĐÃ CÓ (không lặp lại):\n" + "\n".join(f"- {t}" for t in recent[-40:])
           + '\n\nChỉ trả về JSON array các chuỗi, ví dụ: ["Tiêu đề 1 — góc nhìn ngắn", "..."]')
    body = {"contents": [{"role": "user", "parts": [{"text": ask}]}],
            "generationConfig": {"temperature": 1.0}}
    if use_search:
        try:
            parts = _generate(TEXT_MODEL, {**body, "tools": [{"google_search": {}}]})
            return [str(x).strip() for x in _json_from_text("".join(p.get("text", "") for p in parts))][:n]
        except (GeminiError, ValueError) as e:
            print("Gợi ý có Google Search lỗi, thử lại không search:", e)
    parts = _generate(TEXT_MODEL, body)
    return [str(x).strip() for x in _json_from_text("".join(p.get("text", "") for p in parts))][:n]
