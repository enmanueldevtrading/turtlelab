"""Tests del motor BT: indicadores, senales, ejecucion, look-ahead, datos, MC."""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import pandas as pd
from bt.indicators import ema, atr, donchian
from bt.strategies import get_strategy
from bt.execution import ExecConfig, Portfolio
from bt.backtest import run_backtest
from bt.validator import validate
from bt.montecarlo import run_montecarlo
from bt.metrics import compute_metrics


def bars(n=300, start=100.0, step=0.5, up=True):
    rows = []
    p = start
    import datetime
    t0 = pd.Timestamp("2026-01-01", tz="UTC")
    for i in range(n):
        o = p
        p = p + step if up else p - step
        rows.append({"timestamp": t0 + pd.Timedelta(minutes=i), "open": o,
                     "high": max(o, p) + 0.1, "low": min(o, p) - 0.1,
                     "close": p, "tick_volume": 10, "spread": 0})
    return pd.DataFrame(rows)


def flat_then_trend(n_flat=200, start=100.0, step=0.5, n_trend=60, up=True):
    rows = []
    import pandas as pd
    t0 = pd.Timestamp("2026-01-01", tz="UTC")
    p = start
    closes = [start] * n_flat
    for k in range(n_trend):
        p = p + step if up else p - step
        closes.append(p)
    for i, c in enumerate(closes):
        o = closes[i - 1] if i else c
        rows.append({"timestamp": t0 + pd.Timedelta(minutes=i), "open": o,
                     "high": max(o, c) + 0.1, "low": min(o, c) - 0.1,
                     "close": c, "tick_volume": 10, "spread": 0})
    return pd.DataFrame(rows)


def test_ema_seed_and_cross():
    s, _ = get_strategy("ema_cross")
    df = flat_then_trend(up=True)
    ctx = s.prepare(df, {"fast": 10, "slow": 30})
    sigs = [s.entry_signal(df, i, ctx, {"fast": 10, "slow": 30}) for i in range(len(df))]
    assert 1 in sigs, "tendencia alcista debe dar BUY"
    df2 = flat_then_trend(up=False)
    ctx2 = s.prepare(df2, {"fast": 10, "slow": 30})
    sigs2 = [s.entry_signal(df2, i, ctx2, {"fast": 10, "slow": 30}) for i in range(len(df2))]
    assert -1 in sigs2


def test_no_lookahead_turtle():
    s, _ = get_strategy("turtle20_10")
    df = bars(100, up=True)
    ctx = s.prepare(df, {"entry": 20, "exit": 10, "atr_period": 20, "sl_mult": 2.0})
    # la senal en i no debe cambiar si se agregan barras futuras
    a = s.entry_signal(df, 50, ctx, {"entry": 20, "exit": 10, "atr_period": 20, "sl_mult": 2.0})
    df2 = pd.concat([df, bars(10)]).reset_index(drop=True)
    ctx2 = s.prepare(df2, {"entry": 20, "exit": 10, "atr_period": 20, "sl_mult": 2.0})
    b = s.entry_signal(df2, 50, ctx2, {"entry": 20, "exit": 10, "atr_period": 20, "sl_mult": 2.0})
    assert a == b


def test_sl_tp_and_costs():
    cfg = ExecConfig(initial_balance=100.0, lot=1.0, spread=0.1, commission=0.5, slippage=0.0)
    pf = Portfolio(cfg)
    pos = pf.open(1, "t0", 100.0, "t0", 100.0, 90.0, 120.0, 1.0, "test")
    assert pos is not None
    bar = {"open": 100, "high": 121, "low": 89, "close": 100}
    should, px, reason = pf.manage_bar(pos, bar, None)
    assert should and reason == "TOPE", "TOPE tiene prioridad conservadora"
    pf2 = Portfolio(ExecConfig(initial_balance=100.0, lot=1.0))
    p2 = pf2.open(1, "t", 100.0, "t", 100.0, None, None, 1.0, "x")
    pnl = pf2.close(p2, "t2", 110.0, "exit")
    assert abs(pnl - 10.0) < 1e-9


