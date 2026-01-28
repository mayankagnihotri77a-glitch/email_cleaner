import sqlite3
import datetime
import os

DB_PATH = "email_bot.db"

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    c = conn.cursor()
    
    # Leads Table
    c.execute('''
        CREATE TABLE IF NOT EXISTS leads (
            email TEXT PRIMARY KEY,
            name TEXT,
            company TEXT,
            city TEXT,
            state TEXT,
            niche TEXT,
            status TEXT DEFAULT 'PENDING', -- PENDING, SENT, REPLIED, BOUNCED, STOPPED
            campaign_id TEXT,
            last_contact_date DATE,
            next_followup_date DATE,
            emails_sent_count INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Sent Logs (History)
    c.execute('''
        CREATE TABLE IF NOT EXISTS email_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT,
            subject TEXT,
            body TEXT,
            sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (email) REFERENCES leads (email)
        )
    ''')

    conn.commit()
    conn.close()
    print("[+] Database initialized successfully.")

def add_lead(lead_dict):
    """
    Adds a lead if not exists.
    lead_dict: {'Email': '...', 'Company': '...', ...}
    """
    conn = get_db_connection()
    c = conn.cursor()
    
    try:
        c.execute('''
            INSERT OR IGNORE INTO leads (email, name, company, city, state, niche, status, next_followup_date)
            VALUES (?, ?, ?, ?, ?, ?, 'PENDING', ?)
        ''', (
            lead_dict.get('Email'),
            lead_dict.get('Company'), # Using Company as name if name missing
            lead_dict.get('Company'),
            lead_dict.get('City'),
            lead_dict.get('State'),
            lead_dict.get('Niche'),
            datetime.date.today() # Ready to send immediately
        ))
        conn.commit()
        return c.rowcount # Returns 1 if added, 0 if existed
    except Exception as e:
        print(f"[!] Error adding lead {lead_dict.get('Email')}: {e}")
        return 0
    finally:
        conn.close()

def get_leads_to_mail(limit=10, stage_filter=None):
    """
    Returns leads pending to send.
    stage_filter: If set (int), only returns leads with this specific emails_sent_count.
    """
    conn = get_db_connection()
    c = conn.cursor()
    
    today = datetime.date.today()
    
    # Base Query
    query = '''
        SELECT * FROM leads 
        WHERE status NOT IN ('REPLIED', 'STOPPED', 'BOUNCED')
        AND (next_followup_date IS NULL OR next_followup_date <= ?)
    '''
    params = [today]
    
    # Add Stage Filter
    if stage_filter is not None:
        query += " AND emails_sent_count = ?"
        params.append(stage_filter)
        
    query += " ORDER BY last_contact_date ASC LIMIT ?"
    params.append(limit)
    
    leads = c.execute(query, tuple(params)).fetchall()
    conn.close()
    return [dict(lead) for lead in leads]

def mark_sent(email, subject, body):
    conn = get_db_connection()
    c = conn.cursor()
    
    today = datetime.date.today()
    
    # Logic: If count=0 -> set next followup +3 days
    # If count=1 -> set next followup +7 days
    # If count=2 -> set next followup +14 days
    # If count>=3 -> set status STOPPED (Finished sequence)
    
    # First get current count
    curr = c.execute("SELECT emails_sent_count FROM leads WHERE email=?", (email,)).fetchone()
    count = curr['emails_sent_count'] if curr else 0
    
    new_status = 'SENT'
    next_date = None
    
    if count == 0:
        next_date = today + datetime.timedelta(days=3)  # Day 3
    elif count == 1:
        next_date = today + datetime.timedelta(days=3)  # Day 6 (3+3)
    elif count == 2:
        next_date = today + datetime.timedelta(days=4)  # Day 10 (6+4)
    elif count == 3:
        next_date = today + datetime.timedelta(days=4)  # Day 14 (10+4)
    elif count == 4:
        next_date = today + datetime.timedelta(days=4)  # Day 18 (14+4)
    else:
        new_status = 'STOPPED' # End of campaign
        next_date = None
        
    c.execute('''
        UPDATE leads 
        SET status = ?, 
            last_contact_date = ?, 
            next_followup_date = ?,
            emails_sent_count = emails_sent_count + 1
        WHERE email = ?
    ''', (new_status, today, next_date, email))
    
    # Log it
    c.execute('''
        INSERT INTO email_logs (email, subject, body) VALUES (?, ?, ?)
    ''', (email, subject, body))
    
    conn.commit()
    conn.close()

def mark_replied(email):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("UPDATE leads SET status='REPLIED', next_followup_date=NULL WHERE email=?", (email,))
    conn.commit()
    conn.close()
    print(f"[!] Marked {email} as REPLIED. Stopped follow-ups.")
