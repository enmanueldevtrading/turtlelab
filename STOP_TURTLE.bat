@echo off
REM TurtleLab - Detener aplicacion de forma segura
setlocal
cd /d "%~dp0"

echo Deteniendo TurtleLab...

REM Buscar y detener el proceso Python que ejecuta panel_server.py
powershell -NoProfile -Command "Get-CimInstance Win32_Process -Filter \"Name='python.exe'\" | Where-Object { $_.CommandLine -like '*panel_server*' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue; Write-Host ('Proceso ' + $_.ProcessId + ' detenido.') }"

REM Limpiar PID si existe
if exist "panel.pid" del /q "panel.pid" 2>nul

echo.
echo TurtleLab detenido. Puedes cerrar esta ventana.
pause
endlocal