def test_trailing_and_breakeven():
    cfg = ExecConfig(initial_balance=100.0, lot=1.0, trailing_mult=1.0)
    pf = Portfolio(cfg)
    pos = pf.open(1, "t", 100.0, "t", 100.0, 90.0, None, 1.0, "x")
    pf.manage_bar(pos, {"open": 100, "high": 115, "low": 100, "close": 112}, atr_now=2.0)
    assert pos["sl"] > 90.0, "trailing debe subir el SL"


def test_backtest_reproducible_and_metrics():
    df = flat_then_trend()
    cfg = ExecConfig(initial_balance=50.0, lot=0.01)
    r1 = run_backtest(df, "ema_cross", {"fast": 10, "slow": 30}, cfg, "TEST", "M1", "h", save=False)
    r2 = run_backtest(df, "ema_cross", {"fast": 10, "slow": 30}, cfg, "TEST", "M1", "h", save=False)
    assert r1["metrics"] == r2["metrics"]
    assert r1["metrics"]["total"] > 0
    assert "sharpe" in r1["metrics"] and "max_drawdown_pct" in r1["metrics"]


def test_validator():
    df = bars(50)
    rep = validate(df, "M1")
    assert rep["ok"]
    bad = df.iloc[::-1].reset_index(drop=True)
    assert not validate(bad, "M1")["ok"]
    dup = pd.concat([df, df.iloc[[0]]]).reset_index(drop=True)
    assert "duplicados" in " ".join(validate(dup, "M1")["errors"])


def test_montecarlo_seed():
    trades = [{"pnl": 1.0, "direction": "LONG"}] * 10 + [{"pnl": -0.5, "direction": "SHORT"}] * 5
    a = run_montecarlo(trades, 50.0, n_sims=50, seed=7)
    b = run_montecarlo(trades, 50.0, n_sims=50, seed=7)
    assert a == b
    assert 0.0 <= a["p_loss"] <= 1.0


def _flat_df(n, price=100.0):
    import pandas as pd
    t0 = pd.Timestamp("2026-01-01", tz="UTC")
    return pd.DataFrame([{"timestamp": t0 + pd.Timedelta(minutes=i), "open": price,
                          "high": price, "low": price, "close": price,
                          "tick_volume": 10, "spread": 0} for i in range(n)])


def test_turtle_close_never_triggers_on_own_high():
    """El cierre de una vela jamas supera su propio maximo: sin barras previas
    mas altas no puede haber entrada (el bug original del EA)."""
    from bt.strategies import get_strategy
    s, _ = get_strategy("turtle20_10")
    df = _flat_df(30, 100.0)
    # ultimas 5 velas suben: el canal de las 20 previas llega hasta 100
    for i in range(25, 30):
        df.loc[i, "close"] = 100.0 + (i - 24)
        df.loc[i, "high"] = 100.0 + (i - 24)
    ctx = s.prepare(df, {"entry": 20, "exit": 10, "atr_period": 20, "sl_mult": 2.0})
    # barra 25: close=101 > maximo previo 100 -> senal real
    assert s.entry_signal(df, 25, ctx, {"entry": 20, "exit": 10, "atr_period": 20, "sl_mult": 2.0}) == 1
    # en plano total no hay senal en ninguna barra
    df2 = _flat_df(30, 100.0)
    ctx2 = s.prepare(df2, {"entry": 20, "exit": 10, "atr_period": 20, "sl_mult": 2.0})
    assert all(s.entry_signal(df2, i, ctx2, {"entry": 20, "exit": 10, "atr_period": 20, "sl_mult": 2.0}) == 0
               for i in range(len(df2)))


def test_turtle_exact_numbers():
    """Serie a mano: ruptura en barra 25 (close 101), SL=101-2*ATR.
    ATR(20) con TR=0 en plano y TR=1 en barra 25: seed media 20 barras."""
    from bt.strategies import get_strategy
    from bt.execution import ExecConfig
    from bt.backtest import run_backtest
    df = _flat_df(60, 100.0)
    for i in range(25, 60):
        df.loc[i, "close"] = 100.0 + (i - 24) * 1.0
        df.loc[i, "high"] = 100.0 + (i - 24) * 1.0
    r = run_backtest(df, "turtle20_10",
                     {"entry": 20, "exit": 10, "atr_period": 20, "sl_mult": 2.0},
                     ExecConfig(initial_balance=100.0, lot=1.0), "T", "M1", "h", save=False)
    assert r["metrics"]["total"] >= 1
    t0 = r["trades"][0]
    assert t0["direction"] == "LARGO" and t0["entry"] == 101.0
    # SL = 101 - 2*ATR ; ATR seed = media TR(5..24)=0 (19 ceros + TR barra25=1)/20 = 0.05
    assert abs(t0["sl"] - (101.0 - 2 * 0.05)) < 1e-9
    assert t0["qty"] == 1.0


