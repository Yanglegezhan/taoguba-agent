@echo off
chcp 65001 >nul
echo ========================================
echo 使用 Tushare API 获取股票概念
echo ========================================
echo.

python ../scripts/fetch_concepts_tushare.py

echo.
echo ========================================
echo 完成！按任意键退出...
echo ========================================
pause >nul
