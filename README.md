# TurtleLab — Laboratorio de Backtesting Cuantitativo

Laboratorio local de backtesting para estrategias mecánicas en **índices sintéticos de Weltrade**.

## Qué es

TurtleLab es una aplicación Python que permite:
- Descargar datos históricos de MT5 (Weltrade) y Yahoo Finance.
- Ejecutar backtests de 6 estrategias mecánicas sobre 41+ símbolos × 8 temporalidades.
- Comparar resultados, analizar operaciones y ejecutar Monte Carlo.
- Todo en local, sin conexión de trading real, sin IA, sin MT5 para el backtest.

## Qué son los índices sintéticos de Weltrade

Los datos históricos provienen de **índices sintéticos de Weltrade**, obtenidos a través de MetaTrader 5 (MT5). Estos índices NO son Forex tradicional, acciones ni criptomonedas.

- Son instrumentos sintéticos creados por Weltrade.
- Se descargan desde MT5 mediante `scripts/download_data.py`.
- Se almacenan en `data/weltrade/` como CSV comprimidos (gzip).
- Cada símbolo tiene archivos por temporalidad: M1, M3, M5, M15, M30, H1, H4, D1.
- Incluyen información real de MT5: spread, tick value, volumen min/max/paso.
- Los datos son históricos y estáticos (no se actualizan en tiempo real).

## Requisitos

- Windows 10/11.
- Python 3.14+ (probado con 3.14.6).
- MT5 instalado solo para descarga de datos (no para backtest).

## Instalación

```powershell
cd D:\TurtleLab
python -m pip install -r requirements.txt
```

## Ejecución

Doble clic en `TURTLE_APP.bat` (recomendado) o desde consola:

```powershell
python panel_server.py
```

Abre `http://127.0.0.1:8080` en el navegador. El navegador se abre UNA sola vez.

## Detener

Doble clic en `STOP_TURTLE.bat` o cierra la ventana de consola / Ctrl+C.

## Estructura del proyecto

```
TurtleLab/
├── bt/                  # Motor de backtest (ejecución, métricas, fondeo)
│   ├── registry.py      # Registro de estrategias (descubre plugins)
│   ├── sdk.py           # Contrato que cumple toda estrategia
│   └── plugins/         # Estrategias incluidas (turtle.py, ema.py, vwap.py)
├── user_strategies/     # TUS estrategias: suelta un .py y aparece en el panel
├── web/                 # Interfaz (index.html, app.css, app.js, logo.svg)
├── panel_server.py      # Panel web (stdlib, sin dependencias externas)
├── scripts/             # Descarga MT5, importación, validación, tests
├── tests/               # 32 pruebas del motor
├── data/                # Datos locales (Weltrade M1-D1, Yahoo) — NO se versiona
├── results/             # Backtests guardados (BT-XXXXXX)
├── GUIA_ESTRATEGIAS.txt # Cómo crear y cargar estrategias nuevas (con IA)
├── TURTLE_APP.bat       # Lanzador principal
├── STOP_TURTLE.bat      # Detener aplicación
└── requirements.txt     # Dependencias Python
```

## Datos locales (no están en GitHub)

Todo son **índices sintéticos de Weltrade** (41 pares). Cada par vive en
`data/weltrade/<PAR>/` con un archivo por temporalidad:

| Qué | Dónde | ¿Está en GitHub? |
|---|---|---|
| Velas D1, H4, H1 | `data/weltrade/<PAR>/<TF>.csv.gz` | **Sí** (123 archivos, 17,9 MB) |
| Velas M1–M30 | `data/weltrade/<PAR>/<TF>.csv.gz` | No (se bajan de MT5 desde el panel) |
| Costes del par | `data/weltrade/<PAR>/info.json` | **Sí** (spread, swap, lote, tick) |

Las 8 temporalidades completas ocupan ~162 MB, demasiado para un repositorio (y se
pueden regenerar), por eso solo viaja el histórico de D1/H4/H1. Para completar tu
copia en local:

Desde el propio panel (**Datos → Importar datos desde MT5**) eliges pares,
temporalidades, cuántas velas y el tipo de dato (velas, tick a tick o foto del
libro de órdenes). También por consola:

```powershell
python scripts/download_data.py                 # desde MT5 (Weltrade abierto)
python scripts/import_data.py                   # importa SwitchX1800_Dataset y auditoria_total
```

El panel detecta todo solo: vista **Datos**, con cada par agrupado por familia, sus
temporalidades y los costes reales que publica Weltrade en MT5.

