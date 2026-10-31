"""DataManager: almacenamiento local SYMBOL/TF. CSV gzip siempre, Parquet opcional."""
import os
import hashlib
import pandas as pd
from .config import DATA_ROOT

COLS = ["timestamp", "open", "high", "low", "close", "tick_volume", "spread"]


def _safe_sym(symbol: str) -> str:
    return "".join(c if (c.isalnum() or c in ("-", "_", " ")) else "_" for c in symbol).strip()


def data_path(symbol: str, tf: str, root: str = DATA_ROOT) -> str:
    return os.path.join(root, _safe_sym(symbol), f"{tf}.csv.gz")


def parquet_path(symbol: str, tf: str, root: str = DATA_ROOT) -> str:
    return os.path.join(root, _safe_sym(symbol), f"{tf}.parquet")


def save_bars(df: pd.DataFrame, symbol: str, tf: str, root: str = DATA_ROOT) -> dict:
    df = df.copy()
    df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)
    df = df.sort_values("timestamp").drop_duplicates(subset=["timestamp"]).reset_index(drop=True)
    for c in COLS:
        if c not in df.columns:
            df[c] = 0
    df = df[COLS]
    path = data_path(symbol, tf, root)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    df.to_csv(path, index=False, compression="gzip")
    out = {"csv": path, "rows": len(df)}
    try:
        import pyarrow  # noqa: F401
        pq = parquet_path(symbol, tf, root)
        df.to_parquet(pq, index=False)
        out["parquet"] = pq
    except Exception:
        pass
    # hash reproducible de los datos
    h = hashlib.sha256(pd.util.hash_pandas_object(df, index=False).values.tobytes()).hexdigest()[:16]
    out["data_hash"] = h
    return out


def load_bars(symbol: str, tf: str, root: str = DATA_ROOT) -> pd.DataFrame:
    for p in (parquet_path(symbol, tf, root), data_path(symbol, tf, root)):
        if os.path.exists(p):
            df = pd.read_parquet(p) if p.endswith(".parquet") else pd.read_csv(p, compression="gzip")
            df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)
            return df.sort_values("timestamp").reset_index(drop=True)
    raise FileNotFoundError(f"Sin datos locales para {symbol} {tf}. Ejecuta download_data primero.")


def _cache_path(root: str = DATA_ROOT) -> str:
    # El cache debe distinguir la fuente: weltrade y yahoo pueden tener
    # los mismos nombres de símbolo con coberturas distintas.
    if os.path.abspath(root) == os.path.abspath(DATA_ROOT):
        return os.path.join("results", "inventory_cache.json")
    import hashlib
    tag = hashlib.sha1(os.path.abspath(root).encode("utf-8")).hexdigest()[:8]
    return os.path.join("results", f"inventory_cache_{tag}.json")


def symbol_info(symbol: str, root: str = DATA_ROOT) -> dict:
    """Lee info.json real de MT5 (spread, tick, volumen min/max/step).
    Si no existe, devuelve valores neutros marcados como alternativa."""
    import json
    p = os.path.join(root, _safe_sym(symbol), "info.json")
    if os.path.exists(p):
        try:
            d = json.load(open(p, encoding="utf-8"))
            d["fallback"] = False
            return d
        except Exception:
            pass
    return {"spread": 0, "trade_tick_value": 0.0, "trade_tick_size": 0.0,
            "volume_min": 0.01, "volume_max": 100.0, "volume_step": 0.01,
            "trade_contract_size": 1.0, "digits": 2, "point": 0.0,
            "point_price": 0.0, "fallback": True}


def contract_size(info: dict) -> float:
    """$ por punto de precio y por lote, segun tick de MT5."""
    tv = info.get("trade_tick_value") or 0.0
    ts = info.get("trade_tick_size") or 0.0
    if tv and ts:
        return tv / ts
    return info.get("trade_contract_size", 1.0) or 1.0


def inventory(root: str = DATA_ROOT, use_cache: bool = True) -> list:
    """Inventario con cache por (mtime, tamaño): no re-lee archivos sin cambios.
    Asi el panel puede actualizarse sin cargar los 300+ ficheros en RAM."""
    import json
    cache_file = _cache_path(root)
    cache = {}
    if use_cache and os.path.exists(cache_file):
        try:
            cache = json.load(open(cache_file, encoding="utf-8"))
        except Exception:
            cache = {}
    inv = []
    changed = False
    if not os.path.isdir(root):
        return inv
    for sym in sorted(os.listdir(root)):
        d = os.path.join(root, sym)
        if not os.path.isdir(d):
            continue
        for f in sorted(os.listdir(d)):
            if not f.endswith(".csv.gz"):
                continue
            tf = f[:-7]
            p = os.path.join(d, f)
            try:
                st = os.stat(p)
                key = f"{sym}/{tf}"
                hit = cache.get(key)
                if hit and hit.get("mtime") == st.st_mtime and hit.get("size") == st.st_size:
                    inv.append(hit["item"])
                    continue
                df = pd.read_csv(p, compression="gzip", usecols=["timestamp"])
                item = {"symbol": sym, "timeframe": tf, "rows": len(df),
                        "from": str(df["timestamp"].iloc[0]), "to": str(df["timestamp"].iloc[-1])}
                del df
                cache[key] = {"mtime": st.st_mtime, "size": st.st_size, "item": item}
                changed = True
                inv.append(item)
            except Exception as e:
                inv.append({"symbol": sym, "timeframe": tf, "error": str(e)[:120]})
    if changed:
        try:
            os.makedirs(os.path.dirname(cache_file), exist_ok=True)
            tmp = cache_file + ".tmp"
            json.dump(cache, open(tmp, "w", encoding="utf-8"))
            os.replace(tmp, cache_file)  # atomico: un corte nunca deja basura
        except Exception:
            pass
    return inv
