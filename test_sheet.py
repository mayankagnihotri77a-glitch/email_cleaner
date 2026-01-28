import gspread
from oauth2client.service_account import ServiceAccountCredentials
import os

KEY_PATH = r"C:\Users\my\.gemini\antigravity\scratch\buzzscope_today_automation\service_account.json"
SHEET_URL = "https://docs.google.com/spreadsheets/d/1CDomOmwx5ExqgHSabEneY_Z8KGF5aRPxLrQFu92Bt-M/edit?usp=sharing"

print("Starting Auth...")
scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
creds = ServiceAccountCredentials.from_json_keyfile_name(KEY_PATH, scope)
client = gspread.authorize(creds)
print("Auth Done. Opening Sheet...")

sheet = client.open_by_url(SHEET_URL)
print(f"Sheet Title: {sheet.title}")

print("Worksheets:")
for ws in sheet.worksheets():
    print(f"- {ws.title}")

try:
    ws_email = sheet.worksheet("Leads with Email")
    rows = ws_email.get_all_values()
    print(f"\n[Leads with Email] Row Count: {len(rows)}")
    if len(rows) > 0:
        print(f"Header: {rows[0]}")
except Exception as e:
    print(f"[!] Error accessing Leads with Email: {e}")
