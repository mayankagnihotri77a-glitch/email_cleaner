import time
import random
import os
import pandas as pd
from dotenv import load_dotenv

from email_bot.database import init_db, add_lead, get_leads_to_mail, mark_sent, get_db_connection, mark_replied
from email_bot.sender import send_email
from email_bot.inbox_monitor import check_for_replies
import datetime
import sys

load_dotenv()

# Configuration
# Configuration
DAILY_LIMIT = 20
MIN_DELAY = 60
MAX_DELAY = 180
DRY_RUN = os.getenv("DRY_RUN", "True").lower() == "true"
YOUR_NAME = "Mayank Agnihotri"

# Templates List (Index 0 = Initial, 1..5 = Followups)
TEMPLATES = [
    # 0: Initial
    {
        "subjects": [
            "Quick question regarding {BusinessName}",
            "Start here",
            "{City} {Niche} inquiry",
            "{BusinessName} website feedback",
            "Saw your store on Google Maps",
            "Question about your Instagram feed"
        ],
        "body": """\
<p>Hi Team,</p>
<p>I was searching for <strong>{ConversationalNiche}</strong> in {City} and came across your site.</p>
<p>Quick question — do you know how clean your email list is right now?</p>
<p>I help teams quietly check lists before campaigns (fix bad emails, bounces, spam-risk).</p>
<p>Happy to run a free scan and share how many addresses might need improvement.</p>
<p>No pitch — just a quick report.</p>
<p>Worth checking?</p>
<p>Thanks,<br>
{YourName}</p>
"""
    },
    # 1: Follow-up 1
    {
        "subjects": [
            "Following up re: list health",
            "Did this get buried?",
            "Re: {BusinessName} email report"
        ],
        "body": """\
<p>Hi Team,</p>
<p>Just checking back — didn’t want this to get lost.</p>
<p>I can run a free email list health check for {BusinessName} and show:</p>
<ul>
    <li>invalid emails</li>
    <li>risky domains</li>
    <li>estimated bounce %</li>
</ul>
<p>No obligation at all.</p>
<p>Want me to take a look?</p>
<p>{YourName}</p>
"""
    },
    # 2: Follow-up 2
    {
        "subjects": [
            "One small thing hurting inbox rates",
            "About email bounces",
            "Quick heads-up on email lists"
        ],
        "body": """\
<p>Hi Team,</p>
<p>Most lists I check sit around 5–10% bad emails —<br>
that’s often enough to push campaigns into spam.</p>
<p>I’m offering a free scan to show exact numbers for {BusinessName}.</p>
<p>Should I run it?</p>
<p>– {YourName}</p>
"""
    },
    # 3: Follow-up 3
    {
        "subjects": [
            "Quick example from last week",
            "What we found for a similar brand",
            "Email list insight (30 seconds)"
        ],
        "body": """\
<p>Hi Team,</p>
<p>Last week I checked a list for a business similar to {BusinessName} —<br>
they found ~7% emails causing bounces.</p>
<p>They cleaned the list before sending and avoided inbox issues.</p>
<p>Happy to run the same free check for you.</p>
<p>Okay to proceed?</p>
<p>{YourName}</p>
"""
    },
    # 4: Follow-up 4
    {
        "subjects": [
            "Checking once more 🙂",
            "Still relevant?",
            "Should I close this?"
        ],
        "body": """\
<p>Hi Team,</p>
<p>Just checking once more —<br>
should I close the loop, or would a free list check be useful for {BusinessName}?</p>
<p>Either is totally fine.</p>
<p>Thanks!<br>
{YourName}</p>
"""
    },
    # 5: Follow-up 5 (Break-up)
    {
        "subjects": [
            "Last note from me",
            "Closing the loop",
            "I’ll pause here"
        ],
        "body": """\
<p>Hi Team,</p>
<p>I haven’t heard back, so I’ll pause after this.</p>
<p>If email deliverability or bounce rates ever become a concern at {BusinessName},<br>
happy to run a free list check anytime.</p>
<p>Wishing you strong campaigns ahead 🙌<br>
{YourName}</p>
"""
    }
]

