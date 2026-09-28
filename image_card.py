"""Tạo ảnh bằng Pillow (miễn phí): thẻ nội dung, chèn tiêu đề, watermark tên."""
import io
import os
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).parent
BRAND = os.environ.get("BRAND_NAME") or "Phạm Thanh Lam"
HANDLE = os.environ.get("BRAND_HANDLE") or ""          # vd: fb.com/phamthanhlam
TAG = os.environ.get("CARD_TAG") or "AI × MARKETING"
TILE_WATERMARK = (os.environ.get("TILE_WATERMARK") or "true").lower() == "true"

BG_TOP, BG_BOTTOM = (11, 16, 38), (42, 20, 88)        # xanh đêm -> tím
ACCENT = (255, 181, 71)                               # vàng cam
WHITE, MUTED = (255, 255, 255), (200, 200, 225)


def _font(size, bold=True):
    name = "BeVietnamPro-Bold.ttf" if bold else "BeVietnamPro-Medium.ttf"
    for path in (ROOT / name, ROOT / "fonts" / name):  # font để ở thư mục gốc hoặc fonts/
        if path.is_file():
            return ImageFont.truetype(str(path), size)
    return ImageFont.load_default(size)


def _wrap(draw, text, font, max_w):
    lines, cur = [], ""
    for word in text.split():
        test = f"{cur} {word}".strip()
        if draw.textlength(test, font=font) <= max_w or not cur:
            cur = test
        else:
            lines.append(cur)
            cur = word
    if cur:
        lines.append(cur)
    return lines


def _fit(draw, text, max_w, max_lines, start, bold=True, min_size=28):
    size = start
    while True:
        font = _font(size, bold)
        lines = _wrap(draw, text, font, max_w)
        if len(lines) <= max_lines or size <= min_size:
            return font, lines, size
        size -= 4


