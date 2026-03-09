@echo off
chcp 65001 >nul
echo ========================================
echo 使用同花顺获取股票概念 - V2版本
echo ========================================
echo.

python ../scripts/fetch_concepts_tonghuashun_v2.py

echo.
echo ========================================
echo 完成！按任意键退出...
echo ========================================
pause >nul
