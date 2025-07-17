
from flask import Flask, request, jsonify
import requests
import os
import hmac
import hashlib
import time

app = Flask(__name__)

# --- Nastavení proměnných z Render prostředí ---
API_KEY = os.environ.get("MEXC_API_KEY")
API_SECRET = os.environ.get("MEXC_API_SECRET")
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

# --- Konfigurace bota ---
SYMBOL = "BTCUSDT"
LEVERAGE = 15
ORDER_TYPE = 1  # 1 = market
PERCENT_BALANCE = 10  # 10 % zůstatku

# --- Telegram logování ---
def send_telegram(msg):
    if TELEGRAM_TOKEN and TELEGRAM_CHAT_ID:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        data = {"chat_id": TELEGRAM_CHAT_ID, "text": msg}
        try:
            requests.post(url, json=data)
        except:
            pass

# --- Výpočet HMAC podpisu ---
def get_signature(query_string, secret):
    return hmac.new(secret.encode('utf-8'), query_string.encode('utf-8'), hashlib.sha256).hexdigest()

# --- Načtení zůstatku (pro výpočet velikosti pozice) ---
def get_balance():
    try:
        url = "https://contract.mexc.com/api/v1/private/account/assets"
        timestamp = str(int(time.time() * 1000))
        query = f"timestamp={timestamp}"
        signature = get_signature(query, API_SECRET)
        headers = {
            "ApiKey": API_KEY,
            "Request-Time": timestamp,
            "Signature": signature,
            "Content-Type": "application/json"
        }
        response = requests.get(f"{url}?{query}", headers=headers)
        assets = response.json().get("data", [])
        for asset in assets:
            if asset["currency"] == "USDT":
                return float(asset["availableBalance"])
    except:
        return 0.0

# --- Obchodní logika ---
def place_order(signal):
    send_telegram(f"📩 Signál přijat: {signal}")

    balance = get_balance()
    if balance == 0:
        send_telegram("❌ Nelze načíst zůstatek, obchod neproveden.")
        return

    size = round((balance * PERCENT_BALANCE / 100), 2)
    side = 1 if signal == "long" else 2  # 1=buy, 2=sell

    order_data = {
        "symbol": SYMBOL,
        "price": 0,
        "vol": size,
        "leverage": LEVERAGE,
        "side": side,
        "type": ORDER_TYPE,
        "open_type": 1,
        "position_id": 0,
        "external_oid": f"oid_{int(time.time())}",
        "stop_loss_price": 0,
        "take_profit_price": 0,
        "position_mode": 1
    }

    timestamp = str(int(time.time() * 1000))
    query = f"timestamp={timestamp}"
    signature = get_signature(query, API_SECRET)

    headers = {
        "ApiKey": API_KEY,
        "Request-Time": timestamp,
        "Signature": signature,
        "Content-Type": "application/json"
    }

    url = "https://contract.mexc.com/api/v1/private/order/submit"
    try:
        response = requests.post(f"{url}?{query}", json=order_data, headers=headers)
        res_json = response.json()
        if res_json.get("success"):
            send_telegram(f"✅ Obchod proveden: {signal.upper()} za {size} USDT")
        else:
            send_telegram(f"⚠️ Obchod selhal: {res_json}")
    except Exception as e:
        send_telegram(f"❌ Chyba při zadávání obchodu: {e}")

# --- Webhook přijímá signál z TradingView ---
@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.get_json()
    if not data or "signal" not in data:
        return jsonify({"status": "invalid request"}), 400

    signal = data["signal"].lower()
    if signal in ["long", "short"]:
        send_telegram(f"📥 Webhook přijat – signál: {signal.upper()}")
        place_order(signal)
        return jsonify({"status": "order sent"}), 200
    else:
        return jsonify({"status": "unknown signal"}), 400

# --- Spuštění aplikace ---
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
