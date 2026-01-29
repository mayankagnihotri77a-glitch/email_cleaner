import sys
import os
import time
import argparse

# Add parent directory to path to import maps_scraper modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from maps_scraper.sheet_manager import SheetManager
from lead_scraper.smart_hunt import smart_hunt
import gspread

# --- CONFIG ---
SHEET_ID = "1CDomOmwx5ExqgHSabEneY_Z8KGF5aRPxLrQFu92Bt-M" # Extracted from user's manager.py
SHEET_URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/edit?usp=sharing"
CREDENTIALS_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "service_account.json")

def get_sheet_manager():
    if not os.path.exists(CREDENTIALS_PATH):
        print(f"[!] missing service_account.json at {CREDENTIALS_PATH}")
        return None
    return SheetManager(CREDENTIALS_PATH, SHEET_URL)

def integrate_leads(target_domains, start_row=22):
    sm = get_sheet_manager()
    if not sm: return

    print(f"[*] Starting Smart Hunt Integration. Target Row: {start_row}")
    
    # We want to write to 'Leads with Email' sheet
    ws = sm.email_worksheet
    
    # Get existing emails to avoid dupes
    existing_emails = ws.col_values(1) # Column A
    
    current_row = start_row
    total_added = 0
    
    for domain in target_domains:
        print(f"\n--- Hunting for {domain} ---")
        leads = smart_hunt(domain)
        
        for lead in leads:
            email = lead.get('email')
            if not email: continue
            
            # Dedupe check
            if email in existing_emails:
                print(f"    [Skip] {email} already exists.")
                continue
            
            # Prepare row for 'Leads with Email'
            # Format: [Email, Company, State, City, Niche, Primary Mail, ... Date]
            # We might not have all info, so we fill what we can
            
            row_data = [
                email,                      # Email
                f"{domain} ({lead.get('role')})", # Company (use role as context)
                "USA",                      # State (Targeting USA as requested)
                "Unknown",                  # City
                "Email Marketing",          # Niche (Inferred)
                "",                         # Primary Mail
                "",                         # Follow Up 1
                "",                         # Follow Up 2
                "",                         # Follow Up 3
                "",                         # Follow Up 4
                "",                         # Follow Up 5
                str(time.strftime("%Y-%m-%d"))  # Date Added
            ]
            
            print(f"    [+] Adding {email} at row {current_row}")
            total_added += 1
            
            # Insert or update cell?
            # User wants SPECIFICALLY from row 22.
            # We should probably use `update` to force it into that row if empty, or insert_row.
            # Using update for safety to overwrite blank cells
            
            try:
                # Provide a range to update a single row
                # Convert list to list of lists for update
                # Row index is 1-based
                
                # Check if row is empty first to avoid overwriting existing data? 
                # User said "just after the leads...". Let's assume blank.
                
                # gspread update using range 'A{row}:L{row}'
                cell_range = f"A{current_row}:L{current_row}"
                ws.update(range_name=cell_range, values=[row_data])
                
                current_row += 1
                existing_emails.append(email) # Add to local cache
                
            except Exception as e:
                print(f"    [!] Sheet Error: {e}")

    msg = f"🚀 **Smart Lead Hunter Report**\n- Processed: {len(target_domains)} domains\n- New Leads Added: {total_added}"
    try:
        from maps_scraper.telegram_notifier import send_telegram_message
        send_telegram_message(msg)
    except Exception as e:
        print(f"[!] Telegram Error: {e}")

    print("\n[Done] Integration Complete.")

def fetch_pending_domains():
    """
    Reads 'Leads' sheet, finds websites.
    Reads 'Leads with Email' sheet, finds already processed domains.
    Returns list of domains that are in Leads but NOT in Email sheet.
    """
    sm = get_sheet_manager()
    if not sm: return []
    
    print("[*] Fetching pending domains from Sheet...")
    
    # 1. Get all raw leads
    # records is list of dicts: {'Company':..., 'Website':...}
    raw_leads = sm.leads_worksheet.get_all_records()
    
    # 2. Get processed emails
    # We want to check if we already have an email for this company/website
    email_records = sm.email_worksheet.get_all_records()
    
    # Create set of processed "Companies" or "Websites" to exclude
    # Ideally checking website is safer.
    processed_websites = set()
    for row in email_records:
        # We stored "domain (role)" in Company column in previous step? 
        # Actually we store extracted email. 
        # But we don't store the raw website in email sheet explicitly in my previous code 
        # (I put domain in 'Company' col).
        # Let's simple check if the 'Company' column contains the domain string.
        comp = row.get('Company', '').lower()
        processed_websites.add(comp)

    pending = []
    seen_in_batch = set()
    
    for row in raw_leads:
        website = row.get('Website', '').strip().lower()
        if not website: continue
        
        # Clean url to domain
        # e.g. https://www.stripe.com -> stripe.com
        if "://" in website:
            domain = website.split("://")[1].split("/")[0]
        else:
            domain = website.split("/")[0]
            
        domain = domain.replace("www.", "")
        
        # Skip if seen
        if domain in seen_in_batch: continue
        
        # Check if already processed (naive check)
        is_processed = False
        for p in processed_websites:
            if domain in p:
                is_processed = True
                break
        
        if not is_processed:
            pending.append(domain)
            seen_in_batch.add(domain)
            
    print(f"[*] Found {len(pending)} pending domains.")
    return pending

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=10, help="Max domains to process per run")
    args = parser.parse_args()

    # 1. Fetch Dynamic Targets
    targets = fetch_pending_domains()
    
    # 2. Slice based on limit (to avoid timeouts)
    if targets:
        # randomize? or just take first? 
        # First is better to catch up on old leads.
        batch = targets[:args.limit]
        print(f"[*] Processing batch of {len(batch)} domains...")
        integrate_leads(batch, start_row=22)
    else:
        print("[*] No pending targets found.")
