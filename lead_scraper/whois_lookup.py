import whois
import argparse
import sys

def get_whois_emails(domain):
    """
    Fetches WHOIS data and returns a list of unique emails found.
    """
    print(f"[*] Checking WHOIS for: {domain}")
    found_emails = []
    
    try:
        w = whois.whois(domain)
        
        # 'emails' can be a list or a string or None
        raw_emails = w.emails
        
        if raw_emails:
            if isinstance(raw_emails, list):
                found_emails.extend(raw_emails)
            else:
                found_emails.append(raw_emails)
        
        # Dedupe and clean
        cleaned = []
        for email in found_emails:
            email = email.lower().strip()
            # Filter out privacy guard emails if possible (optional)
            # define known privacy domains?
            # if "privacy" in email or "proxy" in email: continue
            cleaned.append(email)
            
        return list(set(cleaned))
        
    except Exception as e:
        print(f"[!] WHOIS failed: {e}")
        return []

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("domain", help="Domain to check")
    args = parser.parse_args()
    
    emails = get_whois_emails(args.domain)
    
    if emails:
        print(f"[+] Found emails: {emails}")
    else:
        print("[-] No emails found in WHOIS record.")
