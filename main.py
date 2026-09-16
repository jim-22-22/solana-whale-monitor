import time
from datetime import datetime, timezone
import requests

# ==========================================
# SOLANA EARLY MOMENTUM MONITOR
# Source: GeckoTerminal
# ==========================================

URL = "https://api.geckoterminal.com/api/v2/networks/solana/new_pools"

HEADERS = {
    "Accept": "application/json;version=20230203"
}

CHECK_INTERVAL = 60

# ---- FILTERS ----

MAX_AGE_MINUTES = 15

MIN_LIQUIDITY = 2000
MAX_LIQUIDITY = 100000

MIN_FDV = 1000
MAX_FDV = 1000000

MIN_VOLUME_5M = 500

MIN_TRADES_5M = 5

seen_pools = set()


def safe_float(value):
    try:
        return float(value or 0)
    except:
        return 0


def safe_int(value):
    try:
        return int(value or 0)
    except:
        return 0


def get_new_pools():

    try:

        response = requests.get(
            URL,
            headers=HEADERS,
            params={
                "include": "base_token,quote_token,dex",
                "page": 1
            },
            timeout=20
        )

        print("GeckoTerminal status:", response.status_code)

        if response.status_code != 200:
            print("GeckoTerminal error:")
            print(response.text[:500])
            return None

        return response.json()

    except Exception as e:

        print("GeckoTerminal request error:", e)

        return None


def pool_age_minutes(created_at):

    try:

        created = datetime.fromisoformat(
            created_at.replace("Z", "+00:00")
        )

        now = datetime.now(timezone.utc)

        return (now - created).total_seconds() / 60

    except:

        return 999999


def calculate_score(
    age,
    liquidity,
    fdv,
    volume,
    buys,
    sells
):

    score = 0

    trades = buys + sells

    # AGE
    if age <= 3:
        score += 3
    elif age <= 7:
        score += 2
    elif age <= 15:
        score += 1

    # LIQUIDITY
    if liquidity >= 10000:
        score += 2
    elif liquidity >= 5000:
        score += 1

    # SMALL FDV / EARLY PROJECT
    if 0 < fdv <= 100000:
        score += 2
    elif fdv <= 500000:
        score += 1

    # VOLUME 5M
    if volume >= 10000:
        score += 3
    elif volume >= 3000:
        score += 2
    elif volume >= 500:
        score += 1

    # NUMBER OF TRADES
    if trades >= 50:
        score += 2
    elif trades >= 20:
        score += 1

    # BUY PRESSURE
    if trades > 0:

        buy_ratio = buys / trades

        if buy_ratio >= 0.70:
            score += 3

        elif buy_ratio >= 0.60:
            score += 2

        elif buy_ratio >= 0.55:
            score += 1

    return score


def score_label(score):

    if score >= 11:
        return "🔥🔥 EXTREME EARLY MOMENTUM"

    if score >= 8:
        return "🚀 HIGH EARLY MOMENTUM"

    if score >= 5:
        return "👀 EARLY WATCH"

    return "LOW SIGNAL"


def monitor():

    data = get_new_pools()

    if not data:
        return

    pools = data.get("data", [])

    print("New pools received:", len(pools))

    for pool in pools:

        attributes = pool.get("attributes", {})

        pool_address = attributes.get("address", "")

        if not pool_address:
            continue

        if pool_address in seen_pools:
            continue

        seen_pools.add(pool_address)

        name = attributes.get("name", "UNKNOWN")

        created_at = attributes.get(
            "pool_created_at",
            ""
        )

        age = pool_age_minutes(created_at)

        # Ignore older pools
        if age > MAX_AGE_MINUTES:
            continue

        liquidity = safe_float(
            attributes.get("reserve_in_usd")
        )

        fdv = safe_float(
            attributes.get("fdv_usd")
        )

        market_cap = safe_float(
            attributes.get("market_cap_usd")
        )

        volume_data = attributes.get(
            "volume_usd",
            {}
        )

        volume_5m = safe_float(
            volume_data.get("m5")
        )

        tx_data = attributes.get(
            "transactions",
            {}
        )

        tx_5m = tx_data.get(
            "m5",
            {}
        )

        buys = safe_int(
            tx_5m.get("buys")
        )

        sells = safe_int(
            tx_5m.get("sells")
        )

        trades = buys + sells

        # BASIC QUALITY FILTERS

        if liquidity < MIN_LIQUIDITY:
            continue

        if liquidity > MAX_LIQUIDITY:
            continue

        if fdv > MAX_FDV:
            continue

        if fdv > 0 and fdv < MIN_FDV:
            continue

        if volume_5m < MIN_VOLUME_5M:
            continue

        if trades < MIN_TRADES_5M:
            continue

        score = calculate_score(
            age,
            liquidity,
            fdv,
            volume_5m,
            buys,
            sells
        )

        signal = score_label(score)

        buy_ratio = 0

        if trades > 0:
            buy_ratio = (buys / trades) * 100

        print("")
        print("========================================")
        print(signal)
        print("========================================")

        print("Pool:", name)

        print(
            "Age:",
            round(age, 1),
            "minutes"
        )

        print(
            "Liquidity: $",
            round(liquidity, 2)
        )

        print(
            "Market Cap: $",
            round(market_cap, 2)
        )

        print(
            "FDV: $",
            round(fdv, 2)
        )

        print(
            "Volume 5m: $",
            round(volume_5m, 2)
        )

        print(
            "Trades 5m:",
            trades
        )

        print(
            "Buys/Sells:",
            buys,
            "/",
            sells
        )

        print(
            "Buy pressure:",
            round(buy_ratio, 1),
            "%"
        )

        print(
            "MOMENTUM SCORE:",
            score
        )

        print(
            "Pool address:",
            pool_address
        )

        print("========================================")
        print("")


print("")
print("========================================")
print("SOLANA EARLY MOMENTUM MONITOR STARTED")
print("Source: GeckoTerminal")
print("Checking new pools every 60 seconds")
print("========================================")
print("")

while True:

    monitor()

    time.sleep(CHECK_INTERVAL)
