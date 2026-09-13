import os
import pandas as pd


def find_regular_fractals(df):
    """3-bar fractals. Mark on center candle."""
    df = df.copy()
    df["fractal_high"] = False
    df["fractal_low"] = False

    for i in range(1, len(df) - 1):
        if df["high"].iloc[i] > df["high"].iloc[i - 1] and df["high"].iloc[i] > df["high"].iloc[i + 1]:
            df.at[df.index[i], "fractal_high"] = True
        if df["low"].iloc[i] < df["low"].iloc[i - 1] and df["low"].iloc[i] < df["low"].iloc[i + 1]:
            df.at[df.index[i], "fractal_low"] = True

    return df


def bullish_imb(df, k):
    """Pine: close[k+1] > high[k+2] and low[k] > high[k+2]. k - bar offset back."""
    if k + 2 >= len(df):
        return False
    return (df["close"].iloc[k + 1] > df["high"].iloc[k + 2]
            and df["low"].iloc[k] > df["high"].iloc[k + 2])


def bearish_imb(df, k):
    """Pine: close[k+1] < low[k+2] and high[k] < low[k+2]."""
    if k + 2 >= len(df):
        return False
    return (df["close"].iloc[k + 1] < df["low"].iloc[k + 2]
            and df["high"].iloc[k] < df["low"].iloc[k + 2])


def find_all_obs(df):
    """
    Full Pine replication. Keep duplicates.
    Iterates k as bar offset back (0 = current candle).
    """
    df = df.copy()
    df["ob_top"] = None
    df["ob_bottom"] = None
    df["ob_type"] = None
    df["ob_idx"] = None
    df["ob_time"] = None
    df["ob_fractal_time"] = None

    fractal_highs = []   # list of (value, abs_index)
    fractal_lows = []

    fvg_distance = 3
    bars_back = 500

    for i in range(len(df)):
        # Update fractal arrays on current candle
        if df["fractal_high"].iloc[i]:
            fractal_highs.append((df["high"].iloc[i], i))
        if df["fractal_low"].iloc[i]:
            fractal_lows.append((df["low"].iloc[i], i))

        current_close = df["close"].iloc[i]

        # --- BULLISH OB: break of fractal high ---
        j = 0
        while j < len(fractal_highs):
            fractal_high, fractal_idx = fractal_highs[j]

            if current_close > fractal_high:
                # BOS confirmed. Iterate k back from current candle to fractal
                idx_abs = None
                min_low = df["high"].iloc[i]   # Pine: minLow = high (current)
                gap_idx_abs = None

                for k in range(0, bars_back):
                    idx_bar = i - k
                    if idx_bar < fractal_idx:
                        break
                    c = df.iloc[idx_bar]
                    if c["close"] < c["open"] and c["low"] < min_low:
                        idx_abs = idx_bar
                        min_low = c["low"]
                    if bullish_imb(df, k):
                        # Pine: gapIndex := k + 2 (offset back). abs index = i - (k+2)
                        gap_idx_abs = i - (k + 2)

                # FVG filter: idx != 0 (offset), and 0 <= idx_offset - gapIndex_offset <= 3
                if idx_abs is not None and idx_abs != i and gap_idx_abs is not None:
                    # offsets back
                    idx_offset = i - idx_abs
                    gap_offset = i - gap_idx_abs
                    filter_fvg = (0 <= idx_offset - gap_offset <= fvg_distance)
                else:
                    filter_fvg = False

                if idx_abs is not None and idx_abs != i and filter_fvg:
                    df.at[df.index[i], "ob_top"] = df["open"].iloc[idx_abs]
                    df.at[df.index[i], "ob_bottom"] = df["low"].iloc[idx_abs]
                    df.at[df.index[i], "ob_type"] = "bullish"
                    df.at[df.index[i], "ob_idx"] = idx_abs
                    df.at[df.index[i], "ob_time"] = df["ts"].iloc[idx_abs]
                    df.at[df.index[i], "ob_fractal_time"] = df["ts"].iloc[fractal_idx]

                fractal_highs.pop(j)
            else:
                j += 1

        # --- BEARISH OB: break of fractal low ---
        j = 0
        while j < len(fractal_lows):
            fractal_low, fractal_idx = fractal_lows[j]

            if current_close < fractal_low:
                idx_abs = None
                max_high = df["low"].iloc[i]
                gap_idx_abs = None

                for k in range(0, bars_back):
                    idx_bar = i - k
                    if idx_bar < fractal_idx:
                        break
                    c = df.iloc[idx_bar]
                    if c["close"] > c["open"] and c["high"] > max_high:
                        idx_abs = idx_bar
                        max_high = c["high"]
                    if bearish_imb(df, k):
                        gap_idx_abs = i - (k + 2)

                if idx_abs is not None and idx_abs != i and gap_idx_abs is not None:
                    idx_offset = i - idx_abs
                    gap_offset = i - gap_idx_abs
                    filter_fvg = (0 <= idx_offset - gap_offset <= fvg_distance)
                else:
                    filter_fvg = False

                if idx_abs is not None and idx_abs != i and filter_fvg:
                    df.at[df.index[i], "ob_top"] = df["high"].iloc[idx_abs]
                    df.at[df.index[i], "ob_bottom"] = df["open"].iloc[idx_abs]
                    df.at[df.index[i], "ob_type"] = "bearish"
                    df.at[df.index[i], "ob_idx"] = idx_abs
                    df.at[df.index[i], "ob_time"] = df["ts"].iloc[idx_abs]
                    df.at[df.index[i], "ob_fractal_time"] = df["ts"].iloc[fractal_idx]

                fractal_lows.pop(j)
            else:
                j += 1

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
    print(f"\n=== TOTAL OB (with FVG filter, duplicates kept): {len(obs)} ===\n", flush=True)

    print(f"{'#':<3} {'OB date':<12} {'Type':<9} {'Top':<10} {'Bottom':<10} {'BOS date':<12}")
    print("-" * 65)
    for i, row in obs.iterrows():
        print(
            f"{i+1:<3} {str(row['ob_time'])[:10]:<12} "
            f"{row['ob_type'].upper():<9} {row['ob_top']:<10.2f} "
            f"{row['ob_bottom']:<10.2f} {str(row['ts'])[:10]:<12}",
            flush=True
        )

    # Debug: September 2026
    print(f"\n=== OB in September 2026 ===", flush=True)
    for _, row in obs.iterrows():
        ts = row["ob_time"]
        if pd.Timestamp("2026-09-01") <= ts <= pd.Timestamp("2026-09-30"):
            print(
                f"{str(row['ob_time'])[:10]} | {row['ob_type']} | "
                f"top={row['ob_top']:.2f} | bottom={row['ob_bottom']:.2f}",
                flush=True
            )
