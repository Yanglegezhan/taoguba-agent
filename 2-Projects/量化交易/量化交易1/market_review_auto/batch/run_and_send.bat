@echo off
setlocal
cd /d %~dp0.. 

call conda activate market_review_auto
if errorlevel 1 (
  echo Failed to activate conda env: market_review_auto
  exit /b 1
)

REM Please set MAIL_USERNAME / MAIL_PASSWORD / MAIL_FROM_ADDR before running.
python src\app\run_nightly_recap.py --send --email-to 2358638763@qq.com
endlocal
pause
