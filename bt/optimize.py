"""Grid search por lotes, con limite de combinaciones y guardado incremental."""
import itertools
import os
import pandas as pd


def grid_combos(grid: dict, max_combos: int = 200):
    keys = sorted(grid.keys())
    vals = [grid[k] if isinstance(grid[k], list) else [grid[k]] for k in keys]
    combos = list(itertools.product(*vals))
    if len(combos) > max_combos:
        raise ValueError(f"Combinaciones={len(combos)} > max {max_combos}. Reduce el grid.")
    return [dict(zip(keys, c)) for c in combos]


def run_grid(load_fn, strategy_key, grid, exec_cfg_fn, symbols, tfs,
             out_csv="results/optimize.csv", max_combos=200, workers=2):
    from .backtest import run_backtest
    combos = grid_combos(grid, max_combos)
    rows = []
    if os.path.exists(out_csv):
        try:
            done = pd.read_csv(out_csv)
            seen = set(zip(done["symbol"], done["timeframe"], done["params"]))
        except Exception:
            seen = set()
    else:
        seen = set()
    for sym in symbols:
        for tf in tfs:
            df, dh = load_fn(sym, tf)
            for p in combos:
                key = (sym, tf, str(sorted(p.items())))
                if key in seen:
                    continue
                r = run_backtest(df, strategy_key, p, exec_cfg_fn(), sym, tf, dh, save=False)
                m = r["metrics"]
                rows.append({"bt_id": r["bt_id"], "symbol": sym, "timeframe": tf,
                             "params": str(sorted(p.items())), **{k: m.get(k) for k in
                             ("net_profit", "profit_factor", "max_drawdown_pct", "win_rate", "total")}})
                pd.DataFrame(rows).to_csv(out_csv, index=False)  # incremental
    return pd.DataFrame(rows)
