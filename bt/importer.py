"""Importador de datos sueltos: busca OHLC en el proyecto y los normaliza.

Motivo: hay velas fuera de `data/` (por ejemplo `SwitchX1800_Dataset/`) que el
panel no veía. Este modulo las detecta, las convierte al formato del motor
(`data/weltrade/<Simbolo>/<TF>.csv.gz` + `info.json`) y no sobrescribe nada:
fusiona por timestamp y descarta duplicados.
"""
import glob
import json
import os

import pandas as pd

from .data_manager import load_bars, save_bars

TF_LIST = ["M1", "M3", "M5", "M15", "M30", "H1", "H4", "D1"]
TF_SECONDS = {"M1": 60, "M3": 180, "M5": 300, "M15": 900, "M30": 1800,
              "H1": 3600, "H4": 14400, "D1": 86400}
COLS = ["timestamp", "open", "high", "low", "close", "tick_volume", "spread"]
CANDIDATE_DIRS = ["SwitchX1800_Dataset", "SwitchX1800_Dataset.zip"]

ES_KEYS = {
    "tick_size": "trade_tick_size", "tick_value": "trade_tick_value",
    "tamano_contrato": "trade_contract_size", "volumen_minimo": "volume_min",
    "volumen_maximo": "volume_max", "paso_volumen": "volume_step",
    "digitos": "digits", "punto": "point", "nombre": "symbol",
    "descripcion": "description",
}


def _read_header(path):
    try:
        if path.endswith(".gz"):
            import gzip
            with gzip.open(path, "rt", encoding="utf-8", errors="replace") as f:
                return [h.strip().lower() for h in f.readline().split(",")]
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            return [h.strip().lower() for h in f.readline().split(",")]
    except Exception:
        return []


def _has_ohlc(header):
    need = {"open", "high", "low", "close"}
    return need <= set(header) and (("timestamp" in header) or ("time" in header)
                                    or ("fecha" in header) or ("date" in header))


def _count_rows(path):
    n = 0
    try:
        if path.endswith(".gz"):
            import gzip
            with gzip.open(path, "rb") as f:
                for _ in f:
                    n += 1
        else:
            with open(path, "rb") as f:
                for _ in f:
                    n += 1
    except Exception:
        return 0
    return max(0, n - 1)


TF_ANY = {"M1": 60, "M2": 120, "M3": 180, "M4": 240, "M5": 300, "M15": 900,
          "M30": 1800, "H1": 3600, "H4": 14400, "D1": 86400}


def _guess_tf(path, header, path_dir):
    """Temporalidad por nombre de archivo. Devuelve tambien M2/M4 (no soportadas)
    para poder rechazarlas en vez de etiquetarlas mal."""
    import re
    up = os.path.basename(path).upper()
    m = re.findall(r"(?:^|[^A-Z0-9])(M1|M2|M3|M4|M5|M15|M30|H1|H4|D1)(?:[^0-9]|$)", up)
    if not m:
        m = re.findall(r"(M1|M2|M3|M4|M5|M15|M30|H1|H4|D1)(?=CSV|$)", up)
    if m:
        return sorted(m, key=len)[-1]
    return ""


def _known_symbols():
    """Simbolos ya conocidos por el motor -> mapa normalizado."""
    out = {}
    root = "data/weltrade"
    try:
        for name in os.listdir(root):
            if os.path.isdir(os.path.join(root, name)):
                out[_norm(name)] = name
    except OSError:
        pass
    return out


def _norm(s):
    return "".join(c.lower() for c in str(s) if c.isalnum())


def _match_known(text, known):
    hay = _norm(text)
    for norm, real in sorted(known.items(), key=lambda kv: -len(kv[0])):
        if norm and norm in hay:
            return real
    return ""


def _symbol_from(path):
    folder = os.path.dirname(path)
    known = _known_symbols()
    # 1) manifiestos de la carpeta: clave explicita o ruta de origen
    try:
        for name in sorted(os.listdir(folder)):
            if not name.endswith(".json") or not name.startswith("manifest"):
                continue
            raw = open(os.path.join(folder, name), encoding="utf-8").read()
            try:
                d = json.loads(raw)
            except Exception:
                d = {}
            for k in ("simbolo", "symbol", "nombre"):
                if d.get(k):
                    return str(d[k]).strip()
            hit = _match_known(raw, known)
            if hit:
                return hit
    except OSError:
        pass
    # 2) nombre de archivo, carpeta o carpetas superiores
    hit = _match_known(os.path.basename(path), known) or _match_known(folder, known)
    if hit:
        return hit
    # 3) nombre de carpeta util (nunca una temporalidad suelta)
    generic = {"data", "dataset", "datos", "raw", "csv", "exports", "", "ticks"}
    base = os.path.basename(folder)
    if base.lower() not in generic and _norm(base) not in (_norm(t) for t in TF_ANY):
        return base
    parent = os.path.basename(os.path.dirname(folder))
    if parent and parent.lower() not in generic:
        return parent
    stem = os.path.splitext(os.path.basename(path))[0]
    if _norm(stem) in (_norm(t) for t in TF_ANY):
        return "sin_nombre"
    return stem


