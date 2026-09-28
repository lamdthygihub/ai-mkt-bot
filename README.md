# Bot nội dung AI-Marketing cho Facebook cá nhân — Phạm Thanh Lam

```
 /goiy  ──> Gemini gợi ý chủ đề ──> Google Sheet ("Ý tưởng")
 /viet 12 ─> Gemini viết bài + làm ảnh có tên bạn ──> Sheet ("Chờ duyệt") + xem trước trên Telegram
 /duyet 12 (hoặc chọn "Duyệt" trên Sheet) ──> Telegram gửi ảnh + nội dung sẵn sàng
 Bạn: lưu ảnh → bấm copy chữ → đăng Facebook cá nhân (~20 giây)
```

Mọi việc viết bài, tạo ảnh chạy trong repo bằng **Gemini API**, không tốn token Claude.

> **Vì sao không tự đăng lên Facebook cá nhân?** Facebook chỉ cho đăng tự động (qua API) lên **Fanpage**,
> không cho lên trang cá nhân. Công cụ tự đăng lên nick cá nhân đều phải giả lập đăng nhập, dễ bị checkpoint hoặc khoá nick.
> Nếu sau này bạn làm Fanpage, chỉ cần đổi `PUBLISH_MODE=page` là bot tự đăng (xem cuối trang).

## Dùng hằng ngày

| Lệnh Telegram | Việc |
|---|---|
| `/goiy` | AI gợi ý 7 chủ đề mới (có tra Google để bám tin AI gần đây), thêm vào Sheet |
| `/goiy prompt cho TikTok Shop` | Gợi ý theo hướng bạn muốn |
| `/viet 12` | Viết bài cho ý tưởng số 12 |
| `/viet cách dùng Gemini tóm tắt báo cáo ads` | Viết bài theo chủ đề bạn tự đưa |
| Gửi ảnh + caption `/viet <chủ đề>` | Dùng ảnh của bạn (tự đóng dấu tên) |
| `/viet https://youtu.be/xxx` | Bài chia sẻ/bình luận một video |
| `/duyet 12` hoặc `/duyet 12 13` | Duyệt → bot gửi bản sẵn sàng đăng |
| `/help`, `/id` | Hướng dẫn, xem chat ID |

**Mỗi sáng thứ Hai 7:00** bot tự gợi ý 7 chủ đề mới.

**Trên Google Sheet** (làm được trên điện thoại):
- Đổi Trạng thái **Ý tưởng → Viết**: AI viết bài dòng đó.
- Sửa thẳng ô **Nội dung bài** nếu muốn, rồi đổi **Chờ duyệt → Duyệt**.
- **Giờ đăng**: điền `30/09/2026 20:00` → đến giờ bot mới gửi (dùng như lời nhắc đăng bài).
- Đổi ảnh: dán link ảnh khác (hoặc link Google Drive chia sẻ công khai) vào **Link ảnh**.
- Đăng xong: dán link bài vào cột **Link bài FB**, chọn **Đã đăng** để theo dõi.

| Trạng thái | Nghĩa |
|---|---|
| Ý tưởng | AI gợi ý, chưa viết |
| Viết | Bạn chọn → bot viết ở lần chạy tới |
| Chờ duyệt | Đã có bài + ảnh |
| Duyệt | Bot sẽ gửi bản sẵn sàng qua Telegram |
| Đã gửi | Đã nhận trên Telegram, chờ bạn đăng |
| Đã đăng / Bỏ / Lỗi | Tự giải thích (Lỗi: xem cột Ghi chú) |

**Đổi giọng văn / nhóm chủ đề**: sửa `prompt.md` (cách viết bài) và `prompt_ideas.md` (cách gợi ý). Không cần sửa code.

## Ảnh
- Mặc định (`IMAGE_MODE=card`): **thẻ nội dung** 1080×1350 (tiêu đề + 3 ý chính + tên bạn), vẽ bằng code nên **miễn phí**.
- Mọi ảnh đều có tên **Phạm Thanh Lam** ở góc dưới và watermark chìm lặp chéo (tắt: `TILE_WATERMARK=false`).
- `IMAGE_MODE=ai`: Gemini vẽ ảnh minh hoạ rồi in tiêu đề lên (khoảng 0,02–0,03 USD/ảnh, cần bật Billing). Lỗi thì tự quay về thẻ nội dung.

## Chi phí
- Viết bài, gợi ý chủ đề: nằm trong gói miễn phí Gemini (tra Google: 5.000 lượt/tháng miễn phí).
- Ảnh thẻ nội dung: miễn phí. GitHub Actions: miễn phí nếu repo public.

## Cài đặt (1 lần)

### 1. Repo GitHub
Tạo repo **public** (vd `ai-mkt-bot`), upload toàn bộ thư mục này (giữ thư mục `.github`).
Public để Sheet hiện được ảnh xem trước; các key vẫn bí mật trong Secrets.
Repo private vẫn chạy được, nhưng ô ảnh xem trước sẽ trống; khi đó sửa cron trong `bot.yml` thành `*/30 * * * *`.

