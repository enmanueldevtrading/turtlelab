"""Un backtest reproducible sin MT5. Ej: python scripts/run_backtest.py --symbol 'TrendX 1800' --timeframe M1 --strategy ema_cross --params '{"fast":72,"slow":150}' --balance 10"""
import argparse
import json
import sys
sys.path.insert(0, ".")
from bt.data_manager import load_bars
from bt.execution import ExecConfig
from bt.backtest import run_backtest
from bt.reports import save_report
import hashlib
import pandas as pd


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--symbol", required=True)
    ap.add_argument("--timeframe", required=True)
    ap.add_argument("--strategy", required=True)
    ap.add_argument("--params", default="{}")
    ap.add_argument("--balance", type=float, default=10.0)
    ap.add_argument("--lot", type=float, default=0.0)
    ap.add_argument("--min-lot", type=float, default=0.01)
    ap.add_argument("--risk", type=float, default=1.0)
    ap.add_argument("--spread", type=float, default=0.0)
    ap.add_argument("--commission", type=float, default=0.0)
    ap.add_argument("--slippage", type=float, default=0.0)
    ap.add_argument("--entry-mode", default="close", choices=["close", "next_open"])
    a = ap.parse_args()
    df = load_bars(a.symbol, a.timeframe)
    dh = hashlib.sha256(pd.util.hash_pandas_object(df, index=False).values.tobytes()).hexdigest()[:16]
    cfg = ExecConfig(initial_balance=a.balance, lot=a.lot, risk_pct=a.risk,
                     min_lot=a.min_lot, spread=a.spread, commission=a.commission,
                     slippage=a.slippage, entry_mode=a.entry_mode)
    r = run_backtest(df, a.strategy, json.loads(a.params), cfg, a.symbol, a.timeframe, dh, save=True)
    if r.get("empty") or r.get("bt_id") is None:
        print(json.dumps({"bt_id": None, "metrics": r["metrics"], "nota": "Sin operaciones en este período. No se asignó ID ni se guardó reporte."}, indent=2, default=str))
        return
    save_report(r, f"results/{r['bt_id']}")
    print(json.dumps({"bt_id": r["bt_id"], "metrics": r["metrics"]}, indent=2, default=str))
    print(f"Reporte: results/{r['bt_id']}/report.html")


if __name__ == "__main__":
    main()