def _load_any(path, light=False):
    cols = ["timestamp", "time", "fecha", "date", "time_msc"] if light else None
    try:
        df = pd.read_csv(path, compression="gzip" if path.endswith(".gz") else None,
                         usecols=cols)
    except Exception:
        df = pd.read_csv(path, compression="gzip" if path.endswith(".gz") else None)
    low = {c.lower(): c for c in df.columns}
    ren = {}
    for want in ("timestamp", "time", "fecha", "date"):
        if want in low:
            ren[low[want]] = "timestamp"
            break
    if "timestamp" not in ren.values() and "time_msc" in low:
        ren[low["time_msc"]] = "timestamp_ms"
    for c in ("open", "high", "low", "close", "tick_volume", "spread"):
        if c in low:
            ren[low[c]] = c
    df = df.rename(columns=ren)
    if "timestamp" not in df.columns and "timestamp_ms" in df.columns:
        df["timestamp"] = pd.to_datetime(df["timestamp_ms"], unit="ms", utc=True)
    else:
        df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True, errors="coerce")
    for c in COLS:
        if c not in df.columns:
            df[c] = 0
    df = df[COLS].dropna(subset=["timestamp"])
    return df


def _infer_tf(df):
    """Temporalidad por delta real. Devuelve '' si el paso no es exacto."""
    if len(df) < 3:
        return "M1"
    delta = df["timestamp"].diff().dt.total_seconds().dropna()
    delta = delta[delta > 0]
    if not delta.size:
        return "M1"
    sec = float(delta.median())
    for tf, s in sorted(TF_ANY.items(), key=lambda kv: kv[1]):
        if abs(s - sec) <= max(1.0, s * 0.01):
            return tf
    return ""


def _specs_to_info(path_dir, df):
    info = {}
    p = os.path.join(path_dir, "especificaciones.json")
    if os.path.exists(p):
        try:
            raw = json.load(open(p, encoding="utf-8"))
            for k, v in raw.items():
                key = ES_KEYS.get(k, k)
                if key in ("symbol", "description"):
                    continue
                info[key] = v
        except Exception:
            pass
    spread_pts = 0.0
    if "spread" in df.columns and len(df):
        try:
            spread_pts = float(pd.to_numeric(df["spread"], errors="coerce").median() or 0)
        except Exception:
            spread_pts = 0.0
    point = float(info.get("point") or 0.0)
    info.setdefault("spread", spread_pts)
    info["spread"] = spread_pts or info.get("spread", 0)
    info["point_price"] = round(float(info["spread"]) * (point or 0.01), 6) if info["spread"] else 0.0
    info.setdefault("trade_tick_value", 0.01)
    info.setdefault("trade_tick_size", 0.01)
    info.setdefault("volume_min", 0.01)
    info.setdefault("volume_max", 100.0)
    info.setdefault("volume_step", 0.01)
    info.setdefault("trade_contract_size", 1.0)
    info.setdefault("digits", 2)
    info.setdefault("point", 0.01)
    info["fallback"] = False
    return info


def scan(root=".", extra_dirs=None, max_files=400):
    """Busca archivos OHLC fuera del almacen del motor. Solo lectura."""
    found = []
    roots = list(extra_dirs or [])
    for cand in CANDIDATE_DIRS:
        if os.path.isdir(os.path.join(root, cand)):
            roots.append(cand)
    # carpetas de primer y segundo nivel con CSV (excepto el almacen normal)
    try:
        for name in sorted(os.listdir(root)):
            p = os.path.join(root, name)
            if not os.path.isdir(p) or name.startswith("."):
                continue
            if name in ("data", "results", ".git", "__pycache__", "node_modules"):
                continue
            if name not in roots:
                roots.append(name)
    except Exception:
        pass

    seen = set()
    for rel in roots:
        base = os.path.join(root, rel)
        if not os.path.isdir(base):
            continue
        for path in _walk_csv(base, max_depth=4):
            rp = os.path.realpath(path)
            if rp in seen:
                continue
            seen.add(rp)
            rel_path = os.path.relpath(path, root)
            norm = "/" + rel_path.replace(os.sep, "/") + "/"
            if norm.startswith("/data/") or norm.startswith("/results/"):
                continue
            header = _read_header(path)
            if not _has_ohlc(header):
                continue
            tf = _guess_tf(path, header, base)
            item = {"path": rel_path, "symbol": _symbol_from(path),
                    "timeframe": tf, "rows": _count_rows(path),
                    "size_mb": round(os.path.getsize(path) / 1e6, 2)}
            found.append(item)
            if len(found) >= max_files:
                return found
    return found


SKIP_DIRS = {".git", "__pycache__", "node_modules", ".freebuff", ".agents",
             ".wrangler", ".next", "venv", ".venv", "site-packages"}


