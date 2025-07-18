import os
from flask import Flask, request, jsonify
import requests

app = Flask(__name__)

TG_BOT = os.environ.get("TG_BOT") or "7244101592:AAHgAjv5tLsfOt3jft-oahnXypy75h62Bn4"
TG_CHAT = os.environ.get("TG_CHAT") or "6618535645"

def send_telegram_message(message):
    url = f"https://api.telegram.org/bot{TG_BOT}/sendMessage"
    data = {"chat_id": TG_CHAT, "text": message}
    try:
        r = requests.post(url, data=data, timeout=10)
        print("Telegram response:", r.text)
    except Exception as e:
        print("Telegram error:", e)

@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.json
    print("Received data:", data)
    send_telegram_message(f"ALERT: {data}")
    return jsonify({"status": "ok"})

if __name__ == "__main__":
    send_telegram_message("Bot je online a čeká na alert!")
    app.run(host="0.0.0.0", port=10000)
