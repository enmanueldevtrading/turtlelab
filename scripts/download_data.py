"""Descarga MT5 -> data/weltrade. MT5 solo se usa aqui."""
import argparse
import json
import sys
sys.path.insert(0, ".")
from bt.downloader import connect, available_symbols, download_symbol_tf, MT5_PATH_DEFAULT


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--symbols", default="ALL", help="ALL o lista separada por comas")
    ap.add_argument("--tfs", default="M1,M5,M15,M30,H1,H4,D1")
    ap.add_argument("--bars", type=int, default=50000)
    ap.add_argument("--mt5-path", default=MT5_PATH_DEFAULT)
    ap.add_argument("--root", default="data/weltrade")
    a = ap.parse_args()
    mt5 = connect(a.mt5_path)
    avail = available_symbols(mt5)
    print(f"Simbolos MT5: {len(avail)}")
    if a.symbols == "ALL":
        syms = avail
    else:
        syms = [s.strip() for s in a.symbols.split(",") if s.strip()]
    tfs = [t.strip() for t in a.tfs.split(",") if t.strip()]
    report = []
    total = len(syms) * len(tfs)
    done = 0
    for s in syms:
        for tf in tfs:
            done += 1
            try:
                r = download_symbol_tf(mt5, s, tf, a.bars, a.root)
                print(f"[{done}/{total}] {s} {tf}: {r.get('rows')} filas ok={r.get('validation', {}).get('ok')}")
                report.append(r)
            except Exception as e:
                print(f"[{done}/{total}] {s} {tf} ERROR: {str(e)[:150]}")
                report.append({"symbol": s, "tf": tf, "error": str(e)[:200]})
    mt5.shutdown()
    with open("results/download_report.json", "w") as f:
        json.dump(report, f, indent=2, default=str)
    print("Reporte: results/download_report.json")


if __name__ == "__main__":
    main()
