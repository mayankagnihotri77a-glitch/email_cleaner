from maps_scraper.sheet_manager import SheetManager
import os

DEFAULT_SHEET_URL = "https://docs.google.com/spreadsheets/d/1CDomOmwx5ExqgHSabEneY_Z8KGF5aRPxLrQFu92Bt-M/edit?usp=sharing"
SERVICE_ACCOUNT_KEY = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "buzzscope_today_automation", "service_account.json")

def fix():
    mgr = SheetManager(SERVICE_ACCOUNT_KEY, DEFAULT_SHEET_URL)
    
    # New Headers
    new_headers = ["Company", "State", "City", "Niche", "Email", "Website", "Instagram", "Facebook", "LinkedIn", "Source", "Date"]
    
    print(f"[i] Updating headers for 'Leads' tab to: {new_headers}")
    
    # Update Row 1
    # resize cols if needed or just update cells
    for col_idx, header_name in enumerate(new_headers, start=1):
        mgr.leads_worksheet.update_cell(1, col_idx, header_name)
        
    print("[+] Headers updated successfully.")

if __name__ == "__main__":
    fix()
