@echo off
setlocal
cd /d %~dp0.. 

echo Creating conda env market_review_auto...
conda env create -f environment.yml
if errorlevel 1 (
  echo Failed to create environment.
  exit /b 1
)

echo Done.
endlocal
pause
