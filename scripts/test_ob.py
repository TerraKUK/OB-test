def find_ob_for_bos(df):
    """
    For each BOS, find OB candle.
    Match Pine Script: iterate from current candle BACK to fractal time.
    """
    df = df.copy()
    df["ob_price"] = None
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
            for k in range(start, end - 1, -1):   # BACK
                candle = df.iloc[k]
                if candle["close"] < candle["open"]:
                    if candle["low"] < min_low:
                        min_low = candle["low"]
                        best_idx = k
            if best_idx is not None:
                df.at[df.index[i], "ob_idx"] = best_idx
                df.at[df.index[i], "ob_price"] = df["high"].iloc[best_idx]
                df.at[df.index[i], "ob_type"] = "bullish"
                df.at[df.index[i], "ob_time"] = df["ts"].iloc[best_idx]

        # BEARISH BOS
        if row["break_low"] and row["fractal_low_idx"] is not None:
            start = i
            end = int(row["fractal_low_idx"])
            best_idx = None
            max_high = -float("inf")
            for k in range(start, end - 1, -1):   # BACK
                candle = df.iloc[k]
                if candle["close"] > candle["open"]:
                    if candle["high"] > max_high:
                        max_high = candle["high"]
                        best_idx = k
            if best_idx is not None:
                df.at[df.index[i], "ob_idx"] = best_idx
                df.at[df.index[i], "ob_price"] = df["low"].iloc[best_idx]
                df.at[df.index[i], "ob_type"] = "bearish"
                df.at[df.index[i], "ob_time"] = df["ts"].iloc[best_idx]

    return df
