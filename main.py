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
        response = requests.get(
            url,
            headers=HEADERS,
            params={
                "sort_by": "v24hUSD",
                "sort_type": "desc",
                "offset": 0,
                "limit": 10
            },
            timeout=20
        )

        response.raise_for_status()
        data = response.json()

        print("Birdeye connection OK")

        tokens = data.get("data", {}).get("tokens", [])

        for token in tokens:
            symbol = token.get("symbol", "UNKNOWN")
            address = token.get("address", "")
            price = token.get("price", 0)
            liquidity = token.get("liquidity", 0)
            volume = token.get("v24hUSD", 0)

            print(
                f"{symbol} | "
                f"Price: {price} | "
                f"Liquidity: {liquidity} | "
                f"24h Volume: {volume} | "
                f"Address: {address}"
            )

    except Exception as e:
        print(f"Birdeye error: {e}")


print("Solana token monitor started")

while True:
    check_birdeye()
    time.sleep(60)
