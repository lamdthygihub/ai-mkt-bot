"""Google Sheet làm kho ý tưởng + hàng chờ duyệt bài."""
import datetime as dt
import json
import os
from zoneinfo import ZoneInfo

import gspread

TZ = ZoneInfo(os.environ.get("TIMEZONE") or "Asia/Ho_Chi_Minh")
TAB = os.environ.get("SHEET_TAB") or "Posts"
HEADERS = ["ID", "Tạo lúc", "Chủ đề / Nguồn", "Nội dung bài", "Ảnh xem trước", "Link ảnh",
           "Giờ đăng (tuỳ chọn)", "Trạng thái", "Link bài FB", "Ghi chú"]
C_ID, C_CREATED, C_SOURCE, C_TEXT, C_PREVIEW, C_IMAGE, C_WHEN, C_STATUS, C_LINK, C_NOTE = range(1, 11)

IDEA, WRITE, PENDING, APPROVED, SKIP = "Ý tưởng", "Viết", "Chờ duyệt", "Duyệt", "Bỏ"
WORKING, SENT, POSTED, ERROR = "Đang xử lý", "Đã gửi", "Đã đăng", "Lỗi"
STATUSES = [IDEA, WRITE, PENDING, APPROVED, SKIP, WORKING, SENT, POSTED, ERROR]
COLORS = {IDEA: (.93, .9, 1), WRITE: (.8, .9, 1), PENDING: (1, .95, .75), APPROVED: (.8, .95, .8),
          SENT: (.85, .95, .95), POSTED: (.88, .88, .88), ERROR: (1, .8, .8)}

_ws = None


def ws():
    global _ws
    if _ws:
        return _ws
    creds = os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON", "").strip()
    sheet_id = os.environ.get("SHEET_ID", "").strip()
    if not creds or not sheet_id:
        raise RuntimeError("Thiếu secret GOOGLE_SERVICE_ACCOUNT_JSON hoặc SHEET_ID")
    sh = gspread.service_account_from_dict(json.loads(creds)).open_by_key(sheet_id)
    try:
        _ws = sh.worksheet(TAB)
    except gspread.WorksheetNotFound:
        _ws = sh.add_worksheet(TAB, rows=1000, cols=len(HEADERS))
    if _ws.row_values(1)[:len(HEADERS)] != HEADERS:
        _setup(sh, _ws)
    return _ws


def _setup(sh, w):
    """Tạo tiêu đề, định dạng, danh sách chọn trạng thái (chạy 1 lần)."""
    w.update([HEADERS], "A1")
    sid = w.id
    col = lambda c: {"sheetId": sid, "startRowIndex": 1, "startColumnIndex": c - 1, "endColumnIndex": c}
    widths = [50, 120, 260, 420, 200, 150, 140, 110, 170, 220]
    reqs = [
        {"updateSheetProperties": {"properties": {"sheetId": sid, "gridProperties": {"frozenRowCount": 1}},
                                   "fields": "gridProperties.frozenRowCount"}},
        {"repeatCell": {"range": {"sheetId": sid, "startRowIndex": 0, "endRowIndex": 1},
                        "cell": {"userEnteredFormat": {"textFormat": {"bold": True},
                                                       "backgroundColor": {"red": .9, "green": .93, "blue": 1}}},
                        "fields": "userEnteredFormat(textFormat,backgroundColor)"}},
        {"repeatCell": {"range": {"sheetId": sid, "startRowIndex": 1},
                        "cell": {"userEnteredFormat": {"wrapStrategy": "WRAP", "verticalAlignment": "TOP"}},
                        "fields": "userEnteredFormat(wrapStrategy,verticalAlignment)"}},
        {"repeatCell": {"range": col(C_WHEN),
                        "cell": {"userEnteredFormat": {"numberFormat": {"type": "DATE_TIME", "pattern": "dd/mm/yyyy hh:mm"}}},
                        "fields": "userEnteredFormat.numberFormat"}},
        {"setDataValidation": {"range": col(C_STATUS), "rule": {
            "condition": {"type": "ONE_OF_LIST", "values": [{"userEnteredValue": s} for s in STATUSES]},
            "showCustomUi": True, "strict": False}}},
    ]
    for i, px in enumerate(widths):
        reqs.append({"updateDimensionProperties": {
            "range": {"sheetId": sid, "dimension": "COLUMNS", "startIndex": i, "endIndex": i + 1},
            "properties": {"pixelSize": px}, "fields": "pixelSize"}})
    for status, (r, g, b) in COLORS.items():
        reqs.append({"addConditionalFormatRule": {"index": 0, "rule": {
            "ranges": [{"sheetId": sid, "startRowIndex": 1}],
            "booleanRule": {"condition": {"type": "CUSTOM_FORMULA",
                                          "values": [{"userEnteredValue": f'=$H2="{status}"'}]},
                            "format": {"backgroundColor": {"red": r, "green": g, "blue": b}}}}}})
    sh.batch_update({"requests": reqs})


