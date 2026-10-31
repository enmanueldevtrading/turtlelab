@echo off
REM TurtleLab - Panel web (sin abrir navegador)
REM Uso: para ejecutar el servidor sin abrir navegador automaticamente.
setlocal EnableDelayedExpansion
cd /d "%~dp0"

REM Verificar Python
where python >nul 2>nul
if %errorlevel% neq 0 (
    where py >nul 2>nul
    if %errorlevel% neq 0 (
        echo ERROR: Python no esta disponible.
        pause
        exit /b 1
    )
    set "PY=py -3"
) else (
    set "PY=python"
)

REM Verificar que no haya otra instancia
powershell -NoProfile -Command "if (Get-CimInstance Win32_Process -Filter \"Name='python.exe'\" | Where-Object { $_.CommandLine -like '*panel_server*' }) { exit 1 } else { exit 0 }" >nul 2>nul
if %errorlevel% equ 1 (
    echo Ya hay una instancia de TurtleLab corriendo.
    echo Abre http://127.0.0.1:8080 en tu navegador.
    pause
    exit /b 0
)

REM Iniciar servidor
echo Iniciando TurtleLab...
%PY% panel_server.py
echo.
echo El panel se detuvo.
pause
endlocal