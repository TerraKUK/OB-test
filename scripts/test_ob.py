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


def find_all_fvgs(df):
    """
    Return list of (fvg_type, gap_index) for all FVGs.
    bullish: close[k+1] > high[k+2] and low[k] > high[k+2]  -> gap_index = k+2
    bearish: close[k+1] < low[k+2]  and high[k] < low[k+2]  -> gap_index = k+2
    """
    fvgs = []
    for k in range(0, len(df) - 2):
        if (df["close"].iloc[k + 1] > df["high"].iloc[k + 2]
                and df["low"].iloc[k] > df["high"].iloc[k + 2]):
            fvgs.append(("bullish", k + 2))

        if (df["close"].iloc[k + 1] < df["low"].iloc[k + 2]
                and df["high"].iloc[k] < df["low"].iloc[k + 2]):
            fvgs.append(("bearish", k + 2))

    return fvgs


def has_fvg_nearby(fvgs, ob_idx, ob_type, max_distance=3):
    """
    Pine: _filterFvg = (gapIndex > 0 and idx > 0 and idx - gapIndex >= 0 and idx - gapIndex <= fvgDistance)
    i.e. OB is at or after FVG, within max_distance candles.
    """
    for fvg_type, gap_index in fvgs:
        if fvg_type != ob_type:
            continue
        dist = ob_idx - gap_index
        if 0 <= dist <= max_distance:
            return True
    return False


def find_ob_for_bos(df, fvgs):
    df = df.copy()
    df["ob_top"] = None
    df["ob_bottom"] = None
    df["ob_type"] = None
    df["ob_idx"] = None
    df["ob_time"] = None

    for i in range(len(df)):
        row = df.iloc[i]

        # BULLISH BOS
        if row["break_high"] and row["fractal_high_idx"] is not None:
            start = i
            end = int(row["fractal_high_idx"])
            best_idx = None
            min_low = float("inf")
            for k in range(start, end - 1, -1):
                candle = df.iloc[k]
                if candle["close"] < candle["open"]:
                    if candle["low"] < min_low:
                        min_low = candle["low"]
                        best_idx = k
            if best_idx is not None and has_fvg_nearby(fvgs, best_idx, "bullish"):
                df.at[df.index[i], "ob_idx"] = best_idx
                df.at[df.index[i], "ob_top"] = df["open"].iloc[best_idx]
                df.at[df.index[i], "ob_bottom"] = df["low"].iloc[best_idx]
                df.at[df.index[i], "ob_type"] = "bullish"
                df.at[df.index[i], "ob_time"] = df["ts"].iloc[best_idx]

        # BEARISH BOS
        if row["break_low"] and row["fractal_low_idx"] is not None:
            start = i
            end = int(row["fractal_low_idx"])
            best_idx = None
            max_high = -float("inf")
            for k in range(start, end - 1, -1):
                candle = df.iloc[k]
                if candle["close"] > candle["open"]:
                    if candle["high"] > max_high:
                        max_high = candle["high"]
                        best_idx = k
            if best_idx is not None and has_fvg_nearby(fvgs, best_idx, "bearish"):
                df.at[df.index[i], "ob_idx"] = best_idx
                df.at[df.index[i], "ob_top"] = df["high"].iloc[best_idx]
                df.at[df.index[i], "ob_bottom"] = df["open"].iloc[best_idx]
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
    print(f"Loading: {file_path}", flush=True)

    df = pd.read_csv(file_path, parse_dates=["ts"])
    print(f"Loaded {len(df)} candles", flush=True)

    df = find_regular_fractals(df)
    df = find_bos(df)

    # Find all FVGs
    fvgs = find_all_fvgs(df)
    bull_fvgs = [g for t, g in fvgs if t == "bullish"]
    bear_fvgs = [g for t, g in fvgs if t == "bearish"]
    print(f"\n=== FVG COUNT ===", flush=True)
    print(f"Bullish FVGs: {len(bull_fvgs)}", flush=True)
    print(f"Bearish FVGs: {len(bear_fvgs)}", flush=True)

    # Show first 10 FVGs
    print(f"\n=== FIRST 10 FVGs ===", flush=True)
    for fvg_type, gap_index in fvgs[:10]:
        print(
            f"{str(df['ts'].iloc[gap_index])[:10]} | {fvg_type} | gap_index={gap_index}",
            flush=True
        )

    # Total BOS count
    print(f"\n=== BOS COUNT ===", flush=True)
    print(f"Bullish BOS: {df['break_high'].sum()}", flush=True)
    print(f"Bearish BOS: {df['break_low'].sum()}", flush=True)

    # Find OB
    df = find_ob_for_bos(df, fvgs)

    obs = df[df["ob_type"].notna()].reset_index(drop=True)

    print(f"\n=== TOTAL OB (with FVG filter): {len(obs)} ===\n", flush=True)

    print(f"{'#':<3} {'OB date':<12} {'Type':<9} {'Top':<10} {'Bottom':<10} {'BOS date':<12}")
    print("-" * 65)
    for i, row in obs.iterrows():
        print(
            f"{i+1:<3} {str(row['ob_time'])[:10]:<12} "
            f"{row['ob_type'].upper():<9} {row['ob_top']:<10.2f} "
            f"{row['ob_bottom']:<10.2f} {str(row['ts'])[:10]:<12}",
            flush=True
        )
