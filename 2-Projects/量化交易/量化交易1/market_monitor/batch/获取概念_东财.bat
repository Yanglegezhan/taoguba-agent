@echo off
chcp 65001 >nul
echo ========================================
echo 从东方财富网获取股票概念信息
echo ========================================
echo.
echo 这个脚本会从东方财富网爬取概念数据
echo 预计需要3-5分钟
echo.
pause

python ../scripts/fetch_concepts_eastmoney.py

echo.
echo ========================================
echo 完成！
echo ========================================
pause
