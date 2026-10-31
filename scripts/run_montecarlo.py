"""Monte Carlo sobre un BT existente. Ej: python scripts/run_montecarlo.py --bt-id BT-2026-000001 --sims 500 --seed 12345"""
import argparse
import json
import os
import sys
sys.path.insert(0, ".")
from bt.montecarlo import run_montecarlo
import pandas as pd


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--bt-id", required=True)
    ap.add_argument("--sims", type=int, default=500)
    ap.add_argument("--seed", type=int, default=12345)
    ap.add_argument("--method", default="shuffle", choices=["shuffle", "bootstrap"])
    a = ap.parse_args()
    tpath = os.path.join("results", a.bt_id, "trades.csv")
    mpath = os.path.join("results", a.bt_id, "metrics.json")
    if not os.path.exists(tpath):
        print(f"No existe {tpath}. Ejecuta un backtest primero.")
        sys.exit(1)
    trades = pd.read_csv(tpath).to_dict("records")
    capital = json.load(open(mpath))["capital"] if os.path.exists(mpath) else 10.0
    mc = run_montecarlo([{"pnl": float(t.get("pnl", 0)), "direction": t.get("direction", "LONG")} for t in trades],
                        capital, a.sims, a.seed, method=a.method)
    mc_id = f"{a.bt_id}-MC{seed_str(a.seed)}-{a.sims}"
    outdir = os.path.join("results", a.bt_id)
    with open(os.path.join(outdir, f"montecarlo_{a.sims}_{a.seed}.json"), "w") as f:
        json.dump({"mc_id": mc_id, **mc}, f, indent=2, default=str)
    print(json.dumps({"mc_id": mc_id, **mc}, indent=2, default=str))


def seed_str(s):
    return str(s)


if __name__ == "__main__":
    main()
