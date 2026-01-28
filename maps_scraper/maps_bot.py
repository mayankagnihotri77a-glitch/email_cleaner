import os
import time
import random
import json
import re
from playwright.sync_api import sync_playwright
from maps_scraper.sheet_manager import SheetManager

# Configuration
DEFAULT_SHEET_URL = "https://docs.google.com/spreadsheets/d/1CDomOmwx5ExqgHSabEneY_Z8KGF5aRPxLrQFu92Bt-M/edit?usp=sharing"

# Service Account Path Logic (Supports Local & GitHub Actions)
_base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) # email_cleaner/
_local_path = os.path.join(os.path.dirname(_base_dir), "buzzscope_today_automation", "service_account.json") # ../buzzscope/
_repo_path = os.path.join(_base_dir, "service_account.json") # ./service_account.json

if os.path.exists(_local_path):
    SERVICE_ACCOUNT_KEY = _local_path
else:
    SERVICE_ACCOUNT_KEY = _repo_path

class MapsScraper:
    def __init__(self, headless=False):
        self.headless = headless
        self.sheet_url = os.getenv("GOOGLE_SHEET_URL") or DEFAULT_SHEET_URL
        self.sheet_manager = SheetManager(SERVICE_ACCOUNT_KEY, self.sheet_url)
        self.existing_domains = self.sheet_manager.get_existing_domains()
        print(f"[i] Loaded {len(self.existing_domains)} existing domains to skip.")
        
        self.locations = self._load_json("locations.json")
        self.niches = self._load_file("niches.txt")
        self.status = self.sheet_manager.get_status()

    def _load_file(self, filename):
        path = os.path.join(os.path.dirname(os.path.abspath(__file__)), filename)
        with open(path, "r", encoding="utf-8") as f:
            return [line.strip() for line in f if line.strip()]

    def _load_json(self, filename):
        path = os.path.join(os.path.dirname(os.path.abspath(__file__)), filename)
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)

    def extract_email(self, page, website_url):
        """Visits the website to find an email address."""
        if not website_url or "http" not in website_url:
            return ""
        
        # Helper to extract email from content
        def find_emails_in_content(content):
            emails = set(re.findall(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}", content))
            return [e for e in emails if not e.endswith(('.png', '.jpg', '.gif', '.webp', '.svg', '.js', '.css'))]

        print(f"    -> Visiting {website_url} for email...")
        try:
            context = page.context
            site_page = context.new_page()
            
            try:
                # 1. Check Original URL
                site_page.goto(website_url, timeout=12000)
                time.sleep(1) # Allow dynamic content
                
                # Check Mailto links first (High confidence)
                try:
                    mailto = site_page.locator('a[href^="mailto:"]').first
                    if mailto.count() > 0:
                        href = mailto.get_attribute("href")
                        email = href.replace("mailto:", "").split("?")[0].strip()
                        if email:
                            print(f"    [+] Found mailto: {email}")
                            site_page.close()
                            return email
                except: pass

                # Regex on page content
                valid_emails = find_emails_in_content(site_page.content())
                if valid_emails:
                    print(f"    [+] Email found: {valid_emails[0]}")
                    site_page.close()
                    return valid_emails[0]
                
                # 2. Check "Contact" page
                try:
                    contact_link = site_page.get_by_text("Contact", exact=False).first
                    if contact_link.count() > 0:
                        contact_href = contact_link.get_attribute("href")
                        if contact_href:
                            # Handle relative URLs
                            if not contact_href.startswith("http"):
                                base_url = "/".join(website_url.split("/")[:3]) # http://domain.com
                                contact_href = base_url.rstrip("/") + "/" + contact_href.lstrip("/")
                            
                            print(f"    -> Checking Contact page: {contact_href}")
                            site_page.goto(contact_href, timeout=10000)
                            valid_emails = find_emails_in_content(site_page.content())
                            if valid_emails:
                                print(f"    [+] Email found on Contact: {valid_emails[0]}")
                                site_page.close()
                                return valid_emails[0]
                except: pass

                # 3. Check Root Domain (if we were on a deep link)
                # Simple logic: if path has > 1 slash after double slash, it might be deep
                # e.g. .com/store/location -> go to .com
                parts = website_url.split("/")
                if len(parts) > 3 and parts[3]: # http://domain.com/something
                    root_url = "/".join(parts[:3])
                    print(f"    -> Checking Root Domain: {root_url}")
                    site_page.goto(root_url, timeout=12000)
                    
                    # Mailto check on root
                    try:
                        mailto = site_page.locator('a[href^="mailto:"]').first
                        if mailto.count() > 0:
                            href = mailto.get_attribute("href")
                            email = href.replace("mailto:", "").split("?")[0].strip()
                            if email:
                                print(f"    [+] Found mailto on root: {email}")
                                site_page.close()
                                return email
                    except: pass
                    
                    valid_emails = find_emails_in_content(site_page.content())
                    if valid_emails:
                        print(f"    [+] Email found on Root: {valid_emails[0]}")
                        site_page.close()
                        return valid_emails[0]

            except Exception as e:
                # print(f"    [!] Website access failed: {e}")
                pass
            
            site_page.close()
        except:
            pass
            
        print("    [-] No email found.")
        return ""

    def run(self):
        last_niche = self.status.get("Last Niche", "")
        last_state = self.status.get("Last State", "")
        last_city = self.status.get("Last City", "")
        
        start_processing = False
        if not last_niche:
            start_processing = True # Start from beginning
            
        print(f"[i] Resuming from: Niche='{last_niche}', State='{last_state}', City='{last_city}'")

        total_leads_this_session = 0
        TARGET_LEADS = 100

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=self.headless)
            context = browser.new_context(
                viewport={'width': 1280, 'height': 800},
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            )
            page = context.new_page()

            for niche in self.niches:
                # Resume Logic: Skip niches until we reach the last one
                if not start_processing:
                    if niche != last_niche:
                        continue
                        
                for state, cities in self.locations.items():
                    # Resume Logic: Inside the target niche, skip states until we reach last state
                    if not start_processing:
                        if niche == last_niche and state != last_state and last_state in self.locations:
                             # Only skip if last_state is valid and we haven't reached it
                             continue

                    for city in cities:
                        # Resume Logic: Inside target state, skip cities
                        if not start_processing:
                            if niche == last_niche and state == last_state and city != last_city:
                                continue
                            else:
                                start_processing = True # Found the resume point!
                        
                        # Verify we are processing
                        if not start_processing: continue

                        if total_leads_this_session >= TARGET_LEADS:
                            print(f"[i] Target reached ({TARGET_LEADS} leads). Stopping.")
                            
                            # Calculate Stats for Telegram
                            success_cnt = len([d for d in self.existing_domains if "@" in str(d)]) # Rough fix, better to track session emails
                            # Better: Get from sheet status or track locally. 
                            # Let's track locally for this session report
                            
                            msg = f"🗺️ **Maps Scraper Finished**\n" \
                                  f"- Leads Found Today: {total_leads_this_session}\n" \
                                  f"- Location: {city}, {state}\n" \
                                  f"- Niche: {niche}"
                                  
                            from telegram_notifier import send_telegram_message
                            send_telegram_message(msg)
                            
                            browser.close()
                            return

                        print(f"\n--- Searching: {niche} in {city}, {state} ---")
                        try:
                            # Pass session stats tracker if needed, for now just scraping
                            added, emails_found = self.scrape_niche_in_city(page, city, state, niche)
                            total_leads_this_session += added
                            
                            # Update status after every city
                            self.sheet_manager.update_status("Last Niche", niche)
                            self.sheet_manager.update_status("Last State", state)
                            self.sheet_manager.update_status("Last City", city)
                            self.sheet_manager.update_status("Leads Found Today", total_leads_this_session) 
                        except Exception as e:
                            print(f"[!] Error processing {niche} in {city}: {e}")
                        
                        # Pause between cities
                        time.sleep(random.uniform(2, 5))

            browser.close()
            
            # End of loop report
            msg = f"🗺️ **Maps Scraper Session Ended**\n" \
                  f"- Leads Found: {total_leads_this_session}\n" \
                  f"- Last: {last_city}, {last_state}"
            from telegram_notifier import send_telegram_message
            send_telegram_message(msg)

    def scrape_niche_in_city(self, page, city, state, niche):
        query = f"{niche} in {city}, {state}"
        page.goto(f"https://www.google.com/maps/search/{query.replace(' ', '+')}", timeout=60000)
        
        try:
            page.wait_for_selector('div[role="feed"]', timeout=10000)
        except:
            print("[!] No results feed found.")
            return 0

        feed_selector = 'div[role="feed"]'
        print("[i] Scrolling for results...")
        for _ in range(5): 
            page.hover(feed_selector)
            page.mouse.wheel(0, 5000)
            time.sleep(2)
        
        links = page.locator('div[role="feed"] > div > div > a').all()
        print(f"[i] Found {len(links)} potential items.")
        
        count_added = 0
        emails_found_count = 0
        for link in links:
            href = link.get_attribute("href")
            if not href or "/maps/place/" not in href:
                continue
            
            company_name = link.get_attribute("aria-label")
            if not company_name:
                continue

            try:
                link.scroll_into_view_if_needed()
                link.click(force=True)
                
                try:
                    page.wait_for_url(lambda u: "/maps/place/" in u, timeout=5000)
                    time.sleep(1.5)
                except:
                    continue
                
                # Extract Website
                website = ""
                try:
                    website_btn = page.locator('a[data-item-id="authority"]')
                    if website_btn.count() > 0:
                        website = website_btn.first.get_attribute("href")
                except:
                    pass
                
                if website:
                    if website in self.existing_domains:
                        print(f"[-] Skipping existing domain: {website}")
                        continue
                    
                    # EXTRACT EMAIL
                    email = self.extract_email(page, website)
                    if email: emails_found_count += 1
                    
                    lead = {
                        "Company": company_name,
                        "State": state,
                        "City": city,
                        "Niche": niche,
                        "Website": website,
                        "Email": email,
                        "Source": "Google Maps"
                    }
                    self.sheet_manager.add_lead(lead)
                    self.existing_domains.add(website)
                    count_added += 1
                    print(f"[+] Added: {company_name} ({email})")
                    
            except Exception as e:
                pass
                
            if count_added >= 5: 
                break
        
        print(f"[i] Added {count_added} leads from {city}.")
        return count_added, emails_found_count

if __name__ == "__main__":
    scraper = MapsScraper(headless=True)
    scraper.run()