def test_empty_backtest_has_no_id():
    df = _flat_df(100, 100.0)
    from bt.execution import ExecConfig
    from bt.backtest import run_backtest
    r = run_backtest(df, "ema_cross", {"fast": 10, "slow": 30},
                     ExecConfig(initial_balance=50.0), "T", "M1", "h", save=False)
    assert r.get("empty") is True and r["bt_id"] is None


def test_enriched_trade_fields():
    """Cada operacion registra riesgo real, R, duracion y excursiones."""
    from bt.execution import ExecConfig
    from bt.backtest import run_backtest
    df = flat_then_trend()
    r = run_backtest(df, "turtle20_10",
                     {"entry": 20, "exit": 10, "atr_period": 20, "sl_mult": 2.0},
                     ExecConfig(initial_balance=100.0, lot=1.0), "T", "M1", "h", save=False)
    assert r["metrics"]["total"] > 0
    for t in r["trades"]:
        for k in ("risk_money", "risk_pct_real", "bars_held", "mfe_price", "mae_price",
                  "mfe_money", "mae_money", "r_multiple", "atr_entry", "sl_dist",
                  "spread_cfg", "commission_total", "contract_size"):
            assert k in t, f"falta {k}"
        assert t["bars_held"] is None or t["bars_held"] >= 0
        assert t["mfe_price"] >= 0 and t["mae_price"] <= 0
        if t["risk_money"]:
            assert (t["pnl"] > 0) == (t["r_multiple"] > 0)
    # con lote fijo 1.0 y SL, el riesgo real por trade es estable y conocido
    t0 = r["trades"][0]
    assert abs(t0["risk_money"] - t0["sl_dist"] * 1.0) < 1e-6


def _trend_con_dip():
    """Subida con caida intermedia: rompe la salida de 10 pero no la de 20."""
    import pandas as pd
    import numpy as np
    t0 = pd.Timestamp("2026-01-01", tz="UTC")
    closes = []
    for i in range(140):
        c = 100.0 + 0.5 * i
        if 70 <= i < 80:
            c -= 7.0 * np.sin(np.pi * (i - 70) / 10)
        closes.append(c)
    rows = [{"timestamp": t0 + pd.Timedelta(minutes=i), "open": closes[i - 1] if i else closes[0],
             "high": c + 0.1, "low": c - 0.1, "close": c,
             "tick_volume": 10, "spread": 0} for i, c in enumerate(closes)]
    return pd.DataFrame(rows)


def test_turtle_variants_differ():
    """20/10, 20/20 y 55/20 son logicas distintas: resultados distintos."""
    from bt.execution import ExecConfig
    from bt.backtest import run_backtest
    df = _trend_con_dip()
    outs = {}
    for key in ("turtle20_10", "turtle20_20", "turtle55_20"):
        r = run_backtest(df, key, {}, ExecConfig(initial_balance=100.0, lot=1.0),
                         "T", "M1", "h", save=False)
        outs[key] = (r["metrics"]["total"], round(r["metrics"]["net_profit"], 4))
    assert len(set(v[0] for v in outs.values())) > 1, f"mismo n. ops: {outs}"
    assert len(set(v[1] for v in outs.values())) > 1, f"mismo neto: {outs}"


def test_spike_filter_off_by_default():
    """Sin orden expresa, el filtro de picos no altera nada."""
    from bt.execution import ExecConfig
    assert ExecConfig().spike_k == 0.0
    assert ExecConfig().spike_close is False


def test_equity_incluye_flotante():
    """La curva incluye el flotante: el drawdown no esconde posiciones abiertas."""
    from bt.execution import ExecConfig
    from bt.backtest import run_backtest
    df = flat_then_trend()
    r = run_backtest(df, "turtle20_10",
                     {"entry": 20, "exit": 10, "atr_period": 20, "sl_mult": 2.0},
                     ExecConfig(initial_balance=100.0, lot=1.0), "T", "M1", "h", save=False)
    assert len(r["equity_curve"]) == len(df)
    assert r["metrics"]["max_drawdown"] >= 0


