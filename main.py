import time
from datetime import datetime, timezone
import requests
import os
# =====================================================
# SOLANA EARLY PUMP / MOMENTUM MONITOR
# Source: GeckoTerminal
# =====================================================

URL = "https://api.geckoterminal.com/api/v2/networks/solana/new_pools"

HEADERS = {
    "Accept": "application/json;version=20230203"
}
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHECK_INTERVAL = 60
print("Telegram token loaded:", bool(TELEGRAM_BOT_TOKEN))
def get_telegram_chat_id():
    if not TELEGRAM_BOT_TOKEN:
        print("Telegram bot token not found")
        return

    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getUpdates"
        response = requests.get(url, timeout=20)
        data = response.json()

        if data.get("ok") and data.get("result"):
            chat_id = data["result"][-1]["message"]["chat"]["id"]
            print("TELEGRAM CHAT ID:", chat_id)
            return chat_id
        else:
            print("No Telegram messages found")

    except Exception as e:
        print("Telegram Chat ID error:", e)

def send_telegram_message(chat_id, message):
    if not TELEGRAM_BOT_TOKEN or not chat_id:
        return

    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        response = requests.post(
            url,
            data={
                "chat_id": chat_id,
                "text": message
            },
            timeout=20
        )
        response.raise_for_status()
        print("Telegram alert sent")

    except Exception as e:
        print("Telegram send error:", e)


# ---------------- FILTERS ----------------

MAX_AGE_MINUTES = 30

MIN_LIQUIDITY = 2000
MAX_LIQUIDITY = 150000

MIN_FDV = 5000
MAX_FDV = 1000000

MIN_VOLUME_5M = 500
MIN_TRADES_5M = 5

MIN_ALERT_SCORE = 6

# Don't calculate acceleration until enough history exists
MIN_AGE_FOR_ACCELERATION = 10

seen_pools = set()


def safe_float(value):
    try:
        return float(value or 0)
    except (TypeError, ValueError):
        return 0.0


def safe_int(value):
    try:
        return int(value or 0)
    except (TypeError, ValueError):
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

        return max(
            0,
            (now - created).total_seconds() / 60
        )

    except Exception:
        return 999999


def get_tx(transactions, timeframe):
    data = transactions.get(timeframe, {})

    buys = safe_int(data.get("buys"))
    sells = safe_int(data.get("sells"))

    return buys, sells


def calculate_score(
    age,
    liquidity,
    fdv,
    volume_5m,
    volume_1h,
    buys_5m,
    sells_5m,
    buys_1h,
    sells_1h
):
    score = 0
    penalties = 0

    trades_5m = buys_5m + sells_5m
    trades_1h = buys_1h + sells_1h

    # ---------------- AGE: max +3 ----------------

    if age <= 3:
        score += 3
    elif age <= 10:
        score += 2
    elif age <= 30:
        score += 1

    # ---------------- LIQUIDITY: max +2 ----------------

    if 10000 <= liquidity <= 75000:
        score += 2
    elif liquidity >= 5000:
        score += 1

    # ---------------- FDV: max +2 ----------------

    if 20000 <= fdv <= 150000:
        score += 2
    elif 0 < fdv <= 500000:
        score += 1

    # ---------------- VOLUME 5M: max +3 ----------------

    if volume_5m >= 10000:
        score += 3
    elif volume_5m >= 3000:
        score += 2
    elif volume_5m >= 500:
        score += 1

    # ---------------- TRADES 5M: max +2 ----------------

    if trades_5m >= 50:
        score += 2
    elif trades_5m >= 15:
        score += 1

    # =================================================
    # BUY / SELL PRESSURE
    #
    # Strong buying = bonus
    # Strong selling = penalty
    # =================================================

    buy_ratio = 0

    if trades_5m > 0:
        buy_ratio = buys_5m / trades_5m

        # BUYING BONUS

        if buy_ratio >= 0.70:
            score += 3

        elif buy_ratio >= 0.60:
            score += 2

        elif buy_ratio >= 0.55:
            score += 1

        # SELLING PENALTY

        elif buy_ratio < 0.35:
            penalties += 4

        elif buy_ratio < 0.40:
            penalties += 3

        elif buy_ratio < 0.45:
            penalties += 2

        elif buy_ratio < 0.50:
            penalties += 1

    # =================================================
    # ACCELERATION
    # =================================================

    volume_acceleration = None
    trade_acceleration = None

    if age >= MIN_AGE_FOR_ACCELERATION:

        periods_alive = min(
            12,
            max(2, age / 5)
        )

        # ---------------- VOLUME ACCELERATION ----------------

        if volume_1h > 0:

            average_volume = volume_1h / periods_alive

            if average_volume > 0:

                volume_acceleration = (
                    volume_5m / average_volume
                )

                if volume_acceleration >= 3:
                    score += 3

                elif volume_acceleration >= 2:
                    score += 2

                elif volume_acceleration >= 1.3:
                    score += 1

        # ---------------- TRADE ACCELERATION ----------------

        if trades_1h > 0:

            average_trades = trades_1h / periods_alive

            if average_trades > 0:

                trade_acceleration = (
                    trades_5m / average_trades
                )

                if trade_acceleration >= 2.5:
                    score += 2

                elif trade_acceleration >= 1.5:
                    score += 1

    # Apply selling penalties at the end

    raw_score = score
    final_score = max(0, score - penalties)

    return {
        "score": final_score,
        "raw_score": raw_score,
        "penalties": penalties,
        "buy_ratio": buy_ratio,
        "volume_acceleration": volume_acceleration,
        "trade_acceleration": trade_acceleration
    }


