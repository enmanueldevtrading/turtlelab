"""Yahoo Finance -> data/yahoo. Separado de Weltrade (data/weltrade intacto)."""
import os
import pandas as pd
from .data_manager import save_bars
from .validator import validate

YAHOO_SYMBOLS = {
    "Oro": "GC=F",
    "NAS100": "^NDX",
    "Dow Jones": "^DJI",
    "EURUSD": "EURUSD=X",
    "USDJPY": "USDJPY=X",
    "EURJPY": "EURJPY=X",
    "CADJPY": "CADJPY=X",
    "NZDJPY": "NZDJPY=X",
    "BTC": "BTC-USD",
    "Plata": "SI=F",
    "Crudo": "CL=F",
    "SP500": "^GSPC",
    "GBPUSD": "GBPUSD=X",
    "GBPJPY": "GBPJPY=X",
    "USDCHF": "USDCHF=X",
}

YAHOO_TFS = {
    "D1": {"interval": "1d", "period": "max"},
    "H1": {"interval": "1h", "period": "2y"},
    "M5": {"interval": "5m", "period": "60d"},
    "M15": {"interval": "15m", "period": "60d"},
    "M1": {"interval": "1m", "period": "7d"},
}

ROOT = "data/yahoo"


def download_one(display: str, tf: str, root: str = ROOT) -> dict:
    import yfinance as yf
    ticker = YAHOO_SYMBOLS[display]
    cfg = YAHOO_TFS[tf]
    df = yf.download(ticker, interval=cfg["interval"], period=cfg["period"],
                     auto_adjust=False, progress=False)
    if df is None or len(df) == 0:
        return {"display": display, "tf": tf, "rows": 0, "error": "sin datos"}
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    out = pd.DataFrame({
        "timestamp": pd.to_datetime(df.index, utc=True),
        "open": df["Open"].to_numpy(float),
        "high": df["High"].to_numpy(float),
        "low": df["Low"].to_numpy(float),
        "close": df["Close"].to_numpy(float),
        "tick_volume": df["Volume"].fillna(0).to_numpy(float),
        "spread": 0.0,
    })
    out = out.dropna(subset=["open", "high", "low", "close"]).reset_index(drop=True)
    info = save_bars(out, display, tf, root)
    info.update({"display": display, "tf": tf, "ticker": ticker,
                 "validation": validate(out, "D1" if tf == "D1" else "H1")})
    return info


def download_all(symbols=None, tfs=("D1", "H1"), root: str = ROOT) -> list:
    syms = symbols or sorted(YAHOO_SYMBOLS)
    rep = []
    for s in syms:
        for tf in tfs:
            try:
                rep.append(download_one(s, tf, root))
            except Exception as e:
                rep.append({"display": s, "tf": tf, "rows": 0, "error": str(e)[:150]})
    return rep
