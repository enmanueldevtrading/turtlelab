"""Grid search por lotes. Ej: python scripts/optimize.py --strategy ema_cross --symbols 'TrendX 1800' --tfs M1 --balance 10"""
import argparse
import json
import sys
sys.path.insert(0, ".")
from bt.data_manager import load_bars
from bt.execution import ExecConfig
from bt.optimize import run_grid
import hashlib
import pandas as pd


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--strategy", required=True)
    ap.add_argument("--grid", default='{"fast":[30,72],"slow":[150]}')
    ap.add_argument("--symbols", default="TrendX 1800")
    ap.add_argument("--tfs", default="M1")
    ap.add_argument("--balance", type=float, default=10.0)
    ap.add_argument("--max-combos", type=int, default=50)
    a = ap.parse_args()
    grid = json.loads(a.grid)
    syms = [s.strip() for s in a.symbols.split(",")]
    tfs = [t.strip() for t in a.tfs.split(",")]

    def load_fn(s, tf):
        df = load_bars(s, tf)
        dh = hashlib.sha256(pd.util.hash_pandas_object(df, index=False).values.tobytes()).hexdigest()[:16]
        return df, dh

    df_out = run_grid(load_fn, a.strategy, grid, lambda: ExecConfig(initial_balance=a.balance),
                      syms, tfs, max_combos=a.max_combos)
    print(df_out.sort_values("net_profit", ascending=False).head(20).to_string())


if __name__ == "__main__":
    main()