def score_label(score):

    if score >= 15:
        return "🚨🚨 EXTREME EARLY MOMENTUM"

    if score >= 12:
        return "🔥 VERY HIGH EARLY MOMENTUM"

    if score >= 9:
        return "🚀 HIGH EARLY MOMENTUM"

    if score >= 6:
        return "👀 EARLY MOMENTUM WATCH"

    return "LOW SIGNAL"


def monitor():

    data = get_new_pools()

    if not data:
        return

    pools = data.get("data", [])

    print("New pools received:", len(pools))

    candidates = 0

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

        # ---------------- VOLUME ----------------

        volume = attributes.get(
            "volume_usd",
            {}
        )

        volume_5m = safe_float(
            volume.get("m5")
        )

        volume_1h = safe_float(
            volume.get("h1")
        )

        # ---------------- TRANSACTIONS ----------------

        transactions = attributes.get(
            "transactions",
            {}
        )

        buys_5m, sells_5m = get_tx(
            transactions,
            "m5"
        )

        buys_1h, sells_1h = get_tx(
            transactions,
            "h1"
        )

        trades_5m = buys_5m + sells_5m

        # ---------------- BASIC FILTERS ----------------

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

        if trades_5m < MIN_TRADES_5M:
            continue

        # ---------------- SCORE ----------------

        result = calculate_score(
            age,
            liquidity,
            fdv,
            volume_5m,
            volume_1h,
            buys_5m,
            sells_5m,
            buys_1h,
            sells_1h
        )

        score = result["score"]

        if score < MIN_ALERT_SCORE:
            continue

        candidates += 1

        label = score_label(score)

        buy_percentage = (
            result["buy_ratio"] * 100
        )

        volume_acceleration = result[
            "volume_acceleration"
        ]

        trade_acceleration = result[
            "trade_acceleration"
        ]

        print("")
        print("========================================")
        print(label)
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
            "Volume 1h: $",
            round(volume_1h, 2)
        )

        print(
            "Trades 5m:",
            trades_5m
        )

        print(
            "Buys/Sells 5m:",
            buys_5m,
            "/",
            sells_5m
        )

        print(
            "Buy pressure:",
            round(buy_percentage, 1),
            "%"
        )

        # Show selling penalty

        if result["penalties"] > 0:
            print(
                "⚠️ Selling pressure penalty:",
                "-",
                result["penalties"],
                "points"
            )

        # Show acceleration

        if volume_acceleration is None:

            print(
                "Volume acceleration: N/A "
                "(pool too new)"
            )

        else:

            print(
                "Volume acceleration:",
                round(volume_acceleration, 2),
                "x"
            )

        if trade_acceleration is None:

            print(
                "Trade acceleration: N/A "
                "(pool too new)"
            )

        else:

            print(
                "Trade acceleration:",
                round(trade_acceleration, 2),
                "x"
            )

        print(
            "Raw score:",
            result["raw_score"]
        )

        print(
            "FINAL MOMENTUM SCORE:",
            score,
            "/ 18"
        )

        print(
            "Pool address:",
            pool_address
        )

        print("========================================")
        print("")

    print(
        "Candidates this cycle:",
        candidates
    )


print("")
print("========================================")
print("SOLANA EARLY PUMP MONITOR STARTED")
print("Source: GeckoTerminal")
print("Fake 12x fix: ACTIVE")
print("Selling pressure filter: ACTIVE")
print("Checking every 60 seconds")
print("========================================")
print("")
TELEGRAM_CHAT_ID = get_telegram_chat_id()
while True:

    monitor()

    time.sleep(CHECK_INTERVAL)
