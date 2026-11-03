"""Importador MT5 para el panel: velas y ticks, siempre secuencial y con progreso.

Reglas del proyecto:
  - MT5 SOLO se usa aquí y en bt/downloader.py. El motor no lo necesita.
  - Nada se lanza de golpe: un trabajo, un símbolo/temporalidad a la vez.
  - Nada se inventa: si MT5 no está conectado o no tiene el histórico pedido,
    se informa del error real que devuelve MT5.
  - Los archivos se guardan en data/weltrade/<SÍMBOLO>/ (CSV gzip), igual que
    el resto de la app, así que el inventario los detecta sin tocar nada más.
"""
import os
import threading
import time

TF_ATTR = {
    "M1": "TIMEFRAME_M1", "M3": "TIMEFRAME_M3", "M5": "TIMEFRAME_M5",
    "M15": "TIMEFRAME_M15", "M30": "TIMEFRAME_M30",
    "H1": "TIMEFRAME_H1", "H4": "TIMEFRAME_H4", "D1": "TIMEFRAME_D1",
}
DATA_ROOT = "data/weltrade"

# Un único trabajo MT5 a la vez: MT5 no admite dos conexiones desde el mismo hilo
# y así no se satura la RAM ni el disco.
_LOCK = threading.Lock()
JOBS = {}
_ACTIVE = {"id": None}


def _safe_sym(symbol: str) -> str:
    return "".join(c if (c.isalnum() or c in ("-", "_", " ")) else "_" for c in symbol).strip()


def availability() -> dict:
    """¿Se puede hablar con MT5 ahora mismo? Devuelve el motivo exacto si no."""
    try:
        import MetaTrader5 as mt5
    except Exception as e:  # módulo no instalado
        return {"available": False, "reason": "Falta el paquete MetaTrader5: pip install MetaTrader5",
                "detail": str(e)[:200], "version": None}
    try:
        ok = mt5.initialize()
        if not ok:
            code, msg = mt5.last_error()
            hint = ("Abre MetaTrader 5, conéctalo a la cuenta de Weltrade y vuelve a intentarlo. "
                    "Si no está en la ruta por defecto, cambia MT5_PATH_DEFAULT en bt/downloader.py.")
            if "not found" in str(msg).lower() or "IPC" in str(msg):
                hint = ("MetaTrader 5 no está abierto o no se encuentra. Ábrelo, entra con tu cuenta "
                        "de Weltrade y deja la ventana abierta mientras descargas. Si lo tienes "
                        "instalado en otra carpeta, ajusta MT5_PATH_DEFAULT en bt/downloader.py.")
            if "Incompatible" in str(msg):
                hint = ("El módulo Python y el terminal no son la misma versión. Actualiza el "
                        "terminal MT5 (Ayuda → Comprobar actualizaciones) o reinstala "
                        "'pip install --upgrade MetaTrader5' y cierra MT5 del todo antes de reintentar.")
            return {"available": False, "reason": msg, "hint": hint,
                    "code": code, "version": mt5.__version__, "detail": ""}
        ti = mt5.terminal_info()
        acc = mt5.account_info()
        out = {"available": True, "reason": "", "version": mt5.__version__,
               "terminal": getattr(ti, "name", "") if ti else "",
               "company": getattr(acc, "company", "") if acc else "",
               "server": getattr(acc, "server", "") if acc else "",
               "login": getattr(acc, "login", None) if acc else None}
        mt5.shutdown()
        return out
    except Exception as e:
        return {"available": False, "reason": str(e)[:200], "hint": "", "version": None}


