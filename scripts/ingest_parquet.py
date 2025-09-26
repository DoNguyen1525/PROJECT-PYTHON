import os, zipfile
import pandas as pd
from pathlib import Path
RAW_PATH = "staging"
PARQUET_PATH = "parquet"

def normalize(df):
    df.columns = [c.strip().lower() for c in df.columns]
    rename_map = {"ticker":"symbol", "date":"date", "open":"open", "high":"high",
                  "low":"low", "close":"close", "volume":"volume"}
    df = df.rename(columns={k:v for k,v in rename_map.items() if k in df.columns})
    df['date'] = pd.to_datetime(df['date']).dt.date
    keep = ["symbol","date","open","high","low","close","volume"]
    return df[[c for c in keep if c in df.columns]]

def write_symbol_parquet(df, symbol):
    # group by year to avoid huge parquet
    for year, grp in df.groupby(df['date'].apply(lambda d: d.year)):
        outdir = Path(PARQUET_PATH)/f"symbol={symbol}"/f"year={year}"
        outdir.mkdir(parents=True, exist_ok=True)
        # deterministic file name: symbol-year-yyyymmdd-hhmmss
        fname = outdir / f"part-{symbol}-{year}-{pd.Timestamp.now().strftime('%Y%m%d%H%M%S')}.parquet"
        grp.to_parquet(fname, index=False)

def process_csvfile(path_or_filelike):
    chunksize = 200_000
    for chunk in pd.read_csv(path_or_filelike, chunksize=chunksize):
        df = normalize(chunk)
        for symbol, grp in df.groupby("symbol"):
            write_symbol_parquet(grp, symbol)

def main():
    for root, _, files in os.walk(RAW_PATH):
        for f in files:
            if f.endswith(".zip"):
                with zipfile.ZipFile(os.path.join(root,f)) as z:
                    for mem in z.namelist():
                        if mem.lower().endswith(".csv"):
                            with z.open(mem) as fh:
                                process_csvfile(fh)
            elif f.endswith(".csv"):
                process_csvfile(os.path.join(root,f))
    print("done")
