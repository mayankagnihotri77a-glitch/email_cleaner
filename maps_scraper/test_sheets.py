from maps_scraper.sheet_manager import SheetManager
import os

# Configuration for Test
# 1. Sheet URL (User must provide this)
GOOGLE_SHEET_URL = "https://docs.google.com/spreadsheets/d/1CDomOmwx5ExqgHSabEneY_Z8KGF5aRPxLrQFu92Bt-M/edit?usp=sharing"
# 2. Service Account (Using local fallback)
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SERVICE_ACCOUNT_KEY = os.path.join(os.path.dirname(os.path.dirname(SCRIPT_DIR)), "buzzscope_today_automation", "service_account.json")

def test_connection():
    if not os.path.exists(SERVICE_ACCOUNT_KEY):
        print(f"[!] Service account file not found at: {SERVICE_ACCOUNT_KEY}")
        return

    print(f"[i] Using Service Account: {SERVICE_ACCOUNT_KEY}")
    
    # ASK USER FOR URL IF NOT SET
    sheet_url = os.getenv("GOOGLE_SHEET_URL") or GOOGLE_SHEET_URL
    if "1BfEF" in sheet_url: # Detect placeholder
         print("[!] Please set a valid GOOGLE_SHEET_URL in the script or env var.")
         return

    try:
        mgr = SheetManager(SERVICE_ACCOUNT_KEY, sheet_url)
        print("[+] Connection Successful!")
        print("[+] 'Leads' tab accessed/created.")
        print("[+] 'Status' tab accessed/created.")
        
        status = mgr.get_status()
        print(f"[i] Current Status: {status}")
        
    except Exception as e:
        print(f"[!] Connection Failed: {repr(e)}")
        print("\nPossible fix: Share the sheet with the email inside service_account.json")

if __name__ == "__main__":
    test_connection()