def test_vwap_exit_solo_en_sesion():
    """Fuera de sesion no hay salidas: la posicion se mantiene abierta."""
    import pandas as pd
    import numpy as np
    from bt.strategies import get_strategy
    s, _ = get_strategy("vwap_session")
    p = {"ema": 9, "sessions": [["07:00", "10:00"], ["12:00", "15:00"]]}
    t0 = pd.Timestamp("2026-01-05 03:00", tz="UTC")
    rows = [{"timestamp": t0 + pd.Timedelta(minutes=3 * i), "open": 100.0,
             "high": 101.0, "low": 99.0, "close": 100.0,
             "tick_volume": 10, "spread": 0} for i in range(40)]
    df = pd.DataFrame(rows)
    ctx = s.prepare(df, p)
    # fuera de sesion no hay SALIDAS por senal: solo aplanado de fin de sesion
    assert all(s.exit_signal(df, i, ctx, p, 1) is True for i in range(1, len(df)))
    assert all(s.exit_signal(df, i, ctx, p, -1) is True for i in range(1, len(df)))
    assert all(s.exit_reason(df, i, ctx, p, 1) == "FIN DE SESION" for i in range(1, len(df)))


def _vwap_df(inicio, n=80, step=3):
    import pandas as pd
    t0 = pd.Timestamp(inicio, tz="UTC")
    rows = [{"timestamp": t0 + pd.Timedelta(minutes=3 * i), "open": 100.0 + i * 0.1,
             "high": 101.0 + i * 0.1, "low": 99.0 + i * 0.1, "close": 100.0 + i * 0.1,
             "tick_volume": 10, "spread": 0} for i in range(n)]
    return pd.DataFrame(rows)


def test_cuenta_en_cero_para():
    """Balance <= 0 cierra todo con motivo y no abre mas (margen)."""
    import pandas as pd
    from bt.execution import ExecConfig
    from bt.backtest import run_backtest
    t0 = pd.Timestamp("2026-01-01", tz="UTC")
    rows = []
    for i in range(120):
        p = 100.0 + i * 0.5
        rows.append({"timestamp": t0 + pd.Timedelta(minutes=i), "open": p,
                     "high": p + 0.1, "low": p - 0.1, "close": p,
                     "tick_volume": 10, "spread": 0})
    df = pd.DataFrame(rows)
    # comision $2 con $1 de capital: al abrir, el balance queda <= 0 con la
    # posicion abierta -> la proxima barra la cierra el margen.
    r = run_backtest(df, "turtle20_10",
                     {"entry": 20, "exit": 10, "atr_period": 20, "sl_mult": 2.0},
                     ExecConfig(initial_balance=1.0, lot=1.0, commission=2.0),
                     "T", "M1", "h", save=False)
    motivos = [t["reason"] for t in r["trades"]]
    assert "CUENTA EN CERO" in motivos
    # el margen es lo ultimo: despues no hay mas operaciones
    assert motivos[-1] == "CUENTA EN CERO"
    assert r["metrics"]["balance"] <= 0


def test_margen_mira_flotante():
    """El broker cierra en flotante: equidad <= 0 aunque el balance siga > 0."""
    import pandas as pd
    from bt.execution import ExecConfig
    from bt.backtest import run_backtest
    t0 = pd.Timestamp("2026-01-01", tz="UTC")
    rows = []
    for i in range(120):
        p = 100.0 if i < 40 else 100.0 + (i - 40)
        if i == 60:
            p = 30.0
        if i > 60:
            p = 30.0
        rows.append({"timestamp": t0 + pd.Timedelta(minutes=i), "open": p,
                     "high": p + 0.1, "low": p - 0.1, "close": p,
                     "tick_volume": 10, "spread": 0})
    df = pd.DataFrame(rows)
    # EMA sin tope, lote 1.0, $2: el desplome hunde el flotante bajo cero
    # con el balance aun positivo -> margen por equidad, no por balance.
    r = run_backtest(df, "ema_cross", {"fast": 10, "slow": 30},
                     ExecConfig(initial_balance=2.0, lot=1.0), "T", "M1", "h", save=False)
    motivos = [t["reason"] for t in r["trades"]]
    assert "CUENTA EN CERO" in motivos


