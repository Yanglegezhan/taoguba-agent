@echo off
chcp 65001
echo ========================================
echo 市场监控系统 - 安装依赖包
echo ========================================
echo.

echo 正在安装Python依赖包...
echo.

pip install -r requirements.txt

echo.
echo ========================================
echo 安装完成！
echo ========================================
echo.
echo 下一步：
echo 1. 运行测试：python test_basic.py
echo 2. 初始化数据：双击"初始化数据.bat"
echo.
echo 按任意键退出...
pause > nul