def restore_state_from_sheet():
    """
    Downloads the Google Sheet and updates local DB state
    to reflect what has already been sent, avoiding duplicates.
    This enables stateless execution on GitHub Actions.
    """
    print("\n[Sync] Restoring state from Google Sheet...")
    
    # 1. Connect to Sheet
    try:
        # Resolve key path similar to other functions or pass explicitly
        # We need this to work in email_bot module context
        import os
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        key_path = os.path.join(base_dir, "buzzscope_today_automation", "service_account.json")
        if not os.path.exists(key_path):
             key_path = "service_account.json"
             
        from maps_scraper.sheet_manager import SheetManager
        sm = SheetManager(key_path, "https://docs.google.com/spreadsheets/d/1CDomOmwx5ExqgHSabEneY_Z8KGF5aRPxLrQFu92Bt-M/edit?usp=sharing")
        
        records = sm.email_worksheet.get_all_records()
        print(f"[Sync] Found {len(records)} rows in 'Leads with Email'. Processing...")
        
        conn = get_db_connection()
        c = conn.cursor()
        
        updated_count = 0
        
        for row in records:
            email = row.get("Email")
            if not email: continue
            
            # Determine existing stage from columns
            # Columns: Primary Mail, Follow Up 1, Follow Up 2...
            # If "Done 2024-..." is present, it's sent.
            
            # Count how many stages are filled
            sent_count = 0
            stages = ["Primary Mail", "Follow Up 1", "Follow Up 2", "Follow Up 3", "Follow Up 4", "Follow Up 5"]
            last_date_str = None
            
            for stage in stages:
                val = str(row.get(stage, "")).strip()
                if val and "Done" in val:
                    sent_count += 1
                    # Extract date if possible: "Done 2025-01-20"
                    parts = val.split(" ")
                    if len(parts) > 1:
                        last_date_str = parts[1]
            
            # Make sure lead exists in DB first
            # We create a dummy lead object to allow add_lead to work (or manual insert)
            # Use 'add_lead' logic but careful about overwriting? 
            # add_lead uses INSERT OR IGNORE, which is perfect.
            
            lead_data = {
                'Email': email,
                'Company': row.get('Company'),
                'City': row.get('City'),
                'State': row.get('State'),
                'Niche': row.get('Niche')
            }
            
            # Ensure it is in DB
            # Use raw SQL to be faster avoiding print loops of add_lead
            c.execute('''
                INSERT OR IGNORE INTO leads (email, company, city, state, niche, status, next_followup_date)
                VALUES (?, ?, ?, ?, ?, 'PENDING', ?)
            ''', (email, row.get('Company'), row.get('City'), row.get('State'), row.get('Niche'), datetime.date.today()))
            
            # Now Update State
            if sent_count > 0:
                # Update sent count and dates
                # If sent_count = 1 (Primary Done), next is F1 (Stage 1).
                # Logic in database.py for next_date is complex, let's approximation or just set what we know.
                # Crucially: We just need to ensure emails_sent_count is correct so we don't resend old stages.
                
                # If last_date_str is valid, parse it
                last_contact = datetime.date.today()
                if last_date_str:
                    try:
                        last_contact = datetime.datetime.strptime(last_date_str, "%Y-%m-%d").date()
                    except:
                        pass
                
                # Calculate next_followup based on simple logic to resume correctly?
                # Actually, if we are stateless, we rely on the scheduler to pick it up ONLY if date triggers.
                # For safety on restoration:
                # If sent_count=1 (Primary done), we want next follow up.
                # Let's rely on standard interval: +3 days from last contact.
                
                intervals = [3, 3, 4, 4, 4] # Same as mark_sent logic
                # 0->1 (+3)
                # 1->2 (+3)
                # 2->3 (+4)
                
                next_date = None
                if sent_count <= 5: # If 6 sent (0-5), it's done. 
                    # index 0 is interval for after Primary(0) -> so sent_count-1?
                    # Sent=1 (Primary). We want interval for F1.
                    # mark_sent logic: if count=0->+3.
                    # so if sent_count=1, the LAST action was stage 0.
                    # so we should add interval[0] to last_contact.
                    idx = sent_count - 1
                    if idx >= 0 and idx < len(intervals):
                        next_date = last_contact + datetime.timedelta(days=intervals[idx])
                
                status = 'SENT'
                if sent_count >= 6:
                    status = 'STOPPED'
                    next_date = None
                
                c.execute('''
                    UPDATE leads
                    SET emails_sent_count = ?,
                        last_contact_date = ?,
                        next_followup_date = ?,
                        status = ?
                    WHERE email = ?
                ''', (sent_count, last_contact, next_date, status, email))
                
                updated_count += 1
        
        conn.commit()
        conn.close()
        print(f"[Sync] restored state for {updated_count} leads.")
        
    except Exception as e:
        print(f"[!] Sync Failed: {e}")

