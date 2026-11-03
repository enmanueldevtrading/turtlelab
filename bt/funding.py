"""Evaluacion de cuenta de fondeo (prop firm) sobre la curva de capital real.

Reglas por defecto (configurables):
  - Cuenta:        $6,000 SIEMPRE (la cuenta de fondeo, no el capital del test)
  - Perdida total: 8% de la cuenta ($480), calculada sobre la equidad real
  - Perdida diaria: 4% del balance de apertura del dia ($240), en UTC
  - Objetivo:      8% de beneficio neto ($480)

No se inventan numeros: todo sale de la curva de capital y de las velas del
backtest. Si el backtest se hizo con otro capital (p.ej. $10), la curva se
reescala proporcionalmente a la cuenta de $6,000 (`base` = capital del test):
asi el veredicto de fondeo siempre se mide sobre la cuenta real de fondeo.
"""
import numpy as np

DEFAULT_ACCOUNT = 6000.0
DEFAULT_MAX_DD_PCT = 8.0
DEFAULT_DAILY_DD_PCT = 4.0
DEFAULT_TARGET_PCT = 8.0

RULES = {
    "account": DEFAULT_ACCOUNT,
    "max_dd_pct": DEFAULT_MAX_DD_PCT,
    "daily_dd_pct": DEFAULT_DAILY_DD_PCT,
    "target_pct": DEFAULT_TARGET_PCT,
}


def _days(stamps):
    """Fecha UTC (YYYY-MM-DD) de cada punto de la curva."""
    import pandas as pd
    s = pd.to_datetime(pd.Series(list(stamps)), utc=True, errors="coerce")
    return s.dt.strftime("%Y-%m-%d").to_numpy()