### 2. Bot Telegram
1. [@BotFather](https://t.me/BotFather) → `/newbot` → lấy token → secret `TELEGRAM_BOT_TOKEN`.
2. Gửi `/id` cho bot → tab **Actions → Bot (Telegram + Sheet) → Run workflow** → bot trả lời chat ID.
3. Lưu chat ID vào secret `TELEGRAM_ALLOWED_CHAT_IDS`.

### 3. Gemini API key
[aistudio.google.com/apikey](https://aistudio.google.com/apikey) → Create API key → secret `GEMINI_API_KEY`.

### 4. Google Sheet + Service account
1. Tạo Google Sheet trống. Lấy **SHEET_ID** trong URL `docs.google.com/spreadsheets/d/`**`SHEET_ID`**`/edit` → secret `SHEET_ID`.
2. [console.cloud.google.com](https://console.cloud.google.com) → chọn project của Gemini key → **APIs & Services → Library** → bật **Google Sheets API**.
3. **IAM & Admin → Service Accounts → Create service account** (vd `ai-mkt-bot`) → Done.
4. Bấm vào service account → **Keys → Add key → JSON** → tải file.
5. Copy **toàn bộ nội dung file** vào secret `GOOGLE_SERVICE_ACCOUNT_JSON`, rồi xoá file khỏi máy.
6. Mở Sheet → **Share** → dán email `client_email` trong file (dạng `...@...iam.gserviceaccount.com`) → **Editor**.

Lần chạy đầu bot tự tạo tab `Posts` với tiêu đề, màu và danh sách trạng thái.

### 5. Thử
Gửi `/goiy` cho bot → Actions → **Bot (Telegram + Sheet)** → Run workflow (khỏi đợi 10 phút).

## Secrets & Variables (Settings → Secrets and variables → Actions)

| Secret | |
|---|---|
| `TELEGRAM_BOT_TOKEN`, `TELEGRAM_ALLOWED_CHAT_IDS` | bắt buộc |
| `GEMINI_API_KEY` | bắt buộc |
| `GOOGLE_SERVICE_ACCOUNT_JSON`, `SHEET_ID` | bắt buộc |
| `YOUTUBE_API_KEY` | tuỳ chọn, để đọc mô tả video khi `/viet <link YouTube>` |

| Variable (tuỳ chọn) | Mặc định | |
|---|---|---|
| `BRAND_NAME` | `Phạm Thanh Lam` | Tên in trên ảnh |
| `BRAND_HANDLE` | (trống) | vd `fb.com/phamthanhlam`, in cạnh tên |
| `CARD_TAG` | `AI × MARKETING` | Nhãn góc trên thẻ |
| `IMAGE_MODE` | `card` | `card` miễn phí, `ai` Gemini vẽ ảnh |
| `TILE_WATERMARK` | `true` | Watermark chìm lặp chéo |
| `IDEAS_USE_SEARCH` | `true` | Gợi ý có tra Google |
| `GEMINI_TEXT_MODEL` | `gemini-flash-latest` | |
| `GEMINI_IMAGE_MODEL` | `gemini-3.1-flash-lite-image` | |
| `PUBLISH_MODE` | `telegram` | `page` = tự đăng Fanpage |

## Sự cố thường gặp
| Lỗi | Cách xử lý |
|---|---|
| `Thiếu secret ...` | Thêm đúng tên secret |
| `PERMISSION_DENIED` khi ghi Sheet | Chưa Share Sheet cho email service account, hoặc chưa bật Google Sheets API |
| `Terminated by other getUpdates` | Token bot đang được dùng nơi khác → dùng bot riêng |
| Gợi ý không có tin mới | Kiểm tra `IDEAS_USE_SEARCH`; bot tự chạy lại không search nếu tra Google lỗi |
| Ô ảnh xem trước trống | Repo private, hoặc ảnh vừa tạo (đợi 1–2 phút) |

## (Tuỳ chọn) Tự đăng lên Fanpage
Tạo Fanpage → lấy token bằng `python3 get_page_token.py` (cần App Facebook có quyền `pages_manage_posts`)
→ thêm secret `FB_PAGE_ID`, `FB_PAGE_TOKEN` → variable `PUBLISH_MODE=page`.

## Cấu trúc
| File | Việc |
|---|---|
| `telegram_poll.py` | Chạy mỗi 10 phút: lệnh Telegram, dòng "Viết", dòng "Duyệt" |
| `manual_run.py` | Nút Run workflow "Gợi ý chủ đề / Viết bài" + gợi ý tự động thứ Hai |
| `drafts.py` | Gợi ý, viết bài, làm ảnh, lưu Sheet |
| `publisher.py` | Gửi bài đã duyệt (Telegram hoặc Fanpage) |
| `image_card.py` | Thẻ nội dung, watermark tên |
| `gemini.py`, `sheet.py`, `tele.py`, `youtube.py`, `fb.py` | Kết nối từng dịch vụ |
| `prompt.md`, `prompt_ideas.md` | Hướng dẫn cho AI |
| `fonts/` | Be Vietnam Pro (SIL Open Font License) |
