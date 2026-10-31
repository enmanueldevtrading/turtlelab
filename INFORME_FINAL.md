# Informe Final — TurtleLab

## Fecha
31 de octubre de 2026

## Problemas solucionados

### 1. Apertura triple del navegador
- **Causa**: `panel_server.py` abría el navegador en el bloque de puertos ocupados, `TURTLE_APP.bat` también lo abría, y `PANEL.bat` lo abría por separado.
- **Solución**: Eliminado `import webbrowser` y `webbrowser.open()` de `panel_server.py`. Solo `TURTLE_APP.bat` abre el navegador (una sola vez). `PANEL.bat` ya no abre navegador.
- **Verificación**: Un solo proceso Python, una sola pestaña.

### 2. Consumo excesivo de recursos
- **Causa**: `list_results()` leía 2073 directorios de resultados en cada llamada a `/api/status` (sin caché). El inventario leía todos los archivos CSV sin distinguir la fuente.
- **Solución**: Agregado caché con TTL de 5 minutos para `list_results()`. Invalidación automática al crear/borrar resultados. `inventory()` ahora acepta parámetro `root` para distinguir weltrade/yahoo.
- **Resultado**: Primera carga ~2s, siguientes ~0.07s. RAM ~19MB.

### 3. `scripts/run_backtest.py` fallaba con 0 operaciones
- **Causa**: No manejaba el caso de resultados vacíos (guardaba en `results/None`).
- **Solución**: Agregado manejo explícito: si `r.get("empty")` o `bt_id is None`, imprime mensaje y retorna sin guardar.

### 4. `optimize.py` consumía IDs sin guardar
- **Causa**: `run_backtest(save=False)` llamaba a `next_bt_id()` siempre, consumiendo IDs.
- **Solución**: `run_backtest()` ahora solo consume BT-ID cuando `save=True`. Cuando `save=False`, `bt_id=None`.

### 5. `download_data.bat` no incluía M3
- **Solución**: Agregado M3 a la lista de temporalidades: `M1,M3,M5,M15,M30,H1,H4,D1`.

### 6. Credenciales expuestas en `.env.example`
- **Causa**: El `.env.example` original contenía credenciales reales de Cloudflare R2.
- **Solución**: Reescrito `.env.example` sin credenciales reales, solo placeholders.

### 7. Credenciales en `checklists/cloudflare-checklist.md`
- **Solución**: Agregado `checklists/` al `.gitignore`.

## Cambios de diseño

- No se realizaron cambios visuales mayores en esta iteración (prioridad: rendimiento y estabilidad).
- El panel ya tenía un diseño funcional con 5 vistas, tablas, gráficos SVG inline.
- Se optimizó el rendimiento del frontend: caché de resultados, carga bajo demanda del inventario.

## Funcionalidades que funcionan

- ✅ Motor de backtest (6 estrategias, 25/25 pruebas pasan).
- ✅ Panel web (5 vistas: Datos, Estrategias, Trabajo, Pruebas, Monte Carlo).
- ✅ Descarga de datos MT5 y Yahoo.
- ✅ Monte Carlo (shuffle/bootstrap con semilla).
- ✅ Costes reales por símbolo.
- ✅ Optimización de recursos (caché, sin polling innecesario).
- ✅ Un solo proceso Python, sin procesos ocultos.
- ✅ Un solo navegador al iniciar.

## Pruebas ejecutadas

- 25/25 pruebas del motor pasan (0.9s).
- Panel web carga correctamente (5 vistas, 0 errores de consola).
- Endpoints `/api/status` y `/api/inventory` funcionan.
- Inicio y detención verificados.

## Qué queda pendiente

- Exportar/borrar resultados completo desde el panel.
- Comparador lado a lado.
- Optimización visible en el panel.
- Fechas y parámetros editables.
- Monte Carlo completo con costes en la UI.
- Mejora visual de UI/UX (diseño Apple, jerarquía, espaciado).
- Publicación en GitHub (esperando autorización del usuario).

## Cómo ejecutar y detener TurtleLab

**Ejecutar**: Doble clic en `TURTLE_APP.bat`
- Verifica Python y dependencias.
- Inicia el servidor en segundo plano.
- Abre el navegador UNA sola vez.
- Muestra estado en la ventana de consola.

**Detener**: Doble clic en `STOP_TURTLE.bat`
- Detiene el proceso Python de forma segura.
- No mata procesos de otros programas.

**Alternativa**: `python panel_server.py` (sin abrir navegador automáticamente).

## Cómo colaborar con modelos gratuitos de IA

1. Lee `AGENTS.md` y después `README.md`.
2. Usa un modelo gratuito compatible con tu herramienta (OpenCode, Copilot, Cursor, etc.).
3. Python realiza los cálculos. La IA solo ayuda a desarrollar y mantener el código.
4. No se requiere suscripción de pago para comprender o ejecutar TurtleLab.
5. Si una tarea requiere capacidades no disponibles en un modelo gratuito, se explica claramente.

## Estado del repositorio GitHub

- Repositorio creado: https://github.com/enmanueldevtrading/turtlelab (vacío).
- NO se ha hecho commit ni push.
- Esperando autorización explícita del usuario para publicar.