def _tile(img, brand):
    """Watermark tên chìm, lặp chéo toàn ảnh (chống lấy ảnh)."""
    w, h = img.size
    layer = Image.new("RGBA", (w * 2, h * 2), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    f = _font(max(24, w // 30))
    step_x, step_y = int(w * 0.45), int(h * 0.16)
    for yi, y in enumerate(range(0, h * 2, step_y)):
        for x in range(-(yi % 2) * step_x // 2, w * 2, step_x):
            d.text((x, y), brand, font=f, fill=(255, 255, 255, 16))
    layer = layer.rotate(25, resample=Image.BICUBIC)
    left, top = (layer.width - w) // 2, (layer.height - h) // 2
    img.alpha_composite(layer.crop((left, top, left + w, top + h)))


def _to_jpeg(img):
    out = io.BytesIO()
    img.convert("RGB").save(out, "JPEG", quality=92)
    return out.getvalue()


def _signature(img, brand, handle, y=None):
    """Tên (và handle) ở góc dưới trái, có vạch màu nhấn."""
    d = ImageDraw.Draw(img)
    w, h = img.size
    pad = int(w * 0.07)
    f = _font(int(w * 0.036))
    y = y or h - pad - int(w * 0.036)
    d.rectangle((pad, y + 6, pad + 8, y + int(w * 0.036) + 4), fill=ACCENT)
    d.text((pad + 24, y), brand, font=f, fill=WHITE)
    if handle:
        hx = pad + 24 + d.textlength(brand, font=f) + 20
        d.text((hx, y + int(w * 0.008)), handle, font=_font(int(w * 0.026), False), fill=MUTED)


def make_card(title, points=(), brand=BRAND, handle=HANDLE, tag=TAG, size=(1080, 1350)):
    """Thẻ nội dung 4:5 (hợp feed Facebook): tag, tiêu đề, 3 ý chính, chữ ký."""
    w, h = size
    img = Image.new("RGBA", size)
    for y in range(h):  # nền gradient
        t = y / h
        img.paste(tuple(int(a + (b - a) * t) for a, b in zip(BG_TOP, BG_BOTTOM)) + (255,), (0, y, w, y + 1))
    d = ImageDraw.Draw(img)
    # vầng sáng trang trí
    glow = Image.new("RGBA", size, (0, 0, 0, 0))
    ImageDraw.Draw(glow).ellipse((w * 0.55, -h * 0.15, w * 1.35, h * 0.45), fill=(124, 92, 255, 55))
    img.alpha_composite(glow)
    if TILE_WATERMARK:
        _tile(img, brand)
    d = ImageDraw.Draw(img)
    pad = int(w * 0.08)

    # Tag
    tf = _font(30)
    tw = d.textlength(tag, font=tf)
    d.rounded_rectangle((pad, pad, pad + tw + 44, pad + 58), radius=29, outline=ACCENT, width=3)
    d.text((pad + 22, pad + 10), tag, font=tf, fill=ACCENT)

    # Tiêu đề
    y = pad + 110
    font, lines, fs = _fit(d, title.strip(), w - 2 * pad, 4, 88)
    for line in lines:
        d.text((pad, y), line, font=font, fill=WHITE)
        y += int(fs * 1.22)

    # Ý chính
    y += 40
    d.line((pad, y, pad + 120, y), fill=ACCENT, width=6)
    y += 50
    for i, p in enumerate([p for p in points if p][:3], start=1):
        pf, plines, ps = _fit(d, p.strip(), w - 2 * pad - 100, 2, 44, bold=False, min_size=30)
        r = 30
        d.ellipse((pad, y, pad + 2 * r, y + 2 * r), fill=ACCENT)
        num = str(i)
        nf = _font(34)
        d.text((pad + r - d.textlength(num, font=nf) / 2, y + 8), num, font=nf, fill=BG_TOP)
        ty = y + 4
        for line in plines:
            d.text((pad + 90, ty), line, font=pf, fill=WHITE)
            ty += int(ps * 1.3)
        y = max(y + 2 * r, ty) + 36
        if y > h - 220:
            break

    _signature(img, brand, handle)
    return _to_jpeg(img)


def watermark(image_bytes, brand=BRAND, handle=HANDLE):
    """Đóng dấu tên lên ảnh có sẵn (ảnh bạn gửi, thumbnail, ảnh AI)."""
    img = Image.open(io.BytesIO(image_bytes)).convert("RGBA")
    if img.width < 1080:
        img = img.resize((1080, int(img.height * 1080 / img.width)), Image.LANCZOS)
    w, h = img.size
    if TILE_WATERMARK:
        _tile(img, brand)
    # dải tối nhẹ ở đáy để chữ ký luôn đọc được
    band_h = int(w * 0.13)
    band = Image.new("RGBA", (w, band_h), (0, 0, 0, 0))
    bd = ImageDraw.Draw(band)
    for y in range(band_h):
        bd.line((0, y, w, y), fill=(0, 0, 0, int(150 * y / band_h)))
    img.alpha_composite(band, (0, h - band_h))
    _signature(img, brand, handle)
    return _to_jpeg(img)


def add_title(image_bytes, title, brand=BRAND, handle=HANDLE):
    """Ảnh nền (vd ảnh AI) + tiêu đề lớn + chữ ký."""
    img = Image.open(io.BytesIO(image_bytes)).convert("RGBA")
    if img.width < 1080:
        img = img.resize((1080, int(img.height * 1080 / img.width)), Image.LANCZOS)
    w, h = img.size
    if TILE_WATERMARK:
        _tile(img, brand)
    grad_h = int(h * 0.55)
    grad = Image.new("RGBA", (w, grad_h), (0, 0, 0, 0))
    gd = ImageDraw.Draw(grad)
    for y in range(grad_h):
        gd.line((0, y, w, y), fill=(0, 0, 0, int(220 * (y / grad_h) ** 1.5)))
    img.alpha_composite(grad, (0, h - grad_h))
    d = ImageDraw.Draw(img)
    pad = int(w * 0.07)
    font, lines, fs = _fit(d, (title or "").strip(), w - 2 * pad, 3, int(w * 0.08))
    y = h - pad - int(w * 0.036) - 40 - int(fs * 1.2) * len(lines)
    for line in lines:
        d.text((pad, y), line, font=font, fill=WHITE, stroke_width=2, stroke_fill=(0, 0, 0))
        y += int(fs * 1.2)
    _signature(img, brand, handle)
    return _to_jpeg(img)
