import os
import requests
import pandas as pd
from datetime import datetime, timedelta, timezone

API_BASE_URL = "https://api.binance.us"
RAW_DATA_DIR = "data/raw"

PAIRS = [
    "BTCUSDT", "ETHUSDT", "BNBUSDT", "XRPUSDT", "SOLUSDT",
    "TRXUSDT", "HYPEUSDT", "ZECUSDT", "DOGEUSDT", "LINKUSDT",
    "ADAUSDT", "XLMUSDT", "BCHUSDT", "UNIUSDT", "LTCUSDT",
    "HBARUSDT", "AVAXUSDT", "SUIUSDT", "SHIBUSDT", "NEARUSDT",
    "AAVEUSDT", "ONDOUSDT", "WLFIUSDT", "ENAUSDT", "DOTUSDT",
    "SKYUSDT", "PUMPUSDT", "WLDUSDT", "ICPUSDT", "PEPEUSDT",
    "ARBUSDT", "ETCUSDT", "POLUSDT", "JUPUSDT", "ALGOUSDT",
    "ATOMUSDT", "RENDERUSDT", "QNTUSDT", "FILUSDT", "VETUSDT",
    "XDCUSDT", "CRVUSDT", "APTUSDT", "INJUSDT", "TIAUSDT",
    "FETUSDT", "SEIUSDT", "LDOUSDT", "IMXUSDT", "OPUSDT",
    "ENSUSDT", "FLOKIUSDT", "JASMYUSDT", "WIFUSDT", "GRTUSDT",
    "COMPUSDT", "THETAUSDT", "AXSUSDT", "NEOUSDT", "MANAUSDT",
    "CHZUSDT", "APEUSDT", "EGLDUSDT", "1INCHUSDT", "SANDUSDT",
    "GALAUSDT", "QTUMUSDT", "SUSDT", "TWTUSDT", "KSMUSDT",
    "SNXUSDT", "BONKUSDT", "ASTERUSDT", "USELESSUSDT",
    "BLURUSDT", "GRAMUSDT",
]

STABLECOINS = {
    "USDC", "BUSD", "DAI", "TUSD", "USDP", "USDD",
    "USD1", "FDUSD", "PYUSD", "USDE", "USDS", "USDF", "GUSD",
    "UST", "USTC", "FRAX", "LUSD", "SUSD", "MIM", "ALUSD",
}

INTERVAL = "1d"
DAYS_BACK = 365

os.makedirs(RAW_DATA_DIR, exist_ok=True)


def fetch_klines(pair):
    base = pair.replace("USDT", "")
    if base in STABLECOINS:
        print(f"Skip {pair}: stablecoin")
        return None

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
        response = requests.get(endpoint, params=params, timeout=30)
        response.raise_for_status()
        batch = response.json()
        if not batch:
            break
        all_data.extend(batch)
        params["startTime"] = batch[-1][0] + 1

    if not all_data:
        print(f"Skip {pair}: exchange returned no candles")
        return None

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
            if df is None:
                continue
            output = f"{RAW_DATA_DIR}/{pair}_{INTERVAL}.csv"
            df.to_csv(output, index=False)
            print(f"Saved {pair}: {len(df)} candles -> {output}")
        except Exception as e:
            print(f"Failed {pair}: {e}")


if __name__ == "__main__":
    main()
