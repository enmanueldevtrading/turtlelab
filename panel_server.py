"""TurtleLab — panel web local (stdlib, sin dependencias externas).

Sirve la UI desde web/ y expone la API para lanzar trabajos, ver resultados
y recargar estrategias en caliente (user_strategies/*.py).
"""
PORT = 8080
TURTLE_JOBS = {}

import json
import mimetypes
import os
import socketserver
import threading
import time
import traceback
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qs, urlparse

ROOT = os.path.dirname(os.path.abspath(__file__))
WEB = os.path.join(ROOT, "web")
TF_ORDER = ["M1", "M3", "M5", "M15", "M30", "H1", "H4", "D1"]


def quick_counts(root="data/weltrade"):
    files, syms = 0, set()
    try:
        for sym in os.listdir(root):
            d = os.path.join(root, sym)
            if not os.path.isdir(d):
                continue
            syms.add(sym)
            for f in os.listdir(d):
                if f.endswith(".csv.gz"):
                    files += 1
    except Exception:
        pass
    return files, syms


def find_live_panel(ports=(8080, 8081, 8082, 8090)):
    import urllib.request
    for cand in ports:
        try:
            with urllib.request.urlopen(f"http://127.0.0.1:{cand}/api/status", timeout=2) as r:
                data = json.loads(r.read().decode())
                if isinstance(data, dict) and "files" in data and "results" in data:
                    return cand
        except Exception:
            continue
    return None


def low_priority():
    try:
        import ctypes
        BELOW_NORMAL = 0x00004000
        ctypes.windll.kernel32.SetPriorityClass(
            ctypes.windll.kernel32.GetCurrentProcess(), BELOW_NORMAL)
    except Exception:
        pass


_RESULTS_CACHE = {"data": None, "expires": 0}
_SCAN_CACHE = {"data": None, "t": 0}
_RESULTS_INDEX_FILE = os.path.join("results", "_index.json")


def _guess_src(symbol, tf):
    for root in ("data/weltrade", "data/yahoo"):
        if os.path.exists(os.path.join(root, symbol or "", (tf or "") + ".csv.gz")):
            return "yahoo" if "yahoo" in root else "weltrade"
    return "weltrade"


def _rebuild_results_index():
    """Reconstruye el indice de resultados desde disco (lento, solo si es necesario)."""
    out = []
    root = "results"
    if not os.path.isdir(root):
        return out
    for d in sorted(os.listdir(root)):
        p = os.path.join(root, d)
        if not (d.startswith("BT-") and os.path.isdir(p)):
            continue
        try:
            cfg = json.load(open(os.path.join(p, "config.json"), encoding="utf-8"))
            met = json.load(open(os.path.join(p, "metrics.json"), encoding="utf-8"))
            fund = {}
            fp = os.path.join(p, "funding.json")
            if os.path.exists(fp):
                try:
                    fund = json.load(open(fp, encoding="utf-8"))
                except Exception:
                    fund = {}
            out.append({"bt_id": d, "src": _guess_src(cfg.get("symbol"), cfg.get("timeframe")),
                        "fund_status": fund.get("status", ""),
                        "fund_dd": fund.get("max_dd"),
                        "fund_daily": fund.get("max_daily_dd"),
                        "fund_net_pct": fund.get("net_pct"),
                        "fund_target": fund.get("target_hit", False),
                        "fund_account": fund.get("account"),
                        "strategy": cfg.get("strategy"),
                        "symbol": cfg.get("symbol"), "timeframe": cfg.get("timeframe"),
                        "net": met.get("net_profit"), "pf": met.get("profit_factor"),
                        "dd": met.get("max_drawdown_pct"), "dd_cap": met.get("max_drawdown"),
                        "trades": met.get("total"), "wr": met.get("win_rate"),
                        "capital": met.get("capital"), "from": cfg.get("from"),
                        "to": cfg.get("to"),
                        "mws": met.get("max_win_streak"), "mws_amt": met.get("max_win_streak_amt"),
                        "mls": met.get("max_loss_streak"), "mls_amt": met.get("max_loss_streak_amt")})
        except Exception:
            continue
    try:
        os.makedirs(os.path.dirname(_RESULTS_INDEX_FILE), exist_ok=True)
        tmp = _RESULTS_INDEX_FILE + ".tmp"
        json.dump(out, open(tmp, "w", encoding="utf-8"), default=str)
        os.replace(tmp, _RESULTS_INDEX_FILE)
    except Exception:
        pass
    return out


