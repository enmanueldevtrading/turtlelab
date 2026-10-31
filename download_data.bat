@echo off
python scripts\download_data.py --symbols ALL --tfs M1,M3,M5,M15,M30,H1,H4,D1 --bars 50000
pause
