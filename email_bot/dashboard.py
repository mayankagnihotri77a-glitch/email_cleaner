import streamlit as st
import sqlite3
import pandas as pd
import time
import os
import psutil
import sys

# Add parent dir to path to import maps_scraper
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from maps_scraper.sheet_manager import SheetManager

# Configuration
DB_PATH = "email_bot.db"
DEFAULT_SHEET_URL = "https://docs.google.com/spreadsheets/d/1CDomOmwx5ExqgHSabEneY_Z8KGF5aRPxLrQFu92Bt-M/edit?usp=sharing"
SERVICE_ACCOUNT_KEY = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "buzzscope_today_automation", "service_account.json")

st.set_page_config(
    page_title="Email Bot Command Center",
    page_icon="🚀",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Custom CSS
st.markdown("""
<style>
    .metric-card {
        background-color: #262730;
        padding: 15px;
        border-radius: 10px;
        color: white;
        text-align: center;
        margin-bottom: 10px;
    }
    .metric-value {
        font_size: 24px;
        font-weight: bold;
    }
    .status-active { color: #00FF00; font-weight: bold; }
    .status-inactive { color: #888888; font-weight: bold; }
    .section-header { font-size: 20px; font-weight: bold; margin-top: 20px; margin-bottom: 10px; border-bottom: 1px solid #444; }
</style>
""", unsafe_allow_html=True)

def get_db_connection():
    return sqlite3.connect(DB_PATH)

def is_bot_running():
    for p in psutil.process_iter(['name', 'cmdline']):
        try:
            if p.info['cmdline'] and 'email_bot.manager' in ' '.join(p.info['cmdline']):
                return True
        except: pass
    return False

@st.cache_data(ttl=10) # Cache for 10 seconds to save API calls
def load_scraper_data():
    try:
        mgr = SheetManager(SERVICE_ACCOUNT_KEY, DEFAULT_SHEET_URL)
        rows = mgr.leads_worksheet.get_all_records()
        leads_count = len(rows)
        email_count = sum(1 for r in rows if r.get('Email', '').strip())
        status = mgr.get_status()
        return leads_count, email_count, status
    except Exception as e:
        return 0, 0, {"Error": str(e)}

def load_bot_data():
    conn = get_db_connection()
    sent = pd.read_sql("SELECT count(*) as count FROM leads WHERE emails_sent_count > 0", conn)['count'][0]
    replied = pd.read_sql("SELECT count(*) as count FROM leads WHERE status='REPLIED'", conn)['count'][0]
    pipeline = pd.read_sql("SELECT emails_sent_count, count(*) as count FROM leads WHERE status != 'REPLIED' GROUP BY emails_sent_count", conn)
    logs = pd.read_sql("SELECT * FROM email_logs ORDER BY sent_at DESC LIMIT 20", conn)
    conn.close()
    return sent, replied, logs, pipeline

# --- UI ---
st.title("🚀 Command Center")

if st.button("🔄 Refresh Data"):
    load_scraper_data.clear()
    st.rerun()

# 1. SCRAPER BOT STATUS (Google Maps)
st.markdown("<div class='section-header'>📍 Scraper Bot Status (Google Maps)</div>", unsafe_allow_html=True)
leads_count, email_count, scraper_status = load_scraper_data()

if "Error" in scraper_status:
    st.error(f"Failed to load Scraper Data: {scraper_status['Error']}")
else:
    sc1, sc2, sc3 = st.columns(3)
    with sc1:
        st.markdown(f"<div class='metric-card'>Total Leads Scraped<br><span class='metric-value'>{leads_count}</span></div>", unsafe_allow_html=True)
    with sc2:
        st.markdown(f"<div class='metric-card'>Emails Found<br><span class='metric-value'>{email_count}</span></div>", unsafe_allow_html=True)
    with sc3:
        rate = (email_count/leads_count*100) if leads_count else 0
        st.markdown(f"<div class='metric-card'>Success Rate<br><span class='metric-value'>{rate:.1f}%</span></div>", unsafe_allow_html=True)

    st.info(f"**Current Task:** Searching for **{scraper_status.get('Last Niche', 'Unknown')}** in **{scraper_status.get('Last City', 'Unknown')}, {scraper_status.get('Last State', 'Unknown')}**")


# 2. EMAIL BOT STATUS
st.markdown("<div class='section-header'>📧 Email Bot Status</div>", unsafe_allow_html=True)
bot_active = is_bot_running()
status_html = f"<span class='status-active'>● ONLINE</span>" if bot_active else f"<span class='status-inactive'>● OFFLINE</span>"
st.markdown(f"**Bot Connection:** {status_html}", unsafe_allow_html=True)

sent, replied, logs, pipeline = load_bot_data()

ec1, ec2 = st.columns(2)
with ec1:
    st.markdown(f"<div class='metric-card'>Emails Sent<br><span class='metric-value'>{sent}</span></div>", unsafe_allow_html=True)
with ec2:
    st.markdown(f"<div class='metric-card' style='border: 1px solid #00FF00;'>Replies Received<br><span class='metric-value' style='color:#00FF00'>{replied}</span></div>", unsafe_allow_html=True)

# Pipeline
st.subheader("🔗 Follow-up Pipeline")
if not pipeline.empty:
    pipeline['Stage'] = pipeline['emails_sent_count'].apply(lambda x: "Waiting for Email #1" if x == 0 else f"Sent Email #{x}")
    st.bar_chart(pipeline.set_index("Stage")['count'])
else:
    st.info("No active leads in pipeline.")

# Controls
st.subheader("⚡ Controls")
if st.button("▶️ START SENDING (One Batch)"):
    os.system("start cmd /k python -m email_bot.manager")
    st.success("Email process started!")
    time.sleep(2)
    st.rerun()

st.caption(f"Last Updated: {time.strftime('%H:%M:%S')}")
