
import os
import sys
import pandas as pd
from colorama import init, Fore, Style

# Add root directory to path to allow imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from maps_scraper.sheet_manager import SheetManager
from validators.syntax import SyntaxValidator
from validators.mx_check import MXValidator
from validators.disposable import DisposableValidator
from main import generate_report

init(autoreset=True)

# Configuration
DEFAULT_SHEET_URL = "https://docs.google.com/spreadsheets/d/1CDomOmwx5ExqgHSabEneY_Z8KGF5aRPxLrQFu92Bt-M/edit?usp=sharing"

# Service Account Path Logic
_base_dir = os.path.dirname(os.path.abspath(__file__)) # email_cleaner/
_local_path = os.path.join(os.path.dirname(_base_dir), "buzzscope_today_automation", "service_account.json")
_repo_path = os.path.join(_base_dir, "service_account.json")

if os.path.exists(_local_path):
    SERVICE_ACCOUNT_KEY = _local_path
elif os.path.exists(_repo_path):
    SERVICE_ACCOUNT_KEY = _repo_path
else:
    print(Fore.RED + "[!] Service account file not found.")
    sys.exit(1)

def run_sheet_audit():
    print(Fore.CYAN + "\n--- Connecting to Google Sheet ---\n")
    
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

    # Initialize Validators
    syntax_val = SyntaxValidator()
    mx_val = MXValidator()
    disp_val = DisposableValidator()

    results = []
    stats = {
        "total": 0,
        "valid": 0,
        "invalid_syntax": 0,
        "invalid_mx": 0,
        "disposable": 0,
        "typos_fixed": 0
    }

    print(f"\nScanning {len(records)} emails...")

    for row in records:
        email = str(row.get('Email', '')).strip()
        if not email: continue
        
        stats["total"] += 1
        
        # Step 1: Syntax
        is_syntax_valid, suggestion, err = syntax_val.validate(email)
        if not is_syntax_valid:
            if suggestion:
                status = "Typo"
                detail = f"Did you mean {suggestion}?"
                stats["typos_fixed"] += 1
            else:
                status = "Invalid Syntax"
                detail = err
                stats["invalid_syntax"] += 1
            
            results.append({"Email": email, "Status": status, "Detail": detail})
            continue

        # Step 2: Disposable
        is_not_disposable, err = disp_val.validate(email)
        if not is_not_disposable:
            stats["disposable"] += 1
            results.append({"Email": email, "Status": "Disposable", "Detail": "Risk: Burner Check"})
            print(Fore.YELLOW + f"   [!] Disposable: {email}")
            continue

        # Step 3: MX Record
        print(f"\r   Checking DNS: {email.split('@')[-1]}...", end="")
        is_mx_valid, err = mx_val.validate(email)
        if not is_mx_valid:
            stats["invalid_mx"] += 1
            results.append({"Email": email, "Status": "Dead Domain", "Detail": err})
            continue

        # Valid
        stats["valid"] += 1
        results.append({"Email": email, "Status": "Valid", "Detail": "Safe to send"})

    print("\n" + Fore.GREEN + "Scan Complete.")
    
    # Generate Report
    generate_report(stats, results, "sheet_audit_report.txt")

if __name__ == "__main__":
    run_sheet_audit()
