import os
import pandas as pd


def find_regular_fractals(df):
    df = df.copy()
    df["fractal_high"] = False
    df["fractal_low"] = False

    for i in range(1, len(df) - 1):
        curr_high = df["high"].iloc[i]
        curr_low = df["low"].iloc[i]

        if curr_high > df["high"].iloc[i - 1] and curr_high > df["high"].iloc[i + 1]:
            df.at[df.index[i], "fractal_high"] = True

        if curr_low < df["low"].iloc[i - 1] and curr_low < df["low"].iloc[i + 1]:
            df.at[df.index[i], "fractal_low"] = True

    return df


def find_bos(df):
    """Track last fractal, mark breakouts. Store fractal index for later."""
    df = df.copy()
    df["break_high"] = False
    df["break_low"] = False
    df["fractal_high_idx"] = None
    df["fractal_low_idx"] = None

    last_high_idx = None
    last_low_idx = None

    for i in range(len(df)):
        row = df.iloc[i]

        if row["fractal_high"]:
            last_high_idx = i
        if row["fractal_low"]:
            last_low_idx = i

        if last_high_idx is not None and row["close"] > df["high"].iloc[last_high_idx]:
            df.at[df.index[i], "break_high"] = True
            df.at[df.index[i], "fractal_high_idx"] = last_high_idx
            last_high_idx = None

        if last_low_idx is not None and row["close"] < df["low"].iloc[last_low_idx]:
            df.at[df.index[i], "break_low"] = True
            df.at[df.index[i], "fractal_low_idx"] = last_low_idx
            last_low_idx = None

    return df


def find_ob_for_bos(df):
    """
    For each BOS, find the OB candle:
    - Bullish BOS: find red candle with lowest low between fractal and breakout
    - Bearish BOS: find green candle with highest high between fractal and breakout
    """
    df = df.copy()
    df["ob_price"] = None
    df["ob_type"] = None
    df["ob_idx"] = None
    df["ob_time"] = None

    for i in range(len(df)):
        row = df.iloc[i]

        # BULLISH BOS: find OB between fractal_high_idx and i
        if row["break_high"] and row["fractal_high_idx"] is not None:
            start = int(row["fractal_high_idx"])
            end = i
            best_idx = None
            min_low = float("inf")
            for k in range(start, end + 1):
                candle = df.iloc[k]
                if candle["close"] < candle["open"]:   # red candle
                    if candle["low"] < min_low:
                        min_low = candle["low"]
                        best_idx = k
            if best_idx is not None:
                df.at[df.index[i], "ob_idx"] = best_idx
                df.at[df.index[i], "ob_price"] = df["high"].iloc[best_idx]  # body top
                df.at[df.index[i], "ob_type"] = "bullish"
                df.at[df.index[i], "ob_time"] = df["ts"].iloc[best_idx]

        # BEARISH BOS: find OB between fractal_low_idx and i
        if row["break_low"] and row["fractal_low_idx"] is not None:
            start = int(row["fractal_low_idx"])
            end = i
            best_idx = None
            max_high = -float("inf")
            for k in range(start, end + 1):
                candle = df.iloc[k]
                if candle["close"] > candle["open"]:   # green candle
                    if candle["high"] > max_high:
                        max_high = candle["high"]
                        best_idx = k
            if best_idx is not None:
                df.at[df.index[i], "ob_idx"] = best_idx
                df.at[df.index[i], "ob_price"] = df["low"].iloc[best_idx]   # body bottom
                df.at[df.index[i], "ob_type"] = "bearish"
                df.at[df.index[i], "ob_time"] = df["ts"].iloc[best_idx]

    return df


if __name__ == "__main__":
    raw_dir = "data/raw"
    files = [f for f in os.listdir(raw_dir) if f.endswith(".csv")]
    if not files:
        print("No CSV files in data/raw/")
        exit(1)

    file_path = os.path.join(raw_dir, files[0])
    print(f"Loading: {file_path}")

    df = pd.read_csv(file_path, parse_dates=["ts"])
    print(f"Loaded {len(df)} candles")

    df = find_regular_fractals(df)
    df = find_bos(df)
    df = find_ob_for_bos(df)

    obs = df[df["ob_type"].notna()]
    print(f"\n=== RESULTS ===")
    print(f"Total OB detected: {len(obs)}")

    print(f"\n=== LAST 15 OB ===")
    for _, row in obs.tail(15).iterrows():
        print(
            f"{row['ob_time']} | {row['ob_type'].upper():8} | "
            f"OB price={row['ob_price']:.4f} | BOS at {row['ts']}"
        )
