from email_bot.manager import get_template, import_leads_from_csv
from email_bot.database import get_db_connection
from email_bot.sender import send_email
from dotenv import load_dotenv
import os

# Override user just for this test
TEST_RECIPIENT = "mayank77a@gmail.com"

def test_send_to_me():
    load_dotenv()
    
    # Ensure we have data
    conn = get_db_connection()
    c = conn.cursor()
    lead = c.execute("SELECT * FROM leads LIMIT 1").fetchone()
    
    if not lead:
        print("[!] No leads in DB. Importing default...")
        conn.close()
        import_leads_from_csv("maps_scraper/leads_usa_maps.csv")
        conn = get_db_connection()
        lead = conn.cursor().execute("SELECT * FROM leads LIMIT 1").fetchone()
        
    conn.close()
    
    if not lead:
        print("[!] Still no leads found. verify CSV path.")
        return

    # Prepare context
    lead_dict = dict(lead)
    print(f"[i] Using lead data for: {lead_dict.get('company')} ({lead_dict.get('email')})")
    
    context = {
        'Name': lead_dict.get('name', ''),
        'Company': lead_dict.get('company', ''),
        'City': lead_dict.get('city', ''),
        'State': lead_dict.get('state', ''), 
        'Niche': lead_dict.get('niche', '')
    }
    
    # Get Template #0 (Initial)
    subject, body = get_template(0, context)
    
    print(f"\n[TEST] Sending to {TEST_RECIPIENT} (Spoofing lead {lead_dict.get('email')})")
    print(f"Subject: {subject}")
    # print(f"Body: {body}")
    
    # Force send
    success = send_email(TEST_RECIPIENT, subject, body, dry_run=False) # REAL SEND
    if success:
        print("[+] Test email sent successfully!")
    else:
        print("[!] Test email failed.")

if __name__ == "__main__":
    test_send_to_me()
