import csv
import time
import re
import random
import os
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# --- CONFIGURATION ---
OUTPUT_FILE = "leads_automated.csv"
QUERIES_FILE = "lead_scraper/search_queries.txt"
SAFE_DELAY = (5, 10) # Seconds to sleep between actions (Min, Max)

def get_random_delay():
    return random.uniform(SAFE_DELAY[0], SAFE_DELAY[1])

def extract_email_from_text(text):
    if not text: return None
    match = re.search(r'[\w\.-]+@[\w\.-]+\.\w+', text)
    if match:
        email = match.group(0)
        # Block junk
        if email.lower().endswith(('png', 'jpg', 'gif', 'css', 'js', 'example.com')): return None
        # Block user self-reference
        if "mayank" in email.lower(): return None
        return email
    return None

def run_browser_bot():
    print("--- 🤖 Semi-Automated Browser Bot (Selenium) ---")
    print("[*] Launching Chrome... (Please wait)")
    
    # Setup Chrome
    options = webdriver.ChromeOptions()
    # options.add_argument("--headless") # Commented out so user can solve CAPTCHA
    options.add_argument("--start-maximized")
    options.add_argument("--disable-blink-features=AutomationControlled") 
    
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    
    try:
        # Load Queries
        if not os.path.exists(QUERIES_FILE):
            print(f"[!] Queries file not found: {QUERIES_FILE}")
            return
        
        with open(QUERIES_FILE, "r") as f:
            queries = [line.strip() for line in f if line.strip() and not line.startswith("#")]

        print(f"[*] Loaded {len(queries)} queries.")
        
        # Load existing emails
        existing_emails = set()
        if os.path.exists(OUTPUT_FILE):
            with open(OUTPUT_FILE, 'r', encoding='utf-8') as f:
                reader = csv.reader(f)
                next(reader, None)
                for row in reader: 
                    if row: existing_emails.add(row[1])

        for i, query in enumerate(queries):
            print(f"\n[{i+1}/{len(queries)}] Searching Google for: '{query}'")
            
            # Go to Google
            driver.get("https://www.google.com")
            time.sleep(get_random_delay())
            
            # Find search box
            search_box = driver.find_element(By.NAME, "q")
            search_box.clear()
            search_box.send_keys(query)
            search_box.send_keys(Keys.RETURN)
            
            # Wait for results
            time.sleep(5)
            
            # Check for CAPTCHA
            if "captcha" in driver.page_source.lower() or "unusual traffic" in driver.page_source.lower():
                print("\n[!] CAPTCHA DETECTED! Please solve it manually in the browser window.")
                input("Press Enter here in the terminal once you have solved it... ")
            
            # Scroll to load more results (The &num=100 trick is hard via selenium, scrolling is safer)
            print("   [i] Scrolling down to load results...")
            for _ in range(5):
                driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(2)
            
            # Extract Data
            results = driver.find_elements(By.CSS_SELECTOR, "div.g")

            # --- DEBUG BLOCK ---
            print(f"   [debug] Page Title: {driver.title}")
            
            # Check for common blockers
            page_src = driver.page_source.lower()
            if "sorry" in page_src and "robot" in page_src:
                print("   [!] BLOCK DETECTED: Google says 'Sorry... we think you are a robot'.")
            if "consent" in page_src and "agree" in page_src:
                print("   [!] CONSENT POPUP DETECTED: You might need to click 'I agree' manually.")

            print(f"   [debug] Found {len(results)} 'div.g' blocks.")
            
            if len(results) == 0:
                print("   [debug] Selector failed? Taking screenshot...")
                driver.save_screenshot("debug_error.png")
                with open("debug_source.html", "w", encoding="utf-8") as f:
                    f.write(driver.page_source)
                print("   [debug] Saved 'debug_error.png' and 'debug_source.html'. Check these files!")
                
                # Try generic H3 fallback
                results = driver.find_elements(By.TAG_NAME, "h3")
                print(f"   [debug] Found {len(results)} H3 tags (potential titles).")

            if len(results) > 0:
                 pass # We rely on the loop below if results exist or if H3 fallback worked (but H3 structure is diff)
            # -------------------

            found_in_query = 0
            
            # Logic if we are using the standard Div.g selector
            if len(driver.find_elements(By.CSS_SELECTOR, "div.g")) > 0:
                 results = driver.find_elements(By.CSS_SELECTOR, "div.g")
                 for res in results:
                    try:
                        full_text = res.text
                        email = extract_email_from_text(full_text)
                        
                        if email and email not in existing_emails:
                            try:
                                title = res.find_element(By.TAG_NAME, "h3").text
                            except:
                                title = "Unknown"
                            
                            try:
                                link = res.find_element(By.TAG_NAME, "a").get_attribute("href")
                            except:
                                link = ""

                            data = {
                                "Company": title,
                                "Email": email,
                                "Source": "Google (Selenium)",
                                "Link": link
                            }
                            
                            file_exists = os.path.exists(OUTPUT_FILE)
                            with open(OUTPUT_FILE, 'a', newline='', encoding='utf-8') as f:
                                writer = csv.DictWriter(f, fieldnames=["Company", "Email", "Source", "Link"])
                                if not file_exists: writer.writeheader()
                                writer.writerow(data)
                            
                            existing_emails.add(email)
                            found_in_query += 1
                            print(f"   [+] Found: {email}")
                    except:
                        continue
            
            # Fallback Loop for H3s if Div.g failed (Crude)
            elif len(driver.find_elements(By.TAG_NAME, "h3")) > 0:
                 print("   [i] Trying emergency H3 scanning...")
                 body_text = driver.find_element(By.TAG_NAME, "body").text
                 # Just scan the whole page text
                 found_emails = re.findall(r'[\w\.-]+@[\w\.-]+\.\w+', body_text)
                 for email in found_emails:
                     if "mayank" in email or "example" in email: continue
                     if email not in existing_emails:
                         
                         # Save to CSV
                         data = {
                            "Company": "Unknown (Text Scan)",
                            "Email": email,
                            "Source": "Google (Fallback)",
                            "Link": "N/A"
                         }
                         file_exists = os.path.exists(OUTPUT_FILE)
                         with open(OUTPUT_FILE, 'a', newline='', encoding='utf-8') as f:
                            writer = csv.DictWriter(f, fieldnames=["Company", "Email", "Source", "Link"])
                            if not file_exists: writer.writeheader()
                            writer.writerow(data)

                         print(f"   [+] Found (via text scan): {email}")
                         existing_emails.add(email)
                         found_in_query += 1

            print(f"   -> Extracted {found_in_query} new leads.")

            print(f"   -> Extracted {found_in_query} new leads.")
            time.sleep(get_random_delay())

    except Exception as e:
        print(f"\n[!] Browser Crash: {e}")
    finally:
        print("[*] Closing browser...")
        driver.quit()

if __name__ == "__main__":
    run_browser_bot()
