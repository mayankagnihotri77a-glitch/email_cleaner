import argparse
import json
import csv
from dork_search import dork_hunt
from site_crawler import crawl_site
from whois_lookup import get_whois_emails
from directory_scraper import search_directory_leads # Optional integration
from urllib.parse import urlparse

def smart_hunt(domain):
    print(f"\n[{domain}] --- Starting Smart Hunt ---")
    all_emails = []
    
    # 1. Dork Search (The "free database" trick)
    # site:domain.com "ceo" email
    print("\n[Method 1] Google/DDG Dorks...")
    dork_results = dork_hunt(domain)
    all_emails.extend(dork_results)
    
    # 2. Site Crawl (The "deep dive")
    # About/Team pages
    print("\n[Method 2] Site Crawl...")
    crawl_results = crawl_site(domain)
    all_emails.extend(crawl_results)
    
    # 3. WHOIS (The "owner registration" check)
    print("\n[Method 3] WHOIS Lookup...")
    whois_emails = get_whois_emails(domain)
    for email in whois_emails:
        all_emails.append({
            'source': 'WHOIS',
            'url': domain,
            'email': email,
            'role': 'Domain Registrant (Likely Owner)'
        })
        
    return all_emails

def batch_hunt_agencies(niche):
    print(f"[*] Starting Batch Hunt for: {niche}")
    # 1. Find Agencies via Directory Scraper
    agencies = search_directory_leads(niche)
    print(f"[*] Found {len(agencies)} potential agencies to hunt.")
    
    final_data = []
    
    for agency in agencies:
        name = agency['Agency']
        print(f"\n--- Hunting: {name} ---")
        
        # 2. Find Domain?
        # We only have name from directory scraper. Need to search domain.
        # Quick hack: use dork_search.py logic or just guess
        # Let's Skip this for now or implement a "find_domain" helper?
        # For this MVP, let's just create a placeholder
        pass 
        
    return final_data

def save_csv(data, filename="smart_leads.csv"):
    if not data:
        print("[!] No data to save.")
        return
        
    # Flatten
    # data is list of dicts: source, email, role...
    
    unique = {}
    for item in data:
        email = item['email']
        if email not in unique:
            unique[email] = item
            
    with open(filename, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=['email', 'role', 'source', 'url', 'query', 'title'])
        writer.writeheader()
        for item in unique.values():
            # filter keys to match fieldnames
            clean = {k: item.get(k, '') for k in ['email', 'role', 'source', 'url', 'query', 'title']}
            writer.writerow(clean)
    
    print(f"[+] Saved {len(unique)} leads to {filename}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--domain", help="Single domain to hunt (e.g. stripe.com)")
    parser.add_argument("--output", default="smart_leads.csv")
    args = parser.parse_args()
    
    if args.domain:
        results = smart_hunt(args.domain)
        print(f"\n[Summary] Found {len(results)} emails.")
        for r in results:
            print(f"- {r['email']} ({r['role']}) via {r['source']}")
            
        save_csv(results, args.output)
    else:
        print("Usage: python smart_hunt.py --domain example.com")
