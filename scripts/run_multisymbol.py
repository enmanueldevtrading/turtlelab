"""Una estrategia sobre N simbolos x M TFs, sin MT5. Total + por simbolo."""
import argparse
import json
import sys
sys.path.insert(0, ".")
from bt.data_manager import load_bars, inventory
from bt.execution import ExecConfig
from bt.backtest import run_backtest
from bt.portfolio import aggregate
import hashlib
import pandas as pd


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--strategy", required=True)
    ap.add_argument("--params", default="{}")
    ap.add_argument("--symbols", default="ALL")
    ap.add_argument("--tfs", default="M1,M5")
    ap.add_argument("--balance", type=float, default=10.0)
    ap.add_argument("--lot", type=float, default=0.0)
    ap.add_argument("--min-lot", type=float, default=0.01)
    ap.add_argument("--risk", type=float, default=1.0)
    a = ap.parse_args()
    inv = inventory()
    avail = sorted(set(i["symbol"] for i in inv))
    syms = avail if a.symbols == "ALL" else [s.strip() for s in a.symbols.split(",")]
    tfs = [t.strip() for t in a.tfs.split(",")]
    params = json.loads(a.params)
    results = []
    for s in syms:
        for tf in tfs:
            try:
                df = load_bars(s, tf)
            except FileNotFoundError as e:
                print(f"{s} {tf}: {e}")
                continue
            dh = hashlib.sha256(pd.util.hash_pandas_object(df, index=False).values.tobytes()).hexdigest()[:16]
            cfg = ExecConfig(initial_balance=a.balance, lot=a.lot, risk_pct=a.risk, min_lot=a.min_lot)
            r = run_backtest(df, a.strategy, params, cfg, s, tf, dh, save=True)
            m = r["metrics"]
            print(f"{s} {tf}: {r['bt_id']} net={m['net_profit']} pf={m['profit_factor']} dd%={m['max_drawdown_pct']} trades={m['total']}")
            results.append(r)
    agg = aggregate(results, a.balance)
    print("\nTOTAL:", json.dumps(agg["total"], indent=2, default=str))
    print("\nPOR SIMBOLO:")
    for sym, d in sorted(agg["by_symbol"].items(), key=lambda x: x[1]["metrics"]["net_profit"], reverse=True):
        print(f"  {sym}: net={d['metrics']['net_profit']} pf={d['metrics']['profit_factor']} dd%={d['metrics']['max_drawdown_pct']} trades={d['metrics']['total']}")
    with open("results/multisymbol_summary.json", "w") as f:
        json.dump({"total": agg["total"], "by_symbol": {k: v["metrics"] for k, v in agg["by_symbol"].items()}}, f, indent=2, default=str)


if __name__ == "__main__":
    main()
