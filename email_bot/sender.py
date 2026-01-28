import smtplib
import ssl
import os
import random
import re
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dotenv import load_dotenv

load_dotenv()

SMTP_SERVER = os.getenv("SMTP_SERVER", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", 587))
EMAIL_USER = os.getenv("EMAIL_USER")
EMAIL_PASS = os.getenv("EMAIL_PASS")

def spintax(text):
    """
    Parses {A|B|C} spintax and returns a random variation.
    Example: "{Hello|Hi|Hey} there" -> "Hi there"
    """
    pattern = r"\{([^{}]+)\}"
    while True:
        match = re.search(pattern, text)
        if not match:
            break
        options = match.group(1).split("|")
        choice = random.choice(options)
        text = text[:match.start()] + choice + text[match.end():]
    return text

def send_email(to_email, subject, body_html, dry_run=False):
    """
    Sends an individual email via SMTP.
    Returns True if successful, False otherwise.
    """
    # 1. Process Spintax
    final_subject = spintax(subject)
    final_body = spintax(body_html)
    
    if dry_run:
        print(f"\n[DRY RUN] Would send to: {to_email}")
        print(f"Subject: {final_subject}")
        print(f"Body Preview: {final_body[:100]}...")
        return True

    if not EMAIL_USER or not EMAIL_PASS:
        print("[!] Error: EMAIL_USER or EMAIL_PASS not set in .env")
        return False

    msg = MIMEMultipart()
    msg["From"] = EMAIL_USER
    msg["To"] = to_email
    msg["Subject"] = final_subject
    msg.attach(MIMEText(final_body, "html"))

    try:
        context = ssl.create_default_context()
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls(context=context)
            server.login(EMAIL_USER, EMAIL_PASS)
            server.sendmail(EMAIL_USER, to_email, msg.as_string())
        
        print(f"[+] Sent email to {to_email}")
        return True
    
    except Exception as e:
        print(f"[!] Failed to send to {to_email}: {e}")
        return False

if __name__ == "__main__":
    # Test
    print(spintax("{Hello|Hi|Hey} World, this is a {test|demo|experiment}."))
