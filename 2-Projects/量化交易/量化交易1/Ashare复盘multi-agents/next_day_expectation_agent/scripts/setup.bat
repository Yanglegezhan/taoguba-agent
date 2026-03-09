@echo off
REM 项目初始化脚本 (Windows)

echo ========================================
echo 次日核心个股超预期分析系统 - 初始化
echo ========================================
echo.

REM 创建虚拟环境
echo [1/5] 创建Python虚拟环境...
python -m venv venv
if %errorlevel% neq 0 (
    echo 错误: 创建虚拟环境失败
    exit /b 1
)
echo 虚拟环境创建成功
echo.

REM 激活虚拟环境
echo [2/5] 激活虚拟环境...
call venv\Scripts\activate.bat
echo.

REM 安装依赖
echo [3/5] 安装依赖包...
pip install -r requirements.txt
if %errorlevel% neq 0 (
    echo 错误: 安装依赖失败
    exit /b 1
)
echo 依赖安装成功
echo.

REM 复制配置文件模板
echo [4/5] 创建配置文件...
if not exist config\system_config.yaml (
    copy config\system_config.yaml.template config\system_config.yaml
    echo 已创建 config\system_config.yaml
)
if not exist config\agent_config.yaml (
    copy config\agent_config.yaml.template config\agent_config.yaml
    echo 已创建 config\agent_config.yaml
)
if not exist config\data_source_config.yaml (
    copy config\data_source_config.yaml.template config\data_source_config.yaml
    echo 已创建 config\data_source_config.yaml
)
if not exist .env (
    copy .env.example .env
    echo 已创建 .env
)
echo.

REM 创建必要的目录
echo [5/5] 创建数据目录...
if not exist data\stage1_output mkdir data\stage1_output
if not exist data\stage2_output mkdir data\stage2_output
if not exist data\stage3_output mkdir data\stage3_output
if not exist data\historical mkdir data\historical
if not exist data\logs mkdir data\logs
echo 数据目录创建成功
echo.

echo ========================================
echo 初始化完成！
echo ========================================
echo.
echo 下一步：
echo 1. 编辑 config\system_config.yaml 配置系统参数
echo 2. 编辑 config\agent_config.yaml 配置Agent参数
echo 3. 编辑 config\data_source_config.yaml 配置数据源
echo 4. 编辑 .env 配置API密钥和环境变量
echo.
echo 运行测试：
echo   pytest tests\
echo.
pause
