import pandas as pd
import os
import datetime
from maps_scraper.sheet_manager import SheetManager

# Correct path: sibling directory "buzzscope_today_automation"
BASE_DIR = os.path.dirname(os.path.abspath(__file__)) # email_cleaner
KEY_PATH = os.path.join(os.path.dirname(BASE_DIR), "buzzscope_today_automation", "service_account.json")

if not os.path.exists(KEY_PATH):
    print(f"[!] Key not found at {KEY_PATH}")
    # Fallback to local
    KEY_PATH = "service_account.json"

SHEET_URL = "https://docs.google.com/spreadsheets/d/1CDomOmwx5ExqgHSabEneY_Z8KGF5aRPxLrQFu92Bt-M/edit?usp=sharing"

def migrate():
    print("--- MIGRATION STARTED ---")
    print(f"[debug] Using Key: {KEY_PATH}")
    
    # 1. Init Sheet Manager
    print(f"[i] connecting to sheet...")
    try:
        sm = SheetManager(KEY_PATH, SHEET_URL)
    except Exception as e:
        print(f"[!] Failed to connect: {e}")
        return

    # 2. Get Existing Emails (to avoid dupes)
    print(f"[i] Fetching existing emails from 'Leads with Email'...")
    existing_emails = set(sm.email_worksheet.col_values(1)) # Set for O(1) lookup
    print(f"[i] Found {len(existing_emails)} existing emails.")
    
    # helper
    def migrate_lead(email, company, city, state, niche, source_name):
        nonlocal count
        if not email or "@" not in str(email):
            return
        
        if email in existing_emails:
            # print(f"[-] Skipping existing: {email}") # noisy
            return
            
        row_data = [
            email,
            company,
            state,
            city,
            niche,
            "", # Primary
            "", # F1
            "", # F2
            "", # F3
            "", # F4
            "", # F5
            str(datetime.date.today())
        ]
        
        print(f"[+] Migrating ({source_name}): {email}")
        try:
            sm.email_worksheet.append_row(row_data)
            existing_emails.add(email) # Add to local set to prevent dupes within this run
            count += 1
        except Exception as e:
            print(f"[!] Error appending {email}: {e}")

    count = 0

    # 3. Source A: 'Leads' Sheet Tab
    print(f"\n[Phase 1] Checking 'Leads' tab for valid emails...")
    try:
        leads_records = sm.leads_worksheet.get_all_records()
        print(f"[i] Scanned {len(leads_records)} rows from 'Leads' tab.")
        
        for row in leads_records:
            migrate_lead(
                row.get("Email"),
                row.get("Company"),
                row.get("City"),
                row.get("State"),
                row.get("Niche"),
                "Leads Tab"
            )
    except Exception as e:
        print(f"[!] Error reading Leads tab: {e}")

    # 4. Source B: Local CSV
    print(f"\n[Phase 2] Checking Local CSV...")
    csv_path = "maps_scraper/leads_usa_maps.csv"
    if os.path.exists(csv_path):
        try:
            df = pd.read_csv(csv_path)
            print(f"[i] Loaded {len(df)} leads from CSV.")
            
            for _, row in df.iterrows():
                # Handle CSV column names (Capitalized in file?)
                migrate_lead(
                    row.get("Email"),
                    row.get("Company"),
                    row.get("City"),
                    row.get("State"),
                    row.get("Niche"),
                    "CSV"
                )
        except Exception as e:
            print(f"[!] CSV Error: {e}")
    else:
        print("[!] CSV not found (Skipping Phase 2).")
        
    print(f"\n--- MIGRATION COMPLETE ({count} new added) ---")

if __name__ == "__main__":
    migrate()
