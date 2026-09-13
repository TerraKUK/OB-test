import os
import pandas as pd


def find_regular_fractals(df):
    """
    Pine isRegularFractal for 3-bar:
    Confirmed on bar [0] (current). Center of fractal is bar [1].
    So on candle i (in Python), if high[i] > high[i-1] and high[i] > high[i+1],
    then this candle is the CENTER. Mark it.
    """
    df = df.copy()
    df["fractal_high"] = False
    df["fractal_low"] = False

    for i in range(1, len(df) - 1):
        if df["high"].iloc[i] > df["high"].iloc[i - 1] and df["high"].iloc[i] > df["high"].iloc[i + 1]:
            df.at[df.index[i], "fractal_high"] = True
        if df["low"].iloc[i] < df["low"].iloc[i - 1] and df["low"].iloc[i] < df["low"].iloc[i + 1]:
            df.at[df.index[i], "fractal_low"] = True

    return df


def find_all_obs(df):
    """
    Pine replication.

    Pine uses bar offsets back (0 = current bar):
      k = 0 -> current bar
      k = 1 -> 1 bar back
      ...

    idx      - offset back to OB candle
    gapIndex - offset back to left FVG candle
    fractalTime - time of fractal center candle

    Condition for FVG filter:
      gapIndex > 0 AND idx > 0 AND 0 <= (idx - gapIndex) <= fvgDistance
    """
    df = df.copy()
    df["ob_top"] = None
    df["ob_bottom"] = None
    df["ob_type"] = None
    df["ob_idx"] = None
    df["ob_time"] = None
    df["ob_bos_idx"] = None
    df["ob_fractal_time"] = None

    # Arrays: list of dicts {value, ts, abs_idx}
    fractal_highs = []
    fractal_lows = []

    fvg_distance = 3
    bars_back = 500

    for i in range(len(df)):
        # Push new fractals on candle i
        if df["fractal_high"].iloc[i]:
            fractal_highs.append({"value": df["high"].iloc[i], "ts": df["ts"].iloc[i], "abs_idx": i})
        if df["fractal_low"].iloc[i]:
            fractal_lows.append({"value": df["low"].iloc[i], "ts": df["ts"].iloc[i], "abs_idx": i})

        current_close = df["close"].iloc[i]

        # ========== BULLISH OB (fractal HIGH break) ==========
        # Pine: for i = array.size(fractal_highs) - 1 to 0 by 1
        #       (iterate from end to start of array; check each; remove after check)
        j = len(fractal_highs) - 1
        while j >= 0:
            fh = fractal_highs[j]
            fractal_high = fh["value"]
            fractal_ts = fh["ts"]
            fractal_abs_idx = fh["abs_idx"]

            if current_close > fractal_high:
                # BOS confirmed. Find OB and FVG.
                idx = 0                # Pine: idx = 0
                min_low = df["high"].iloc[i]   # Pine: minLow = high (current)
                gap_index = 0          # Pine: gapIndex = 0

                # for k = 0 to bars_back
                for k in range(0, bars_back):
                    abs_k = i - k
                    if abs_k < 0:
                        break
                    # if time[k] < fractalTime: break
                    if df["ts"].iloc[abs_k] < fractal_ts:
                        break
                    # if close[k] < open[k] and low[k] < minLow
                    if df["close"].iloc[abs_k] < df["open"].iloc[abs_k] and df["low"].iloc[abs_k] < min_low:
                        idx = k
                        min_low = df["low"].iloc[abs_k]
                    # if bullishImb(k): gapIndex := k + 2
                    if k + 2 < len(df):
                        close_k1 = df["close"].iloc[i - k - 1]
                        high_k2 = df["high"].iloc[i - k - 2]
                        low_k = df["low"].iloc[i - k]
                        if close_k1 > high_k2 and low_k > high_k2:
                            gap_index = k + 2

                # _filterFvg = filterFvgs ? (gapIndex > 0 and idx > 0 and idx - gapIndex >= 0 and idx - gapIndex <= fvgDistance) : true
                if gap_index > 0 and idx > 0 and 0 <= (idx - gap_index) <= fvg_distance:
                    filter_fvg = True
                else:
                    filter_fvg = False

                # if idx != 0 and _filterFvg
                if idx != 0 and filter_fvg:
                    ob_abs_idx = i - idx
                    df.at[df.index[i], "ob_top"] = df["open"].iloc[ob_abs_idx]
                    df.at[df.index[i], "ob_bottom"] = df["low"].iloc[ob_abs_idx]
                    df.at[df.index[i], "ob_type"] = "bullish"
                    df.at[df.index[i], "ob_idx"] = ob_abs_idx
                    df.at[df.index[i], "ob_time"] = df["ts"].iloc[ob_abs_idx]
                    df.at[df.index[i], "ob_bos_idx"] = i
                    df.at[df.index[i], "ob_fractal_time"] = fractal_ts

                # Pine: array.remove always
                fractal_highs.pop(j)
            j -= 1

        # ========== BEARISH OB (fractal LOW break) ==========
        j = len(fractal_lows) - 1
        while j >= 0:
            fl = fractal_lows[j]
            fractal_low = fl["value"]
            fractal_ts = fl["ts"]
            fractal_abs_idx = fl["abs_idx"]

            if current_close < fractal_low:
                idx = 0
                max_high = df["low"].iloc[i]   # Pine: maxHigh = low (current)
                gap_index = 0

                for k in range(0, bars_back):
                    abs_k = i - k
                    if abs_k < 0:
                        break
                    if df["ts"].iloc[abs_k] < fractal_ts:
                        break
                    if df["close"].iloc[abs_k] > df["open"].iloc[abs_k] and df["high"].iloc[abs_k] > max_high:
                        idx = k
                        max_high = df["high"].iloc[abs_k]
                    if k + 2 < len(df):
                        close_k1 = df["close"].iloc[i - k - 1]
                        low_k2 = df["low"].iloc[i - k - 2]
                        high_k = df["high"].iloc[i - k]
                        if close_k1 < low_k2 and high_k < low_k2:
                            gap_index = k + 2

                if gap_index > 0 and idx > 0 and 0 <= (idx - gap_index) <= fvg_distance:
                    filter_fvg = True
                else:
                    filter_fvg = False

                if idx != 0 and filter_fvg:
                    ob_abs_idx = i - idx
                    df.at[df.index[i], "ob_top"] = df["high"].iloc[ob_abs_idx]
                    df.at[df.index[i], "ob_bottom"] = df["open"].iloc[ob_abs_idx]
                    df.at[df.index[i], "ob_type"] = "bearish"
                    df.at[df.index[i], "ob_idx"] = ob_abs_idx
                    df.at[df.index[i], "ob_time"] = df["ts"].iloc[ob_abs_idx]
                    df.at[df.index[i], "ob_bos_idx"] = i
                    df.at[df.index[i], "ob_fractal_time"] = fractal_ts

                fractal_lows.pop(j)
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
