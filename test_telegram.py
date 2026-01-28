from telegram_notifier import send_telegram_message

if __name__ == "__main__":
    print("Sending test message...")
    success = send_telegram_message("✅ **System Test**: Telegram notifications are now CONNECTED!")
    if success:
        print("Success!")
    else:
        print("Failed.")
