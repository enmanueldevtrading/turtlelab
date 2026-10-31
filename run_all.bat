@echo off
python scripts\validate_data.py
python scripts\run_multisymbol.py --strategy ema_cross --params "{\"fast\":72,\"slow\":150}" --tfs M1,M5 --balance 10
pause
