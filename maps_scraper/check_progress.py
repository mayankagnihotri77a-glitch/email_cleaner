from maps_scraper.sheet_manager import SheetManager
import os

DEFAULT_SHEET_URL = "https://docs.google.com/spreadsheets/d/1CDomOmwx5ExqgHSabEneY_Z8KGF5aRPxLrQFu92Bt-M/edit?usp=sharing"
SERVICE_ACCOUNT_KEY = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "buzzscope_today_automation", "service_account.json")

def check():
    mgr = SheetManager(SERVICE_ACCOUNT_KEY, DEFAULT_SHEET_URL)
    
    # Check Leads
    rows = mgr.leads_worksheet.get_all_records()
    leads_count = len(rows)
    email_count = sum(1 for r in rows if r.get('Email', '').strip())
    
    print(f"[i] Total Leads found: {leads_count}")
    print(f"[i] Total Emails found: {email_count}")
    print(f"[i] Email Success Rate: {email_count/leads_count*100:.1f}%" if leads_count else "0%")
    
    # Check Status
    status = mgr.get_status()
    print(f"[i] Current Status: {status}")

if __name__ == "__main__":
    check()
