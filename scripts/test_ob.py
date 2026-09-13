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


def bullish_imb(df, k):
    if k + 2 >= len(df):
        return False
    return (df["close"].iloc[k + 1] > df["high"].iloc[k + 2]
            and df["low"].iloc[k] > df["high"].iloc[k + 2])


def bearish_imb(df, k):
    if k + 2 >= len(df):
        return False
    return (df["close"].iloc[k + 1] < df["low"].iloc[k + 2]
            and df["high"].iloc[k] < df["low"].iloc[k + 2])


def find_all_obs(df):
    """
    Full replication of Pine logic.
    For each BOS (on any candle, for any fractal in array), find OB.
    """
    df = df.copy()
    df["ob_top"] = None
    df["ob_bottom"] = None
    df["ob_type"] = None
    df["ob_idx"] = None
    df["ob_time"] = None
    df["ob_bos_idx"] = None

    fractal_highs = []   # list of (value, index)
    fractal_lows = []

    fvg_distance = 3
    bars_back = 500

    for i in range(len(df)):
        # Update fractal arrays
        if df["fractal_high"].iloc[i]:
            fractal_highs.append((df["high"].iloc[i], i))
        if df["fractal_low"].iloc[i]:
            fractal_lows.append((df["low"].iloc[i], i))

        current_close = df["close"].iloc[i]
        current_high = df["high"].iloc[i]
        current_low = df["low"].iloc[i]

        # Check all fractal highs (bullish OB) - iterate from newest to oldest
        for j in range(len(fractal_highs) - 1, -1, -1):
            fractal_high, fractal_idx = fractal_highs[j]
            if current_close > fractal_high:   # BOS!
                idx = None
                min_low = current_high   # initial
                gap_index = None
                # cycle from current to fractal
                for k in range(i, fractal_idx - 1, -1):
                    c = df.iloc[k]
                    if c["close"] < c["open"] and c["low"] < min_low:
                        idx = k
                        min_low = c["low"]
                    if bullish_imb(df, k):
                        gap_index = k + 2
                # FVG filter
                filter_fvg = (gap_index is not None and idx is not None
                              and idx - gap_index >= 0
                              and idx - gap_index <= fvg_distance)
                if idx is not None and idx != i and filter_fvg:
                    df.at[df.index[i], "ob_top"] = df["open"].iloc[idx]
                    df.at[df.index[i], "ob_bottom"] = df["low"].iloc[idx]
                    df.at[df.index[i], "ob_type"] = "bullish"
                    df.at[df.index[i], "ob_idx"] = idx
                    df.at[df.index[i], "ob_time"] = df["ts"].iloc[idx]
                    df.at[df.index[i], "ob_bos_idx"] = i
                    fractal_highs.pop(j)  # remove processed fractal
                    break

        # Check all fractal lows (bearish OB)
        for j in range(len(fractal_lows) - 1, -1, -1):
            fractal_low, fractal_idx = fractal_lows[j]
            if current_close < fractal_low:   # BOS!
                idx = None
                max_high = current_low
                gap_index = None
                for k in range(i, fractal_idx - 1, -1):
                    c = df.iloc[k]
                    if c["close"] > c["open"] and c["high"] > max_high:
                        idx = k
                        max_high = c["high"]
                    if bearish_imb(df, k):
                        gap_index = k + 2
                filter_fvg = (gap_index is not None and idx is not None
                              and idx - gap_index >= 0
                              and idx - gap_index <= fvg_distance)
                if idx is not None and idx != i and filter_fvg:
                    df.at[df.index[i], "ob_top"] = df["high"].iloc[idx]
                    df.at[df.index[i], "ob_bottom"] = df["open"].iloc[idx]
                    df.at[df.index[i], "ob_type"] = "bearish"
                    df.at[df.index[i], "ob_idx"] = idx
                    df.at[df.index[i], "ob_time"] = df["ts"].iloc[idx]
                    df.at[df.index[i], "ob_bos_idx"] = i
                    fractal_lows.pop(j)
                    break

    return df


if __name__ == "__main__":
    raw_dir = "data/raw"
    files = [f for f in os.listdir(raw_dir) if f.endswith(".csv")]
    file_path = os.path.join(raw_dir, files[0])
    print(f"Loading: {file_path}", flush=True)

    df = pd.read_csv(file_path, parse_dates=["ts"])
    print(f"Loaded {len(df)} candles", flush=True)

    df = find_regular_fractals(df)
    df = find_all_obs(df)

    obs = df[df["ob_type"].notna()].reset_index(drop=True)
    print(f"\n=== TOTAL OB: {len(obs)} ===\n", flush=True)

    print(f"{'#':<3} {'OB date':<12} {'Type':<9} {'Top':<10} {'Bottom':<10} {'BOS date':<12}")
    print("-" * 65)
    for i, row in obs.iterrows():
        print(
            f"{i+1:<3} {str(row['ob_time'])[:10]:<12} "
            f"{row['ob_type'].upper():<9} {row['ob_top']:<10.2f} "
            f"{row['ob_bottom']:<10.2f} {str(row['ts'])[:10]:<12}",
            flush=True
        )

    # Debug: OB around September 2026
    print(f"\n=== OB in September 2026 ===", flush=True)
    for _, row in obs.iterrows():
        ts = row["ob_time"]
        if pd.Timestamp("2026-09-01") <= ts <= pd.Timestamp("2026-09-30"):
            print(
                f"{str(row['ob_time'])[:10]} | {row['ob_type']} | "
                f"top={row['ob_top']:.2f} | bottom={row['ob_bottom']:.2f} | "
                f"BOS at {str(row['ts'])[:10]}",
                flush=True
            )
