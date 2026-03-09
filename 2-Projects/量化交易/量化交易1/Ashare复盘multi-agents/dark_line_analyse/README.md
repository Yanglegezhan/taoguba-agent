# 涨停题材暗线挖掘智能体

一个基于统计学分析和命名语义分析，识别A股涨停池中隐藏题材"暗线"的智能体。

## 核心功能

### 1. 共性挖掘

- **地域集聚分析**：识别某省份/区域股票涨停频率是否显著高于市场基准
- **企业性质分析**：分析央企/国企/民企的涨停分布差异
- **估值特征分析**：分析PB、市值、股价区间的分布特征
- **盘面特征分析**：分析连板高度、融资融券、可转债等属性分布

### 2. 命名语义分析

- **吉祥命名**：识别"东方、数字、龙凤"等字眼的聚集
- **相似命名**：识别高相似度股票名称，暗示关联性
- **前缀模式**：识别"中字头、国字号"等命名模式

### 3. 暗线识别

基于多维度交叉验证，识别以下暗线类型：
- 地域集聚型（如浙江地域政策）
- 企业性质主题型（如央企重组预期）
- PB价值主题型（如破净修复）
- 命名模式型（如东方系、数字股）
- 技术形态型（如强势连板梯队）

### 4. LLM 解读

使用大语言模型对识别出的暗线进行深度解读，包括：
- 题材性质判断（事件驱动/政策驱动/情绪驱动/资金驱动）
- 持续性判断（短期/中期/长期）
- 关键驱动因素
- 风险提示
- 操作建议

## 安装

```bash
# 安装依赖
pip install -r requirements.txt
```

或单独安装：
```bash
pip install pandas numpy pydantic pyyaml tushare akshare requests python-dateutil zhipuai
```

## 配置

复制 `config/config.example.yaml` 为 `config/config.yaml` 并修改配置：

```yaml
llm:
  provider: "zhipu"              # zhipu / openai / deepseek
  api_key: "your_api_key"        # 必填：LLM API密钥
  model_name: "glm-4-flash"      # 推荐使用 glm-4-flash
  temperature: 0.7

data_source:
  tushare:
    api_token: "your_tushare_token"  # 可选：用于获取基础信息（需要2000积分）
    
analysis:
  lift_ratio_threshold: 2.0      # 提升倍数阈值
  min_sample_size: 3            # 最小样本量
```

## 使用方法

### 方式一：命令行接口（推荐）

```bash
# 分析今天
dark_line_cli.bat

# 分析指定日期
dark_line_cli.bat --date 2026-02-05

# 分析昨天
dark_line_cli.bat --yesterday

# 指定输出格式
dark_line_cli.bat --format json

# 指定配置文件
dark_line_cli.bat --config /path/to/config.yaml

# 不保存报告
dark_line_cli.bat --no-save
```

### 方式二：Python 脚本

```bash
# 使用 run_analysis.py
python run_analysis.py
```

或在代码中调用：

```python
from src.agent import DarkLineAgent
from config.config_manager import ConfigManager

# 初始化
config = ConfigManager()
agent = DarkLineAgent(config)

# 执行分析
result = agent.analyze(date="2026-02-05")

# 获取暗线列表
for dark_line in result.dark_lines:
    print(f"{dark_line.title}: 置信度 {dark_line.confidence:.2f}")
```

### 方式三：查看个股详情

```bash
# 查看涨停个股列表及市值
python show_stocks.py
```

## 数据源说明

系统采用多数据源智能切换策略，确保数据完整性和准确性：

### 主要数据源

1. **AKShare（主力）**
   - 涨停个股列表（完整数据，包括首板和连板）
   - 市值数据（总市值、流通市值）
   - 融资融券标的
   - 概念板块、行业板块
   - **优势**：免费、数据完整、实时性好

2. **TuShare（辅助）**
   - 股票基础信息（注册地、行业、上市日期等）
   - 企业性质判断
   - 财务指标（PB、PE等）
   - **要求**：需要2000积分，可选配置

3. **开盘啦（备用）**
   - 实时涨停数据
   - 连板梯队信息
   - **用途**：当 AKShare 失败时的降级方案

### 数据获取优先级

- **涨停列表**：AKShare → 开盘啦实时接口 → 开盘啦历史接口
- **市值数据**：AKShare 直接提供（最准确）
- **融资融券**：AKShare（免费完整数据）
- **基础信息**：TuShare（如配置）→ AKShare 简化版

## 输出格式

报告保存在 `output/reports/` 目录：

- **JSON**：`dark_line_analysis_YYYYMMDD.json` - 结构化数据，适合程序处理
- **Markdown**：`dark_line_analysis_YYYYMMDD.md` - 格式化报告，适合阅读

