import requests
from bs4 import BeautifulSoup
import argparse
import time
import random
from duckduckgo_search import DDGS

def search_directory_leads(niche="email marketing agencies"):
    """
    Search Clutch/GoodFirms via DuckDuckGo to find profile pages, 
    then extract websites. 
    Direct crawling of Clutch is often blocked by Cloudflare, 
    so we use Search Engine Result Pages (SERP) to find the agencies directly.
    """
    query = f"site:clutch.co {niche}"
    print(f"[*] Searching Directory (Clutch via DDG): '{query}'")
    
    leads = []
    
    try:
        with DDGS() as ddgs:
            results = ddgs.text(query, max_results=20)
            
            for r in results:
                title = r.get('title', '')
                url = r.get('href', '')
                snippet = r.get('body', '')
                
                # We want the AGENCY website, not the Clutch profile URL.
                # But Clutch profiles usually link to the website.
                # Scraping Clutch profile directly might be blocked.
                
                # Strategy 2: Use the title to guess the brand and search for THEIR site.
                # "Top Email Marketing Company - [Agency Name]"
                
                agency_name = title.split("-")[0].strip()
                if "Clutch" in agency_name: 
                    # Try other side of hyphen
                    parts = title.split("-")
                    if len(parts) > 1:
                        agency_name = parts[0].strip()
                
                # Check for " Reviews "
                agency_name = agency_name.replace(" Reviews", "").replace("Clutch.co", "").strip()
                
                if agency_name:
                    leads.append({
                        'Agency': agency_name,
                        'Source': 'Clutch',
                        'Profile': url
                    })

    except Exception as e:
        print(f"[!] Directory Search Error: {e}")
        
    return leads

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--niche", default="email marketing agencies", help="Niche to search for")
    args = parser.parse_args()
    
    leads = search_directory_leads(args.niche)
    print(f"Found {len(leads)} agencies on Clutch (via Search):")
    for l in leads:
        print(f"- {l['Agency']} ({l['Profile']})")
