# Datos en TurtleLab

El panel no inventa datos: si la carpeta `data/` está vacía, no hay nada que
probar. Esto es lo que puedes hacer.

## 1. Descargar de MT5 (desde el panel)

En la vista **Datos** → tarjeta **Importar datos desde MT5**:

1. Elige los **pares** (por defecto, los que ya tienes).
2. Elige las **temporalidades** (M1 … D1).
3. Elige **cuántas velas** por archivo (5.000 a 500.000).
4. Elige **qué datos**:
   - **Velas**: lo normal para backtests. Incremental, nunca sobrescribe.
   - **Tick a tick**: lo más fino que guarda MT5 (bid/ask de cada operación),
     pero MT5 solo conserva unos días. Se guarda en `ticks_AAAAMMDD.csv.gz`
     y no sustituye a las velas.
   - **Libro de órdenes**: MT5 no guarda histórico de profundidad; se toma una
     foto del libro en ese momento (`book_FECHA.json`).
5. Pulsa **Descargar y guardar en local**. Se descarga de uno en uno, con
   barra de progreso y registro de lo que MT5 devuelve (velas nuevas o error).

Si MT5 no responde, la tarjeta muestra el motivo exacto que da MT5 y qué hacer.

### Por consola (equivalente)

```powershell
python scripts/download_data.py --symbols ALL --tfs M1,M3,M5,M15,M30,H1,H4,D1
```

La descarga es incremental: si vuelves a ejecutarla, solo añade las velas
nuevas. También se guarda `info.json` por símbolo con spread, tick value y
lote mínimo/máximo reales de MT5 (los costes del backtest salen de ahí).

## 2. Restaurar un paquete

```powershell
python scripts/data_pack.py unpack datos_weltrade.zip
```

## 3. Crear un paquete para otro equipo

```powershell
python scripts/data_pack.py pack
python scripts/data_pack.py info datos_weltrade.zip
```

Los `.zip` de datos van a **GitHub Releases**, nunca dentro del repositorio
(171 MB de archivos ya comprimidos que se pueden regenerar).

## Qué significa cada cosa en la vista Datos

- **Archivos**: número de `.csv.gz` locales.
- **Pares**: cada símbolo (índice sintético de Weltrade) con su sello.
- **Temporalidad**: cada par se muestra con sus 8 temporalidades; dentro de
  cada recuadro están las velas y las fechas reales de cobertura.
- **Desde / Hasta**: cobertura real; varía por par y por temporalidad.

Weltrade y Yahoo son fuentes separadas: no se mezclan en el mismo backtest.
