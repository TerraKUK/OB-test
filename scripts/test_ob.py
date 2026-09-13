import os
import pandas as pd


def find_regular_fractals(df):
    """
    Pine: isRegularFractal
    Buy:  high[0] < high[1] and (high[2] < high[1] or (high[2] == high[1] and high[3] < high[2]))
    Sell: low[0] > low[1]  and (low[2] > low[1]  or (low[2] == low[1]  and low[3] > low[2]))
    In Pine [0] = current bar. The fractal is confirmed at bar i (current),
    and the center of the fractal is at bar i-1 (for 3-bar) -> offset -1 in plotshape.
    So: fractal_high is True on bar i if high[i-1] is the local max.
    We mark the CENTER candle (i-1) as fractal in our DataFrame.
    """
    df = df.copy()
    df["fractal_high"] = False
    df["fractal_low"] = False

    for i in range(1, len(df) - 1):
        # center candle is i, neighbors i-1 and i+1
        if df["high"].iloc[i] > df["high"].iloc[i - 1] and df["high"].iloc[i] > df["high"].iloc[i + 1]:
            df.at[df.index[i], "fractal_high"] = True
        if df["low"].iloc[i] < df["low"].iloc[i - 1] and df["low"].iloc[i] < df["low"].iloc[i + 1]:
            df.at[df.index[i], "fractal_low"] = True

    return df


def bullish_imb(df, k):
    """
    Pine: close[k+1] > high[k+2] and low[k] > high[k+2]
    k = offset back from current bar (0 = current).
    """
    if k + 2 >= len(df):
        return False
    return (df["close"].iloc[k + 1] > df["high"].iloc[k + 2]
            and df["low"].iloc[k] > df["high"].iloc[k + 2])


def bearish_imb(df, k):
    """
    Pine: close[k+1] < low[k+2] and high[k] < low[k+2]
    """
    if k + 2 >= len(df):
        return False
    return (df["close"].iloc[k + 1] < df["low"].iloc[k + 2]
            and df["high"].iloc[k] < df["low"].iloc[k + 2])


