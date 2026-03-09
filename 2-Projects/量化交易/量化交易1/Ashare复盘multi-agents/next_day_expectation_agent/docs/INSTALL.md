# 安装指南

## 系统要求

- Python 3.9 或更高版本
- Windows 10/11 或 Linux
- 至少 2GB 可用磁盘空间
- 稳定的网络连接（用于访问数据源API）

## 快速安装

### Windows

1. 运行初始化脚本：
```bash
cd Ashare复盘multi-agents/next_day_expectation_agent
scripts\setup.bat
```

### 手动安装

1. 创建虚拟环境：
```bash
python -m venv venv
```

2. 激活虚拟环境：

Windows:
```bash
venv\Scripts\activate
```

Linux/Mac:
```bash
source venv/bin/activate
```

3. 安装依赖：
```bash
pip install -r requirements.txt
```

4. 复制配置文件模板：
```bash
cp config/system_config.yaml.template config/system_config.yaml
cp config/agent_config.yaml.template config/agent_config.yaml
cp config/data_source_config.yaml.template config/data_source_config.yaml
cp .env.example .env
```

5. 创建数据目录：
```bash
mkdir -p data/stage1_output
mkdir -p data/stage2_output
mkdir -p data/stage3_output
mkdir -p data/historical
mkdir -p data/logs
```

## 配置

### 1. 系统配置 (config/system_config.yaml)

编辑系统配置文件，设置：
- 数据存储路径
- 日志级别和格式
- 运行时间
- 推送配置
- 性能参数

### 2. Agent配置 (config/agent_config.yaml)

编辑Agent配置文件，设置：
- Stage1: 基因池筛选条件、技术指标参数
- Stage2: 基准预期计算参数、新题材关键词
- Stage3: 超预期分值权重、附加池筛选条件

### 3. 数据源配置 (config/data_source_config.yaml)

编辑数据源配置文件，设置：
- 数据源优先级
- Kaipanla API配置
- AKShare配置（包括代理设置）
- 东方财富API配置
- 新闻数据源配置

### 4. 环境变量 (.env)

编辑环境变量文件，设置：
- Gemini API密钥
- 数据源API密钥（如需要）
- 推送配置（企业微信、邮件）
- 代理配置（如需要）

## 验证安装

运行测试以验证安装：

```bash
pytest tests/
```

如果所有测试通过，说明安装成功。

## 常见问题

### 1. 依赖安装失败

如果遇到依赖安装问题，尝试：
```bash
pip install --upgrade pip
pip install -r requirements.txt --no-cache-dir
```

### 2. 导入模块错误

确保已激活虚拟环境，并且在项目根目录运行命令。

### 3. 配置文件找不到

确保已复制配置文件模板，并且文件名正确（去掉.template后缀）。

## 下一步

安装完成后，请参考：
- [配置说明](CONFIG.md) - 详细的配置指南
- [快速开始](../README.md#快速开始) - 运行系统
- [架构文档](ARCHITECTURE.md) - 了解系统架构
