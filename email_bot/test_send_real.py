from email_bot.sender import send_email
from email_bot.manager import get_template
import os
from dotenv import load_dotenv

load_dotenv()

TARGET_EMAIL = "mayank.legalgrowth@gmail.com"

def test_run():
    print(f"--- SENDING TEST EMAIL TO {TARGET_EMAIL} ---")
    
    # Mock Context
    context = {
        'Name': 'Mayank',
        'Company': 'Legal Growth',
        'City': 'New Delhi',
        'Niche': 'Legal Services'
    }
    
    # Get Template 1
    subj, body = get_template(0, context)
    
    print(f"Subject: {subj}")
    print("Sending...")
    
    # Force dry_run=False to actually send
    success = send_email(TARGET_EMAIL, subj, body, dry_run=False)
    
    if success:
        print("\n[SUCCESS] Check your inbox! (Also check Spam folder just in case)")
    else:
        print("\n[FAILED] Could not send. Check credentials.")

if __name__ == "__main__":
    test_run()
