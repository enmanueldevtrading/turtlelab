# AGENTS.md — Instrucciones para IA de programación (TurtleLab)

## Antes de modificar el proyecto, la IA debe leer AGENTS.md y después README.md.

## Qué es TurtleLab

Laboratorio local de backtesting para estrategias mecánicas en **índices sintéticos de Weltrade** y otros mercados. Python 3.14, stdlib + pandas + numpy. Sin MT5 para backtest (solo para descarga). Sin IA en runtime: Python realiza todos los cálculos.

## Qué son los índices sintéticos de Weltrade

Los datos históricos utilizados por TurtleLab provienen de **índices sintéticos de Weltrade**, obtenidos a través de MetaTrader 5 (MT5). Estos índices NO son Forex tradicional, acciones ni criptomonedas.

Características de los índices sintéticos:
- Son instrumentos sintéticos creados por Weltrade, no activos del mercado real.
- Se descargan desde MT5 mediante el script `scripts/download_data.py`.
- Se almacenan localmente en `data/weltrade/` como archivos CSV comprimidos (gzip).
- Cada símbolo tiene su propia carpeta con archivos por temporalidad (M1, M3, M5, M15, M30, H1, H4, D1).
- Incluyen información real de MT5: spread, tick value, volumen mínimo/máximo/paso, tamaño de contrato.
- Los datos son históricos: no se actualizan automáticamente ni en tiempo real.

Temporalidades disponibles: M1, M3, M5, M15, M30, H1, H4, D1.

Limitaciones de los datos:
- Los datos son históricos y estáticos (no se actualizan en tiempo real).
- La cobertura temporal varía por símbolo (algunos tienen datos desde 2025, otros desde 2026).
- No incluyen datos de mercado real (Forex, acciones, cripto) a menos que se descarguen desde Yahoo Finance.
- Los costes (spread, comisión) se basan en la configuración real de MT5 de Weltrade.

Cómo incorporar nuevos datos compatibles:
1. Ejecutar `scripts/download_data.py` con MT5 abierto y conectado a Weltrade.
2. Los nuevos datos se guardan en `data/weltrade/` automáticamente.
3. El panel los detecta sin cambios de código (inventario automático).
4. Para datos de Yahoo Finance, usar el modo Yahoo del panel (forex, oro, BTC, índices).

## Modelos de IA gratuitos

El proyecto debe poder mantenerse y mejorarse utilizando modelos gratuitos de IA cuando estén disponibles.

Reglas para colaboradores con IA:
- El colaborador puede utilizar modelos gratuitos compatibles con su herramienta de programación (OpenCode, Copilot, Cursor, etc.).
- No se debe exigir una suscripción de pago para comprender o ejecutar TurtleLab.
- No se debe depender de una API de IA para ejecutar los backtests.
- Python realiza los cálculos y operaciones del programa. La IA solamente ayuda a desarrollar, mantener, explicar y mejorar el código.
- Si una tarea requiere capacidades no disponibles en un modelo gratuito (por ejemplo, análisis de imágenes, razonamiento complejo), debe explicarse claramente al colaborador.
- No introducir dependencias innecesarias de servicios de pago.

## Cómo se ejecuta

```powershell
cd D:\TurtleLab
python panel_server.py   # Panel web en http://127.0.0.1:8080
```

O doble clic en `TURTLE_APP.bat` (recomendado: verifica Python, dependencias, inicia el servidor y abre el navegador automáticamente).

Para detener: doble clic en `STOP_TURTLE.bat` o cierra la ventana de consola.

## Cómo se utiliza Python

- `bt/` es el motor: `backtest.py` (loop por barra), `strategies.py` (6 estrategias + registro), `execution.py` (lote, spread, SL/TP), `metrics.py` (20+ métricas), `montecarlo.py` (shuffle/bootstrap).
- `scripts/` son utilidades: `run_backtest.py`, `download_data.py`, `validate_data.py`, `run_bt_tests.py`.
- `panel_server.py` es la interfaz web (stdlib, sin dependencias externas).
- Los datos están en `data/weltrade/` (CSV gzip) y `data/yahoo/`.
- Los resultados se guardan en `results/BT-XXXXXX/` (BT-ID incremental, no se sobrescriben).

## Cómo funciona la interfaz

- Panel web de 5 vistas: Datos, Estrategias, Trabajo, Pruebas, Monte Carlo.
- Corre en `http://127.0.0.1:8080` (ThreadingTCPServer, solo localhost).
- Sin OpenCode ni IA en runtime. La aplicación funciona por sí misma.
- El navegador se abre UNA sola vez al iniciar (desde TURTLE_APP.bat).
- El panel no consume recursos cuando está inactivo (sin polling automático).

## Qué BAT usar

