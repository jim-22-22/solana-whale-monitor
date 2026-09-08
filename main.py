import os
import time
import requests

BIRDEYE_API_KEY = os.getenv("BIRDEYE_API_KEY")

HEADERS = {
    "X-API-KEY": BIRDEYE_API_KEY,
    "x-chain": "solana"
}

seen_tokens = set()

CHECK_EVERY_SECONDS = 30


def check_new_tokens():
    url = "https://public-api.birdeye.so/defi/v2/tokens/new_listing"

    try:
        response = requests.get(
            url,
            headers=HEADERS,
            params={
                "limit": 20,
                "meme_platform_enabled": "true"
            },
            timeout=20
        )

        print("Birdeye status:", response.status_code)
        response.raise_for_status()

        data = response.json()
        tokens = data.get("data", {}).get("items", [])

        print("New listings received:", len(tokens))

        for token in tokens:
            address = token.get("address", "")

            if not address or address in seen_tokens:
                continue

            seen_tokens.add(address)

            name = token.get("name", "UNKNOWN")
            symbol = token.get("symbol", "UNKNOWN")
            liquidity = token.get("liquidity", 0)

            print("")
            print("NEW TOKEN DETECTED")
            print("Name:", name)
            print("Symbol:", symbol)
            print("Liquidity:", liquidity)
            print("Address:", address)
            print("")

    except Exception as e:
        print("Birdeye error:", e)


print("Solana NEW TOKEN monitor started")

while True:
    check_new_tokens()
    time.sleep(CHECK_EVERY_SECONDS)
