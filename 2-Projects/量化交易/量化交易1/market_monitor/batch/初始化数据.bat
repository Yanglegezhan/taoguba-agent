@echo off
chcp 65001
echo ========================================
echo 市场监控系统 - 初始化数据（获取2年历史）
echo ========================================
echo.

python ../scripts/main.py --mode init

echo.
echo 按任意键退出...
pause > nul
