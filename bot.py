import requests
import json
import time

API_KEY = 'TVŮJ_API_KLÍČ'
API_SECRET = 'TVÉ_API_TAJEMSTVÍ'

def execute_trade(signal):
    print(f"Obdržen signál: {signal}")
    # Sem přijde kód pro zadání příkazu na MEXC přes API

def main():
    print("Bot běží. Čeká na signál...")
    while True:
        try:
            with open("signal.txt", "r") as f:
                signal = f.read().strip()
                if signal:
                    execute_trade(signal)
                    open("signal.txt", "w").close()
        except Exception as e:
            print(f"Chyba: {e}")
        time.sleep(3)

if __name__ == "__main__":
    main()
