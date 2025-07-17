from flask import Flask, request, jsonify
import requests
import os

app = Flask(__name__)

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

def send_telegram(msg):
    if TELEGRAM_TOKEN and TELEGRAM_CHAT_ID:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        data = {"chat_id": TELEGRAM_CHAT_ID, "text": msg}
        try:
            requests.post(url, json=data)
        except Exception as e:
            print(f"Telegram error: {e}")

@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.get_json()
    print(f"Obdržený alert z TradingView: {data}")

    signal = data.get("signal")
    if signal in ["long", "short"]:
        text = f"✅ TradingView alert: {signal.upper()}"
        send_telegram(text)
        print(f"Posílám do Telegramu: {text}")
        return jsonify({"status": "ok", "detail": f"Signal {signal} accepted"}), 200
    else:
        send_telegram("❌ Chybný nebo neznámý alert signal!")
        return jsonify({"status": "error", "detail": "Invalid or missing signal"}), 400

@app.route("/", methods=["GET"])
def home():
    return "Bot běží a čeká na alerty na endpointu /webhook."

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
