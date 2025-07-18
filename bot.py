import os
import time
import hmac
import hashlib
import requests
from flask import Flask, request, jsonify
import threading

app = Flask(__name__)

# === ENV proměnné ===
MEXC_API_KEY = os.environ.get("MEXC_API_KEY")
MEXC_API_SECRET = os.environ.get("MEXC_API_SECRET")
LEVERAGE = int(os.environ.get("MEXC_LEVERAGE", 15))
SYMBOL = os.environ.get("MEXC_SYMBOL", "BTC_USDT")
SL_PERCENT = float(os.environ.get("SL_PERCENT", 10))
TG_BOT = os.environ.get("TG_BOT")
TG_CHAT = os.environ.get("TG_CHAT")
TRAIL_PERCENT = float(os.environ.get("TRAIL_PERCENT", "0.5").replace(",", "."))

# === Telegram funkce ===
def send_telegram_message(message):
    url = f"https://api.telegram.org/bot{TG_BOT}/sendMessage"
    data = {"chat_id": TG_CHAT, "text": message}
    try:
        requests.post(url, data=data)
    except Exception as e:
        print("Telegram error:", e)

# === Globální stav ===
last_signal = None
position = None
entry_price = None
trailing_stop = None

def get_price():
    url = f"https://api.mexc.com/api/v3/ticker/price?symbol={SYMBOL.replace('_','')}"
    try:
        response = requests.get(url)
        data = response.json()
        return float(data["price"])
    except Exception as e:
        print("Price error:", e)
        return None

def mexc_request(method, endpoint, params=None, data=None):
    url = "https://api.mexc.com" + endpoint
    headers = {"Content-Type": "application/json"}
    if params is None: params = {}
    params['api_key'] = MEXC_API_KEY
    query = '&'.join([f"{k}={v}" for k, v in sorted(params.items())])
    sign = hmac.new(MEXC_API_SECRET.encode(), query.encode(), hashlib.sha256).hexdigest()
    params['sign'] = sign
    try:
        if method == "POST":
            r = requests.post(url, params=params, json=data, headers=headers)
        else:
            r = requests.get(url, params=params, headers=headers)
        return r.json()
    except Exception as e:
        print("MEXC API error:", e)
        return None

def open_position(signal):
    global position, entry_price, trailing_stop
    price = get_price()
    if price is None:
        send_telegram_message("❗ Nepodařilo se získat cenu BTC.")
        return
    side = "BUY" if signal in ["long", "buy"] else "SELL"
    # --- Demo, místo skutečné objednávky loguje ---
    send_telegram_message(f"🚀 Otevírám pozici: {side} na {price}\nLeverage: {LEVERAGE}x\nSL: {SL_PERCENT}%\nTrailing: {TRAIL_PERCENT}%")
    print(f"Open position: {side} {price}")
    position = side
    entry_price = price
    trailing_stop = price * (1 - TRAIL_PERCENT / 100) if side == "BUY" else price * (1 + TRAIL_PERCENT / 100)

def close_position():
    global position, entry_price, trailing_stop
    if position:
        send_telegram_message(f"❌ Pozice uzavřena ({position}).")
    position = None
    entry_price = None
    trailing_stop = None

def price_watcher():
    global position, entry_price, trailing_stop
    while True:
        if position and entry_price:
            price = get_price()
            if price:
                if position == "BUY":
                    # SL i trailing
                    new_trailing = max(trailing_stop, price * (1 - TRAIL_PERCENT / 100))
                    if price <= new_trailing or price <= entry_price * (1 - SL_PERCENT / 100):
                        send_telegram_message(f"🔔 Trailing nebo SL hitnuto!\nCena: {price}")
                        close_position()
                    else:
                        trailing_stop = new_trailing
                elif position == "SELL":
                    new_trailing = min(trailing_stop, price * (1 + TRAIL_PERCENT / 100))
                    if price >= new_trailing or price >= entry_price * (1 + SL_PERCENT / 100):
                        send_telegram_message(f"🔔 Trailing nebo SL hitnuto!\nCena: {price}")
                        close_position()
                    else:
                        trailing_stop = new_trailing
        time.sleep(2)

@app.route("/webhook", methods=["POST"])
def webhook():
    global last_signal
    data = request.json
    print("Received:", data)
    if not data:
        return jsonify({"error": "No data"}), 400
    signal = None
    # Přizpůsob se formátu alertu!
    if "signal" in data:
        signal = data["signal"]
    elif "action" in data:
        # Pokud používáš "action": "buy" / "sell"
        signal = data["action"]

    if signal:
        last_signal = signal
        open_position(signal)
        return jsonify({"status": "ok"})
    return jsonify({"error": "Unknown format"}), 400

if __name__ == "__main__":
    # Start watching price (trailing, SL)
    t = threading.Thread(target=price_watcher, daemon=True)
    t.start()
    send_telegram_message("✅ Bot je online! (MEXC, trailing/SL/Telegram)")
    app.run(host="0.0.0.0", port=10000)
