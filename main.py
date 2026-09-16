import os
import time
import requests

BIRDEYE_API_KEY = os.getenv("BIRDEYE_API_KEY")

HEADERS = {
    "X-API-KEY": BIRDEYE_API_KEY,
    "x-chain": "solana"
}

CHECK_INTERVAL = 60
REQUEST_DELAY = 2

MIN_LIQUIDITY = 3000
MAX_MARKET_CAP = 500000
MAX_TOKENS_PER_CYCLE = 5

seen_tokens = set()


def birdeye_get(url, params=None):
    try:
        response = requests.get(
            url,
            headers=HEADERS,
            params=params,
            timeout=20
        )

        print("Birdeye status:", response.status_code)

        if response.status_code == 429:
            print("Birdeye rate limit reached. Waiting...")
            time.sleep(30)
            return None

        if response.status_code != 200:
            print("Birdeye request error:", response.status_code)
            print(response.text[:500])
            return None

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

    time.sleep(REQUEST_DELAY)

    if not data:
        return None

    return data.get("data", {})


def calculate_score(token):
    score = 0

    liquidity = float(token.get("liquidity") or 0)
    market_cap = float(
        token.get("marketCap")
        or token.get("mc")
        or 0
    )

    volume_5m = float(
        token.get("v5mUSD")
        or token.get("volume5m")
        or 0
    )

    trades_5m = int(
        token.get("trade5m")
        or token.get("trades5m")
        or 0
    )

    buys_5m = int(
        token.get("buy5m")
        or token.get("buys5m")
        or 0
    )

    sells_5m = int(
        token.get("sell5m")
        or token.get("sells5m")
        or 0
    )

    # Liquidity
    if liquidity >= 10000:
        score += 2
    elif liquidity >= 5000:
        score += 1

    # Small market cap
    if 0 < market_cap <= 100000:
        score += 2
    elif market_cap <= 500000:
        score += 1

    # Early volume
    if volume_5m >= 10000:
        score += 3
    elif volume_5m >= 5000:
        score += 2
    elif volume_5m >= 1000:
        score += 1

    # Trading activity
    if trades_5m >= 50:
        score += 2
    elif trades_5m >= 20:
        score += 1

    # Buy pressure
    total = buys_5m + sells_5m

    if total > 0:
        buy_ratio = buys_5m / total

        if buy_ratio >= 0.70:
            score += 3
        elif buy_ratio >= 0.60:
            score += 2
        elif buy_ratio >= 0.55:
            score += 1

    return score


def score_label(score):
    if score >= 9:
        return "🔥 VERY HIGH MOMENTUM"

    if score >= 7:
        return "🚀 HIGH MOMENTUM"

    if score >= 5:
        return "👀 MEDIUM MOMENTUM"

    return "LOW SIGNAL"


def check_new_tokens():
    url = "https://public-api.birdeye.so/defi/v2/tokens/new_listing"

    # Keep this request minimal.
    # meme_platform_enabled was removed because it was
    # causing Birdeye to reject the request with HTTP 400.
    data = birdeye_get(
        url,
        {
            "limit": 20
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
        new_tokens.append(token)

    print("New tokens:", len(new_tokens))

    for token in new_tokens[:MAX_TOKENS_PER_CYCLE]:

        address = token.get("address", "")
        name = token.get("name", "UNKNOWN")
        symbol = token.get("symbol", "UNKNOWN")

        overview = get_token_overview(address)

        if not overview:
            continue

        liquidity = float(overview.get("liquidity") or 0)

        market_cap = float(
            overview.get("marketCap")
            or overview.get("mc")
            or 0
        )

        if liquidity < MIN_LIQUIDITY:
            continue

        if market_cap > MAX_MARKET_CAP:
            continue

        score = calculate_score(overview)
        signal = score_label(score)

        volume_5m = float(
            overview.get("v5mUSD")
            or overview.get("volume5m")
            or 0
        )

        trades_5m = int(
            overview.get("trade5m")
            or overview.get("trades5m")
            or 0
        )

        buys_5m = int(
            overview.get("buy5m")
            or overview.get("buys5m")
            or 0
        )

        sells_5m = int(
            overview.get("sell5m")
            or overview.get("sells5m")
            or 0
        )

        print("")
        print("================================")
        print(signal)
        print("EARLY TOKEN WATCH")
        print("Score:", score)
        print("Name:", name)
        print("Symbol:", symbol)
        print("Liquidity: $", round(liquidity, 2))
        print("Market Cap: $", round(market_cap, 2))
        print("Volume 5m: $", round(volume_5m, 2))
        print("Trades 5m:", trades_5m)
        print("Buys/Sells 5m:", buys_5m, "/", sells_5m)
        print("Address:", address)
        print("================================")
        print("")


print("Solana EARLY MOMENTUM SCORE monitor started")

while True:
    check_new_tokens()
    time.sleep(CHECK_INTERVAL)