def test_vwap_sesiones_horario_verano():
    """Londres 08:00 local: en agosto es 07:00 UTC, en enero 08:00 UTC."""
    import numpy as np
    from bt.strategies import get_strategy
    s, _ = get_strategy("vwap_session")
    p = {"ema": 9, "sessions": [["Europe/London", "08:00", "11:00"],
                                ["America/New_York", "08:00", "11:00"]]}
    inv = _vwap_df("2026-01-15 06:00")  # Londres en GMT: sesion 08:00-11:00 UTC
    ctx = s.prepare(inv, p)
    ts = inv["timestamp"]
    dentro = (ts.dt.hour * 60 + ts.dt.minute) >= 8 * 60
    assert bool((~np.isnan(ctx["vwap"]) == dentro).all())
    ver = _vwap_df("2026-08-15 05:30")  # Londres en BST: sesion 07:00-10:00 UTC
    ctx2 = s.prepare(ver, p)
    ts2 = ver["timestamp"]
    dentro2 = (ts2.dt.hour * 60 + ts2.dt.minute) >= 7 * 60
    assert bool((~np.isnan(ctx2["vwap"]) == dentro2).all())


def test_vwap_m15_ref_dos_velas():
    """Variante A: referencia = 2 primeras velas, esas no operan."""
    import pandas as pd
    import numpy as np
    from bt.strategies import get_strategy
    s, _ = get_strategy("vwap_m15")
    p = {"ema": 9, "ref_bars": 2, "sessions": [["Europe/London", "08:00", "11:00"],
                                              ["America/New_York", "08:00", "11:00"]]}
    df = _vwap_df("2026-08-15 05:30", n=120)
    ctx = s.prepare(df, p)
    # sesion Londres agosto = 07:00-10:00 UTC = barras 30-89; ref = 30 y 31
    assert not ctx["trade_ok"][:32].any()
    assert ctx["trade_ok"][32:90].all()
    assert not ctx["trade_ok"][90:].any()
    rh = ctx["ref_h"][40]
    assert rh == max(df["high"].iloc[30], df["high"].iloc[31])


def test_vwap_rr_stop_objetivo():
    """Variante B: tope en apertura, objetivo al doble; sin recorrido no abre."""
    import pandas as pd
    from bt.strategies import get_strategy
    s, _ = get_strategy("vwap_rr12")
    t0 = pd.Timestamp("2026-08-15 07:00", tz="UTC")
    rows = [{"timestamp": t0 + pd.Timedelta(minutes=3 * i), "open": 100.0,
             "high": 101.0, "low": 99.0, "close": 100.0,
             "tick_volume": 10, "spread": 0} for i in range(30)]
    df = pd.DataFrame(rows)
    ctx = s.prepare(df, {"ema": 9, "need_sl": True,
                         "sessions": [["Europe/London", "08:00", "11:00"],
                                      ["America/New_York", "08:00", "11:00"]]})
    sl, tp = s.stop_price(df, 10, ctx, {}, 1, 100.5)
    assert sl == 100.0 and tp == 101.5
    sl2, tp2 = s.stop_price(df, 10, ctx, {}, 1, 99.5)
    assert (sl2, tp2) == (None, None)


def test_vwap_solo_cruce():
    """Sin rango M15: el cruce VWAP/EMA dispara aunque el precio este dentro."""
    import numpy as np
    from bt.strategies import get_strategy
    s, _ = get_strategy("vwap_session")
    n = 30
    vwap = np.linspace(100.0, 102.0, n)
    e = np.full(n, 101.0)
    ctx = {"close": np.linspace(100.5, 101.5, n), "vwap": vwap,
           "ref_h": np.full(n, 999.0), "ref_l": np.full(n, -999.0),
           "trade_ok": np.ones(n, dtype=bool), "e": e}
    df = None
    assert s.entry_signal(df, 15, ctx, {}) == 1
    ctx2 = dict(ctx, vwap=np.linspace(102.0, 100.0, n))
    assert s.entry_signal(df, 15, ctx2, {}) == -1


