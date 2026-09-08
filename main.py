import os
import time
import requests

BIRDEYE_API_KEY = os.getenv("BIRDEYE_API_KEY")

HEADERS = {
    "X-API-KEY": BIRDEYE_API_KEY,
    "x-chain": "solana"
}

seen_tokens = set()

CHECK_EVERY_SECONDS = 60
DELAY_BETWEEN_REQUESTS = 2
MAX_TOKENS_TO_ANALYZE = 5

MIN_LIQUIDITY = 3000
MAX_MARKET_CAP = 500000


def birdeye_get(url, params=None):
    try:
        response = requests.get(
            url,
            headers=HEADERS,
            params=params,
            timeout=20
        )

        if response.status_code == 429:
            print("Rate limit 429 - waiting 15 seconds...")
            time.sleep(15)
            return None

        response.raise_for_status()
        return response.json()

    except Exception as e:
        print("Birdeye request error:", e)
        return None


def get_token_overview(address):
    url = "https://public-api.birdeye.so/defi/token_overview"

    data = birdeye_get(
        url,
        {
            "address": address
        }
    )

    if not data:
        return None

    return data.get("data", {})


def check_new_tokens():
    url = "https://public-api.birdeye.so/defi/v2/tokens/new_listing"

    data = birdeye_get(
        url,
        {
            "limit": 20,
            "meme_platform_enabled": "true"
        }
    )

    if not data:
        return

    tokens = data.get("data", {}).get("items", [])

    print("New listings received:", len(tokens))

    new_tokens = []

    for token in tokens:
        address = token.get("address", "")

        if not address or address in seen_tokens:
            continue

        seen_tokens.add(address)

        liquidity = float(token.get("liquidity") or 0)

        if liquidity < MIN_LIQUIDITY:
            continue

        new_tokens.append(token)

    print("Passed liquidity filter:", len(new_tokens))

    for token in new_tokens[:MAX_TOKENS_TO_ANALYZE]:

        time.sleep(DELAY_BETWEEN_REQUESTS)

        address = token.get("address", "")
        name = token.get("name", "UNKNOWN")
        symbol = token.get("symbol", "UNKNOWN")

        overview = get_token_overview(address)

        if not overview:
            continue

        liquidity = float(overview.get("liquidity") or 0)
        market_cap = float(overview.get("marketCap") or 0)

        volume_5m = float(overview.get("v5mUSD") or 0)
        trades_5m = int(overview.get("trade5m") or 0)
        buys_5m = int(overview.get("buy5m") or 0)
        sells_5m = int(overview.get("sell5m") or 0)

        print("")
        print("SCANNING:", symbol)
        print("Liquidity:", liquidity)
        print("Market Cap:", market_cap)
        print("Volume 5m:", volume_5m)
        print("Trades 5m:", trades_5m)
        print("Buys/Sells 5m:", buys_5m, "/", sells_5m)

        if market_cap > 0 and market_cap > MAX_MARKET_CAP:
            continue

        print("")
        print("🔥 EARLY TOKEN WATCH")
        print("Name:", name)
        print("Symbol:", symbol)
        print("Liquidity: $", round(liquidity, 2))
        print("Market Cap: $", round(market_cap, 2))
        print("Volume 5m: $", round(volume_5m, 2))
        print("Trades 5m:", trades_5m)
        print("Buys/Sells 5m:", buys_5m, "/", sells_5m)
        print("Address:", address)
        print("")


print("Solana EARLY TOKEN monitor started")

while True:
    check_new_tokens()
    time.sleep(CHECK_EVERY_SECONDS)
