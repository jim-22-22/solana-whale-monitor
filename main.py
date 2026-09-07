import os
import time
import requests

BIRDEYE_API_KEY = os.getenv("BIRDEYE_API_KEY")

HEADERS = {
    "X-API-KEY": BIRDEYE_API_KEY,
    "x-chain": "solana"
}

def check_birdeye():
    url = "https://public-api.birdeye.so/defi/tokenlist"

    try:
        response = requests.get(url, headers=HEADERS, timeout=20)

        print("Birdeye status:", response.status_code)

        if response.status_code == 200:
            print("Monitor funcionando correctamente.")
        else:
            print("Error Birdeye:", response.text)

    except Exception as e:
        print("Error:", e)

while True:
    check_birdeye()
    time.sleep(60)
