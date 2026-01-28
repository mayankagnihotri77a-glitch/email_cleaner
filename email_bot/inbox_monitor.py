import imaplib
import email
from email.header import decode_header
import os
import re
from dotenv import load_dotenv
from email_bot.database import mark_replied, get_db_connection

load_dotenv()

IMAP_SERVER = os.getenv("IMAP_SERVER", "imap.gmail.com")
EMAIL_USER = os.getenv("EMAIL_USER")
EMAIL_PASS = os.getenv("EMAIL_PASS")

def check_for_replies():
    """
    Connects to IMAP, looks for recent emails, and checks if they are from our leads.
    If match found, marks lead as REPLIED.
    """
    if not EMAIL_USER or not EMAIL_PASS:
        print("[!] Credentials missing.")
        return

    try:
        mail = imaplib.IMAP4_SSL(IMAP_SERVER)
        mail.login(EMAIL_USER, EMAIL_PASS)
        mail.select("inbox")
        
        # Search for all emails (or optimize to search UNSEEN)
        # For simplicity in this bot, we search recent 50 emails to catch everything
        status, messages = mail.search(None, "ALL")
        email_ids = messages[0].split()
        
        # Look at last 50 emails
        recent_ids = email_ids[-50:] if len(email_ids) > 50 else email_ids
        
        print(f"[i] Checking last {len(recent_ids)} emails for replies...")
        
        conn = get_db_connection()
        c = conn.cursor()
        
        # Get list of tracked emails to compare against
        # Only care about people we actually sent pending emails to
        tracked_leads = [row['email'].lower() for row in c.execute("SELECT email FROM leads WHERE status IN ('SENT', 'PENDING')").fetchall()]
        conn.close()
        
        if not tracked_leads:
            print("[i] No active leads to check replies for.")
            mail.logout()
            return

        for e_id in reversed(recent_ids):
            _, msg_data = mail.fetch(e_id, "(RFC822)")
            for response_part in msg_data:
                if isinstance(response_part, tuple):
                    msg = email.message_from_bytes(response_part[1])
                    
                    # Decode sender
                    from_header = msg.get("From")
                    sender_email = ""
                    if "<" in from_header:
                        sender_email = from_header.split("<")[1].split(">")[0]
                    else:
                        sender_email = from_header
                    
                    sender_email = sender_email.strip().lower()
                    
                    # Check match
                    if sender_email in tracked_leads:
                        print(f"[!!!!] REPLY DETECTED from: {sender_email}")
                        mark_replied(sender_email)
                        
        mail.close()
        mail.logout()
        
    except Exception as e:
        print(f"[!] IMAP Error: {e}")

if __name__ == "__main__":
    check_for_replies()
