# data/ — velas locales (NO se versionan)

`data/` guarda las velas que usa el motor. Los archivos `.csv.gz` están en
`.gitignore` a propósito: son ~171 MB y se pueden regenerar, así que no viven
en el repositorio.

```
data/weltrade/<Símbolo>/<TF>.csv.gz   + info.json (spread, lote min/max, tick)
data/yahoo/<Símbolo>/<TF>.csv.gz
```

## Si acabas de clonar el repo y el panel no muestra nada

No es un fallo: no hay velas todavía. Elige una vía.

**A) Descargar de MT5** (necesita MetaTrader 5 abierto, conectado a Weltrade):

```powershell
python scripts/download_data.py --symbols ALL --tfs M1,M3,M5,M15,M30,H1,H4,D1
```

o doble clic en `download_data.bat`.

**B) Restaurar un paquete de datos** (rápido, sin MT5):

```powershell
python scripts/data_pack.py unpack datos_weltrade.zip
```

**C) Crear el paquete en la máquina que sí tiene los datos**:

```powershell
python scripts/data_pack.py pack
python scripts/data_pack.py info datos_weltrade.zip
```

Sube el `.zip` a **GitHub Releases** (no al repo) y compártelo. Al restaurar,
el panel detecta los símbolos sin reiniciar.

## Reglas

- No se modifican los archivos originales ni se inventan velas.
- Cada símbolo se identifica por carpeta; la temporalidad por nombre de archivo.
- `results/inventory_cache.json` acelera el inventario; se puede borrar sin miedo.