def _walk_csv(base, max_depth=4):
    base = os.path.abspath(base)
    for dirpath, dirnames, filenames in os.walk(base):
        rel = os.path.relpath(dirpath, base)
        depth = 0 if rel == "." else rel.count(os.sep) + 1
        if depth >= max_depth:
            dirnames[:] = []
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS and not d.startswith(".")]
        for f in sorted(filenames):
            if f.lower().endswith((".csv", ".csv.gz")):
                yield os.path.join(dirpath, f)


def describe(item, root="."):
    """Añade accion prevista y cobertura al item del escaneo."""
    path = os.path.join(root, item["path"])
    try:
        df = _load_any(path, light=True)
    except Exception as exc:
        item["action"] = "error"
        item["error"] = str(exc)[:150]
        return item
    tf = item.get("timeframe") or _infer_tf(df)
    item["timeframe"] = tf
    item["rows"] = len(df)
    item["from"] = str(df["timestamp"].iloc[0]) if len(df) else ""
    item["to"] = str(df["timestamp"].iloc[-1]) if len(df) else ""
    item["fingerprint"] = (item["symbol"], tf, item["rows"], item["from"], item["to"])
    if tf and tf not in TF_SECONDS:
        item["action"] = "omitir: TF %s no soportada (solo %s)" % (tf, ", ".join(TF_LIST))
        return item
    if not tf:
        item["action"] = "omitir: paso de tiempo irregular"
        return item
    try:
        old = _stored_ts(item["symbol"], tf)
        item["existing_rows"] = int(len(old))
        old_ts = set(old.astype("int64").tolist())
        new = df[~df["timestamp"].astype("int64").isin(old_ts)]
        item["new_rows"] = int(len(new))
        item["action"] = "fusionar" if item["new_rows"] else "ya está"
    except FileNotFoundError:
        item["existing_rows"] = 0
        item["new_rows"] = len(df)
        item["action"] = "importar"
    except Exception as exc:
        item["action"] = "error"
        item["error"] = str(exc)[:150]
    return item


def import_item(item, root="."):
    """Fusiona el archivo detectado en el almacen del motor."""
    path = os.path.join(root, item["path"])
    df = _load_any(path)
    tf = item.get("timeframe") or _infer_tf(df)
    symbol = item["symbol"]
    try:
        old = load_bars(symbol, tf)
        merged = pd.concat([old, df], ignore_index=True)
        before = len(old)
    except FileNotFoundError:
        merged = df
        before = 0
    merged = (merged.sort_values("timestamp")
                    .drop_duplicates(subset=["timestamp"], keep="last")
                    .reset_index(drop=True))
    info = _specs_to_info(os.path.dirname(path), merged)
    saved = save_bars(merged, symbol, tf, "data/weltrade")
    ipath = os.path.join("data/weltrade", _safe(symbol), "info.json")
    if not os.path.exists(ipath):
        os.makedirs(os.path.dirname(ipath), exist_ok=True)
        with open(ipath, "w", encoding="utf-8") as f:
            json.dump(info, f, indent=2, default=str)
    return {"symbol": symbol, "timeframe": tf, "before": before,
            "after": len(merged), "added": len(merged) - before,
            "csv": saved["csv"], "hash": saved.get("data_hash")}


def _stored_ts(symbol, tf):
    """Fechas ya guardadas para un simbolo/TF (lectura de una sola columna)."""
    from .data_manager import _safe_sym
    p = os.path.join("data/weltrade", _safe_sym(symbol), f"{tf}.csv.gz")
    if not os.path.exists(p):
        raise FileNotFoundError(p)
    ts = pd.read_csv(p, compression="gzip", usecols=["timestamp"])["timestamp"]
    return pd.to_datetime(ts, utc=True, errors="coerce")


def _safe(sym):
    return "".join(c if (c.isalnum() or c in ("-", "_", " ")) else "_" for c in sym).strip()


def plan(root=".", extra_dirs=None):
    """Escaneo + diagnostico + deduplicado por cobertura identica."""
    items = [describe(i, root) for i in scan(root, extra_dirs=extra_dirs)]
    seen = {}
    for it in items:
        if str(it.get("action", "")).startswith("omitir"):
            continue
        fp = it.get("fingerprint")
        if fp and fp in seen:
            it["action"] = "duplicado de " + seen[fp]
            continue
        if fp:
            seen[fp] = it["path"]
    return items


def import_all(root=".", dry_run=True):
    items = plan(root)
    out = {"dry_run": dry_run, "items": items, "imported": []}
    if dry_run:
        return out
    for it in items:
        if it.get("action") in ("importar", "fusionar"):
            try:
                out["imported"].append(import_item(it, root))
            except Exception as exc:
                it["action"] = "error"
                it["error"] = str(exc)[:200]
    if out["imported"]:
        cache = os.path.join("results", "inventory_cache.json")
        if os.path.exists(cache):
            try:
                os.remove(cache)
            except OSError:
                pass
    return out
