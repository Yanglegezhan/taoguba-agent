@echo off
chcp 65001
echo ========================================
echo 市场监控系统 - 仅生成分析报表
echo ========================================
echo.

python ../scripts/main.py --mode analyze

echo.
echo 按任意键退出...
pause > nul
