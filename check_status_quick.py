import sqlite3
import pandas as pd

conn = sqlite3.connect("email_bot.db")
try:
    sent_count = pd.read_sql("SELECT count(*) as count FROM leads WHERE emails_sent_count > 0", conn)['count'][0]
    total_leads = pd.read_sql("SELECT count(*) as count FROM leads", conn)['count'][0]
    print(f"Total Leads: {total_leads}")
    print(f"Emails Actually Sent: {sent_count}")
except Exception as e:
    print(e)
finally:
    conn.close()
