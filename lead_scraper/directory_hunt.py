import sys
import os
import time
import argparse
import random
from duckduckgo_search import DDGS

# Add parent directory to path to import maps_scraper and lead_scraper modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from maps_scraper.sheet_manager import SheetManager
from lead_scraper.smart_hunt import smart_hunt
from lead_scraper.directory_scraper import search_directory_leads

# --- CONFIG ---
SHEET_ID = "1CDomOmwx5ExqgHSabEneY_Z8KGF5aRPxLrQFu92Bt-M" 
SHEET_URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/edit?usp=sharing"
CREDENTIALS_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "service_account.json")

# Tier 1 Niches (High Conversion)
TIER_1_NICHES = [
    "Digital Marketing Agencies USA",
    "SaaS Companies USA",
    "Ecommerce Brands USA",
    "Lead Generation Companies USA",
    "Email Marketing Consultants USA"
]

def get_sheet_manager():
    if not os.path.exists(CREDENTIALS_PATH):
        print(f"[!] missing service_account.json at {CREDENTIALS_PATH}")
        return None
    return SheetManager(CREDENTIALS_PATH, SHEET_URL)

def find_domain_from_name(agency_name):
    """
    Uses DDG to find the official website of an agency.
    "Agency Name official site"
    """
    query = f"{agency_name} official site"
    print(f"    [?] Searching domain for: {agency_name}...")
    try:
        with DDGS() as ddgs:
            results = ddgs.text(query, max_results=3)
            for r in results:
                url = r.get('href', '')
                if "clutch.co" in url or "linkedin" in url or "facebook" in url:
                    continue # Skip social profiles
                return url
    except Exception as e:
        print(f"    [!] Domain Search Error: {e}")
    
    return None

def run_directory_hunt(limit_per_niche=5):
    sm = get_sheet_manager()
    if not sm: return

    ws = sm.email_worksheet
    existing_emails = ws.col_values(1)
    
    # We also want to check existing Company names to avoid re-hunting same agency
    # Column 2 is Company
    existing_companies = ws.col_values(2)
    
    processed_domains = set()
    for row in existing_emails:
        # A bit loose, but avoids mostly
        pass

    total_leads_added = 0
    for niche in TIER_1_NICHES:
        print(f"\n=== Hunting Niche: {niche} ===")
        
        # 1. Find Agencies
        agencies = search_directory_leads(niche)
        
        # Shuffle to get variety if run updates frequently
        random.shuffle(agencies)
        
        count = 0
        for agency in agencies:
            if count >= limit_per_niche: break
            
            name = agency['Agency']
            print(f"\n--- Processing: {name} ---")
            
            # Check if likely already in sheet (naive check)
            if any(name.lower() in c.lower() for c in existing_companies):
                print(f"    [Skip] {name} seems to be in sheet already.")
                continue

            # 2. Find Domain
            url = find_domain_from_name(name)
            if not url:
                print("    [!] Could not find domain.")
                continue
                
            domain = url.split("//")[-1].split("/")[0].replace("www.", "")
            print(f"    [+] Found Domain: {domain}")
            
            # 3. Smart Hunt
            leads = smart_hunt(domain)
            
            # 4. Save to Sheet with Priority (Insert after last sent lead)
            saved_count = 0
            for lead in leads:
                email = lead.get('email')
                if not email: continue
                if email in existing_emails: continue
                
                row_data = [
                    email,
                    f"{name} ({domain})", # Company Field
                    "USA",
                    "Unknown",
                    niche, # Niche
                    "", "", "", "", "", "", # Stages
                    str(time.strftime("%Y-%m-%d"))
                ]
                
                try:
                    # Strategy: Find the best row to insert to maximize priority
                    # We want to insert AFTER the last row that has a "Primary Mail" sent date.
                    # This puts it at the top of the "Pending" list.
                    
                    # optimized: fetch col 6 (Primary Mail) only once per batch logic, or just now
                    # For safety, let's fetch roughly where to insert.
                    # Actually, if we just insert at Row 22 (or where user specified earlier), we push others down.
                    # But the user specifically said "after the leads to which bot already send mails".
                    
                    # Let's find the first empty "Primary Mail" cell.
                    # Col 6 is Primary Mail.
                    primary_col = ws.col_values(6) 
                    # primary_col[0] is header.
                    
                    insert_idx = len(primary_col) + 1 # Default: append to end
                    
                    for idx, val in enumerate(primary_col):
                        if idx == 0: continue # Header
                        if not val.strip():
                            # Found first empty slot!
                            insert_idx = idx + 1 # 1-based index
                            break
                    
                    print(f"    [+] Priority Insert {email} at row {insert_idx}...")
                    ws.insert_row(row_data, index=insert_idx)
                    
                    existing_emails.append(email)
                    saved_count += 1
                    total_leads_added += 1
                except Exception as e:
                    print(f"    [!] Sheet Error: {e}")
            
            if saved_count > 0:
                count += 1
            
            # Sleep to be polite
            time.sleep(2)
            
    msg = f"🎯 **Directory Hunter Report**\n- Niches Scanned: {len(TIER_1_NICHES)}\n- New Leads Added: {total_leads_added}"
    try:
        from maps_scraper.telegram_notifier import send_telegram_message
        send_telegram_message(msg)
    except Exception as e:
        print(f"[!] Telegram Error: {e}")

if __name__ == "__main__":
    run_directory_hunt(limit_per_niche=5)
