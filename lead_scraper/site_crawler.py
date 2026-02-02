import requests
from bs4 import BeautifulSoup
import re
import argparse
from urllib.parse import urljoin, urlparse

# Common headers to look like a browser
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
}

def get_soup(url):
    try:
        resp = requests.get(url, headers=HEADERS, timeout=10)
        if resp.status_code == 200:
            return BeautifulSoup(resp.text, 'html.parser')
    except Exception as e:
        # print(f"[!] Error fetching {url}: {e}")
        pass
    return None

def extract_emails_from_text(text):
    raw = re.findall(r'[\w\.-]+@[\w\.-]+\.\w+', text)
    valid = []
    for email in raw:
        email = email.lower()
        if email.endswith(('png','jpg','jpeg','gif','css','js')): continue
        if email in ['example.com', 'email.com', 'domain.com']: continue
        valid.append(email)
    return list(set(valid))

def crawl_site(start_url):
    print(f"[*] Crawling: {start_url}")
    
    if not start_url.startswith("http"):
        start_url = "https://" + start_url
        
    domain = urlparse(start_url).netloc
    
    soup = get_soup(start_url)
    if not soup:
        print("[!] Could not access homepage.")
        return []
    
    # 1. Check Homepage
    found_emails = []
    found_emails.extend(extract_emails_from_text(soup.get_text()))
    
    # 2. Find Interesting Links (About, Team, Contact)
    interesting_keywords = ['about', 'team', 'staff', 'people', 'leadership', 'contact']
    to_visit = set()
    
    for a in soup.find_all('a', href=True):
        href = a['href']
        full_url = urljoin(start_url, href)
        
        # Ensure internal link
        if domain in urlparse(full_url).netloc:
            # Check keywords in URL text or href
            link_text = a.get_text().lower()
            url_lower = full_url.lower()
            
            for kw in interesting_keywords:
                if kw in link_text or kw in url_lower:
                    to_visit.add(full_url)
                    break
    
    # Limit visits to avoid getting banned or wasting time
    max_pages = 5
    print(f"[*] Found {len(to_visit)} potential lead pages. Visiting top {max_pages}...")
    
    for url in list(to_visit)[:max_pages]:
        # print(f"    -> Visiting {url}")
        sub_soup = get_soup(url)
        if sub_soup:
            found_emails.extend(extract_emails_from_text(sub_soup.get_text()))
            
    # Dedupe
    unique_emails = list(set(found_emails))
    
    # Identify roles nearby (Simple heuristic)
    # This is hard to do perfectly without NLP, but we return the raw list for now.
    
    results = []
    for email in unique_emails:
        results.append({
            'source': 'Site Crawl',
            'url': start_url,
            'email': email,
            'role': 'Website Scrape'
        })
        
    return results

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("url", help="URL to scan")
    args = parser.parse_args()
    
    res = crawl_site(args.url)
    print(res)
