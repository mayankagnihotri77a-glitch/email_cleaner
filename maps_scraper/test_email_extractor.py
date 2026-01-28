from playwright.sync_api import sync_playwright
import re

def extract_email(page, website_url):
    print(f"Visiting {website_url}...")
    try:
        page.goto(website_url, timeout=15000)
        content = page.content()
        emails = set(re.findall(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}", content))
        valid_emails = [e for e in emails if not e.endswith(('.png', '.jpg', '.gif', '.webp'))]
        
        if valid_emails:
            print(f"FOUND: {valid_emails[0]}")
            return
        
        print("Not found on home, checking contact...")
        try:
            contact_link = page.get_by_text("Contact", exact=False).first
            if contact_link.count() > 0:
                contact_href = contact_link.get_attribute("href")
                if contact_href:
                    if not contact_href.startswith("http"):
                         contact_href = website_url.rstrip("/") + "/" + contact_href.lstrip("/")
                    
                    print(f"Visiting Contact: {contact_href}")
                    page.goto(contact_href, timeout=10000)
                    content = page.content()
                    emails = set(re.findall(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}", content))
                    valid_emails = [e for e in emails if not e.endswith(('.png', '.jpg', '.gif', '.webp'))]
                    if valid_emails:
                        print(f"FOUND on Contact: {valid_emails[0]}")
                        return
        except Exception as e:
            print(f"Contact nav error: {e}")
            
    except Exception as e:
        print(f"Error: {e}")

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()
    # Test on a site likely to have an email
    extract_email(page, "https://www.urbanoutfitters.com") # Might be hard, large retailer
    extract_email(page, "https://thetailorynyc.com/") # From previous run
    browser.close()
