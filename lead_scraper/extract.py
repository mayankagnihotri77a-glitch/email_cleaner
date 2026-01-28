import os
import re
import csv
import argparse
from bs4 import BeautifulSoup

def extract_from_file(html_file):
    """
    Helper to parse a single file and return a list of lead dicts.
    """
    if not os.path.exists(html_file):
        return []

    leads = []
    try:
        with open(html_file, 'r', encoding='utf-8', errors='ignore') as f:
            soup = BeautifulSoup(f, 'html.parser')
    except Exception as e:
        print(f"[!] Error reading '{html_file}': {e}")
        return []

    # Strategy: Look for standard "g" class or robust containers
    results = soup.select('div.g') 
    
    for res in results:
        text_content = res.get_text(" ", strip=True)
        
        # 1. Extract Email
        email_match = re.search(r'[\w\.-]+@[\w\.-]+\.\w+', text_content)
        if not email_match:
            continue
        email = email_match.group(0)

        # 2. Extract Title / Name
        h3 = res.find('h3')
        full_title = h3.get_text(strip=True) if h3 else "Unknown"
        clean_title = full_title.split('- Instagram')[0].strip().split('...')[0].strip()

        # 3. Extract Instagram Handle
        link_tag = res.find('a')
        link = link_tag['href'] if link_tag else ""
        handle = "Unknown"
        if "instagram.com/" in link:
            parts = link.split('instagram.com/')
            if len(parts) > 1:
                handle = parts[1].split('/')[0]

        # 4. Company Name
        company = handle if handle != "Unknown" else clean_title

        leads.append({
            "Company": company,
            "Email": email,
            "Source Title": clean_title,
            "Instagram": link
        })
    
    # --- FALLBACK: If HTML parsing found nothing (likely MHTML), use Dirty Regex ---
    if len(leads) == 0:
        print(" (HTML parse failed, trying raw regex)...", end="")
        try:
            with open(html_file, 'r', encoding='utf-8', errors='ignore') as f:
                raw_text = f.read()
            
            # Simple Quoted-Printable cleanup if common in MHTML (e.g. =3D -> =)
            raw_text = raw_text.replace('=\n', '').replace('=3D', '=')
            
            # Regex for emails
            raw_emails = re.findall(r'[\w\.-]+@[\w\.-]+\.\w+', raw_text)
            
            # Regex for Instagram handles (e.g. instagram.com/brandname)
            # We map handles to the list of emails we found heuristically
            raw_handles = re.findall(r'instagram\.com/([A-Za-z0-9_.]+)', raw_text)
            fallback_handle = raw_handles[0] if raw_handles else "Unknown"

            for i, email in enumerate(raw_emails):
                # Basic filter to avoid junk like "w3.org" or image extensions
                if email.lower().endswith(('png', 'jpg', 'gif', 'css', 'js')): continue
                if "example.com" in email: continue
                # MHTML artifact filters
                if "mhtml.blink" in email: continue
                if email.startswith("css-"): continue
                
                # Exclude User's Own Emails (Logged in session)
                if "mayanknibi6" in email: continue
                if "mayank.legalgrowth" in email: continue
                if "mayankagnihotri" in email: continue

                # Try to assign a unique handle if possible, else reuse or generic
                # (Raw regex on MHTML loses the connection between Email <-> Handle, so this is a best guess)
                guess_handle = raw_handles[i] if i < len(raw_handles) else fallback_handle
                
                leads.append({
                    "Company": guess_handle if guess_handle != "Unknown" else "Extracted from MHTML",
                    "Email": email,
                    "Source Title": "Raw Search Result (MHTML)",
                    "Instagram": f"https://instagram.com/{guess_handle}" if guess_handle != "Unknown" else "Unknown"
                })
        except Exception as e:
            print(f" [!] Regex failed: {e}")

    return leads

def main():
    parser = argparse.ArgumentParser(description="Google Search -> Lead List Scraper")
    parser.add_argument("input_path", help="Path to an HTML file OR a folder containing HTML files")
    parser.add_argument("--output", default="leads.csv", help="Output CSV filename")
    args = parser.parse_args()

    all_leads = []
    files_to_process = []

    # 1. Determine input source
    if os.path.isdir(args.input_path):
        print(f"[*] Scanning folder '{args.input_path}' for HTML/MHTML files...")
        for root, dirs, files in os.walk(args.input_path):
            for file in files:
                if file.lower().endswith(('.html', '.htm', '.mhtml')):
                    files_to_process.append(os.path.join(root, file))
    else:
        files_to_process.append(args.input_path)

    if not files_to_process:
        print("[!] No HTML/MHTML files found to process.")
        return

    # 2. Process all files
    print(f"[*] Processing {len(files_to_process)} files...")
    for fpath in files_to_process:
        print(f"    -> Parsing '{os.path.basename(fpath)}'...", end="")
        file_leads = extract_from_file(fpath)
        print(f" Found {len(file_leads)}")
        all_leads.extend(file_leads)

    # 3. Deduplicate (Global)
    total_found = len(all_leads)
    unique_leads = {l['Email']: l for l in all_leads}.values()
    
    print(f"\n--- STATS ---")
    print(f"Total Lines Scanned: {total_found}")
    print(f"Duplicates Removed:  {total_found - len(unique_leads)}")
    print(f"Unique Leads Final:  {len(unique_leads)}")

    # 4. Save
    if unique_leads:
        with open(args.output, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=["Company", "Email", "Source Title", "Instagram"])
            writer.writeheader()
            writer.writerows(unique_leads)
        print(f"\n[OK] Saved {len(unique_leads)} unique leads to '{args.output}'")
        print("     -> Open this CSV in Excel or Google Sheets.")
    else:
        print("\n[!] No leads found in any of the files.")
        print("     Tip: If using MHTML, ensure the file contains text content.")

if __name__ == "__main__":
    main()