- `TURTLE_APP.bat`: lanzador principal. Verifica Python, dependencias, inicia el servidor, abre el navegador UNA vez. (Recomendado)
- `STOP_TURTLE.bat`: detiene el servidor de forma segura.
- `PANEL.bat`: lanza el panel sin abrir navegador (para uso avanzado).
- `backtest.bat`: un backtest reproducible (5 args: symbol TF strategy params balance).
- `test_bt.bat`: ejecuta las 25 pruebas del motor.
- `download_data.bat`: descarga datos de MT5 (incluye M1, M3, M5, M15, M30, H1, H4, D1).
- `optimize.bat`: optimización de parámetros.

## Cómo detener la aplicación

- Doble clic en `STOP_TURTLE.bat` o cierra la ventana de consola / Ctrl+C.
- El panel solo escucha en localhost. No quedan procesos en segundo plano.

## Archivos importantes

| Archivo | Qué hace |
|---|---|
| `bt/backtest.py` | Loop por barra, sin futuro, BT-ID |
| `bt/strategies.py` | 6 estrategias + registro STRATEGY_META |
| `bt/execution.py` | Lote, spread, comisión, SL/TP, trailing |
| `bt/metrics.py` | 20+ métricas |
| `bt/montecarlo.py` | Shuffle/bootstrap con semilla |
| `panel_server.py` | Panel web completo |
| `scripts/run_backtest.py` | Un backtest reproducible |
| `scripts/download_data.py` | Descarga MT5 incremental |
| `scripts/run_bt_tests.py` | 25 pruebas automatizadas |

## Estrategias disponibles

1. **Tortuga 20/10** (turtle20_10): Donchian breakout con trailing stop.
2. **Tortuga 20/20** (turtle20_20): Donchian breakout simétrico.
3. **Tortuga 55/20** (turtle55_20): Donchian breakout largo con salida corta.
4. **EMA 72/150** (ema_cross): Cruce de medias exponenciales.
5. **EMA 30/75/150** (ema30_75_150): Triple EMA con filtro de tendencia.
6. **VWAP Sesiones** (vwap_session): Reversión a VWAP por sesiones.

## Partes terminadas

- Motor de backtest reproducible (BT-ID, hashes, sin look-ahead).
- 6 estrategias mecánicas.
- Panel web con datos, estrategias, trabajo, pruebas y Monte Carlo.
- Descarga de datos MT5 y Yahoo.
- 25 pruebas automatizadas (100% pasan).
- Costes reales por símbolo.
- Optimización de consumo de recursos (caché, sin polling innecesario).
- Corrección de apertura duplicada del navegador.

## Partes pendientes

- Exportar/borrar resultados desde el panel (funciona parcialmente).
- Comparador lado a lado.
- Optimización visible en el panel.
- Fechas y parámetros editables.
- Monte Carlo completo con costes en la UI.

## Errores conocidos

- Monte Carlo ignora el sizing compuesto.
- Sharpe/Sortino son por operación, no anualizados.

## Cómo ejecutar pruebas

```powershell
python scripts/run_bt_tests.py
```

Resultado esperado: 25/25 passed.

## Cómo modificar

1. Añadir estrategia: registrar en `bt/strategies.py` (STRATEGIES + ALIASES + STRATEGY_META).
2. Ejecutar pruebas: `python scripts/run_bt_tests.py`.
3. Los datos originales (`data/`) no se modifican.
4. Los resultados (`results/`) no se sobrescriben (BT-ID incremental).

## Qué evitar

- No dejar procesos Python sin control (el panel es un solo proceso).
- No modificar datos originales (`data/`).
- No sobrescribir resultados (`results/`).
- No usar OpenCode para ejecutar el programa (funciona por sí mismo).
- No inventar datos, métricas ni resultados.
- No abrir el navegador desde Python (solo desde el BAT).
- No introducir dependencias de servicios de pago.

## Instrucción expresa para IA de programación

ANTES DE MODIFICAR EL PROYECTO, LA IA DEBE LEER AGENTS.md Y README.md.

Después debe explicar al colaborador, en lenguaje natural y sencillo:

1. Qué hace TurtleLab: laboratorio de backtesting mecánico para índices sintéticos de Weltrade.
2. Cómo se ejecuta: doble clic en TURTLE_APP.bat o `python panel_server.py`, abre http://127.0.0.1:8080.
3. Cómo se utiliza: datos → estrategias → trabajo → pruebas → Monte Carlo.
4. Qué partes funcionan: motor, 6 estrategias, panel, descarga, 25 pruebas, optimización de recursos.
5. Qué partes se pueden modificar: añadir estrategias en bt/strategies.py, cambiar parámetros, mejorar UI.
6. Qué problemas están pendientes: exportar/borrar completo, comparador, fechas editables.
7. Qué debe evitar: modificar datos originales, sobrescribir resultados, usar IA en runtime, abrir navegador desde Python.

La IA debe mantener actualizado AGENTS.md y README.md cuando cambie el funcionamiento.
La IA puede usar modelos gratuitos para ayudar a desarrollar, mantener y mejorar el código.
Si una tarea requiere capacidades no disponibles en un modelo gratuito, debe explicarlo claramente.
## Licencia

Este proyecto est� licenciado bajo la Licencia MIT. Libre para todos: uso comercial, personal, modificaci�n y distribuci�n.
