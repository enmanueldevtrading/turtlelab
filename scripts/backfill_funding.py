"""Calcula funding.json para resultados antiguos (sin rehacer el backtest).

Usa la curva de capital guardada y las velas locales para reconstruir las
fechas (necesarias para el drawdown diario). No modifica nada mas.

    python scripts/backfill_funding.py            # todos
    python scripts/backfill_funding.py --limit 200
    python scripts/backfill_funding.py --dry-run
"""
import argparse
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

TF_SECONDS = {"M1": 60, "M3": 180, "M5": 300, "M15": 900, "M30": 1800,
              "H1": 3600, "H4": 14400, "D1": 86400}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--force", action="store_true", help="recalcular aunque exista")
    a = ap.parse_args()
    os.chdir(ROOT)

    from bt.funding import evaluate
    from bt.data_manager import load_bars, symbol_info
    import pandas as pd

    root = "results"
    dirs = sorted(d for d in os.listdir(root) if d.startswith("BT-") and os.path.isdir(os.path.join(root, d)))
    if a.limit:
        dirs = dirs[-a.limit:]
    done = skipped = failed = 0
    bars_cache = {}
    for d in dirs:
        base = os.path.join(root, d)
        out = os.path.join(base, "funding.json")
        if os.path.exists(out) and not a.force:
            skipped += 1
            continue
        try:
            cfg = json.load(open(os.path.join(base, "config.json"), encoding="utf-8"))
            eq_path = os.path.join(base, "equity.csv")
            if not os.path.exists(eq_path):
                failed += 1
                continue
            df = pd.read_csv(eq_path)
            curve = df["equity"].to_numpy(float)
            stamps = None
            if "timestamp" in df.columns:
                stamps = pd.to_datetime(df["timestamp"], utc=True)
            else:
                # Cache en segundos int64 (8 B/fila) en vez de Series con zona horaria.
                key = (cfg.get("symbol"), cfg.get("timeframe"))
                if key not in bars_cache:
                    try:
                        import numpy as np
                        ts = load_bars(cfg.get("symbol"), cfg.get("timeframe"))["timestamp"]
                        bars_cache[key] = (ts.astype("int64").to_numpy() // 10**9)
                    except Exception:
                        bars_cache[key] = None
                st = bars_cache[key]
                if st is not None and len(st) == len(curve):
                    stamps = pd.to_datetime(st, unit="s", utc=True)
            base = float((cfg.get("exec") or {}).get("initial_balance")
                         or cfg.get("capital") or 6000.0)
            fund = evaluate(curve, stamps,
                            account=float((cfg.get("exec") or {}).get("funding_account") or 6000.0),
                            base=base,
                            max_dd_pct=float((cfg.get("exec") or {}).get("funding_max_dd_pct", 8.0)),
                            daily_dd_pct=float((cfg.get("exec") or {}).get("funding_daily_dd_pct", 4.0)),
                            target_pct=float((cfg.get("exec") or {}).get("funding_target_pct", 8.0)))
            if not a.dry_run:
                with open(out, "w", encoding="utf-8") as f:
                    json.dump(fund, f, indent=2, default=str)
            done += 1
            if done % 100 == 0:
                print(f"  {done} calculados…", flush=True)
        except Exception:
            failed += 1
    print(f"OK: {done} calculados, {skipped} ya tenían, {failed} omitidos")
    cache = os.path.join(root, "_index.json")
    if os.path.exists(cache) and not a.dry_run:
        os.remove(cache)
        print("Índice de resultados invalidado (se reconstruye al abrir el panel).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
