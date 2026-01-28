import time
import datetime
import schedule
from email_bot.manager import run_bot

# IST Schedule Strategy
# ---------------------
# Day 0 (Seq 0) -> 8:30 PM IST (Initial)
# Day 3 (Seq 1) -> 9:00 PM IST (Follow-up 1)
# Day 6 (Seq 2) -> 1:30 AM IST (Follow-up 2 - Pro Window)
# Day 10 (Seq 3) -> 9:30 PM IST (Follow-up 3)
# Day 14 (Seq 4) -> 9:30 PM IST (Follow-up 4)
# Day 18 (Seq 5) -> 9:30 PM IST (Follow-up 5)

def job_initial():
    print("\n[Scheduler] Triggering INITIAL emails (Seq 0)...")
    try:
        run_bot(stage_filter=0)
    except Exception as e:
        print(f"[!] Job Error: {e}")

def job_followup_1():
    print("\n[Scheduler] Triggering FOLLOW-UP 1 (Seq 1)...")
    try:
        run_bot(stage_filter=1)
    except Exception as e:
        print(f"[!] Job Error: {e}")

def job_followup_2():
    print("\n[Scheduler] Triggering FOLLOW-UP 2 (Seq 2 - Pro Window)...")
    try:
        run_bot(stage_filter=2)
    except Exception as e:
        print(f"[!] Job Error: {e}")

def job_followup_3():
    print("\n[Scheduler] Triggering FOLLOW-UP 3 (Seq 3)...")
    try:
        run_bot(stage_filter=3)
    except Exception as e:
        print(f"[!] Job Error: {e}")
        
def job_followup_4():
    print("\n[Scheduler] Triggering FOLLOW-UP 4 (Seq 4)...")
    try:
        run_bot(stage_filter=4)
    except Exception as e:
        print(f"[!] Job Error: {e}")

def job_followup_5():
    print("\n[Scheduler] Triggering FOLLOW-UP 5 (Seq 5)...")
    try:
        run_bot(stage_filter=5)
    except Exception as e:
        print(f"[!] Job Error: {e}")

def simple_loop():
    print("--- SMART SCHEDULER STARTED (IST Loop) ---")
    print("Checking every minute for trigger times...")
    
    # Triggers (Hour, Minute) in 24h format
    triggers = [
        {"h": 20, "m": 30, "func": job_initial, "name": "Initial (Day 0)"},       # 8:30 PM
        {"h": 21, "m": 00, "func": job_followup_1, "name": "Followup-1 (Day 3)"}, # 9:00 PM
        {"h": 1,  "m": 30, "func": job_followup_2, "name": "Followup-2 (Day 6)"}, # 1:30 AM
        {"h": 21, "m": 30, "func": job_followup_3, "name": "Followup-3 (Day 10)"},# 9:30 PM
        {"h": 21, "m": 30, "func": job_followup_4, "name": "Followup-4 (Day 14)"},# 9:30 PM
        {"h": 21, "m": 30, "func": job_followup_5, "name": "Followup-5 (Day 18)"} # 9:30 PM
    ]
    
    last_run_key = None # To prevent double firing in same minute
    
    while True:
        now = datetime.datetime.now()
        
        # Check Day Validity (Mon-Thu) + maybe Sun night?
        # User said: Tue/Wed/Thu best. Mon okay. Fri Avoid.
        # Weekday: Mon=0 ... Sun=6.
        # So allow 0,1,2,3.
        # Special case: 1:30 AM on Friday morning (technically Thu night campaign) is okay?
        # Let's keep it simple: strict Mon-Thu for now.
        
        is_weekend = now.weekday() >= 4 # Fri, Sat, Sun
        
        # 1:30 AM usually belongs to 'previous night' conceptually.
        # if it is Fri 1:30 AM, it is technically following Thu night work. That sends.
        # if it is Sat 1:30 AM, that follows Fri night work. Fri avoided. So Stop.
        # So Fri 1:30 AM is OK. Sat/Sun/Mon 1:30 AM is BAD.
        
        # Logic:
        # If time > 18:00 (Evening), we check if today is Mon-Thu.
        # If time < 06:00 (Morning), we check if yesterday was Mon-Thu (so Today is Tue-Fri).
        
        allow_run = False
        if now.hour >= 18:
            if now.weekday() in [0, 1, 2, 3]: # Mon-Thu evenings
                allow_run = True
        elif now.hour < 6:
            if now.weekday() in [1, 2, 3, 4]: # Tue-Fri mornings (covering Mon-Thu overnights)
                allow_run = True
                
        if not allow_run:
            # print(f"\r[Status] {now.strftime('%A %H:%M')} - Outside sending window.", end="")
            time.sleep(30)
            continue
            
        current_key = f"{now.hour}:{now.minute}"
        
        if current_key == last_run_key:
            time.sleep(5)
            continue
            
        # Check Triggers
        handled = False
        for t in triggers:
            if now.hour == t["h"] and now.minute == t["m"]:
                print(f"\n[!] TRIGGERING {t['name']} at {current_key}...")
                t["func"]()
                last_run_key = current_key
                handled = True
                break
        
        if not handled:
            print(f"\r[Waiting] {now.strftime('%H:%M:%S')} (Next trigger closest match)", end="")
            
        time.sleep(10)

if __name__ == "__main__":
    simple_loop()
