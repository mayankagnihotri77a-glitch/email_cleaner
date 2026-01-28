import sqlite3

DB_PATH = "email_bot.db"

def reset_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    print("Resetting all leads to PENDING...")
    c.execute("UPDATE leads SET status='PENDING', emails_sent_count=0, last_contact_date=NULL, next_followup_date=DATE('now')")
    c.execute("DELETE FROM email_logs") # Clear logs too so dashboard looks clean
    
    conn.commit()
    conn.close()
    print("[+] Database reset complete. Ready for real sending.")

if __name__ == "__main__":
    reset_db()
