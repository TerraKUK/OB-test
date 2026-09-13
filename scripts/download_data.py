"""Download closed daily USDT perpetual candles from Bybit Linear."""

import os
from datetime import datetime, timedelta, timezone

import pandas as pd
import requests


# Official Bybit Kazakhstan mainnet host for Kazakhstan accounts.
API_BASE_URL = "https://api.bybit.kz"
MARKET_CATEGORY = "linear"
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

INTERVAL = "D"
FILE_INTERVAL = "1d"
DAYS_BACK = 365
DAY_MS = 24 * 60 * 60 * 1000

os.makedirs(RAW_DATA_DIR, exist_ok=True)


def fetch_klines(pair: str) -> pd.DataFrame | None:
    """Fetch only completed D1 candles; Bybit returns newest candles first."""
    params = {
        "category": MARKET_CATEGORY,
        "symbol": pair,
        "interval": INTERVAL,
        "start": int((datetime.now(timezone.utc) - timedelta(days=DAYS_BACK)).timestamp() * 1000),
        "limit": 1000,
    }
    response = requests.get(f"{API_BASE_URL}/v5/market/kline", params=params, timeout=30)
    response.raise_for_status()
    payload = response.json()
    if payload.get("retCode") != 0:
        print(f"Skip {pair}: Bybit error {payload.get('retMsg', 'unknown error')}")
        return None

    rows = payload.get("result", {}).get("list", [])
    if not rows:
        print(f"Skip {pair}: Bybit returned no candles")
        return None

    # Bybit: startTime, open, high, low, close, volume, turnover.
    df = pd.DataFrame(rows, columns=["ts", "open", "high", "low", "close", "volume", "quote_asset_volume"])
    df["ts"] = pd.to_numeric(df["ts"], errors="coerce")
    for column in ("open", "high", "low", "close", "volume", "quote_asset_volume"):
        df[column] = pd.to_numeric(df[column], errors="coerce")
    df = df.dropna().sort_values("ts").drop_duplicates("ts")
    df["close_time"] = df["ts"] + DAY_MS - 1
    df["num_trades"] = None
    df["taker_buy_base"] = None
    df["taker_buy_quote"] = None
    df["ignore"] = None

    now_ms = datetime.now(timezone.utc).timestamp() * 1000
    df = df[df["close_time"] < now_ms].copy()
    df["ts"] = pd.to_datetime(df["ts"], unit="ms", utc=True)
    return df.reset_index(drop=True)


def main() -> None:
    saved = 0
    for pair in PAIRS:
        try:
            df = fetch_klines(pair)
            if df is None:
                continue
            output = f"{RAW_DATA_DIR}/{pair}_{FILE_INTERVAL}.csv"
            df.to_csv(output, index=False)
            saved += 1
            print(f"Saved {pair}: {len(df)} Bybit Linear candles -> {output}")
        except requests.RequestException as error:
            print(f"Failed {pair}: {error}")
        except (TypeError, ValueError) as error:
            print(f"Failed {pair}: invalid Bybit response ({error})")

    if saved == 0:
        raise SystemExit("Bybit Kazakhstan returned no data; stopping to avoid using stale CSV files.")


if __name__ == "__main__":
    main()
