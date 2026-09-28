"""Chạy 1 lần trên máy để lấy Page Access Token KHÔNG hết hạn.

  pip install requests
  python get_page_token.py

Cần: App ID, App Secret (developers.facebook.com -> App -> Settings -> Basic)
và User token ngắn hạn từ Graph API Explorer (có quyền pages_show_list,
pages_manage_posts, pages_read_engagement).
"""
import getpass

import requests

G = "https://graph.facebook.com/v23.0"

app_id = input("App ID: ").strip()
app_secret = getpass.getpass("App Secret (ẩn khi gõ): ").strip()
short = getpass.getpass("User token ngắn hạn (ẩn khi gõ): ").strip()

r = requests.get(f"{G}/oauth/access_token", params={
    "grant_type": "fb_exchange_token", "client_id": app_id,
    "client_secret": app_secret, "fb_exchange_token": short}).json()
if "error" in r:
    raise SystemExit(f"Lỗi đổi token: {r['error']['message']}")

pages = requests.get(f"{G}/me/accounts", params={
    "access_token": r["access_token"], "fields": "id,name,access_token"}).json()
if "error" in pages:
    raise SystemExit(f"Lỗi lấy danh sách Page: {pages['error']['message']}")

print("\nCopy 2 giá trị của Fanpage cần dùng vào GitHub Secrets:\n")
for p in pages.get("data", []):
    print(f"== {p['name']} ==")
    print(f"FB_PAGE_ID    = {p['id']}")
    print(f"FB_PAGE_TOKEN = {p['access_token']}\n")