def import_leads_from_csv(filepath):
    """Imports leads from the Maps Scraper CSV"""
    if not os.path.exists(filepath):
        print(f"[!] CSV not found: {filepath}")
        return
    
    try:
        df = pd.read_csv(filepath)
        count = 0
        for _, row in df.iterrows():
            if pd.isna(row.get('Email')) or not row.get('Email'):
                continue
            
            # Smart parsing of City/State from "City, StateCode"
            raw_city = str(row.get('City', ''))
            city_part = raw_city
            state_part = ""
            
            if "," in raw_city:
                parts = raw_city.split(",")
                city_part = parts[0].strip()
                if len(parts) > 1:
                    state_part = parts[1].strip()
            
            lead = {
                'Email': row.get('Email'),
                'Company': row.get('Company', 'there'),
                'City': city_part,
                'State': state_part,
                'Niche': row.get('Niche', 'your niche')
            }
            if add_lead(lead):
                count += 1
        print(f"[+] Imported {count} new leads from CSV.")
    except Exception as e:
        print(f"[!] Import error: {e}")

def get_template(count, context):
    """Returns (Subject, Body) based on sequence number"""
    if count < 0 or count >= len(TEMPLATES):
        return None, None
        
    template = TEMPLATES[count]
    
    # 1. Select Random Subject
    subject = random.choice(template["subjects"])
    body = template["body"]
    
    # 2. Add YourName to context
    context['YourName'] = YOUR_NAME
    
    # 3. Handle BusinessName alias
    if 'BusinessName' not in context:
        context['BusinessName'] = context.get('Company', 'your company')
    
    # 4. Handle Niche Conversational Format
    # "Clothing Brand" -> "clothing brands"
    # "Jewelry Store" -> "jewelry stores"
    raw_niche = context.get('Niche', 'businesses').lower()
    if raw_niche.endswith("y"):
        conv_niche = raw_niche[:-1] + "ies" # jewelry -> jewelries (maybe weird, but jewelry store -> jewelry stores works below)
    elif raw_niche.endswith("ss"):
        conv_niche = raw_niche + "es"
    elif not raw_niche.endswith("s"):
        conv_niche = raw_niche + "s"
    else:
        conv_niche = raw_niche
        
    # Better logic for known scrapers types if needed, but simple pluralizer works for MVP
    # Fix specific "Store" -> "Stores"
    if " store" in raw_niche and not raw_niche.endswith("s"):
         conv_niche = raw_niche + "s"
            
    context['ConversationalNiche'] = conv_niche

    # 5. Variable Replacement
    for key, val in context.items():
        placeholder = "{" + key + "}"
        subject = subject.replace(placeholder, str(val))
        body = body.replace(placeholder, str(val))
        
    return subject, body

