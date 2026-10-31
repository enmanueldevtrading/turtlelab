"""Agregacion multi-simbolo: total + por simbolo, sin ocultar individuales."""
from .metrics import compute_metrics


def aggregate(results: list, capital_per_symbol: float) -> dict:
    all_trades = []
    per_symbol = {}
    for r in results:
        sym = r["config"]["symbol"]
        per_symbol.setdefault(sym, []).append(r)
    by_symbol = {}
    for sym, rs in per_symbol.items():
        tr = [t for r in rs for t in r["trades"]]
        eq = []
        run = capital_per_symbol
        for t in tr:
            run += t["pnl"]
            eq.append(run)
        by_symbol[sym] = {"metrics": compute_metrics(capital_per_symbol, tr, eq),
                          "bt_ids": [r["bt_id"] for r in rs], "trades": len(tr)}
        all_trades.extend(tr)
    total_cap = capital_per_symbol * max(len(by_symbol), 1)
    eq = []
    run = total_cap
    for t in all_trades:
        run += t["pnl"]
        eq.append(run)
    return {"total": compute_metrics(total_cap, all_trades, eq),
            "by_symbol": by_symbol, "n_symbols": len(by_symbol)}