def list_results(force=False):
    now = time.time()
    try:
        dir_mtime = os.path.getmtime("results")
    except OSError:
        dir_mtime = 0.0
    # Si aparece o desaparece una carpeta BT-*, la caché caduca al instante.
    if (not force and _RESULTS_CACHE["data"] is not None
            and now < _RESULTS_CACHE["expires"]
            and _RESULTS_CACHE.get("mtime") == dir_mtime):
        return _RESULTS_CACHE["data"]
    _RESULTS_CACHE["mtime"] = dir_mtime
    if not force and os.path.exists(_RESULTS_INDEX_FILE):
        try:
            if (os.path.getmtime(_RESULTS_INDEX_FILE) >= os.path.getmtime("results")
                    or not os.path.isdir("results")):
                data = json.load(open(_RESULTS_INDEX_FILE, encoding="utf-8"))
                _RESULTS_CACHE["data"] = data
                _RESULTS_CACHE["expires"] = now + 300
                return data
        except Exception:
            pass
    data = _rebuild_results_index()
    _RESULTS_CACHE["data"] = data
    _RESULTS_CACHE["expires"] = now + 300
    return data


def run_turtle_job(job_id, symbols, tfs, balance=0, mode="turtle", root="data/weltrade"):
    from bt.data_manager import load_bars, symbol_info, contract_size
    from bt.execution import ExecConfig
    from bt.backtest import run_backtest
    from bt.reports import save_report
    from bt.strategies import STRATEGY_META
    import hashlib
    import gc
    import pandas as pd

    job = TURTLE_JOBS[job_id]
    meta = STRATEGY_META.get(mode)
    if meta is None:
        job["status"] = "error: estrategia desconocida " + str(mode)
        return
    variants = meta["variants"]
    if not balance:
        balance = meta["balance"]
    allowed = meta.get("tfs") or tfs
    tfs = [t for t in tfs if t in allowed] or list(allowed)
    jobs_list = [(s, tf, vk, vp) for s in symbols for tf in tfs for vk, vp in variants]
    srcname = "yahoo" if str(root).endswith("yahoo") else "weltrade"
    job["total"] = len(jobs_list)
    try:
        for s, tf, vk, vp in jobs_list:
            if job.get("status") == "cancelado":
                break
            job["current"] = "%s %s" % (s, tf)
            try:
                df = load_bars(s, tf, root)
            except Exception as e:
                job["results"].append({"symbol": s, "tf": tf, "strategy": vk,
                                       "src": srcname, "error": str(e)[:100]})
                job["done"] += 1
                continue
            try:
                dh = hashlib.sha256(
                    pd.util.hash_pandas_object(df, index=False).values.tobytes()).hexdigest()[:16]
                info = symbol_info(s, root)
                _spr = info.get("point_price", 0.0) or 0.0
                cfg = ExecConfig(initial_balance=balance, risk_pct=1.0,
                                 min_lot=info.get("volume_min", 0.01) or 0.01,
                                 max_lot=info.get("volume_max", 100.0) or 100.0,
                                 lot_step=info.get("volume_step", 0.01) or 0.01,
                                 contract_size=contract_size(info),
                                 spread=_spr, slippage=_spr / 2.0)
                r = run_backtest(df, vk, vp, cfg, s, tf, dh, save=True)
                if r.get("empty"):
                    job["results"].append({"symbol": s, "tf": tf, "strategy": vk,
                                           "src": srcname, "note": "sin operaciones"})
                else:
                    save_report(r, os.path.join("results", r["bt_id"]))
                    m = r["metrics"]
                    fd = r.get("funding") or {}
                    job["results"].append({"symbol": s, "tf": tf, "strategy": vk,
                                           "src": srcname, "bt_id": r["bt_id"],
                                           "net": m["net_profit"], "pf": m["profit_factor"],
                                           "dd": m["max_drawdown_pct"], "trades": m["total"],
                                           "fund_status": fd.get("status", ""),
                                           "fund_dd": fd.get("max_dd"),
                                           "fund_daily": fd.get("max_daily_dd")})
            except Exception as e:
                job["results"].append({"symbol": s, "tf": tf, "strategy": vk,
                                       "src": srcname, "error": str(e)[:150]})
            finally:
                df = None
                gc.collect()
            job["done"] += 1
            # Respiro explicito: un backtest a la vez y CPU/RAM libres para el panel.
            if job["done"] % 5 == 0:
                time.sleep(0.05)
            if len(job["results"]) > 300:
                job["results"] = job["results"][-300:]
    except Exception as e:
        job["status"] = "error: " + str(e)[:200]
        traceback.print_exc()
        return
    job["status"] = "terminado"
    try:
        _RESULTS_CACHE["data"] = None
        _RESULTS_CACHE["expires"] = 0
        if os.path.exists(_RESULTS_INDEX_FILE):
            os.remove(_RESULTS_INDEX_FILE)
    except Exception:
        pass