def now():
    return dt.datetime.now(TZ)


def _next_id_and_row(w):
    col = w.col_values(C_ID)
    ids = [int(x) for x in col[1:] if str(x).isdigit()]
    return max(ids, default=0) + 1, len(col) + 1


def _preview(row):
    return f'=IFERROR(IMAGE(INDEX(SPLIT(F{row}, CHAR(10)&","), 1)), "")'


def add_draft(source, text, image_urls, note=""):
    """Thêm 1 dòng 'Chờ duyệt'. Trả về (id, số dòng)."""
    w = ws()
    new_id, row = _next_id_and_row(w)
    images = "\n".join(image_urls)
    w.update([[new_id, now().strftime("%d/%m/%Y %H:%M"), source, text, _preview(row) if images else "",
               images, "", PENDING, "", note]], f"A{row}", value_input_option="USER_ENTERED")
    return new_id, row


def add_ideas(ideas):
    """ideas: list[str]. Thêm các dòng 'Ý tưởng'. Trả về list[(id, text)]."""
    w = ws()
    new_id, row = _next_id_and_row(w)
    stamp = now().strftime("%d/%m/%Y %H:%M")
    values = [[new_id + i, stamp, idea, "", "", "", "", IDEA, "", ""] for i, idea in enumerate(ideas)]
    w.update(values, f"A{row}", value_input_option="USER_ENTERED")
    return [(new_id + i, idea) for i, idea in enumerate(ideas)]


def fill_draft(row, text, image_urls, note=""):
    """Điền bài + ảnh vào một dòng ý tưởng có sẵn, chuyển sang 'Chờ duyệt'."""
    w = ws()
    images = "\n".join(image_urls)
    w.update([[text, _preview(row) if images else "", images]], f"D{row}", value_input_option="USER_ENTERED")
    w.update([[PENDING, "", note]], f"H{row}")


def _parse_when(v):
    """Ô 'Giờ đăng' -> datetime (giờ VN) hoặc None."""
    if v in ("", None):
        return None
    if isinstance(v, (int, float)):  # số serial ngày của Google Sheets
        return (dt.datetime(1899, 12, 30) + dt.timedelta(minutes=round(float(v) * 1440))).replace(tzinfo=TZ)
    for fmt in ("%d/%m/%Y %H:%M", "%d/%m/%Y %H:%M:%S", "%d/%m/%Y", "%Y-%m-%d %H:%M"):
        try:
            return dt.datetime.strptime(str(v).strip(), fmt).replace(tzinfo=TZ)
        except ValueError:
            pass
    raise ValueError(f"Không hiểu giờ đăng '{v}' (dùng dạng 30/09/2026 20:00)")


def all_rows():
    rows = ws().get_all_values(value_render_option="UNFORMATTED_VALUE")
    out = []
    for i, r in enumerate(rows[1:], start=2):
        r = list(r) + [""] * (len(HEADERS) - len(r))
        out.append({"row": i, "id": r[C_ID - 1], "source": str(r[C_SOURCE - 1]).strip(),
                    "text": str(r[C_TEXT - 1]).strip(), "status": str(r[C_STATUS - 1]).strip(),
                    "when_raw": r[C_WHEN - 1],
                    "images": [s.strip() for s in str(r[C_IMAGE - 1]).replace(",", "\n").split("\n") if s.strip()]})
    return out


def rows_by_status(status):
    return [r for r in all_rows() if r["status"] == status]


def find_by_id(draft_id):
    return next((r for r in all_rows() if str(r["id"]).split(".")[0] == str(draft_id)), None)


def recent_topics(n=40):
    return [r["source"] for r in all_rows()[-n:] if r["source"]]


def approved_rows():
    """Các dòng 'Duyệt' đã tới giờ đăng."""
    out = []
    for item in rows_by_status(APPROVED):
        try:
            when = _parse_when(item["when_raw"])
        except ValueError as e:
            set_status(item["row"], ERROR, note=str(e))
            continue
        if when and when > now():
            continue
        out.append(item)
    return out


def set_status(row, status, link=None, note=None):
    w = ws()
    w.update_cell(row, C_STATUS, status)
    if link is not None:
        w.update_cell(row, C_LINK, link)
    if note is not None:
        w.update_cell(row, C_NOTE, note)


def sheet_url():
    return f"https://docs.google.com/spreadsheets/d/{os.environ.get('SHEET_ID', '').strip()}"
