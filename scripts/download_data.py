import os
import requests
import pandas as pd
from datetime import datetime, timedelta, timezone

API_BASE_URL = "https://api.binance.us"
RAW_DATA_DIR = "data/raw"

PAIRS = [
    "BTCUSDT", "ETHUSDT", "BNBUSDT", "XRPUSDT", "SOLUSDT",
    "TRXUSDT", "HYPEUSDT", "ZECUSDT", "DOGEUSDT", "XMRUSDT",
    "LINKUSDT", "ADAUSDT", "XLMUSDT", "BCHUSDT", "UNIUSDT",
    "LTCUSDT", "TONUSDT", "HBARUSDT", "AVAXUSDT", "SUIUSDT",
    "SHIBUSDT", "NEARUSDT", "TAOUSDT", "CROUSDT", "OKBUSDT",
    "AAVEUSDT", "MNTUSDT", "ONDOUSDT", "WLFIUSDT", "ENAUSDT",
    "DOTUSDT", "SKYUSDT", "PUMPUSDT", "WLDUSDT", "ICPUSDT",
    "PEPEUSDT", "BGBUSDT", "MORPHOUSDT", "ARBUSDT", "ETCUSDT",
    "PIUSDT", "POLUSDT", "JUPUSDT", "KASUSDT", "ALGOUSDT",
    "ATOMUSDT", "RENDERUSDT", "QNTUSDT", "FILUSDT", "VETUSDT",
    "XDCUSDT", "CRVUSDT", "FLRUSDT", "APTUSDT", "INJUSDT",
    "STXUSDT", "PYTHUSDT", "ZROUSDT", "TIAUSDT", "FETUSDT",
    "SEIUSDT", "PENDLEUSDT", "LDOUSDT", "RAYUSDT", "BSVUSDT",
    "GNOUSDT", "IMXUSDT", "OPUSDT", "ENSUSDT", "FLOKIUSDT",
    "STRKUSDT", "JASMYUSDT", "WIFUSDT", "GRTUSDT", "COMPUSDT",
    "KAIAUSDT", "ARUSDT", "THETAUSDT", "AXSUSDT", "RUNEUSDT",
    "NEOUSDT", "MANAUSDT", "CHZUSDT", "APEUSDT", "EGLDUSDT",
    "1INCHUSDT", "SANDUSDT", "ZKUSDT", "GALAUSDT", "DYDXUSDT",
    "MINAUSDT", "QTUMUSDT", "ORDIUSDT", "SUSDT", "TWTUSDT",
    "CFXUSDT", "KITEUSDT", "KSMUSDT", "SNXUSDT", "BONKUSDT",
    "RBUSDT", "BTRUSDT", "ASTERUSDT", "USELESSUSDT",
    "BLURUSDT", "VVVUSDT", "APEXUSDT", "GRAMUSDT", "BRUSDT",
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
            if df is None:
                continue
            output = f"{RAW_DATA_DIR}/{pair}_{INTERVAL}.csv"
            df.to_csv(output, index=False)
            print(f"Saved {pair}: {len(df)} candles -> {output}")
        except Exception as e:
            print(f"Failed {pair}: {e}")


if __name__ == "__main__":
    main()
