"""Metricas estandar + Sharpe/Sortino/Recovery. Compatible con bot/stats.py."""
import numpy as np


def compute_metrics(capital, trades, equity_curve=None):
    closed = list(trades or [])
    n = len(closed)
    wins = [t for t in closed if t.get("pnl", 0) > 0]
    losses = [t for t in closed if t.get("pnl", 0) <= 0]
    gross_w = float(sum(t["pnl"] for t in wins))
    gross_l = float(-sum(t["pnl"] for t in losses))
    pnl = gross_w - gross_l
    balance = capital + pnl
    rets = np.array([t["pnl"] / capital for t in closed], dtype=float) if n else np.array([])
    sharpe = float(rets.mean() / (rets.std(ddof=1) + 1e-12) * np.sqrt(max(n, 1))) if n > 1 else 0.0
    neg = rets[rets < 0]
    sortino = float(rets.mean() / (neg.std(ddof=1) + 1e-12) * np.sqrt(max(n, 1))) if len(neg) > 1 else 0.0
    # DD sobre equity curve (o reconstruida)
    eq = list(equity_curve) if equity_curve else []
    if not eq:
        eq = []
        run = capital
        for t in closed:
            run += t["pnl"]
            eq.append(run)
    peak = capital
    max_dd = 0.0
    max_dd_pct = 0.0
    for v in eq:
        peak = max(peak, v)
        dd = peak - v
        max_dd = max(max_dd, dd)
        if peak:
            max_dd_pct = max(max_dd_pct, dd / peak * 100)
    max_w = max_l = w = l = 0
    cw = cl = 0.0
    max_w_amt = 0.0
    max_l_amt = 0.0
    for t in closed:
        if t["pnl"] > 0:
            w += 1; cw += t["pnl"]; l = 0; cl = 0.0
            if (w, cw) > (max_w, max_w_amt):
                max_w, max_w_amt = w, cw
        else:
            l += 1; cl += t["pnl"]; w = 0; cw = 0.0
            if (l, -cl) > (max_l, -max_l_amt):
                max_l, max_l_amt = l, cl
    longs = sum(1 for t in closed if t.get("direction") == "LARGO")
    best = max([t["pnl"] for t in closed], default=0.0)
    worst = min([t["pnl"] for t in closed], default=0.0)
    pf = (gross_w / gross_l) if gross_l else (float("inf") if gross_w else 0.0)
    return {
        "capital": capital, "balance": round(balance, 2),
        "net_profit": round(pnl, 2), "net_pct": round(pnl / capital * 100, 2) if capital else 0.0,
        "gross_profit": round(gross_w, 2), "gross_loss": round(gross_l, 2),
        "profit_factor": round(float(pf), 4) if pf != float("inf") else "inf",
        "max_drawdown": round(max_dd, 2), "max_drawdown_pct": round(max_dd_pct, 2),
        "total": n, "wins": len(wins), "losses": len(losses),
        "win_rate": round(len(wins) / n * 100, 2) if n else 0.0,
        "avg_win": round(gross_w / len(wins), 4) if wins else 0.0,
        "avg_loss": round(-gross_l / len(losses), 4) if losses else 0.0,
        "expectancy": round(pnl / n, 4) if n else 0.0,
        "sharpe": round(sharpe, 4), "sortino": round(sortino, 4),
        "recovery": round(pnl / max_dd, 4) if max_dd else 0.0,
        "longs": longs, "shorts": n - longs,
        "best": round(best, 4), "worst": round(worst, 4),
        "max_win_streak": max_w, "max_loss_streak": max_l,
        "max_win_streak_amt": round(max_w_amt, 2),
        "max_loss_streak_amt": round(max_l_amt, 2),
    }
