"""Downloader MT5 -> local. MT5 SOLO se usa aqui. El resto del motor no lo necesita."""
import os
import time
import pandas as pd
from .config import TF_SECONDS
from .data_manager import save_bars, load_bars
from .validator import validate

MT5_TF_ATTR = {
    "M1": "TIMEFRAME_M1", "M2": "TIMEFRAME_M2", "M3": "TIMEFRAME_M3",
    "M5": "TIMEFRAME_M5", "M15": "TIMEFRAME_M15", "M30": "TIMEFRAME_M30",
    "H1": "TIMEFRAME_H1", "H4": "TIMEFRAME_H4", "D1": "TIMEFRAME_D1",
}

MT5_PATH_DEFAULT = r"C:\Program Files\MetaTrader 5\terminal64.exe"


def connect(mt5_path: str = MT5_PATH_DEFAULT):
    import MetaTrader5 as mt5
    if not mt5.initialize(path=mt5_path):
        raise RuntimeError(f"MT5 no conecta: {mt5.last_error()}")
    return mt5


def available_symbols(mt5) -> list:
    syms = mt5.symbols_get()
    return sorted(s.name for s in syms) if syms else []


def download_symbol_tf(mt5, symbol: str, tf: str, bars: int = 50000,
                       root: str = "data/weltrade") -> dict:
    mt5.symbol_select(symbol, True)
    mt5_tf = getattr(mt5, MT5_TF_ATTR[tf])
    # incremental: continuar desde ultimo timestamp local
    date_from = None
    try:
        old = load_bars(symbol, tf, root)
        if len(old):
            last_ts = pd.to_datetime(old["timestamp"].iloc[-1])
            date_from = last_ts.to_pydatetime()
    except FileNotFoundError:
        old = None
    if date_from is not None:
        rates = mt5.copy_rates_from(symbol, mt5_tf, date_from, bars)
    else:
        rates = mt5.copy_rates_from_pos(symbol, mt5_tf, 0, bars)
    if rates is None or len(rates) == 0:
        return {"symbol": symbol, "tf": tf, "rows": 0, "note": "sin datos (mercado cerrado o sin historial)"}
    df = pd.DataFrame(rates)
    df["timestamp"] = pd.to_datetime(df["time"], unit="s", utc=True)
    df = df.rename(columns={"tick_volume": "tick_volume"})
    if "spread" not in df.columns:
        df["spread"] = 0
    df = df[["timestamp", "open", "high", "low", "close", "tick_volume", "spread"]]
    if old is not None and len(old):
        df = pd.concat([old, df], ignore_index=True)
        df = df.sort_values("timestamp").drop_duplicates(subset=["timestamp"]).reset_index(drop=True)
    info = save_bars(df, symbol, tf, root)
    rep = validate(df, tf)
    info.update({"symbol": symbol, "tf": tf, "validation": rep})
    return info
