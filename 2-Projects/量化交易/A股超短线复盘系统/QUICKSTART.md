# A股超短线复盘系统 - 快速开始指南

## 📦 项目已完成

超短线复盘系统已创建完成，包含以下核心模块：

### 已创建的文件
```
A股超短线复盘系统/
├── README.md                    # 项目说明
├── INSTALL.md                   # 安装指南
├── PROJECT.md                   # 项目文档
├── QUICKSTART.md                # 快速开始（本文件）
├── requirements.txt             # 依赖包
├── main.py                      # 主程序
├── demo.py                      # 演示脚本 ✅
├── simple_test.py               # 简单测试
├── test_system.py               # 完整测试
├── config/
│   └── settings.py              # 配置文件
├── data/
│   ├── market_data_fetcher.py   # 市场数据获取
│   └── sector_data_fetcher.py   # 板块数据获取
├── analysis/
│   └── sentiment_analyzer.py    # 情绪分析
└── output/                      # 输出目录（自动生成）
    └── demo_report.html         # 演示报告 ✅
```

## 🚀 快速开始（3种方式）

### 方式1：查看演示报告（推荐新手）

```bash
# 运行演示脚本（已生成）
python demo.py
```

这会生成一个使用示例数据的HTML报告，让你了解系统功能。

**报告路径**: `output/demo_report.html`

### 方式2：安装Akshare后运行真实数据

```bash
# 1. 安装依赖
pip install akshare pandas matplotlib seaborn openpyxl requests numpy jinja2

# 2. 运行简单测试
python simple_test.py

# 3. 运行完整测试
python test_system.py
```

### 方式3：使用主程序生成报告

```python
from main import MasterReplaySystem

# 创建系统实例
system = MasterReplaySystem()

# 生成今日复盘报告
report_path = system.generate_report("2026-03-05")
print(f"Report: {report_path}")
```

## 📊 核心功能

### 1. 数据获取
- ✅ 市场数据：涨跌家数、涨停跌停
- ✅ 板块数据：概念板块、行业板块
- ✅ 个股数据：连板梯队、最高板

### 2. 情绪分析
- ✅ 大盘系数计算
- ✅ 超短情绪计算
- ✅ 亏钱效应计算
- ✅ 情绪周期判断（冰点/修复/分歧/高潮/震荡）

### 3. 报告生成
- ✅ HTML格式报告
- ✅ 美观的可视化展示
- ✅ 操作建议自动生成

## 🎯 示例数据报告

刚刚生成的演示报告显示：

**市场数据**:
- 上证指数: +1.25%
- 上涨家数: 4079
- 下跌家数: 1306
- 涨停数: 80
- 跌停数: 5

**情绪指标**:
- 大盘系数: 63.99 (震荡)
- 超短情绪: 213.50 (高)
- 亏钱效应: 55.00 (中等)

**情绪周期**: 震荡期
- 描述: 情绪平稳，缺乏方向，适合高抛低吸

## ⚠️ 重要提示

### Akshare使用要求
1. **禁用代理**: 系统会自动处理，无需手动设置
2. **频率限制**: 每次请求间隔2-5秒
3. **交易日**: 非交易日数据为空
4. **数据延迟**: 部分数据有15分钟延迟

### 数据限制
由于使用公开数据源：
- ❌ 炸板率需要估算（12%）
- ❌ 百日新高需要估算
- ❌ 历史连板数据不完整

**建议**: 如需更完整数据，可配合开盘啦API使用。

## 🔧 常见问题

### Q1: 运行报错 "No module named 'akshare'"
**A**: 需要安装akshare
```bash
pip install akshare
```

### Q2: 获取数据失败 "Connection aborted"
**A**: 检查网络连接，禁用代理，降低请求频率

### Q3: 数据为空
**A**: 确保在交易日运行，或使用演示数据

### Q4: 编码错误
**A**: 系统已自动设置UTF-8编码，如仍有问题请检查Python版本（需>=3.8）

## 📈 下一步

1. **查看演示报告**: 在浏览器中打开 `output/demo_report.html`
2. **安装Akshare**: 运行 `pip install -r requirements.txt`
3. **测试真实数据**: 运行 `python simple_test.py`
4. **生成复盘报告**: 运行 `python main.py` 或使用Python代码调用

## 💡 技术支持

- 查看完整文档: `PROJECT.md`
- 查看安装指南: `INSTALL.md`
- 查看项目说明: `README.md`

## 🎉 开始使用

```bash
# 1. 查看演示报告（立即可用）
python demo.py

# 2. 安装依赖（需要真实数据时）
pip install -r requirements.txt

# 3. 测试连接
python simple_test.py

# 4. 生成报告
python main.py
```

**提示**: 演示报告已经生成在 `output/demo_report.html`，可以直接在浏览器中打开查看！
