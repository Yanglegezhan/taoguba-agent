@echo off
chcp 65001 >nul
echo ============================================================
echo Market Monitor - 智能更新（快速版）
echo ============================================================
echo.
echo 智能更新策略：
echo   1. 获取最近20天的涨停股票列表
echo   2. 只更新这些股票的数据（约200-500只）
echo   3. 预计时间：1-3分钟
echo.
echo 对比传统更新：
echo   - 传统更新：5800只股票，需要10-20分钟
echo   - 智能更新：200-500只股票，需要1-3分钟
echo.
pause

cd ..

echo [1/3] 智能更新数据...
python scripts/main.py --mode update-smart
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
