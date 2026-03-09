@echo off
chcp 65001 >nul
echo ============================================================
echo 清理重复数据并重新生成溢价表
echo ============================================================
echo.

cd ..

echo [1/3] 清理重复数据...
python scripts/clean_duplicates.py
if errorlevel 1 (
    echo 错误: 数据清理失败！
    pause
    exit /b 1
)
echo ✓ 数据清理完成
echo.

echo [2/3] 重新分析连板数据...
python scripts/board_analyzer.py
if errorlevel 1 (
    echo 错误: 连板分析失败！
    pause
    exit /b 1
)
echo ✓ 连板分析完成
echo.

echo [3/3] 重新生成彩色溢价表...
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
