import os
import requests
import pandas as pd
from datetime import datetime, timedelta, timezone

API_BASE_URL = "https://api.binance.us"
RAW_DATA_DIR = "data/raw"

PAIRS = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "INJUSDT"]
INTERVAL = "1d"
DAYS_BACK = 365

os.makedirs(RAW_DATA_DIR, exist_ok=True)


def fetch_klines(pair):
    endpoint = f"{API_BASE_URL}/api/v3/klines"
    start_date = datetime.now(timezone.utc) - timedelta(days=DAYS_BACK)
    params = {
        "symbol": pair,
        "interval": INTERVAL,
        "startTime": int(start_date.timestamp() * 1000),
        "limit": 1000
    }

    all_data = []
    while True:
        response = requests.get(endpoint, params=params)
        response.raise_for_status()
        batch = response.json()
        if not batch:
            break
        all_data.extend(batch)
        params["startTime"] = batch[-1][0] + 1

    df = pd.DataFrame(all_data, columns=[
        "ts", "open", "high", "low", "close", "volume", "close_time",
        "quote_asset_volume", "num_trades", "taker_buy_base",
        "taker_buy_quote", "ignore"
    ])
    df["ts"] = pd.to_datetime(df["ts"], unit='ms')
    df[["open", "high", "low", "close"]] = df[["open", "high", "low", "close"]].astype(float)

    now_ms = datetime.now(timezone.utc).timestamp() * 1000
    df = df[df["close_time"] < now_ms]
    df = df.reset_index(drop=True)

    return df


def main():
    for pair in PAIRS:
        try:
            df = fetch_klines(pair)
            output = f"{RAW_DATA_DIR}/{pair}_{INTERVAL}.csv"
            df.to_csv(output, index=False)
            print(f"Saved {pair}: {len(df)} candles -> {output}")
        except Exception as e:
            print(f"Failed {pair}: {e}")


if __name__ == "__main__":
    main()
