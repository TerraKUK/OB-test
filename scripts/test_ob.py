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


def find_all_obs(df):
    df = df.copy()
    df["ob_top"] = None
    df["ob_bottom"] = None
    df["ob_type"] = None
    df["ob_idx"] = None
    df["ob_time"] = None
    df["ob_bos_idx"] = None
    df["ob_fractal_time"] = None

    fractal_highs = []
    fractal_lows = []

    fvg_distance = 3
    bars_back = 500

    for i in range(len(df)):
        if df["fractal_high"].iloc[i]:
            fractal_highs.append({"value": df["high"].iloc[i], "ts": df["ts"].iloc[i], "abs_idx": i})
        if df["fractal_low"].iloc[i]:
            fractal_lows.append({"value": df["low"].iloc[i], "ts": df["ts"].iloc[i], "abs_idx": i})

        current_close = df["close"].iloc[i]

        # ========== BULLISH OB ==========
        j = len(fractal_highs) - 1
        while j >= 0:
            fh = fractal_highs[j]
            fractal_high = fh["value"]
            fractal_ts = fh["ts"]

            if current_close > fractal_high:
                idx = 0
                min_low = df["high"].iloc[i]
                gap_index = 0

                for k in range(0, bars_back):
                    abs_k = i - k
                    if abs_k < 0:
                        break
                    if df["ts"].iloc[abs_k] < fractal_ts:
                        break
                    if df["close"].iloc[abs_k] < df["open"].iloc[abs_k] and df["low"].iloc[abs_k] < min_low:
                        idx = k
                        min_low = df["low"].iloc[abs_k]
                    if k + 2 < len(df):
                        close_k1 = df["close"].iloc[i - k - 1]
                        high_k2 = df["high"].iloc[i - k - 2]
                        low_k = df["low"].iloc[i - k]
                        if close_k1 > high_k2 and low_k > high_k2:
                            gap_index = k + 2

                if gap_index > 0 and idx > 0 and 0 <= (idx - gap_index) <= fvg_distance:
                    filter_fvg = True
                else:
                    filter_fvg = False

                if idx != 0 and filter_fvg:
                    ob_abs_idx = i - idx
                    df.at[df.index[i], "ob_top"] = df["open"].iloc[ob_abs_idx]
                    df.at[df.index[i], "ob_bottom"] = df["low"].iloc[ob_abs_idx]
                    df.at[df.index[i], "ob_type"] = "bullish"
                    df.at[df.index[i], "ob_idx"] = ob_abs_idx
                    df.at[df.index[i], "ob_time"] = df["ts"].iloc[ob_abs_idx]
                    df.at[df.index[i], "ob_bos_idx"] = i
                    df.at[df.index[i], "ob_fractal_time"] = fractal_ts

                fractal_highs.pop(j)
            j -= 1

        # ========== BEARISH OB ==========
        j = len(fractal_lows) - 1
        while j >= 0:
            fl = fractal_lows[j]
            fractal_low = fl["value"]
            fractal_ts = fl["ts"]

            if current_close < fractal_low:
                idx = 0
                max_high = df["low"].iloc[i]
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
    files = sorted([f for f in os.listdir(raw_dir) if f.endswith(".csv")])
    if not files:
        print("No CSV files in data/raw/")
        exit(1)

    all_results = []
    total_ob = 0

    for file_name in files:
        file_path = os.path.join(raw_dir, file_name)
        asset = file_name.split("_")[0]

        try:
            df = pd.read_csv(file_path, parse_dates=["ts"])
        except Exception as e:
            print(f"Skip {asset}: {e}", flush=True)
            continue

        if len(df) < 50:
            print(f"\n=== {asset}: skip (only {len(df)} candles) ===", flush=True)
            continue

        df = find_regular_fractals(df)
        df = find_all_obs(df)

        obs = df[df["ob_type"].notna()].reset_index(drop=True)

        if len(obs) > 0:
            print(f"\n=== {asset}: {len(obs)} OB ===", flush=True)
            print(f"{'#':<3} {'OB date':<12} {'Type':<9} {'Top':<10} {'Bottom':<10} {'BOS date':<12}")
            print("-" * 65)
            for idx, row in obs.iterrows():
                print(
                    f"{idx+1:<3} {str(row['ob_time'])[:10]:<12} "
                    f"{row['ob_type'].upper():<9} {row['ob_top']:<10.2f} "
                    f"{row['ob_bottom']:<10.2f} {str(row['ts'])[:10]:<12}",
                    flush=True
                )
                all_results.append({
                    "asset": asset,
                    "ob_time": str(row["ob_time"])[:10],
                    "ob_type": row["ob_type"],
                    "ob_top": row["ob_top"],
                    "ob_bottom": row["ob_bottom"],
                    "bos_time": str(row["ts"])[:10],
                })
            total_ob += len(obs)
        else:
            print(f"\n=== {asset}: 0 OB ===", flush=True)

    print(f"\n{'='*60}", flush=True)
    print(f"TOTAL: {total_ob} OB across {len(files)} pairs", flush=True)
    print(f"{'='*60}", flush=True)
