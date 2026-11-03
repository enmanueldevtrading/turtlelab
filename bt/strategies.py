"""Registro de estrategias (compatibilidad).

El registro real vive en bt/registry.py y las estrategias en bt/plugins/.
Este modulo mantiene la API historica: STRATEGIES, ALIASES, STRATEGY_META,
get_strategy() y las clases de siempre.
"""
from .registry import (ALL_TFS, ALIASES, CLASSES, PLUGINS, STRATEGIES,
                       STRATEGY_META, ensure_loaded, get_strategy,
                       plugin_report, reload_plugins)
from .sdk import BaseStrategy, add_preset, cross_down, cross_up, strategy

ensure_loaded()

__all__ = ["STRATEGIES", "ALIASES", "STRATEGY_META", "CLASSES", "PLUGINS",
           "BaseStrategy", "add_preset", "strategy", "get_strategy",
           "ensure_loaded", "reload_plugins", "plugin_report",
           "cross_up", "cross_down", "ALL_TFS"]


def _cls(name):
    return CLASSES.get(name)


# Nombres historicos de clase (tests y scripts antiguos los importan).
def __getattr__(attr):
    alias = {
        "EmaCross": "ema_cross",
        "Ema30_72_150": "ema30_72_150",
        "Turtle": "turtle",
        "VwapSession": "vwap_session",
        "VwapM15": "vwap_m15",
        "VwapRR": "vwap_rr12",
    }
    if attr in alias:
        cls = _cls(alias[attr])
        if cls is not None:
            return cls
    raise AttributeError(attr)
