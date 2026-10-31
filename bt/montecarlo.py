"""Monte Carlo POST-proceso sobre trades reales. No genera senales. Con seed."""
import numpy as np
from .metrics import compute_metrics


def _eq_stats(trades, capital):
    m = compute_metrics(capital, trades)
    return m


def run_montecarlo(trades: list, capital: float, n_sims: int = 500, seed: int = 12345,
                   slippage_extra: float = 0.0, commission_extra: float = 0.0,
                   method: str = "shuffle") -> dict:
    rng = np.random.default_rng(seed)
    base = [dict(t) for t in trades]
    if slippage_extra or commission_extra:
        for t in base:
            t["pnl"] = float(t["pnl"]) - abs(commission_extra) - abs(slippage_extra)
    pnls = np.array([t["pnl"] for t in base], dtype=float)
    out = []
    for _ in range(int(n_sims)):
        if method == "bootstrap":
            idx = rng.integers(0, len(pnls), len(pnls)) if len(pnls) else []
        else:  # shuffle
            idx = rng.permutation(len(pnls)) if len(pnls) else []
        sample = [{"pnl": float(pnls[i]), "direction": base[i].get("direction", "LONG")} for i in idx]
        m = _eq_stats(sample, capital)
        out.append(m)
    def pct(key, q):
        vals = sorted(o[key] for o in out if isinstance(o[key], (int, float)))
        if not vals:
            return 0.0
        return float(np.percentile(vals, q))
    res = {
        "n_sims": int(n_sims), "seed": seed, "method": method, "capital": capital,
        "percentiles": {k: {f"P{p}": pct(k, p) for p in (5, 10, 25, 50, 75, 90, 95)}
                        for k in ("net_profit", "max_drawdown", "max_drawdown_pct",
                                  "profit_factor", "win_rate") if out and isinstance(out[0].get(k), (int, float))},
        "p_loss": float(sum(1 for o in out if o["net_profit"] < 0) / max(len(out), 1)),
        "p_profit": float(sum(1 for o in out if o["net_profit"] > 0) / max(len(out), 1)),
        "p_dd10": float(sum(1 for o in out if o["max_drawdown_pct"] > 10) / max(len(out), 1)),
        "p_dd20": float(sum(1 for o in out if o["max_drawdown_pct"] > 20) / max(len(out), 1)),
        "p_dd30": float(sum(1 for o in out if o["max_drawdown_pct"] > 30) / max(len(out), 1)),
    }
    # curvas resumen: mejor/mediana/peor por balance final
    finals = sorted(o["balance"] for o in out)
    res["final_balance"] = {"min": finals[0] if finals else capital,
                            "median": float(np.median(finals)) if finals else capital,
                            "max": finals[-1] if finals else capital}
    return res
