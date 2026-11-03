"""SDK publico para escribir estrategias.

Ejemplo minimo (guardar como user_strategies/mi_idea.py):

    from bt.sdk import BaseStrategy, strategy, ema, atr

    @strategy(label="Cruce EMA 9/50", desc="Cruce simple al cierre.",
              rules=["Compra si EMA9 cruza arriba EMA50 al cierre"],
              tfs=["M15", "H1"], balance=50.0, params={"fast": 9, "slow": 50})
    class CruceRapido(BaseStrategy):
        name = "cruce_rapido"
        defaults = {"fast": 9, "slow": 50}

        def prepare(self, df, p):
            c = df["close"].to_numpy(float)
            return {"c": c, "f": ema(c, p["fast"]), "s": ema(c, p["slow"])}

        def entry_signal(self, df, i, ctx, p):
            ...  # 1 compra, -1 venta, 0 nada
"""
import numpy as np

from .indicators import atr, donchian, ema, rsi, sma
from .registry import (ALL_TFS, add_preset, get_strategy, register_class,
                       reload_plugins, resolve_class, STRATEGIES,
                       STRATEGY_META, PLUGINS, plugin_report)

__all__ = [
    "BaseStrategy", "strategy", "add_preset", "register_class", "ALL_TFS",
    "get_strategy", "reload_plugins", "plugin_report", "resolve_class",
    "STRATEGIES", "STRATEGY_META", "PLUGINS",
    "ema", "sma", "atr", "rsi", "donchian", "cross_up", "cross_down",
    "np",
]


def _eps(x) -> float:
    return 1e-9 * max(1.0, abs(float(x)))


def cross_up(fast, slow, i) -> bool:
    if i < 1 or np.isnan([fast[i - 1], slow[i - 1], fast[i], slow[i]]).any():
        return False
    return bool(fast[i - 1] <= slow[i - 1] + _eps(slow[i - 1])
                and fast[i] > slow[i] + _eps(slow[i]))


def cross_down(fast, slow, i) -> bool:
    if i < 1 or np.isnan([fast[i - 1], slow[i - 1], fast[i], slow[i]]).any():
        return False
    return bool(fast[i - 1] >= slow[i - 1] - _eps(slow[i - 1])
                and fast[i] < slow[i] - _eps(slow[i]))


_eps_ = _eps
_cross_up = cross_up
_cross_down = cross_down


class BaseStrategy:
    name = "base"
    defaults: dict = {}

    def prepare(self, df, params: dict):
        return {}

    def entry_signal(self, df, i: int, ctx: dict, params: dict) -> int:
        return 0

    def exit_reason(self, df, i, ctx, params: dict, direction: int) -> str:
        return "SALIDA POR SEÑAL"

    def exit_signal(self, df, i: int, ctx: dict, params: dict, direction: int) -> bool:
        return False

    def stop_price(self, df, i: int, ctx: dict, params: dict, direction: int,
                   entry_price: float):
        return None, None  # sl, tp


def strategy(*, id=None, label=None, desc="", rules=(), tfs=None,
             balance=50.0, riesgo="", order=100, params=None, presets=None):
    """Decorador: registra la clase y la publica en el panel."""
    def deco(cls):
        register_class(cls)
        if presets:
            for p in presets:
                p = dict(p)
                add_preset(cls, **p)
        else:
            add_preset(cls, id or cls.name, params=params or {},
                       label=label or cls.name, desc=desc, rules=rules,
                       tfs=tfs, balance=balance, riesgo=riesgo, order=order)
        return cls
    return deco
