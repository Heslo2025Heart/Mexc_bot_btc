from flask import Flask, request, jsonify
import requests
import os
import hmac
import hashlib
import time

app = Flask(__name__)

# Klíče načti z environment variables (nastavíš je v Renderu!)
MEXC_API_KEY = os.environ.get("MEXC_API_KEY")
MEXC_API_SECRET = os.environ.get("MEXC_API_SECRET")
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

SYMBOL = "BTCUSDT"
LEVERAGE = 15
ORDER_TYPE = 1  # 1 = market order
PERCENT_BALANCE = 10  # 10 % zůstatku, můžeš upravit kdykoli

def get_balance():
    """Vrátí aktuální USDT zůstatek na futures účtu na MEXC."""
    url = "https://contract.mexc.com/api/v1/private/account/assets"
    timestamp = str(int(time.time() * 1000))
    params = {"api_key": MEXC_API_KEY, "req_time": timestamp}
    sign_payload = f"api_key={MEXC_API_KEY}&req_time={timestamp}"
    sign = hmac.new(MEXC_API_SECRET.encode(), sign_payload.encode(), hashlib.sha256).hexdigest()
    params["sign"] = sign
    try:
        resp = requests.get(url, params=params, timeout=10)
        assets = resp.json()['data']
        for asset in assets:
            if asset['currency'] == "USDT":
                return float(asset['available_balance'])
    except Exception as e:
        print("Chyba při získávání zůstatku:", e)
    return 0.0

def place_order(symbol, side, amount, leverage=LEVERAGE):
    """Zadá market order na MEXC futures (BTCUSDT)."""
    url = "https://contract.mexc.com/api/v1/private/order/submit"
    timestamp = str(int(time.time() * 1000))
    params = {
        "api_key": MEXC_API_KEY,
        "req_time": timestamp,
        "symbol": symbol,
        "price": "0",  # 0 = market order
        "vol": str(amount),  # objem v USDT!
        "leverage": str(leverage),
        "side": side,  # 1=Open Long, 2=Open Short
        "open_type": "CROSSED",  # cross margin
        "position_id": "0",
        "external_oid": str(int(time.time())),
        "stop_loss_price": "0",
        "take_profit_price": "0",
        "position_mode": "MergedSingle",
        "reduce_only": False,
        "order_type": ORDER_TYPE
    }
    sign_payload = "&".join([f"{k}={v}" for k, v in sorted(params.items()) if k != "sign"])
    sign = hmac.new(MEXC_API_SECRET.encode(), sign_payload.encode(), hashlib.sha256).hexdigest()
    params["sign"] = sign
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    resp = requests.post(url, data=params, headers=headers, timeout=10)
    print("MEXC order response:", resp.text)
    return resp.json()

def send_telegram(msg):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": msg}
    try:
        requests.post(url, data=payload, timeout=10)
    except Exception as e:
        print("Chyba při posílání na Telegram:", e)

@app.route("/", methods=["GET"])
def home():
    return "MEXC bot je online."

@app.route("/", methods=["POST"])
def webhook():
    data = request.get_json(force=True, silent=True)
    print("Přijatý webhook:", data)
    if not data or "signal" not in data:
        send_telegram(f"Neplatný nebo neúplný webhook: {data}")
        return jsonify({"status": "ERROR", "msg": "Neplatný formát, očekávám např. {'signal':'long'}"}), 400

    signal = data["signal"]
    balance = get_balance()
    if balance <= 0:
        send_telegram("Zůstatek USDT je nulový nebo se nepodařilo načíst.")
        return jsonify({"status": "ERROR", "msg": "Balance error"}), 400

    amount = round(balance * PERCENT_BALANCE / 100, 2)
    if amount < 1:
        send_telegram(f"Obchod nespouštím, objem ({amount} USDT) je příliš malý.")
        return jsonify({"status": "ERROR", "msg": "Minimální objem nedosažen"}), 400

    if signal == "long":
        side = 1  # 1 = open long
        msg = f"Zadávám LONG na {SYMBOL} za {amount} USDT (páka {LEVERAGE}x)."
    elif signal == "short":
        side = 2  # 2 = open short
        msg = f"Zadávám SHORT na {SYMBOL} za {amount} USDT (páka {LEVERAGE}x)."
    else:
        send_telegram(f"Neznámý signál: {signal}")
        return jsonify({"status": "ERROR", "msg": "Neznámý signál"}), 400

    send_telegram(msg)
    result = place_order(SYMBOL, side, amount)
    send_telegram(f"Výsledek: {result}")
    return jsonify({"status": "OK", "msg": "Obchod odeslán", "result": result}), 200

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
