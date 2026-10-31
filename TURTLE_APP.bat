@echo off
REM TurtleLab - Lanzador principal (Windows 10/11)
REM Uso: doble clic en este archivo. No abre OpenCode ni dependencias ocultas.
setlocal EnableDelayedExpansion
cd /d "%~dp0"

title TurtleLab - NO CERRAR ESTA VENTANA

REM 1. Verificar carpeta correcta
if not exist "panel_server.py" (
    echo ERROR: No se encontro panel_server.py. Ejecuta este BAT desde la carpeta de TurtleLab.
    pause
    exit /b 1
)

REM 2. Verificar Python
where python >nul 2>nul
if %errorlevel% neq 0 (
    where py >nul 2>nul
    if %errorlevel% neq 0 (
        echo ERROR: Python no esta disponible. Instala Python 3.14+ desde python.org.
        pause
        exit /b 1
    )
    set "PY=py -3"
) else (
    set "PY=python"
)

REM 3. Activar entorno virtual si existe
if exist ".venv\Scripts\activate.bat" (
    call .venv\Scripts\activate.bat
) else if exist "venv\Scripts\activate.bat" (
    call venv\Scripts\activate.bat
)

REM 4. Verificar dependencias basicas
%PY% -c "import pandas, numpy" >nul 2>nul
if %errorlevel% neq 0 (
    echo Instalando dependencias (solo una vez)...
    %PY% -m pip install -r requirements.txt
    if %errorlevel% neq 0 (
        echo ERROR: No se pudieron instalar las dependencias.
        pause
        exit /b 1
    )
)

REM 5. Verificar que no haya otra instancia corriendo
powershell -NoProfile -Command "if (Get-CimInstance Win32_Process -Filter \"Name='python.exe'\" | Where-Object { $_.CommandLine -like '*panel_server*' }) { exit 1 } else { exit 0 }" >nul 2>nul
if %errorlevel% equ 1 (
    echo Ya hay una instancia de TurtleLab corriendo.
    echo Reutilizando la instancia existente...
    start "" "http://127.0.0.1:8080"
    pause
    exit /b 0
)

REM 6. Iniciar la aplicacion en segundo plano
echo Iniciando TurtleLab...
echo Esperando a que el servidor este listo...
start /B "" %PY% panel_server.py > panel.log 2>&1

REM Esperar hasta 30 segundos a que el servidor responda
set "READY=0"
for /L %%i in (1,1,30) do (
    if !READY! equ 0 (
        timeout /t 1 /nobreak >nul
        powershell -NoProfile -Command "try { $r = Invoke-WebRequest -Uri 'http://127.0.0.1:8080/api/status' -UseBasicParsing -TimeoutSec 2; if ($r.StatusCode -eq 200) { exit 0 } else { exit 1 } } catch { exit 1 }" >nul 2>nul
        if !errorlevel! equ 0 (
            set "READY=1"
        )
    )
)

if !READY! equ 0 (
    echo ERROR: El servidor no respondio en 30 segundos. Revisa panel.log.
    type panel.log
    pause
    exit /b 1
)

REM 7. Abrir el navegador UNA SOLA VEZ
echo Servidor listo. Abriendo navegador...
start "" "http://127.0.0.1:8080"

echo.
echo TurtleLab esta corriendo en http://127.0.0.1:8080
echo NO CIERRES esta ventana mientras uses la aplicacion.
echo Para detener: ejecuta STOP_TURTLE.bat o presiona Ctrl+C.
echo.

REM Mantener la ventana abierta
pause
endlocal