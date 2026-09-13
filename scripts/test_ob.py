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
    df = find_ob_for_bos(df)

    obs = df[df["ob_type"].notna()].reset_index(drop=True)

    print(f"\n=== TOTAL OB: {len(obs)} ===\n", flush=True)

    print(f"{'#':<3} {'OB date':<12} {'Type':<9} {'OB price':<12} {'BOS date':<12}")
    print("-" * 55)
    for i, row in obs.iterrows():
        print(
            f"{i+1:<3} {str(row['ob_time'])[:10]:<12} "
            f"{row['ob_type'].upper():<9} {row['ob_price']:<12.4f} "
            f"{str(row['ts'])[:10]:<12}",
            flush=True
        )

    # === DEBUG: data around July-August 2026 ===
    print("\n=== DATA: 2026-07-28 to 2026-08-10 ===", flush=True)
    mask = (df["ts"] >= "2026-07-28") & (df["ts"] <= "2026-08-10")
    for _, row in df[mask].iterrows():
        fh = "FH" if row["fractal_high"] else "  "
        fl = "FL" if row["fractal_low"] else "  "
        bh = "BOSup" if row["break_high"] else "     "
        bl = "BOSdn" if row["break_low"] else "     "
        print(
            f"{str(row['ts'])[:10]} | O={row['open']:.2f} H={row['high']:.2f} "
            f"L={row['low']:.2f} C={row['close']:.2f} | {fh} {fl} | {bh} {bl}",
            flush=True
        )
