@echo off
REM Uso: backtest.bat SYMBOL TIMEFRAME STRATEGY PARAMS_JSON BALANCE
python scripts\run_backtest.py --symbol "%1" --timeframe "%2" --strategy "%3" --params "%4" --balance %5
pause
