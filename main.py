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

# Primeros filtros. Después los afinamos con datos reales.
MIN_LIQUIDITY = 3000
MAX_MARKET_CAP = 500000
MIN_VOLUME_5M = 1000
MIN_TRADES_5M = 5


def get_token_overview(address):
    url = "https://public-api.birdeye.so/defi/token_overview"

    response = requests.get(
        url,
        headers=HEADERS,
        params={
            "address": address,
            "frames": "1m,5m,30m,1h"
        },
        timeout=20
    )

    response.raise_for_status()

    return response.json().get("data", {})


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

            try:
                overview = get_token_overview(address)

                liquidity = float(overview.get("liquidity") or 0)
                market_cap = float(overview.get("marketCap") or 0)

                volume_5m = float(
                    overview.get("v5mUSD")
                    or overview.get("volume5m")
                    or 0
                )

                trades_5m = int(
                    overview.get("trade5m")
                    or overview.get("trade5mCount")
                    or 0
                )

                buys_5m = int(
                    overview.get("buy5m")
                    or overview.get("buy5mCount")
                    or 0
                )

                sells_5m = int(
                    overview.get("sell5m")
                    or overview.get("sell5mCount")
                    or 0
                )

                print("")
                print("SCANNING:", symbol)
                print("Liquidity:", liquidity)
                print("Market Cap:", market_cap)
                print("Volume 5m:", volume_5m)
                print("Trades 5m:", trades_5m)
                print("Buys/Sells 5m:", buys_5m, "/", sells_5m)

                if liquidity < MIN_LIQUIDITY:
                    continue

                if market_cap > 0 and market_cap > MAX_MARKET_CAP:
                    continue

                if volume_5m < MIN_VOLUME_5M:
                    continue

                if trades_5m < MIN_TRADES_5M:
                    continue

                print("")
                print("🔥 EARLY MOMENTUM CANDIDATE")
                print("Name:", name)
                print("Symbol:", symbol)
                print("Liquidity: $", round(liquidity, 2))
                print("Market Cap: $", round(market_cap, 2))
                print("Volume 5m: $", round(volume_5m, 2))
                print("Trades 5m:", trades_5m)
                print("Buys/Sells 5m:", buys_5m, "/", sells_5m)
                print("Address:", address)
                print("")

            except Exception as e:
                print("Overview error for", symbol, ":", e)

    except Exception as e:
        print("Birdeye new listing error:", e)


print("Solana EARLY MOMENTUM monitor started")

while True:
    check_new_tokens()
    time.sleep(CHECK_EVERY_SECONDS)