def test_vwap_aplana_fin_sesion():
    """Fuera de sesion la salida es True (aplanar), con motivo FIN DE SESION."""
    import pandas as pd
    from bt.strategies import get_strategy
    s, _ = get_strategy("vwap_session")
    p = {"ema": 9, "sessions": [["Europe/London", "08:00", "11:00"],
                                ["America/New_York", "08:00", "11:00"]]}
    df = _vwap_df("2026-08-15 05:30", n=120)
    ctx = s.prepare(df, p)
    fuera = [i for i in range(len(df)) if __import__("numpy").isnan(ctx["vwap"][i])]
    assert fuera, "debe haber barras fuera de sesion"
    assert all(s.exit_signal(df, i, ctx, p, 1) is True for i in fuera[1:])
    assert all(s.exit_signal(df, i, ctx, p, -1) is True for i in fuera[1:])
    assert s.exit_reason(df, fuera[1], ctx, p, 1) == "FIN DE SESION"


def test_vwap_first_bucket_blocked():
    """En el primer bucket de 15 min de la sesion no hay entradas (rango abierto)."""
    import pandas as pd
    import numpy as np
    from bt.strategies import get_strategy
    s, _ = get_strategy("vwap_session")
    p = {"ema": 9, "sessions": [["07:00", "10:00"], ["12:00", "15:00"]]}
    t0 = pd.Timestamp("2026-01-05 07:00", tz="UTC")
    rows = [{"timestamp": t0 + pd.Timedelta(minutes=3 * i), "open": 100 + i,
             "high": 101 + i, "low": 99 + i, "close": 100 + i,
             "tick_volume": 10, "spread": 0} for i in range(10)]
    df = pd.DataFrame(rows)
    ctx = s.prepare(df, p)
    assert not ctx["trade_ok"][:5].any() and ctx["trade_ok"][5:].all()
    assert all(s.entry_signal(df, i, ctx, p) == 0 for i in range(5))


def test_vwap_only_in_session():
    """Fuera de las ventanas Londres/NY no hay senales ni VWAP."""
    import pandas as pd
    from bt.strategies import get_strategy
    s, _ = get_strategy("vwap_session")
    t0 = pd.Timestamp("2026-01-05 03:00", tz="UTC")  # madrugada: fuera de sesion
    rows = [{"timestamp": t0 + pd.Timedelta(minutes=3 * i), "open": 100 + i * 0.5,
             "high": 101 + i * 0.5, "low": 99 + i * 0.5, "close": 100 + i * 0.5,
             "tick_volume": 10, "spread": 0} for i in range(40)]
    df = pd.DataFrame(rows)
    ctx = s.prepare(df, {"ema": 9, "sessions": [["07:00", "10:00"], ["12:00", "15:00"]]})
    import numpy as np
    assert bool(np.isnan(ctx["vwap"]).all())
    assert all(s.entry_signal(df, i, ctx, {"ema": 9, "sessions": [["07:00", "10:00"], ["12:00", "15:00"]]}) == 0
               for i in range(len(df)))


def test_vwap_m15_breakout_entry():
    """Variante A: solo opera tras las 2 velas de referencia y al romper su rango."""
    import pandas as pd
    from bt.strategies import get_strategy
    s, _ = get_strategy("vwap_m15")
    p = {"ema": 9, "ref_bars": 2, "sessions": [["Europe/London", "08:00", "11:00"]]}
    t0 = pd.Timestamp("2026-08-15 07:00", tz="UTC")  # Londres BST = 07:00 UTC
    closes = [100.0, 101.0, 102.5, 102.0]
    rows = []
    for i, close in enumerate(closes):
        rows.append({"timestamp": t0 + pd.Timedelta(minutes=15 * i), "open": close - 0.5,
                     "high": max(close, 101.0 + i), "low": min(close, 99.0),
                     "close": close, "tick_volume": 10, "spread": 0})
    df = pd.DataFrame(rows)
    ctx = s.prepare(df, p)
    assert not ctx["trade_ok"][:2].any()
    assert s.entry_signal(df, 0, ctx, p) == 0
    assert s.entry_signal(df, 1, ctx, p) == 0
    assert s.entry_signal(df, 2, ctx, p) == 1
    assert s.entry_signal(df, 3, ctx, p) == 0
    df_short = df.copy()
    df_short.loc[2, "low"] = 97.0
    df_short.loc[2, "close"] = 98.0
    ctx_short = s.prepare(df_short, p)
    assert s.entry_signal(df_short, 2, ctx_short, p) == -1