def inventory(root="data/weltrade"):
    from bt.data_manager import inventory as inv
    try:
        return inv(root=root)
    except Exception:
        return []


def strat_meta():
    from bt.strategies import STRATEGY_META, ensure_loaded
    ensure_loaded()
    return STRATEGY_META


def strategies_payload():
    """Presets ordenados + parametros resueltos, listos para el panel."""
    from bt.strategies import get_strategy
    out = {}
    for mode, m in strat_meta().items():
        try:
            _s, defaults = get_strategy(m["variants"][0][0])
            params = {**defaults, **m["variants"][0][1]}
        except Exception:
            params = {}
        out[mode] = {**m, "params": params}
    return out


def _plugins_payload():
    from bt.strategies import plugin_report
    return plugin_report()


class H(BaseHTTPRequestHandler):
    server_version = "TurtleLab"

    def log_message(self, *a):
        pass

    def _json(self, obj, code=200):
        b = json.dumps(obj, default=str).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(b)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(b)

    def _body_json(self):
        try:
            n = int(self.headers.get("Content-Length", 0)) or 0
            raw = self.rfile.read(n) if n else b"{}"
            return json.loads(raw.decode("utf-8") or "{}")
        except Exception:
            return {}

    def _file(self, path, ctype=None):
        try:
            with open(path, "rb") as f:
                b = f.read()
        except OSError:
            self.send_response(404)
            self.end_headers()
            return
        ctype = ctype or mimetypes.guess_type(path)[0] or "application/octet-stream"
        if ctype.startswith("text/") or ctype.endswith("javascript") or ctype.endswith("json"):
            ctype += "; charset=utf-8"
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(b)))
        self.send_header("Cache-Control", "no-store, no-cache, must-revalidate")
        self.end_headers()
        self.wfile.write(b)

    def _static(self, rel):
        path = os.path.normpath(os.path.join(WEB, rel))
        if not path.startswith(WEB) or not os.path.isfile(path):
            self.send_response(404)
            self.end_headers()
            return
        self._file(path)

    def do_GET(self):
        u = urlparse(self.path)
        path = u.path
        q = parse_qs(u.query)
        if path in ("/", "/index.html"):
            self._file(os.path.join(WEB, "index.html"))
        elif path.startswith("/web/"):
            self._static(path[len("/web/"):])
        elif path == "/api/status":
            files, syms = quick_counts()
            yfiles, ysyms = quick_counts(root="data/yahoo")
            self._json({"files": files, "symbols": len(syms),
                        "results": list_results(),
                        "ready": bool(files or yfiles),
                        "workers": 1,
                        "jobs_running": sum(1 for j in TURTLE_JOBS.values()
                                            if j.get("status") == "corriendo"),
                        "sources": {"weltrade": {"files": files, "symbols": len(syms)},
                                    "yahoo": {"files": yfiles, "symbols": len(ysyms)}}})
        elif path == "/api/inventory":
            _src = (q.get("src", ["weltrade"])[0] or "weltrade")
            _root = "data/yahoo" if _src == "yahoo" else "data/weltrade"
            self._json({"inventory": inventory(root=_root), "src": _src})
        elif path == "/api/costs":
            _src = (q.get("src", ["weltrade"])[0] or "weltrade")
            _root = "data/yahoo" if _src == "yahoo" else "data/weltrade"
            from bt.data_manager import symbol_info
            out = {}
            try:
                for name in sorted(os.listdir(_root)):
                    if name in (".gitkeep",) or not os.path.isdir(os.path.join(_root, name)):
                        continue
                    i = symbol_info(name, _root)
                    out[name] = {
                        "spread_pt": i.get("spread") or 0,
                        "point": i.get("point") or 0.0,
                        "spread_price": i.get("point_price") or 0.0,
                        "swap_long": i.get("swap_long"),
                        "swap_short": i.get("swap_short"),
                        "currency": i.get("currency_profit") or "",
                        "min_lot": i.get("volume_min"),
                        "contract": i.get("trade_contract_size"),
                        "fallback": bool(i.get("fallback")),
                    }
            except Exception:
                pass
            self._json({"src": _src, "costs": out})
        elif path == "/api/strategies":
            self._json(strategies_payload())
        elif path == "/api/plugins":
            self._json(_plugins_payload())
        elif path == "/api/mt5/status":
            from bt.mt5_import import availability, active
            self._json({**availability(), **active()})
        elif path == "/api/mt5/symbols":
            from bt.mt5_import import symbols as mt5_symbols
            self._json(mt5_symbols())
        elif path.startswith("/api/mt5/job/"):
            from bt.mt5_import import status as mt5_status
            self._json(mt5_status(path.split("/")[-1]))
        elif path.startswith("/api/job/"):
            jid = path.split("/")[-1]
            j = TURTLE_JOBS.get(jid, {"status": "no existe"})
            self._json({"job_id": jid, "status": j["status"], "done": j.get("done", 0),
                        "total": j.get("total", 0), "results": j.get("results", [])[-20:],
                        "mode": j.get("mode"), "tfs": j.get("tfs"),
                        "balance": j.get("balance"), "started": j.get("started"),
                        "current": j.get("current", ""), "src": j.get("src", "weltrade")})
        elif path == "/api/active":
            running = None
            for _jid, _j in TURTLE_JOBS.items():
                if _j.get("status") == "corriendo":
                    running = {"job_id": _jid, "done": _j.get("done", 0),
                               "total": _j.get("total", 0), "mode": _j.get("mode"),
                               "tfs": _j.get("tfs"), "balance": _j.get("balance"),
                               "started": _j.get("started"),
                               "src": _j.get("src", "weltrade")}
            self._json({"running": running})
        elif path.startswith("/api/backtest/"):
            bt = path.split("/")[-1]
            try:
                import pandas as pd
                base = os.path.join("results", bt)
                cfg = json.load(open(os.path.join(base, "config.json"), encoding="utf-8"))
                met = json.load(open(os.path.join(base, "metrics.json"), encoding="utf-8"))
                tr = pd.read_csv(os.path.join(base, "trades.csv")).head(500).to_dict("records")
                fund = {}
                fp = os.path.join(base, "funding.json")
                if os.path.exists(fp):
                    try:
                        fund = json.load(open(fp, encoding="utf-8"))
                    except Exception:
                        fund = {}
                eq = pd.read_csv(os.path.join(base, "equity.csv"))["equity"].to_numpy(float)
                if len(eq) > 600:
                    eq = eq[:: max(1, len(eq) // 600)]
                self._json({"bt_id": bt, "config": cfg, "metrics": met, "trades": tr,
                            "funding": fund,
                            "equity": [round(float(x), 2) for x in eq]})
            except Exception as e:
                self._json({"error": str(e)[:150]}, 404)
        elif path.startswith("/api/equity/") and path.endswith(".svg"):
            bt = path.split("/")[-1][:-4]
            svg = equity_svg(bt)
            if not svg:
                self.send_response(404)
                self.end_headers()
                return
            b = svg.encode()
            self.send_response(200)
            self.send_header("Content-Type", "image/svg+xml; charset=utf-8")
            self.send_header("Content-Length", str(len(b)))
            self.end_headers()
            self.wfile.write(b)
        elif path == "/guia-estrategias.txt":
            self._file(os.path.join(ROOT, "GUIA_ESTRATEGIAS.txt"), "text/plain; charset=utf-8")
        elif path == "/api/import-scan":
            from bt.importer import plan
            try:
                import time as _t
                now = _t.time()
                if _SCAN_CACHE["data"] is not None and now < _SCAN_CACHE["t"] + 120:
                    self._json(_SCAN_CACHE["data"])
                    return
                items = plan(ROOT)
            except Exception as exc:
                items = []
                traceback.print_exc()
                self._json({"error": str(exc)[:200]}, 500)
                return
            pending = [i for i in items
                       if str(i.get("action", "")).startswith(("importar", "fusionar"))]
            payload = {"items": items, "pending": len(pending),
                       "total_new_rows": sum(int(i.get("new_rows", 0) or 0) for i in pending)}
            _SCAN_CACHE["data"] = payload
            _SCAN_CACHE["t"] = now
            self._json(payload)
        elif path.startswith("/results/"):
            p = os.path.normpath(path.lstrip("/"))
            if ".." in p or not os.path.exists(p):
                self.send_response(404)
                self.end_headers()
                return
            self._file(p)
        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        u = urlparse(self.path)
        q = parse_qs(u.query)
        if u.path == "/api/run-turtle":
            src = (q.get("src", ["weltrade"])[0] or "weltrade").lower()
            root = "data/yahoo" if src == "yahoo" else "data/weltrade"
            mode = (q.get("mode", [""])[0] or "").lower()
            meta = strat_meta()
            if mode not in meta:
                self._json({"error": "estrategia desconocida: " + mode}, 404)
                return
            from bt.data_manager import inventory as inv
            _inv = inv(root=root)
            if not _inv:
                self._json({"error": "no hay datos en " + root +
                                     ". Descarga con download_data o restaura un data pack."}, 409)
                return
            available = sorted(set(i["timeframe"] for i in _inv),
                               key=lambda t: TF_ORDER.index(t) if t in TF_ORDER else 99)
            asked = q.get("tfs", [""])[0]
            if asked:
                tfs = [t.strip().upper() for t in asked.split(",")
                       if t.strip().upper() in available]
            else:
                tf = (q.get("tf", ["ALL"])[0] or "ALL").upper()
                tfs = available if tf == "ALL" else [t for t in [tf] if t in available]
            if not tfs:
                self._json({"error": "ninguna temporalidad pedida existe en los datos"}, 409)
                return
            syms = sorted(set(i["symbol"] for i in _inv))
            wanted = q.get("symbols", [""])[0]
            if wanted:
                keep = {s.strip() for s in wanted.split(",") if s.strip()}
                syms = [s for s in syms if s in keep]
            try:
                limit = int(q.get("limit", ["0"])[0] or 0)
            except Exception:
                limit = 0
            if limit > 0:
                syms = syms[:limit]
            try:
                bal = float(q.get("balance", [0])[0] or 0)
            except Exception:
                bal = 0
            for _jid, _j in TURTLE_JOBS.items():
                if _j.get("status") == "corriendo":
                    self._json({"error": "Ya hay un trabajo corriendo (" + _jid +
                                         "). Espera o cancelalo."}, 409)
                    return
            jid = "job-%d-%d" % (int(time.time()), len(TURTLE_JOBS))
            TURTLE_JOBS[jid] = {"status": "corriendo", "done": 0, "total": 0, "results": [],
                                "mode": mode, "tfs": tfs, "balance": bal, "src": src,
                                "symbols": len(syms), "started": int(time.time()),
                                "current": ""}
            threading.Thread(target=run_turtle_job,
                             args=(jid, syms, tfs, bal, mode, root), daemon=True).start()
            self._json({"job_id": jid, "total": len(syms) * len(tfs)})
        elif u.path == "/api/import-run":
            from bt.importer import import_all
            busy = [k for k, j in TURTLE_JOBS.items() if j.get("status") == "corriendo"]
            if busy:
                self._json({"error": "Hay un trabajo corriendo. Espera a que termine."}, 409)
                return
            try:
                rep = import_all(ROOT, dry_run=False)
            except Exception as exc:
                traceback.print_exc()
                self._json({"error": str(exc)[:200]}, 500)
                return
            _SCAN_CACHE["data"] = None
            _SCAN_CACHE["t"] = 0
            self._json(rep)
        elif u.path == "/api/mt5/import":
            from bt.mt5_import import start as mt5_start
            try:
                body = self._body_json()
            except Exception:
                body = {}
            if any(j.get("status") == "corriendo" for j in TURTLE_JOBS.values()):
                self._json({"error": "Hay un backtest corriendo. Espera a que termine."}, 409)
                return
            mode = (body.get("mode") or "bars").lower()
            if mode not in ("bars", "ticks", "book"):
                self._json({"error": "Modo no válido (bars, ticks o book)."}, 400)
                return
            try:
                bars = max(1000, min(int(body.get("bars") or 50000), 500000))
            except Exception:
                bars = 50000
            try:
                tick_days = max(1, min(int(body.get("tick_days") or 3), 31))
            except Exception:
                tick_days = 3
            res = mt5_start(body.get("symbols") or [], body.get("tfs") or [],
                            bars=bars, mode=mode, tick_days=tick_days)
            self._json(res, 409 if res.get("error") else 200)
        elif u.path == "/api/mt5/cancel":
            from bt.mt5_import import cancel as mt5_cancel
            try:
                body = self._body_json()
            except Exception:
                body = {}
            self._json(mt5_cancel(body.get("job") or ""))
        elif u.path == "/api/reload-plugins":
            from bt.strategies import reload_plugins
            self._json(reload_plugins())
        elif u.path == "/api/results/delete":
            busy = [k for k, j in TURTLE_JOBS.items() if j.get("status") == "corriendo"]
            if busy:
                self._json({"error": "Hay un trabajo corriendo. Cancelalo primero."}, 409)
                return
            import shutil
            n = 0
            for d in os.listdir("results"):
                p = os.path.join("results", d)
                if d.startswith("BT-") and os.path.isdir(p):
                    shutil.rmtree(p, ignore_errors=True)
                    n += 1
            try:
                open(os.path.join("results", "_counter.txt"), "w").write("0")
            except Exception:
                pass
            _RESULTS_CACHE["data"] = None
            _RESULTS_CACHE["expires"] = 0
            self._json({"deleted": n})
        elif u.path == "/api/rerun":
            from bt.execution import ExecConfig
            from bt.backtest import run_backtest
            from bt.reports import save_report
            from bt.data_manager import load_bars
            import hashlib
            import pandas as pd
            src = (q.get("bt", [""])[0] or "")
            try:
                cfg = json.load(open(os.path.join("results", src, "config.json"), encoding="utf-8"))
                df = load_bars(cfg["symbol"], cfg["timeframe"])
                e = cfg.get("exec", {})
                exc = ExecConfig(initial_balance=e.get("initial_balance", 50.0),
                                 lot=e.get("lot", 0.0), risk_pct=e.get("risk_pct", 1.0),
                                 min_lot=e.get("min_lot", 0.01), max_lot=e.get("max_lot", 100.0),
                                 lot_step=e.get("lot_step", 0.01),
                                 contract_size=e.get("contract_size", 1.0),
                                 spread=e.get("spread", 0.0), commission=e.get("commission", 0.0),
                                 slippage=e.get("slippage", 0.0),
                                 max_positions=e.get("max_positions", 1),
                                 allow_long=e.get("allow_long", True),
                                 allow_short=e.get("allow_short", True),
                                 entry_mode=e.get("entry_mode", "close"))
                dh = hashlib.sha256(
                    pd.util.hash_pandas_object(df, index=False).values.tobytes()).hexdigest()[:16]
                r = run_backtest(df, cfg["strategy"], cfg.get("params", {}), exc,
                                 cfg["symbol"], cfg["timeframe"], dh, save=True)
                if r.get("empty"):
                    self._json({"empty": True, "src": src})
                else:
                    save_report(r, os.path.join("results", r["bt_id"]))
                    _RESULTS_CACHE["data"] = None
                    _RESULTS_CACHE["expires"] = 0
                    self._json({"bt_id": r["bt_id"], "src": src,
                                "net": r["metrics"]["net_profit"]})
            except Exception as ex:
                self._json({"error": str(ex)[:200]}, 404)
        elif u.path.startswith("/api/job/") and u.path.endswith("/cancel"):
            jid = u.path.split("/")[-2]
            j = TURTLE_JOBS.get(jid)
            if j and j.get("status") == "corriendo":
                j["status"] = "cancelado"
                self._json({"job_id": jid, "status": "cancelado"})
            else:
                self._json({"error": "no hay trabajo corriendo con ese ID"}, 404)
        elif u.path == "/api/montecarlo":
            import pandas as pd
            from bt.montecarlo import run_montecarlo
            try:
                body = json.loads(self.rfile.read(
                    int(self.headers.get("Content-Length", 0)) or 0) or b"{}")
            except Exception:
                body = {}
            bt = body.get("bt_id", "")
            sims = min(int(body.get("sims", 500)), 5000)
            seed = int(body.get("seed", 12345))
            try:
                trades = pd.read_csv(os.path.join("results", bt, "trades.csv")).to_dict("records")
                met = json.load(open(os.path.join("results", bt, "metrics.json"), encoding="utf-8"))
                mc = run_montecarlo(
                    [{"pnl": float(t.get("pnl", 0)), "direction": t.get("direction", "LONG")}
                     for t in trades],
                    float(met.get("capital", 50.0)), sims, seed)
                mc_id = f"{bt}-MC{seed}-{sims}"
                with open(os.path.join("results", bt, f"montecarlo_{sims}_{seed}.json"), "w") as f:
                    json.dump({"mc_id": mc_id, "bt_id": bt, **mc}, f, indent=2, default=str)
                self._json({"mc_id": mc_id, "bt_id": bt, **mc})
            except Exception as e:
                self._json({"error": str(e)[:200]}, 404)
        else:
            self.send_response(404)
            self.end_headers()


def equity_svg(bt):
    """Curva de capital como SVG (sin dependencias)."""
    try:
        import pandas as pd
        eq = pd.read_csv(os.path.join("results", bt, "equity.csv"))["equity"].to_numpy(float)
    except Exception:
        return None
    if not len(eq):
        return None
    W, H, PAD = 860, 260, 24
    lo, hi = float(eq.min()), float(eq.max())
    if hi == lo:
        hi = lo + 1.0
    n = len(eq)
    step = max(1, n // 900)
    xs = list(range(0, n, step))
    pts = []
    for i in xs:
        x = PAD + (W - 2 * PAD) * (i / max(1, n - 1))
        y = H - PAD - (H - 2 * PAD) * ((eq[i] - lo) / (hi - lo))
        pts.append("%.1f,%.1f" % (x, y))
    color = "#30d158" if eq[-1] >= eq[0] else "#ff453a"
    base_y = H - PAD - (H - 2 * PAD) * ((eq[0] - lo) / (hi - lo))
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 %d %d" width="%d" height="%d">'
        '<rect width="100%%" height="100%%" fill="#0f1424"/>'
        '<line x1="%d" y1="%.1f" x2="%d" y2="%.1f" stroke="#39456b" stroke-dasharray="4 4"/>'
        '<polyline fill="none" stroke="%s" stroke-width="1.8" points="%s"/>'
        '<text x="%d" y="16" fill="#8b9bb5" font-size="11" font-family="sans-serif">'
        'equity %s → %s</text></svg>'
        % (W, H, W, H, PAD, base_y, W - PAD, base_y, color, " ".join(pts),
           PAD, round(float(eq[0]), 2), round(float(eq[-1]), 2)))


if __name__ == "__main__":
    os.chdir(ROOT)
    print("[TurtleLab] arrancando...")
    port = PORT
    srv = None
    for cand in (PORT, 8081, 8082, 8090):
        try:
            srv = socketserver.ThreadingTCPServer(("127.0.0.1", cand), H,
                                                  bind_and_activate=False)
            srv.allow_reuse_address = True
            srv.daemon_threads = True
            srv.server_bind()
            srv.server_activate()
            port = cand
            break
        except OSError:
            continue
    if srv is None:
        live = find_live_panel()
        if live:
            print(f"Puertos ocupados. Panel vivo en {live}.")
            raise SystemExit(0)
        print("ERROR: no se pudo abrir ningun puerto.")
        raise SystemExit(1)
    try:
        open("panel.pid", "w").write(str(os.getpid()))
    except Exception:
        pass
    low_priority()
    print(f"TurtleLab en http://localhost:{port}")
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        print("\n[TurtleLab] detenido.")