def symbols() -> dict:
    """Lista real de símbolos del terminal (vacía si MT5 no responde)."""
    info = availability()
    if not info.get("available"):
        return {"available": False, "reason": info.get("reason", ""), "symbols": []}
    try:
        import MetaTrader5 as mt5
        if not mt5.initialize():
            return {"available": False, "reason": mt5.last_error()[1], "symbols": []}
        syms = mt5.symbols_get() or []
        names = sorted(s.name for s in syms)
        # Los índices sintéticos de Weltrade se pueden separar del resto.
        sint = [n for n in names if any(k in n for k in
                ("X ", "Vol", "Flip", "Trend", "Break", "Gain", "Pain", "Switch", "Plus", "Quad", "Fibo"))]
        mt5.shutdown()
        return {"available": True, "symbols": names, "synthetic": sint, "total": len(names)}
    except Exception as e:
        return {"available": False, "reason": str(e)[:200], "symbols": []}


INFO_FIELDS = ["spread", "trade_tick_value", "trade_tick_size", "volume_min",
               "volume_max", "volume_step", "trade_contract_size", "digits",
               "point", "trade_mode", "swap_long", "swap_short", "swap_mode",
               "swap_rollover3days", "currency_profit", "margin_initial",
               "description"]


def _save_info(mt5, symbol: str) -> bool:
    """Guarda los costes reales que publica el broker en MT5 (spread, swap, lote)."""
    import json
    try:
        info = mt5.symbol_info(symbol)
        if info is None:
            return False
        d = {f: getattr(info, f, None) for f in INFO_FIELDS}
        if d.get("spread") and d.get("point"):
            d["point_price"] = d["spread"] * d["point"]
        else:
            d["point_price"] = 0.0
        folder = os.path.join(DATA_ROOT, _safe_sym(symbol))
        os.makedirs(folder, exist_ok=True)
        with open(os.path.join(folder, "info.json"), "w", encoding="utf-8") as f:
            json.dump(d, f, indent=2, default=str)
        return True
    except Exception:
        return False


def _incremental_from(symbol: str, tf: str):
    """Última vela local, para no volver a descargar lo que ya está."""
    import pandas as pd
    from bt.data_manager import load_bars
    try:
        df = load_bars(symbol, tf, DATA_ROOT)
        if len(df):
            return pd.to_datetime(df["timestamp"].iloc[-1]).to_pydatetime(), len(df)
    except Exception:
        pass
    return None, 0


def _download_bars(mt5, symbol: str, tf: str, bars: int) -> dict:
    import pandas as pd
    attr = TF_ATTR[tf]
    mt5.symbol_select(symbol, True)
    last_ts, old_rows = _incremental_from(symbol, tf)
    if last_ts is not None:
        rates = mt5.copy_rates_from(symbol, getattr(mt5, attr), last_ts, int(bars))
    else:
        rates = mt5.copy_rates_from_pos(symbol, getattr(mt5, attr), 0, int(bars))
    if rates is None or len(rates) == 0:
        code, msg = mt5.last_error()
        return {"ok": False, "rows": 0, "old": old_rows,
                "note": f"MT5 no devolvió velas ({code}: {msg})"}
    df = pd.DataFrame(rates)
    df["timestamp"] = pd.to_datetime(df["time"], unit="s", utc=True)
    for c in ("open", "high", "low", "close", "tick_volume", "spread"):
        if c not in df.columns:
            df[c] = 0
    df = df[["timestamp", "open", "high", "low", "close", "tick_volume", "spread"]]
    new_rows = 0
    if old_rows:
        from bt.data_manager import load_bars
        old = load_bars(symbol, tf, DATA_ROOT)
        before = len(old)
        df = pd.concat([old, df], ignore_index=True)
        df = df.sort_values("timestamp").drop_duplicates(subset=["timestamp"]).reset_index(drop=True)
        new_rows = len(df) - before
    from bt.data_manager import save_bars
    info = save_bars(df, symbol, tf, DATA_ROOT)
    # "new" es lo añadido de verdad: 0 si ya estaba todo descargado.
    return {"ok": True, "rows": info["rows"], "new": (new_rows if old_rows else info["rows"]),
            "old": old_rows}


