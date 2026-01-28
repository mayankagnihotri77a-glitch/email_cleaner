import requests
import json

TOKEN = "8488528206:AAGfMeypl4g7dfP-2mzpLwfGXnP8zz7fprQ"

def get_chat_id():
    url = f"https://api.telegram.org/bot{TOKEN}/getUpdates"
    try:
        print(f"Checking for messages on bot...")
        response = requests.get(url)
        data = response.json()
        
        if not data.get("ok"):
            print(f"Error: {data}")
            return

        result = data.get("result", [])
        if not result:
            print("No messages found. Did you send 'Hello' to the bot?")
            return

        # Get most recent chat id
        chat_id = result[-1]["message"]["chat"]["id"]
        first_name = result[-1]["message"]["chat"].get("first_name", "Unknown")
        
        print(f"FOUND CHAT ID: {chat_id}")
        print(f"User: {first_name}")
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    get_chat_id()
