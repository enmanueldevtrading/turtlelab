"""Descarga Yahoo Finance -> data/yahoo (separado de Weltrade)."""
import sys
sys.path.insert(0, ".")
from bt.yahoo_data import YAHOO_SYMBOLS, download_all

if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--symbols", default="ALL")
    ap.add_argument("--tfs", default="D1,H1")
    a = ap.parse_args()
    syms = None if a.symbols == "ALL" else [s.strip() for s in a.symbols.split(",")]
    tfs = [t.strip() for t in a.tfs.split(",")]
    rep = download_all(symbols=syms, tfs=tfs)
    for r in rep:
        print(r.get("display"), r.get("tf"), "->", r.get("rows", r.get("error")))
