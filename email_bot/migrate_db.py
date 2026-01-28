import sqlite3
import os

DB_PATH = "email_bot.db"

def migrate():
    if not os.path.exists(DB_PATH):
        print("Database not found. analyzed database.py will create it with new schema.")
        return

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    # Check if column exists
    cursor = c.execute("PRAGMA table_info(leads)")
    columns = [row[1] for row in cursor.fetchall()]
    
    if "state" not in columns:
        print("Adding 'state' column to leads table...")
        try:
            c.execute("ALTER TABLE leads ADD COLUMN state TEXT")
            conn.commit()
            print("Migration successful.")
        except Exception as e:
            print(f"Migration failed: {e}")
    else:
        print("'state' column already exists.")
        
    conn.close()

if __name__ == "__main__":
    migrate()
