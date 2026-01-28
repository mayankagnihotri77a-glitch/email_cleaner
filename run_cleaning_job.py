
import os
import sys
import pandas as pd
from colorama import init, Fore, Style

# Add root directory to path to allow imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from maps_scraper.sheet_manager import SheetManager
from validators.mx_check import MXValidator
from validators.disposable import DisposableValidator

init(autoreset=True)

# Configuration
DEFAULT_SHEET_URL = "https://docs.google.com/spreadsheets/d/1CDomOmwx5ExqgHSabEneY_Z8KGF5aRPxLrQFu92Bt-M/edit?usp=sharing"

# Service Account Path Logic
_base_dir = os.path.dirname(os.path.abspath(__file__)) 
_local_path = os.path.join(os.path.dirname(_base_dir), "buzzscope_today_automation", "service_account.json")
_repo_path = os.path.join(_base_dir, "service_account.json")

if os.path.exists(_local_path):
    SERVICE_ACCOUNT_KEY = _local_path
elif os.path.exists(_repo_path):
    SERVICE_ACCOUNT_KEY = _repo_path
else:
    print(Fore.RED + "[!] Service account file not found.")
    sys.exit(1)

def run_cleaner():
    print(Fore.CYAN + "\n--- Running Email Cleaner Job ---\n")
    
    try:
        sm = SheetManager(SERVICE_ACCOUNT_KEY, DEFAULT_SHEET_URL)
        print(Fore.GREEN + "[+] Connected to Sheet.")
        
        print("Fetching 'Leads with Email'...")
        records = sm.email_worksheet.get_all_records()
        print(f"[+] Found {len(records)} rows.")
        
        if not records:
             print("[!] No leads found to audit.")
             return

    except Exception as e:
        print(Fore.RED + f"[!] Connection Failed: {e}")
        return

    mx_val = MXValidator()
    # disp_val = DisposableValidator() # Optional: remove burner? Yes.

    invalid_emails = []
    
    print(f"\nScanning {len(records)} emails...")

    for row in records:
        email = str(row.get('Email', '')).strip()
        if not email: continue
        
        # We only remove Dead Domains (MX fail)
        # Syntax errors usually shouldn't be in sheet if scraper works, but if so, kill them too
        
        # Step 1: MX Record
        print(f"\r   Checking: {email.split('@')[-1]}...", end="")
        is_mx_valid, err = mx_val.validate(email)
        
        if not is_mx_valid:
            print(f" -> INVALID ({err})")
            invalid_emails.append(email)
            continue
            
    print("\n")
    
    if invalid_emails:
        print(Fore.YELLOW + f"[!] Found {len(invalid_emails)} invalid emails to remove.")
        print(Fore.RED + "Removing them from Google Sheet now...")
        sm.remove_invalid_leads(invalid_emails)
        print(Fore.GREEN + "[Done] Sheet Cleaned.")
    else:
        print(Fore.GREEN + "[Pass] No invalid emails found.")

if __name__ == "__main__":
    run_cleaner()