def find_all_obs(df):
    """
    Pine replication. Uses bar offsets back (0 = current bar).
    Keeps duplicates (each BOS -> own OB).
    """
    df = df.copy()
    df["ob_top"] = None
    df["ob_bottom"] = None
    df["ob_type"] = None
    df["ob_idx"] = None
    df["ob_time"] = None
    df["ob_bos_idx"] = None
    df["ob_fractal_time"] = None

    # Arrays of fractals: (value, abs_index)
    fractal_highs = []
    fractal_lows = []

    fvg_distance = 3
    bars_back = 500

    for i in range(len(df)):
        # Push new fractals
        if df["fractal_high"].iloc[i]:
            fractal_highs.append((df["high"].iloc[i], i))
        if df["fractal_low"].iloc[i]:
            fractal_lows.append((df["low"].iloc[i], i))

        current_close = df["close"].iloc[i]

        # ---------- BULLISH OB (fractal HIGH break) ----------
        # Pine: for i = array.size - 1 downto 0 by 1
        j = len(fractal_highs) - 1
        while j >= 0:
            fractal_high, fractal_idx = fractal_highs[j]

            if current_close > fractal_high:
                # BOS. Search OB and FVG.
                idx_abs = None         # abs index of OB candle
                min_low = df["high"].iloc[i]   # Pine: minLow = high (current)
                gap_idx_abs = None     # abs index of left FVG candle

                for k in range(0, bars_back):
                    bar_abs = i - k
                    if bar_abs < fractal_idx:
                        break
                    # condition: close[bar] < open[bar]
                    if df["close"].iloc[bar_abs] < df["open"].iloc[bar_abs] and df["low"].iloc[bar_abs] < min_low:
                        idx_abs = bar_abs
                        min_low = df["low"].iloc[bar_abs]
                    # bullishImb(k): compare abs i-k-1, i-k-2
                    if k + 2 < len(df):
                        close_k1 = df["close"].iloc[i - k - 1]
                        high_k2 = df["high"].iloc[i - k - 2]
                        low_k = df["low"].iloc[i - k]
                        if close_k1 > high_k2 and low_k > high_k2:
                            # Pine: gapIndex := k + 2 -> abs = i - (k + 2)
                            gap_idx_abs = i - (k + 2)

                # FVG filter: idx != 0 (offset), gapIndex != 0 (offset),
                # 0 <= idx_offset - gapIndex_offset <= fvg_distance
                filter_fvg = False
                if idx_abs is not None and gap_idx_abs is not None:
                    idx_offset = i - idx_abs
                    gap_offset = i - gap_idx_abs
                    if gap_offset > 0 and idx_offset > 0:
                        diff = idx_offset - gap_offset
                        if 0 <= diff <= fvg_distance:
                            filter_fvg = True

                # Pine: if idx != 0 and _filterFvg
                if idx_abs is not None and (i - idx_abs) > 0 and filter_fvg:
                    df.at[df.index[i], "ob_top"] = df["open"].iloc[idx_abs]
                    df.at[df.index[i], "ob_bottom"] = df["low"].iloc[idx_abs]
                    df.at[df.index[i], "ob_type"] = "bullish"
                    df.at[df.index[i], "ob_idx"] = idx_abs
                    df.at[df.index[i], "ob_time"] = df["ts"].iloc[idx_abs]
                    df.at[df.index[i], "ob_bos_idx"] = i
                    df.at[df.index[i], "ob_fractal_time"] = df["ts"].iloc[fractal_idx]

                # Pine: array.remove (always)
                fractal_highs.pop(j)
                j -= 1
            else:
                j -= 1

        # ---------- BEARISH OB (fractal LOW break) ----------
        j = len(fractal_lows) - 1
        while j >= 0:
            fractal_low, fractal_idx = fractal_lows[j]

            if current_close < fractal_low:
                idx_abs = None
                max_high = df["low"].iloc[i]   # Pine: maxHigh = low (current)
                gap_idx_abs = None

                for k in range(0, bars_back):
                    bar_abs = i - k
                    if bar_abs < fractal_idx:
                        break
                    if df["close"].iloc[bar_abs] > df["open"].iloc[bar_abs] and df["high"].iloc[bar_abs] > max_high:
                        idx_abs = bar_abs
                        max_high = df["high"].iloc[bar_abs]
                    if k + 2 < len(df):
                        close_k1 = df["close"].iloc[i - k - 1]
                        low_k2 = df["low"].iloc[i - k - 2]
                        high_k = df["high"].iloc[i - k]
                        if close_k1 < low_k2 and high_k < low_k2:
                            gap_idx_abs = i - (k + 2)

                filter_fvg = False
                if idx_abs is not None and gap_idx_abs is not None:
                    idx_offset = i - idx_abs
                    gap_offset = i - gap_idx_abs
                    if gap_offset > 0 and idx_offset > 0:
                        diff = idx_offset - gap_offset
                        if 0 <= diff <= fvg_distance:
                            filter_fvg = True

                if idx_abs is not None and (i - idx_abs) > 0 and filter_fvg:
                    df.at[df.index[i], "ob_top"] = df["high"].iloc[idx_abs]
                    df.at[df.index[i], "ob_bottom"] = df["open"].iloc[idx_abs]
                    df.at[df.index[i], "ob_type"] = "bearish"
                    df.at[df.index[i], "ob_idx"] = idx_abs
                    df.at[df.index[i], "ob_time"] = df["ts"].iloc[idx_abs]
                    df.at[df.index[i], "ob_bos_idx"] = i
                    df.at[df.index[i], "ob_fractal_time"] = df["ts"].iloc[fractal_idx]

                fractal_lows.pop(j)
                j -= 1
            else:
                j -= 1

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
    print(f"First: {df['ts'].iloc[0]} | Last: {df['ts'].iloc[-1]}", flush=True)

    df = find_regular_fractals(df)
    df = find_all_obs(df)

    obs = df[df["ob_type"].notna()].reset_index(drop=True)
    print(f"\n=== TOTAL OB: {len(obs)} ===\n", flush=True)

    print(f"{'#':<3} {'OB date':<12} {'Type':<9} {'Top':<10} {'Bottom':<10} {'BOS date':<12}")
    print("-" * 65)
    for idx, row in obs.iterrows():
        print(
            f"{idx+1:<3} {str(row['ob_time'])[:10]:<12} "
            f"{row['ob_type'].upper():<9} {row['ob_top']:<10.2f} "
            f"{row['ob_bottom']:<10.2f} {str(row['ts'])[:10]:<12}",
            flush=True
        )
