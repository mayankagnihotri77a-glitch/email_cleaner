import argparse
import time
import re
from duckduckgo_search import DDGS
import json

def search_companies_leads(query, max_results=20):
    """
    Uses DuckDuckGo to search for leads based on a dork.
    """
    print(f"[*] Searching: '{query}'")
    results = []
    
    try:
        with DDGS() as ddgs:
            # backend='api' is usually faster / more direct
            ddg_gen = ddgs.text(query, max_results=max_results)
            
            for r in ddg_gen:
                title = r.get('title', '')
                snippet = r.get('body', '')
                url = r.get('href', '')
                
                # Extract emails from snippet
                emails = extract_emails(snippet + " " + title)
                
                if emails:
                    for email in emails:
                        results.append({
                            'source': 'DuckDuckGo',
                            'query': query,
                            'title': title,
                            'url': url,
                            'email': email,
                            'role': detect_role(snippet, title)
                        })
    except Exception as e:
        print(f"[!] Search error: {e}")
        
    return results

def extract_emails(text):
    # Regex to find emails
    # Filter out common junk
    raw = re.findall(r'[\w\.-]+@[\w\.-]+\.\w+', text)
    valid = []
    for email in raw:
        email = email.lower()
        if email.endswith(('png','jpg','jpeg','gif','css','js')): continue
        if email in ['example.com', 'email.com', 'domain.com']: continue
        valid.append(email)
    return list(set(valid))

def detect_role(text, title):
    content = (text + " " + title).lower()
    if 'ceo' in content or 'founder' in content or 'owner' in content:
        return 'Decision Maker (CEO/Founder)'
    if 'marketing' in content:
        return 'Marketing'
    return 'Unknown'

def dork_hunt(domain):
    """
    Runs specific strategies for a single domain.
    """
    strategies = [
        f'site:{domain} "email"',
        f'site:{domain} "founder" OR "ceo" OR "owner"',
        f'site:{domain} "marketing" email'
    ]
    
    found_leads = []
    for strat in strategies:
        leads = search_companies_leads(strat, max_results=10)
        found_leads.extend(leads)
        # Sleep slightly to be nice
        time.sleep(1)
        
    return found_leads

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--domain", help="Target domain to hunt (e.g. stripe.com)")
    parser.add_argument("--query", help="Custom dork query")
    
    args = parser.parse_args()
    
    if args.domain:
        results = dork_hunt(args.domain)
    elif args.query:
        results = search_companies_leads(args.query)
    else:
        print("Provide --domain or --query")
        results = []
        
    print(json.dumps(results, indent=2))