def _download_ticks(mt5, symbol: str, days: int) -> dict:
    """Ticks reales (bid/ask) del rango pedido. MT5 suele guardar poco histórico."""
    import pandas as pd
    from datetime import datetime, timedelta, timezone
    mt5.symbol_select(symbol, True)
    to = datetime.now(timezone.utc) + timedelta(days=1)
    frm = to - timedelta(days=int(days) + 1)
    ticks = mt5.copy_ticks_range(symbol, frm, to, mt5.COPY_TICKS_ALL)
    if ticks is None or len(ticks) == 0:
        code, msg = mt5.last_error()
        return {"ok": False, "rows": 0, "note": f"MT5 no tiene ticks de ese rango ({code}: {msg})"}
    df = pd.DataFrame(ticks)
    df["timestamp"] = pd.to_datetime(df["time_msc"], unit="ms", utc=True)
    keep = [c for c in ("timestamp", "bid", "ask", "last", "volume", "flags") if c in df.columns]
    df = df[keep].sort_values("timestamp").reset_index(drop=True)
    folder = os.path.join(DATA_ROOT, _safe_sym(symbol))
    os.makedirs(folder, exist_ok=True)
    stamp = pd.to_datetime(df["timestamp"].iloc[0]).strftime("%Y%m%d")
    path = os.path.join(folder, f"ticks_{stamp}.csv.gz")
    df.to_csv(path, index=False, compression="gzip")
    days_covered = df["timestamp"].dt.strftime("%Y-%m-%d").nunique()
    return {"ok": True, "rows": len(df), "new": len(df), "path": path, "days": days_covered}