报告包含：
1. 涨停个股统计（总数、连板分布、市值分布）
2. 统计学特征分析（地域、企业性质、估值、盘面特征）
3. 命名语义特征（吉祥命名、相似命名、前缀模式）
4. 暗线检测结果（类型、置信度、证据链）
5. LLM 深度解读（题材性质、持续性、驱动因素、风险、建议）

## 项目结构

```
dark_line_analyse/
├── config/                    # 配置文件
│   ├── config.yaml           # 主配置（需自行创建）
│   └── config.example.yaml   # 配置模板
├── src/
│   ├── data/                 # 数据获取层
│   │   ├── kaipanla_source.py      # 开盘啦数据源（集成AKShare）
│   │   ├── tushare_source.py       # TuShare数据源
│   │   ├── akshare_source.py       # AKShare数据源
│   │   └── data_source_adapter.py  # 数据源适配器
│   ├── analysis/             # 分析层
│   │   ├── statistical_analyzer.py # 统计分析
│   │   ├── naming_analyzer.py      # 命名分析
│   │   └── dark_line_detector.py   # 暗线检测
│   ├── llm/                  # LLM 层
│   │   └── llm_analyzer.py         # LLM解读
│   ├── models/               # 数据模型
│   │   └── data_models.py          # Pydantic模型
│   ├── output/               # 输出层
│   │   └── report_generator.py     # 报告生成
│   └── agent.py              # 主 Agent
├── prompts/                   # 提示词模板
│   └── dark_line_analysis.md # LLM分析提示词
├── output/reports/           # 报告输出目录
├── logs/                     # 日志目录
├── examples/                 # 示例文件
├── dark_line_cli.py          # CLI 入口
├── dark_line_cli.bat         # Windows批处理
├── run_analysis.py           # 简化运行脚本
├── show_stocks.py            # 查看个股详情
├── requirements.txt          # 依赖包
├── 快速开始.md               # 快速入门指南
├── LLM分析功能说明.md        # LLM功能详解
└── 更新日志.md               # 版本更新记录
```

## 快速开始

1. **安装依赖**
   ```bash
   pip install -r requirements.txt
   ```

2. **配置 API**
   - 复制 `config/config.example.yaml` 为 `config/config.yaml`
   - 填写 LLM API Key（必填）
   - 填写 TuShare Token（可选，用于更详细的基础信息）

3. **运行分析**
   ```bash
   # Windows
   dark_line_cli.bat --date 2026-02-05
   
   # 或使用 Python
   python run_analysis.py
   ```

4. **查看报告**
   - 报告位于 `output/reports/` 目录
   - Markdown 格式适合直接阅读
   - JSON 格式适合程序处理

## 注意事项

1. **必需配置**
   - LLM API Key（智谱AI、OpenAI 或 DeepSeek）

2. **可选配置**
   - TuShare Token（2000积分）：提供更详细的基础信息
   - 不配置 TuShare 也能正常运行，使用 AKShare 简化版数据

3. **网络要求**
   - 需要访问 AKShare 数据接口（东方财富）
   - 需要访问 LLM API

4. **日期选择**
   - 建议选择交易日
   - 非交易日可能无涨停数据

5. **数据完整性**
   - AKShare 提供完整的涨停数据（44只，包括首板和连板）
   - 市值数据直接来自 AKShare，准确可靠
   - 融资融券数据使用 AKShare 免费接口

## 更新日志

### v2.0 (2026-02-06)
- ✅ 数据源全面升级：使用 AKShare 作为主力数据源
- ✅ 涨停数据完整性：获取全部涨停个股（包括首板和连板）
- ✅ 市值数据准确性：直接使用 AKShare 提供的市值数据
- ✅ 融资融券优化：改用 AKShare 免费接口，无需权限
- ✅ 智能数据源切换：AKShare → 开盘啦 → TuShare 多级降级
- ✅ 代码清理：删除临时测试文件和文档

### v1.0
- 基础功能实现
- 统计分析、命名分析、暗线检测
- LLM 深度解读

## 常见问题

**Q: 为什么涨停个股数量比预期少？**  
A: 已修复！现在使用 AKShare 获取完整数据，包括所有首板和连板股票。

**Q: 市值数据不准确？**  
A: 已修复！现在直接使用 AKShare 提供的准确市值数据（总市值和流通市值）。

**Q: 融资融券标的获取失败？**  
A: 已修复！现在使用 AKShare 免费接口，无需 TuShare 权限。

**Q: 需要 TuShare 2000积分吗？**  
A: 不是必需的。TuShare 仅用于获取更详细的基础信息（注册地、企业性质等），不配置也能正常运行。

**Q: LLM 解析失败？**  
A: 已修复！优化了 Prompt 模板和 JSON 解析逻辑，确保稳定性。

## License

MIT License

## 贡献

欢迎提交 Issue 和 Pull Request！

## 联系方式

如有问题或建议，请提交 Issue。
