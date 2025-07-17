from flask import Flask, request, jsonify
import requests

app = Flask(__name__)

# --- Nastavení proměnných ---
TELEGRAM_TOKEN = "7244101592:AAHgAjv5tLsfOt3jft-oahnXypy75h62Bn4"  # Tvoje API od BotFathera
TELEGRAM_CHAT_ID = "6618535645"  # Tvoje chat ID (Telegram)

@app.route("/", methods=["GET"])
def home():
    return "Bot běží a čeká na signály z TradingView."

@app.route("/", methods=["POST"])
def webhook():
    data = request.get_json()
    print("Přijatý webhook:", data)

    # Ošetření: pokud není data, ignorovat
    if not data:
        return jsonify({"status": "No data received"}), 400

    # Například očekáváš {"signal": "long"} nebo {"signal": "short"}
    signal = data.get("signal")
    if not signal:
        # Pokud přijde jiný formát, prostě to zaloguj
        send_telegram(f"Neznámý signál: {data}")
        return jsonify({"status": "Missing 'signal'"}), 400

    # Pošli info na Telegram
    send_telegram(f"Obdržený signál: {signal.upper()}")

    # Tady bude obchodní logika! (napojení na MEXC API atd.)

    return jsonify({"status": "Signal processed"}), 200

def send_telegram(text):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": text
    }
    try:
        requests.post(url, data=payload, timeout=10)
    except Exception as e:
        print("Chyba při posílání na Telegram:", e)

if __name__ == "__main__":
    import os
    port = int(os.environ.get("PORT", 5000))  # Render nastavuje proměnnou PORT
    app.run(host="0.0.0.0", port=port)
