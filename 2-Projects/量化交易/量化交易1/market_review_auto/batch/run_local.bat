@echo off
setlocal
cd /d %~dp0.. 

call conda activate market_review_auto
if errorlevel 1 (
  echo Failed to activate conda env: market_review_auto
  exit /b 1
)

python src\app\run_nightly_recap.py
endlocal
pause
