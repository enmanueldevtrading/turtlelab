"""Registro modular de estrategias.

Una estrategia nueva NO requiere tocar el motor ni el panel:

  - built-ins:        bt/plugins/*.py   (se cargan solos)
  - del usuario:      user_strategies/*.py (se cargan solos, hot-reload)

Cada plugin declara su clase con `@strategy(...)` (ver bt/sdk.py) y el panel
la descubre por /api/strategies. `get_strategy(clave)` sigue devolviendo
(instancia, parametros) como siempre.
"""
import importlib
import importlib.util
import os
import sys
import traceback

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
USER_DIR = os.path.join(ROOT, "user_strategies")
BUILTIN_PKG = "bt.plugins"

ALL_TFS = ["M1", "M3", "M5", "M15", "M30", "H1", "H4", "D1"]

# Registro plano: clave -> clase (claves de preset y de clase conviven aqui,
# igual que el antiguo dict STRATEGIES).
STRATEGIES = {}
ALIASES = {}
STRATEGY_META = {}
CLASSES = {}
PLUGINS = []
_LOADED = False
_LOADING = False


def register_class(cls):
    """Registra una clase de estrategia bajo su atributo `name`."""
    key = getattr(cls, "name", "") or ""
    if not key:
        raise ValueError("La estrategia no declara `name`")
    CLASSES[key] = cls
    STRATEGIES.setdefault(key, cls)
    return cls


def resolve_class(cls_or_key):
    if isinstance(cls_or_key, str):
        if cls_or_key in CLASSES:
            return CLASSES[cls_or_key]
        if cls_or_key in STRATEGIES:
            return STRATEGIES[cls_or_key]
        raise ValueError(f"Estrategia desconocida: {cls_or_key}")
    if getattr(cls_or_key, "name", None):
        CLASSES.setdefault(cls_or_key.name, cls_or_key)
        return cls_or_key
    raise ValueError("Clase de estrategia sin `name`")


def add_preset(cls, id, params=None, label=None, desc="", rules=(),
               tfs=None, balance=50.0, riesgo="", order=100, hidden=False):
    """Publica un preset (clase + parametros) con nombre propio en el panel."""
    klass = resolve_class(cls)
    key = id
    STRATEGIES[key] = klass
    if params:
        ALIASES[key] = dict(params)
    if hidden:
        return key
    STRATEGY_META[key] = {
        "label": label or key,
        "desc": desc,
        "rules": list(rules),
        "variants": [(key, dict(params or {}))],
        "balance": float(balance),
        "riesgo": riesgo,
        "tfs": list(tfs or ALL_TFS),
        "order": order,
        "class": klass.name,
        "plugin": _current_plugin(),
    }
    return key


_CURRENT_PLUGIN = {"file": ""}


def _current_plugin():
    return _CURRENT_PLUGIN["file"]


def load_builtins():
    here = os.path.join(ROOT, "bt", "plugins")
    if not os.path.isdir(here):
        return
    for f in sorted(os.listdir(here)):
        if f.endswith(".py") and not f.startswith("_"):
            _import_module(f"{BUILTIN_PKG}.{f[:-3]}", f)


def load_user_plugins():
    os.makedirs(USER_DIR, exist_ok=True)
    for f in sorted(os.listdir(USER_DIR)):
        if not f.endswith(".py") or f.startswith("_"):
            continue
        path = os.path.join(USER_DIR, f)
        _import_module(f"user_strategies_{f[:-3]}", f, path=path)


def _import_module(name, filename, path=None):
    """Importa (o reimporta) un plugin registrando sus errores sin romper."""
    before = len(STRATEGY_META)
    _CURRENT_PLUGIN["file"] = filename
    entry = {"file": filename, "ok": True, "error": "", "presets": 0}
    try:
        if path:
            spec = importlib.util.spec_from_file_location(name, path)
            mod = importlib.util.module_from_spec(spec)
            sys.modules[name] = mod
            spec.loader.exec_module(mod)
        else:
            if name in sys.modules:
                importlib.reload(sys.modules[name])
            else:
                importlib.import_module(name)
        entry["presets"] = len(STRATEGY_META) - before
    except Exception as exc:
        entry["ok"] = False
        entry["error"] = f"{type(exc).__name__}: {exc}"
        traceback.print_exc()
    finally:
        _CURRENT_PLUGIN["file"] = ""
    PLUGINS.append(entry)


def ensure_loaded(force=False):
    global _LOADED, _LOADING
    if _LOADING:
        return
    if _LOADED and not force:
        return
    _LOADING = True
    try:
        if force:
            STRATEGIES.clear()
            ALIASES.clear()
            STRATEGY_META.clear()
            CLASSES.clear()
            PLUGINS.clear()
        load_builtins()
        load_user_plugins()
        _LOADED = True
    finally:
        _LOADING = False


def reload_plugins():
    ensure_loaded(force=True)
    return plugin_report()


def plugin_report():
    return {
        "user_dir": "user_strategies/",
        "plugins": list(PLUGINS),
        "errors": [p for p in PLUGINS if not p["ok"]],
        "count": len(STRATEGY_META),
    }


def get_strategy(key):
    """Devuelve (instancia, parametros con defaults + preset)."""
    ensure_loaded()
    if key not in STRATEGIES:
        raise ValueError(
            f"Estrategia desconocida: {key}. Disponibles: {sorted(STRATEGIES)}")
    strat = STRATEGIES[key]()
    base = dict(strat.defaults)
    base.update(ALIASES.get(key, {}))
    return strat, base
