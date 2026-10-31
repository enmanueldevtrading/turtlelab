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
├── bt/                  # Motor de backtest (6 estrategias, ejecución, métricas)
├── panel_server.py      # Panel web (stdlib, sin dependencias externas)
├── scripts/             # Utilidades: descarga, validación, backtest, tests
├── tests/               # 25 pruebas del motor
├── data/                # Datos locales (Weltrade M1-M5, Yahoo)
├── results/             # Backtests guardados (BT-XXXXXX)
├── TURTLE_APP.bat       # Lanzador principal
├── STOP_TURTLE.bat      # Detener aplicación
└── requirements.txt     # Dependencias Python
```

## Estrategias disponibles

1. **Tortuga 20/10** (turtle20_10): Donchian breakout con trailing stop.
2. **Tortuga 20/20** (turtle20_20): Donchian breakout simétrico.
3. **Tortuga 55/20** (turtle55_20): Donchian breakout largo con salida corta.
4. **EMA 72/150** (ema_cross): Cruce de medias exponenciales.
5. **EMA 30/75/150** (ema30_75_150): Triple EMA con filtro de tendencia.
6. **VWAP Sesiones** (vwap_session): Reversión a VWAP por sesiones.

## Funcionalidades

- **Motor de backtest** reproducible (BT-ID, hashes, sin look-ahead).
- **Panel web** con 5 vistas: Datos, Estrategias, Trabajo, Pruebas, Monte Carlo.
- **Costes reales** por símbolo de MT5 (spread, lote min/max, deslizamiento).
- **Monte Carlo** con shuffle/bootstrap y semilla reproducible.
- **25 pruebas automatizadas** del motor (100% pasan).
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

Resultado esperado: 25/25 passed.


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