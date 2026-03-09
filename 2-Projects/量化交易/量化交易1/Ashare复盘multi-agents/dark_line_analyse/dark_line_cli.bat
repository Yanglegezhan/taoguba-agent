@echo off
chcp 65001 >nul 2>&1
cd /d "%~dp0\pythonProject2\量化交易1\Ashare复盘multi-agents\dark_line_analyse"
python dark_line_cli.py %*
