from maps_scraper.sheet_manager import SheetManager
import os

DEFAULT_SHEET_URL = "https://docs.google.com/spreadsheets/d/1CDomOmwx5ExqgHSabEneY_Z8KGF5aRPxLrQFu92Bt-M/edit?usp=sharing"
SERVICE_ACCOUNT_KEY = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "buzzscope_today_automation", "service_account.json")

def analyze():
    try:
        mgr = SheetManager(SERVICE_ACCOUNT_KEY, DEFAULT_SHEET_URL)
        rows = mgr.leads_worksheet.get_all_records()
        
        missed = []
        total_websites = 0
        total_emails = 0
        
        for r in rows:
            website = r.get('Website', '').strip()
            email = r.get('Email', '').strip()
            
            if website:
                total_websites += 1
                if not email:
                    missed.append(website)
                else:
                    total_emails += 1
        
        print(f"Total Websites Found: {total_websites}")
        print(f"Total Emails Found: {total_emails}")
        print(f"Success Rate: {total_emails/total_websites*100:.1f}%" if total_websites else "0%")
        print("\n--- Missed Websites (Sample) ---")
        for m in missed[:10]:
            print(m)
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    analyze()
