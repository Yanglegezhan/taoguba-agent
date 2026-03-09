@echo off
chcp 65001 >nul
echo ============================================================
echo Market Monitor - 全量更新
echo ============================================================
echo.
echo 警告：全量更新需要10-20分钟！
echo.
echo 全量更新会获取全市场5800只股票的数据
echo 适用场景：
echo   - 长时间未更新（超过1个月）
echo   - 需要分析非涨停股票
echo   - 智能更新失败
echo.
echo 日常使用建议：使用 智能更新.bat 或 一键更新.bat
echo.
pause

cd ..

echo [1/3] 全量更新数据（预计10-20分钟）...
python scripts/main.py --mode update
if errorlevel 1 (
    echo 错误: 数据更新失败！
    pause
    exit /b 1
)
echo ✓ 数据更新完成
echo.

echo [2/3] 分析连板数据...
python scripts/board_analyzer.py
if errorlevel 1 (
    echo 错误: 连板分析失败！
    pause
    exit /b 1
)
echo ✓ 连板分析完成
echo.

echo [3/3] 生成彩色溢价表...
python scripts/generate_colored_auto.py
if errorlevel 1 (
    echo 错误: 溢价表生成失败！
    pause
    exit /b 1
)
echo ✓ 溢价表生成完成
echo.

echo ============================================================
echo 全部完成！
echo ============================================================
echo.
echo 输出文件:
echo   - output/连板溢价表_彩色版.xlsx
echo   - output/连板溢价表_最终版.csv
echo   - output/board_analysis.csv
echo.
pause
