"""BacktestEngine: loop por barra, sin futuro, reproducible con BT-ID."""
import hashlib
import json
import os
import time
import pandas as pd
from .config import ENGINE_VERSION, RESULTS_ROOT
from .execution import Portfolio, ExecConfig, position_size
from .indicators import atr as atr_fn
from .metrics import compute_metrics
from .spike import detect as detect_spikes
from .strategies import get_strategy

_counter_path = os.path.join(RESULTS_ROOT, "_counter.txt")


def next_bt_id() -> str:
    os.makedirs(RESULTS_ROOT, exist_ok=True)
    n = 0
    if os.path.exists(_counter_path):
        try:
            n = int(open(_counter_path).read().strip() or 0)
        except Exception:
            n = 0
    n += 1
    open(_counter_path, "w").write(str(n))
    return f"BT-2026-{n:06d}"


def run_backtest(df: pd.DataFrame, strategy_key: str, strategy_params: dict,
                 exec_cfg: ExecConfig, symbol: str, timeframe: str,
                 data_hash: str = "", save: bool = True) -> dict:
    strat, defaults = get_strategy(strategy_key)
    params = {**defaults, **(strategy_params or {})}
    ctx = strat.prepare(df, params)
    pf = Portfolio(exec_cfg)

    # Columnas a arrays una sola vez: el loop no toca pandas por barra.
    opens = df["open"].to_numpy(float)
    highs = df["high"].to_numpy(float)
    lows = df["low"].to_numpy(float)
    closes = df["close"].to_numpy(float)
    stamps = df["timestamp"].to_numpy()
    atr_arr = None
    try:
        atr_arr = atr_fn(df, int(params.get("atr_period", 20)))
    except Exception:
        atr_arr = None

    n = len(df)

    def eq_now(b):
        # Capital con flotante de abiertas al cierre (drawdown honesto)
        f = 0.0
        for _pp in pf.positions:
            _d = (b["close"] - _pp["entry"]) if _pp["direction"] == 1 else (_pp["entry"] - b["close"])
            f += _d * _pp["qty"] * exec_cfg.contract_size
        return pf.balance + f

    spike_at, blocked_at = detect_spikes(
        highs, lows, closes, k=float(exec_cfg.spike_k),
        period=int(params.get("atr_period", 20)), cooldown=int(exec_cfg.spike_cooldown))
    import time as _time
    blown = False
    for i in range(n):
        if i % 2000 == 0 and i:
            _time.sleep(0)  # ceder CPU: el panel sigue respondiendo en PC lentas
        bar = {"open": opens[i], "high": highs[i], "low": lows[i], "close": closes[i]}
        ts = stamps[i]
        atr_now = float(atr_arr[i]) if atr_arr is not None and i < len(atr_arr) else None
        if atr_now is not None and not (atr_now == atr_now and atr_now > 0):
            atr_now = None

        # 1) gestionar posiciones abiertas con la barra actual
        # Margen sobre CAPITAL + FLOTANTE (como el broker): si la equidad
        # toca cero o menos, se cierra todo y no se abre mas.
        eqnow = eq_now(bar)
        if not blown and eqnow <= 0:
            for pos in list(pf.positions):
                pf.close(pos, ts, bar["close"], "CUENTA EN CERO", exit_idx=i)
            blown = True
        for pos in list(pf.positions):
            if exec_cfg.spike_close and spike_at[i]:
                pf.close(pos, ts, bar["close"], "PICO", exit_idx=i)
                continue
            should, px, reason = pf.manage_bar(pos, bar, atr_now)
            if should:
                pf.close(pos, ts, px, reason, exit_idx=i)
                continue
            if strat.exit_signal(df, i, ctx, params, pos["direction"]):
                pf.close(pos, ts, bar["close"],
                         strat.exit_reason(df, i, ctx, params, pos["direction"]),
                         exit_idx=i)
                continue
            pf.track_bar(pos, bar)

        # 2) nueva señal solo con informacion hasta i (sin futuro)
        if blown:
            pf.equity_curve.append(eq_now(bar))
            continue
        if blocked_at[i]:
            # pico o cooldown: la senal de esta vela es ruido, no se opera
            pf.equity_curve.append(eq_now(bar))
            continue
        sig = strat.entry_signal(df, i, ctx, params)
        if sig == 0:
            pf.equity_curve.append(eq_now(bar))
            continue
        if sig == 1 and not exec_cfg.allow_long:
            pf.equity_curve.append(eq_now(bar))
            continue
        if sig == -1 and not exec_cfg.allow_short:
            pf.equity_curve.append(eq_now(bar))
            continue
        if len(pf.positions) >= exec_cfg.max_positions:
            pf.equity_curve.append(eq_now(bar))
            continue
        # reversa: si hay posicion contraria abierta, el exit de arriba ya la cerro;
        # si aun hay del mismo lado, no duplicar
        if any(p["direction"] == sig for p in pf.positions):
            pf.equity_curve.append(eq_now(bar))
            continue

        if exec_cfg.entry_mode == "next_open" and i + 1 < n:
            ts_in = stamps[i + 1]
            px_in = opens[i + 1]
        else:
            ts_in = ts
            px_in = bar["close"]
        sl, tp = strat.stop_price(df, i, ctx, params, sig, px_in)
        # Si la estrategia exige stop (sl_mult o need_sl) pero no es valido,
        # no se abre: jamas una posicion con stop obligatorio sin stop.
        if sl is None and (params.get("sl_mult") or params.get("need_sl")):
            pf.equity_curve.append(eq_now(bar))
            continue
        sl_dist = abs(px_in - sl) if sl else 0.0
        # Riesgo 1% sobre capital CORRIENTE (interes compuesto, regla Turtle original)
        qty = position_size(pf.balance, exec_cfg.risk_pct, exec_cfg.lot,
                            sl_dist, exec_cfg.min_lot, exec_cfg.max_lot,
                            exec_cfg.lot_step, exec_cfg.contract_size)
        pf.open(sig, ts, bar["close"], ts_in, px_in, sl, tp, qty,
                f"{strategy_key}", atr=atr_now, entry_idx=i)
        pf.equity_curve.append(eq_now(bar))

    # cerrar remanente al ultimo cierre
    if pf.positions:
        last_ts = stamps[n - 1]
        last_px = closes[n - 1]
        for pos in list(pf.positions):
            pf.close(pos, last_ts, last_px, "FIN DE DATOS", exit_idx=n - 1)

    metrics = compute_metrics(exec_cfg.initial_balance, pf.trades, pf.equity_curve)
    cfg = {"strategy": strategy_key, "params": params, "symbol": symbol,
           "timeframe": timeframe, "rows": n,
           "from": str(stamps[0]), "to": str(stamps[n - 1]),
           "data_hash": data_hash, "engine": ENGINE_VERSION,
           "spike_k": float(exec_cfg.spike_k),
           "spike_cooldown": int(exec_cfg.spike_cooldown),
           "spikes_detected": int(spike_at.sum()),
           "spikes_pct": round(100.0 * float(spike_at.sum()) / n, 3) if n else 0.0,
           "exec": exec_cfg.__dict__}
    # Sin operaciones no hay backtest: no se asigna ID ni se guarda nada.
    if metrics["total"] == 0:
        return {"bt_id": None, "config_hash": "", "config": cfg,
                "metrics": metrics, "trades": [], "equity_curve": [],
                "created": int(time.time()), "empty": True}
    digest = hashlib.sha256(json.dumps(cfg, sort_keys=True, default=str).encode()).hexdigest()[:12]
    # Solo consume un BT-ID cuando se guarda de verdad. Si save=False (optimize, MC),
    # no toca el contador ni crea carpeta: evita huecos en results/.
    if save:
        bt_id = next_bt_id()
        outdir = os.path.join(RESULTS_ROOT, bt_id)
        os.makedirs(outdir, exist_ok=True)
        with open(os.path.join(outdir, "config.json"), "w") as f:
            json.dump(cfg, f, indent=2, default=str)
        pd.DataFrame(pf.trades).to_csv(os.path.join(outdir, "trades.csv"), index=False)
        with open(os.path.join(outdir, "metrics.json"), "w") as f:
            json.dump(metrics, f, indent=2, default=str)
        pd.DataFrame({"equity": pf.equity_curve}).to_csv(
            os.path.join(outdir, "equity.csv"), index=False)
    else:
        bt_id = None
    result = {"bt_id": bt_id, "config_hash": digest, "config": cfg,
              "metrics": metrics, "trades": pf.trades,
              "equity_curve": pf.equity_curve, "created": int(time.time())}
    return result