def _snapshot_book(mt5, symbol: str) -> dict:
    """El libro de órdenes (DOM) de MT5 no tiene histórico: se guarda una foto."""
    import json
    from datetime import datetime, timezone
    mt5.symbol_select(symbol, True)
    if not mt5.market_book_add(symbol):
        code, msg = mt5.last_error()
        return {"ok": False, "note": f"MT5 no da libro de órdenes ({code}: {msg}). "
                                     "Suele faltar la profundidad en ese símbolo."}
    time.sleep(0.6)
    book = mt5.market_book_get(symbol)
    mt5.market_book_release(symbol)
    if not book:
        code, msg = mt5.last_error()
        return {"ok": False, "note": f"Libro vacío ({code}: {msg})"}
    levels = [{"type": "bid" if b.type == 1 else "ask", "price": b.price,
               "volume": b.volume, "volume_real": getattr(b, "volume_real", 0)}
              for b in book]
    now = datetime.now(timezone.utc)
    folder = os.path.join(DATA_ROOT, _safe_sym(symbol))
    os.makedirs(folder, exist_ok=True)
    path = os.path.join(folder, "book_" + now.strftime("%Y%m%d_%H%M%S") + ".json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump({"symbol": symbol, "time": now.isoformat(), "levels": levels}, f, indent=1)
    return {"ok": True, "rows": len(levels), "new": len(levels), "path": path}


def _job_loop(job_id: str, symbols_: list, tfs: list, bars: int, mode: str, tick_days: int):
    job = JOBS[job_id]
    try:
        import MetaTrader5 as mt5
    except Exception as e:
        job["status"] = "error"
        job["error"] = "Falta el paquete MetaTrader5: pip install MetaTrader5 (" + str(e)[:120] + ")"
        return
    if not mt5.initialize():
        code, msg = mt5.last_error()
        job["status"] = "error"
        job["error"] = f"MT5 no conecta ({code}: {msg})"
        return
    try:
        if mode == "book":
            job["total"] = len(symbols_)
            for sym in symbols_:
                if job.get("cancel"):
                    job["status"] = "cancelado"
                    return
                job["current"] = sym
                _save_info(mt5, sym)
                try:
                    r = _snapshot_book(mt5, sym)
                except Exception as e:
                    r = {"ok": False, "note": str(e)[:150]}
                job["log"].append({"symbol": sym, "tf": "LIBRO", **{k: r.get(k) for k in
                                    ("ok", "rows", "new", "note", "path") if k in r}})
                job["done"] += 1
                time.sleep(0.1)
        elif mode == "ticks":
            job["total"] = len(symbols_)
            for sym in symbols_:
                if job.get("cancel"):
                    job["status"] = "cancelado"
                    return
                job["current"] = sym
                _save_info(mt5, sym)
                try:
                    r = _download_ticks(mt5, sym, tick_days)
                except Exception as e:
                    r = {"ok": False, "note": str(e)[:150]}
                job["log"].append({"symbol": sym, "tf": "TICKS", **{k: r.get(k) for k in
                                    ("ok", "rows", "new", "note", "days", "path") if k in r}})
                job["done"] += 1
                time.sleep(0.05)
        else:
            job["total"] = len(symbols_) * len(tfs)
            for sym in symbols_:
                _save_info(mt5, sym)
                for tf in tfs:
                    if job.get("cancel"):
                        job["status"] = "cancelado"
                        return
                    job["current"] = f"{sym} {tf}"
                    try:
                        r = _download_bars(mt5, sym, tf, bars)
                    except Exception as e:
                        r = {"ok": False, "note": str(e)[:150]}
                    job["log"].append({"symbol": sym, "tf": tf, **{k: r.get(k) for k in
                                        ("ok", "rows", "new", "old", "note") if k in r}})
                    job["done"] += 1
                    time.sleep(0.02)  # deja respirar a MT5 y al disco
        job["status"] = "hecho"
    finally:
        try:
            mt5.shutdown()
        except Exception:
            pass
        with _LOCK:
            if _ACTIVE["id"] == job_id:
                _ACTIVE["id"] = None


def start(symbols_, tfs, bars=50000, mode="bars", tick_days=3) -> dict:
    """Arranca un trabajo secuencial. Solo uno a la vez."""
    symbols_ = [s.strip() for s in (symbols_ or []) if str(s).strip()]
    tfs = [t for t in (tfs or []) if t in TF_ATTR]
    if not symbols_:
        return {"error": "Elige al menos un símbolo."}
    if mode == "bars" and not tfs:
        return {"error": "Elige al menos una temporalidad."}
    with _LOCK:
        if _ACTIVE["id"]:
            return {"error": "Ya hay una descarga de MT5 en marcha. Espera a que termine.",
                    "job": _ACTIVE["id"]}
        job_id = "mt5-" + str(int(time.time() * 1000))[-8:]
        JOBS[job_id] = {"id": job_id, "status": "trabajando", "done": 0,
                        "total": len(symbols_) * (len(tfs) if mode == "bars" else 1),
                        "current": "", "mode": mode, "log": [], "started": int(time.time())}
        _ACTIVE["id"] = job_id
    t = threading.Thread(target=_job_loop, daemon=True,
                         args=(job_id, symbols_, tfs, bars, mode, tick_days))
    t.start()
    return {"job": job_id, **_peek(job_id)}


def _peek(job_id: str) -> dict:
    j = JOBS.get(job_id)
    if not j:
        return {"error": "trabajo desconocido"}
    out = {k: j[k] for k in ("id", "status", "done", "total", "current", "mode")}
    if j.get("error"):
        out["error"] = j["error"]
    out["log_tail"] = j["log"][-12:]
    out["ok_count"] = sum(1 for x in j["log"] if x.get("ok"))
    out["fail_count"] = sum(1 for x in j["log"] if not x.get("ok"))
    out["saved_rows"] = sum(int(x.get("new") or 0) for x in j["log"])
    return out


def status(job_id: str) -> dict:
    return _peek(job_id)


def active() -> dict:
    return {"active": _ACTIVE["id"]}


def cancel(job_id: str) -> dict:
    j = JOBS.get(job_id)
    if j:
        j["cancel"] = True
        return {"ok": True}
    return {"error": "trabajo desconocido"}
