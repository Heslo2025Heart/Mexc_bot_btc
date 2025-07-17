from flask import Flask, request, jsonify
import os
import requests
import hmac
import hashlib
import time

app = Flask(__name__)

# === Nastavení proměnných ===
API_KEY = os.environ.get("MEXC_API_KEY")
API_SECRET = os.environ.get("MEXC_API_SECRET")
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

SYMBOL = "BTCUSDT"
LEVERAGE = 15
ORDER_TYPE = 1  # 1 = market
PERCENT_BALANCE = 10  # % kapitálu

# === Zjisti zůstatek na futures účtu ===
def get_balance():
    timestamp = str(int(time.time() * 1000))
    query = f"timestamp={timestamp}"
    signature = hmac.new(API_SECRET.encode(), query.encode(), hashlib.sha256).hexdigest()
    headers = {"X-MEXC-API-KEY": API_KEY}
    url = f"https://contract.mexc.com/api/v1/private/account/assets?{query}&signature={signature}"
    response = requests.get(url, headers=headers)
    data = response.json()
    for asset in data.get("data", []):
        if asset["currency"] == "USDT":
            return float(asset["availableBalance"])
    return 0

# === Vypočítej pozici podle procenta kapitálu ===
def calculate_position(balance, price):
    usdt_amount = (balance * PERCENT_BALANCE) / 100
    quantity = round((usdt_amount * LEVERAGE) / price, 3)
    return quantity

# === Otevři obchod ===
def place_order(side):
    balance = get_balance()
    price = float(get_price())
    quantity = calculate_position(balance, price)
    timestamp = str(int(time.time() * 1000))

    body = {
        "symbol": SYMBOL,
        "price": str(price),
        "vol": str(quantity),
        "leverage": LEVERAGE,
        "side": 1 if side == "buy" else 2,
        "type": ORDER_TYPE,
        "open_type": "isolated",
        "position_id": 0,
        "external_oid": f"order_{timestamp}",
        "stop_loss_price": round(price * 0.90, 2),
        "take_profit_price": round(price * 1.015, 2),
        "position_mode": "single",
        "reduce_only": False
    }

    query = f"timestamp={timestamp}"
    signature = hmac.new(API_SECRET.encode(), query.encode(), hashlib.sha256).hexdigest()
    headers = {
        "Content-Type": "application/json",
        "X-MEXC-API-KEY": API_KEY
    }

    url = f"https://contract.mexc.com/api/v1/private/order/submit?{query}&signature={signature}"
    response = requests.post(url, headers=headers, json=body)
    notify_telegram(f"Obchod: {side.upper()} {quantity} BTC @ {price}\nOdpověď: {response.text}")
    return response.text

# === Získej aktuální cenu ===
def get_price():
    url = f"https://contract.mexc.com/api/v1/contract/market/depth?symbol={SYMBOL}&limit=5"
    response = requests.get(url).json()
    return response["data"]["asks"][0][0]

# === Poslat zprávu na Telegram ===
def notify_telegram(message):
    if TELEGRAM_TOKEN and TELEGRAM_CHAT_ID:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        data = {"chat_id": TELEGRAM_CHAT_ID, "text": message}
        requests.post(url, data=data)

# === WEBHOOK ===
@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.get_json()
    if not data or "action" not in data:
        return jsonify({"error": "Chybí akce"}), 400

    action = data["action"].lower()
    if action not in ["buy", "sell"]:
        return jsonify({"error": "Neplatná akce"}), 400

    result = place_order(action)
    return jsonify({"status": "obchod odeslán", "výsledek": result})

# === Spuštění ===
if __name__ == '__main__':
    app.run(host="0.0.0.0", port=10000)