def evaluate(equity, timestamps=None, account=None, max_dd_pct=None,
             daily_dd_pct=None, target_pct=None, base=None):
    """Devuelve el veredicto de fondeo para una curva de capital."""
    if equity is None:
        eq = np.array([], dtype=float)
    else:
        eq = np.asarray(equity, dtype=float).ravel()
        eq = eq[~np.isnan(eq)]
    account = float(account or DEFAULT_ACCOUNT)
    max_dd_pct = float(max_dd_pct if max_dd_pct is not None else DEFAULT_MAX_DD_PCT)
    daily_dd_pct = float(daily_dd_pct if daily_dd_pct is not None else DEFAULT_DAILY_DD_PCT)
    target_pct = float(target_pct if target_pct is not None else DEFAULT_TARGET_PCT)

    # La cuenta de fondeo manda: si el test corrio con otro capital, se reescala.
    base = float(base or 0.0)
    if base > 0 and abs(base - account) > 1e-9 and len(eq):
        eq = eq * (account / base)

    max_loss = round(account * max_dd_pct / 100.0, 2)
    daily_max_loss = round(account * daily_dd_pct / 100.0, 2)
    target_amt = round(account * target_pct / 100.0, 2)
    out = {
        "account": account, "base": base or account,
        "max_dd_pct": max_dd_pct, "daily_dd_pct": daily_dd_pct,
        "target_pct": target_pct,
        "max_loss": max_loss, "daily_max_loss": daily_max_loss,
        "target_amount": target_amt,
        "floor": round(account - max_loss, 2),
        "target_equity": round(account + target_amt, 2),
        "net": 0.0, "net_pct": 0.0,
        "max_dd": 0.0, "max_dd_amt": 0.0, "dd_used_pct": 0.0,
        "max_daily_dd": 0.0, "max_daily_dd_date": "",
        "daily_used_pct": 0.0,
        "peak": round(account, 2), "peak_to_trough": 0.0,
        "target_hit": False, "target_date": "", "bars_to_target": None,
        "breach": "", "breach_date": "", "status": "SIN DATOS",
        "buffer_dd": max_loss, "buffer_daily": daily_max_loss,
        "days_traded": 0, "equity_points": int(len(eq)),
        "meets_target": False, "meets_limits": True, "viable": False,
    }
    if not len(eq):
        return out

    # Curva referencia con el capital de la cuenta como punto de partida.
    curve = np.concatenate(([account], eq)) if eq[0] != account else eq
    peak = np.maximum.accumulate(curve)
    dd_amt = float((peak - curve).max())
    max_dd_amt = max(0.0, account - float(curve.min()))
    max_dd = max(max_dd_amt, dd_amt)
    net = float(curve[-1] - account)

    out["net"] = round(net, 2)
    out["net_pct"] = round(net / account * 100.0, 2) if account else 0.0
    out["max_dd"] = round(max_dd / account * 100.0, 2) if account else 0.0
    out["max_dd_amt"] = round(max_dd, 2)
    out["peak_to_trough"] = round(dd_amt, 2)
    out["peak"] = round(float(peak[-1]), 2)
    out["dd_used_pct"] = round(max_dd / max_loss * 100.0, 2) if max_loss else 0.0
    out["buffer_dd"] = round(max_loss - max_dd, 2)

    # Drawdown diario: balance de apertura del dia (UTC) menos minimo del dia.
    daily = {"date": "", "dd": 0.0}
    if timestamps is not None:
        try:
            days = _days(timestamps)
            idx = np.arange(len(eq))
            if len(days) == len(eq):
                if len(curve) != len(eq):
                    idx = idx  # la curva extra no altera el agrupado por dia
                start_of_day = {}
                low_of_day = {}
                for i, d in enumerate(days):
                    if d not in start_of_day:
                        start_of_day[d] = float(eq[i])
                    low_of_day[d] = min(low_of_day.get(d, float("inf")), float(eq[i]))
                for d, start in start_of_day.items():
                    dd = start - low_of_day[d]
                    if dd > daily["dd"]:
                        daily = {"date": str(d), "dd": dd}
                out["days_traded"] = len(start_of_day)
        except Exception:
            pass
    out["max_daily_dd"] = round(daily["dd"] / account * 100.0, 2) if account else 0.0
    out["max_daily_dd_date"] = daily["date"]
    out["daily_used_pct"] = round(daily["dd"] / daily_max_loss * 100.0, 2) if daily_max_loss else 0.0
    out["buffer_daily"] = round(daily_max_loss - daily["dd"], 2)

    # Objetivo: primer punto que alcanza account + objetivo.
    hit = np.where(curve >= account + target_amt - 1e-9)[0]
    if len(hit):
        out["target_hit"] = True
        out["bars_to_target"] = int(hit[0])
        if timestamps is not None:
            try:
                import pandas as pd
                s = pd.to_datetime(pd.Series(list(timestamps)), utc=True)
                j = int(hit[0])
                j = min(max(j, 0), len(s) - 1)
                out["target_date"] = str(s.iloc[j])[:16]
            except Exception:
                pass

    floor_hit = np.where(curve <= account - max_loss + 1e-9)[0]
    if len(floor_hit):
        out["breach"] = "perdida total"
        if timestamps is not None:
            try:
                import pandas as pd
                s = pd.to_datetime(pd.Series(list(timestamps)), utc=True)
                j = min(int(floor_hit[0]), len(s) - 1)
                out["breach_date"] = str(s.iloc[j])[:16]
            except Exception:
                pass
    elif daily["dd"] >= daily_max_loss:
        out["breach"] = "perdida diaria"
        out["breach_date"] = daily["date"]

    out["meets_target"] = bool(out["target_hit"])
    out["meets_limits"] = not out["breach"]
    out["viable"] = bool(out["meets_target"] and out["meets_limits"])
    if out["breach"]:
        out["status"] = "NO APTO"
    elif out["target_hit"]:
        out["status"] = "APTO"
    else:
        out["status"] = "SIN OBJETIVO"
    return out


def summary(f):
    """Frase corta para tablas: 'APTO · DD 3.1% / 8% · obj. 8.4%'."""
    if not f:
        return "—"
    return "%s · DD %s%% · día %s%% · neto %s%%" % (
        f.get("status", "—"), f.get("max_dd"), f.get("max_daily_dd"), f.get("net_pct"))
