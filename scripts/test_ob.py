import os
import pandas as pd


def find_regular_fractals(df):
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
    df = df.copy()
    df["ob_top"] = None
    df["ob_bottom"] = None
    df["ob_type"] = None
    df["ob_time"] = None
    df["ob_fractal_time"] = None

    fractal_highs = []
    fractal_lows = []

    fvg_distance = 3

    for i in range(len(df)):
        if df["fractal_high"].iloc[i]:
            fractal_highs.append((df["high"].iloc[i], i))
        if df["fractal_low"].iloc[i]:
            fractal_lows.append((df["low"].iloc[i], i))

        current_close = df["close"].iloc[i]

        # --- BULLISH OB ---
        j = 0
        while j < len(fractal_highs):
            fractal_high, fractal_idx = fractal_highs[j]

            if current_close > fractal_high:
                # DEBUG print
                if pd.Timestamp("2026-02-20") <= df["ts"].iloc[i] <= pd.Timestamp("2026-03-20"):
                    print(f"\n[{str(df['ts'].iloc[i])[:10]}] BOS HIGH! fractal_high={fractal_high:.2f} (fractal ts={str(df['ts'].iloc[fractal_idx])[:10]})", flush=True)
                    print(f"  fractal_highs array size BEFORE: {len(fractal_highs)}", flush=True)

                idx = None
                min_low = df["high"].iloc[i]
                gap_index = None

                for k in range(i, fractal_idx - 1, -1):
                    c = df.iloc[k]
                    if c["close"] < c["open"] and c["low"] < min_low:
                        idx = k
                        min_low = c["low"]
                    if bullish_imb(df, k):
                        gap_index = k + 2

                if gap_index is not None and idx is not None:
                    filter_fvg = (0 <= idx - gap_index <= fvg_distance)
                else:
                    filter_fvg = False

                if pd.Timestamp("2026-02-20") <= df["ts"].iloc[i] <= pd.Timestamp("2026-03-20"):
                    print(f"  idx={idx} gap_index={gap_index} filter_fvg={filter_fvg}", flush=True)

                if idx is not None and idx != i and filter_fvg:
                    df.at[df.index[i], "ob_top"] = df["open"].iloc[idx]
                    df.at[df.index[i], "ob_bottom"] = df["low"].iloc[idx]
                    df.at[df.index[i], "ob_type"] = "bullish"
                    df.at[df.index[i], "ob_time"] = df["ts"].iloc[idx]
                    df.at[df.index[i], "ob_fractal_time"] = df["ts"].iloc[fractal_idx]

                fractal_highs.pop(j)
                if pd.Timestamp("2026-02-20") <= df["ts"].iloc[i] <= pd.Timestamp("2026-03-20"):
                    print(f"  fractal_highs array size AFTER pop: {len(fractal_highs)}", flush=True)
            else:
                j += 1

        # --- BEARISH OB ---
        j = 0
        while j < len(fractal_lows):
            fractal_low, fractal_idx = fractal_lows[j]

            if current_close < fractal_low:
                if pd.Timestamp("2026-02-20") <= df["ts"].iloc[i] <= pd.Timestamp("2026-03-20"):
                    print(f"\n[{str(df['ts'].iloc[i])[:10]}] BOS LOW! fractal_low={fractal_low:.2f}", flush=True)

                idx = None
                max_high = df["low"].iloc[i]
                gap_index = None

                for k in range(i, fractal_idx - 1, -1):
                    c = df.iloc[k]
                    if c["close"] > c["open"] and c["high"] > max_high:
                        idx = k
                        max_high = c["high"]
                    if bearish_imb(df, k):
                        gap_index = k + 2

                if gap_index is not None and idx is not None:
                    filter_fvg = (0 <= idx - gap_index <= fvg_distance)
                else:
                    filter_fvg = False

                if idx is not None and idx != i and filter_fvg:
                    df.at[df.index[i], "ob_top"] = df["high"].iloc[idx]
                    df.at[df.index[i], "ob_bottom"] = df["open"].iloc[idx]
                    df.at[df.index[i], "ob_type"] = "bearish"
                    df.at[df.index[i], "ob_time"] = df["ts"].iloc[idx]
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

    print(f"\n=== FRACTALS 2026-02-20 to 2026-03-20 ===", flush=True)
    for i, row in df.iterrows():
        ts = row["ts"]
        if pd.Timestamp("2026-02-20") <= ts <= pd.Timestamp("2026-03-20"):
            fh = "FH" if row["fractal_high"] else "  "
            fl = "FL" if row["fractal_low"] else "  "
            print(f"{str(ts)[:10]} | C={row['close']:.2f} | {fh} {fl}", flush=True)