### Costes: qué se puede descargar y qué no

- **Spread**: sí. Se lee de MT5 y se guarda por par en `info.json` (p. ej. 74 puntos = 0,74).
- **Swap** (mantenimiento nocturno): sí, MT5 lo publica por par (`swap_long` / `swap_short`).
  Se rellena al descargar ese par desde el panel.
- **Lote mínimo/máximo/paso y valor del tick**: sí, también de MT5.
- **Comisión**: **no**. MT5 no la publica; depende de tu cuenta de Weltrade, así que se
  configura en cada backtest (por defecto 0).
Para compartirlos sin subir 162 MB, `python scripts/data_pack.py pack` crea un ZIP
con un subconjunto (ver `data/README.md`).

## Estrategias disponibles

Cada estrategia es un plugin independiente en `bt/plugins/`:

1. **Tortuga 20/10** (turtle20_10): Donchian breakout con trailing stop.
2. **Tortuga 20/20** (turtle20_20): Donchian breakout simétrico.
3. **Tortuga 55/20** (turtle55_20): Donchian breakout largo con salida corta.
4. **EMA 72/150** (ema_cross): Cruce de medias exponenciales.
5. **EMA 30/75/150** (ema30_75_150): Triple EMA con filtro de tendencia.
6. **VWAP Sesiones** (vwap_session): Reversión a VWAP por sesiones.

### Añadir estrategias nuevas (sin tocar el motor)

Suelta un archivo `.py` en `user_strategies/` y pulsa **Recargar plugins** en el panel.
No hace falta editar `bt/strategies.py` ni reiniciar. Si un archivo tiene un error, el
panel lo marca en rojo y las demás estrategias siguen funcionando.
Guía completa con prompt para IA: [GUIA_ESTRATEGIAS.txt](GUIA_ESTRATEGIAS.txt)

## Funcionalidades

- **Motor de backtest** reproducible (BT-ID, hashes, sin look-ahead).
- **Panel web** con 6 vistas: Datos, Estrategias, Trabajo, Pruebas, Fondeo, Monte Carlo.
- **Estrategias modulares**: plugins descubiertos en caliente (`bt/plugins/`, `user_strategies/`).
- **Métrica de fondeo**: cuenta de $6,000, DD total ≤8% ($480), DD diario ≤4% ($240, UTC),
  objetivo +8% ($480). Veredicto APTO / NO APTO / SIN OBJETIVO guardado en cada `funding.json`.
- **Costes reales** por símbolo de MT5 (spread, lote min/max, deslizamiento).
- **Monte Carlo** con shuffle/bootstrap y semilla reproducible.
- **32 pruebas automatizadas** del motor (100% pasan).
- **Optimización de recursos**: caché, sin polling innecesario, un solo proceso.

## Cómo colaborar con modelos gratuitos de IA

El proyecto puede mantenerse y mejorarse utilizando modelos gratuitos de IA:

- El colaborador puede usar modelos gratuitos compatibles con su herramienta (OpenCode, Copilot, Cursor, etc.).
- No se requiere suscripción de pago para comprender o ejecutar TurtleLab.
- No se depende de una API de IA para ejecutar backtests.
- Python realiza los cálculos. La IA solo ayuda a desarrollar, mantener y mejorar el código.
- Si una tarea requiere capacidades no disponibles en un modelo gratuito, se explica claramente.

## Pruebas

```powershell
python scripts/run_bt_tests.py
```

Resultado esperado: 32/32 passed.


## Metodologia de metricas

### Sharpe y Sortino
- **Sharpe**: `rets.mean() / (rets.std(ddof=1) + 1e-12) * sqrt(n)`, donde `rets = pnl/capital` (retorno por operacion).
- **Sortino**: Igual que Sharpe pero usando solo retornos negativos en el denominador.
- **Importante**: Son metricas por operacion, NO anualizadas. No representan rendimiento anual.

### Monte Carlo
- Reordena (shuffle) o remuestrea (bootstrap) las operaciones reales con semilla reproducible.
- **Limitacion**: Usa capital fijo (no simula sizing compuesto). El equity curve se reconstruye con capital inicial fijo.
- No genera senales ni predice resultados futuros.
- Solo mide robustez estadistica de la secuencia de operaciones historicas.

## Credenciales

Cada colaborador configura sus propias credenciales locales en un archivo .env (copiar de .env.example). Nunca comites el archivo .env.

## Licencia

Proyecto privado. Sin licencia pública definida.