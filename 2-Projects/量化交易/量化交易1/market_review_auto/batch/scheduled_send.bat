@echo off
setlocal
cd /d %~dp0.. 

call conda activate CX
if errorlevel 1 (
  exit /b 1
)

python src\app\run_nightly_recap.py --send --email-to 2358638763@qq.com
endlocal
