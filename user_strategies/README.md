# user_strategies/ — estrategias que se cargan solas

Cada archivo `.py` de esta carpeta se carga al arrancar el panel y se publica
en la vista **Estrategias**. No hay que tocar el motor (`bt/`) ni el panel.

## Añadir una estrategia

1. Copia `ejemplo_rsi.py` con otro nombre.
2. Cambia `name`, los `defaults` y la lógica de `entry_signal` / `exit_signal`.
3. Guarda. Pulsa **Recargar plugins** en el panel (o reinicia).

Si el archivo tiene un error, el panel lo muestra en rojo con la línea del
problema, pero el resto de estrategias siguen funcionando.

## Contrato mínimo

```python
from bt.sdk import BaseStrategy, strategy, ema, atr

@strategy(id="mi_clave", label="Nombre visible", desc="Qué hace",
          rules=["Compra cuando ...", "Vende cuando ..."],
          tfs=["M15", "H1"], balance=50.0, params={"periodo": 20})
class MiEstrategia(BaseStrategy):
    name = "mi_estrategia"          # clave unica en el motor
    defaults = {"periodo": 20}

    def prepare(self, df, p):        # indicadores, una vez por backtest
        c = df["close"].to_numpy(float)
        return {"c": c}

    def entry_signal(self, df, i, ctx, p):
        return 1                      # 1 compra, -1 venta, 0 nada

    def exit_signal(self, df, i, ctx, p, direction):
        return False                  # True cierra la posicion

    def stop_price(self, df, i, ctx, p, direction, entry_price):
        return None, None             # (stop_loss, take_profit) o (None, None)
```

Reglas del motor que conviene respetar:

- Solo se ve la barra `i` y las anteriores: no usar el futuro (`i+1`).
- `prepare()` se llama una vez con todo el DataFrame; lo pesado va ahí.
- Devuelve arrays de NumPy alineados con las filas de `df`.
- `sl_mult` en `defaults` exige un stop valido (si no, no se abre la operación).