def run_bot(stage_filter=None):
    print(f"--- COLD EMAIL BOT STARTING (Dry Run: {DRY_RUN}) ---")
    if stage_filter is not None:
        print(f"[i] Filter: Sending only Sequence #{stage_filter}")
    
    # 1. Init
    init_db()
    
    # NEW: Sync State from Sheet (Critical for GitHub)
    restore_state_from_sheet()
    
    # 2. auto-import from maps scraper output if exists (Local usage mainly)
    import_leads_from_csv("maps_scraper/leads_usa_maps.csv")
    
    # 3. Check for Repliers (Don't email them!)
    if not DRY_RUN:
        check_for_replies()
    
    # 4. Get Batch
    leads = get_leads_to_mail(limit=DAILY_LIMIT, stage_filter=stage_filter)
    print(f"[i] Found {len(leads)} leads scheduled for today.")
    
    sent_count = 0
    for lead in leads:
        email = lead['email']
        seq_count = lead['emails_sent_count']
        
        # Prepare Context
        context = {
            'Name': lead['name'].split()[0] if lead['name'] else "there",
            'Company': lead['company'],
            'City': lead['city'],
            'Niche': lead['niche']
        }
        
        # Get Template
        subj, body = get_template(seq_count, context)
        if not subj:
            print(f"[!] No template for seq {seq_count} (Lead: {email}). Skipping.")
            continue
            
        # Send
        print(f"[{sent_count+1}/{len(leads)}] Sending to {email} (Seq: {seq_count+1})...")
        success = send_email(email, subj, body, dry_run=DRY_RUN)
        
        if success:
            mark_sent(email, subj, body)
            sent_count += 1
            
            # Update Google Sheet
            try:
                # Lazy init or just init here?
                # Need SERVICE_ACCOUNT_KEY. It's in maps_scraper/maps_bot.py, let's grab relative path logic or Hardcode for now to be safe/fast
                # Assuming valid path exists
                import os
                key_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "buzzscope_today_automation", "service_account.json")
                if not os.path.exists(key_path):
                     # Fallback to local
                     key_path = "service_account.json"
                     
                from maps_scraper.sheet_manager import SheetManager
                sm = SheetManager(key_path, "https://docs.google.com/spreadsheets/d/1CDomOmwx5ExqgHSabEneY_Z8KGF5aRPxLrQFu92Bt-M/edit?usp=sharing")
                
                # Determine Stage Name
                stage_map = {0: "Primary Mail", 1: "Follow Up 1", 2: "Follow Up 2", 3: "Follow Up 3", 4: "Follow Up 4", 5: "Follow Up 5"}
                stage_name = stage_map.get(seq_count, "Unknown")
                
                sm.update_email_status(email, stage_name, f"Done {datetime.date.today()}")
            except Exception as e:
                print(f"[!] Sheet Update Failed: {e}")
            
            if not DRY_RUN:
                wait_time = random.randint(MIN_DELAY, MAX_DELAY)
                print(f"[i] Sleeping {wait_time}s...")
                time.sleep(wait_time)
        else:
            print("[!] Fail. Continuing...")

    print("--- BATCH COMPLETE ---")
    
    # TELEGRAM REPORT
    if sent_count > 0:
        msg = f"🚀 **Email Bot Report**\n" \
              f"- Filter/Stage: Sequence #{stage_filter if stage_filter is not None else 'ALL'}\n" \
              f"- Sent: {sent_count} emails\n" \
              f"- Errors: {len(leads) - sent_count}\n" \
              f"- Next Check: In ~1 hr (Scheduler)"
        from telegram_notifier import send_telegram_message
        send_telegram_message(msg)

if __name__ == "__main__":
    # Support Command Line Arguments
    # python -m email_bot.manager --sync-only
    # python -m email_bot.manager --stage 0
    
    args = sys.argv[1:]
    
    if "--sync-only" in args:
        init_db()
        restore_state_from_sheet()
        print("[Done] Sync complete.")
    else:
        stage = None
        if "--stage" in args:
            try:
                idx = args.index("--stage")
                stage = int(args[idx+1])
            except:
                print("[!] Invalid stage argument")
                
        run_bot(stage_filter=stage)
