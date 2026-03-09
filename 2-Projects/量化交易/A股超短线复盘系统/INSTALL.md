# 安装指南

## 快速安装

```bash
# 安装依赖
pip install -r requirements.txt

# 或单独安装
pip install akshare pandas matplotlib seaborn openpyxl requests numpy jinja2
```

## Akshare注意事项

### 1. 禁用代理
Akshare要求禁用代理，否则会报错。系统会自动处理，但如果你设置了系统代理，请确保：

```python
import os
os.environ['NO_PROXY'] = '*'
os.environ['no_proxy'] = '*'
```

### 2. 频率限制
Akshare有频率限制，建议：
- 每次请求间隔2-5秒
- 避免高频并发请求
- 使用缓存机制

### 3. 数据完整性
Akshare的部分数据可能不完整：
- 历史连板数据：建议配合开盘啦使用
- 炸板数据：需要估算
- 北向资金：Akshare暂不提供

### 4. 常见问题

#### Q: Connection aborted错误
A: 禁用代理，检查网络连接，降低请求频率

#### Q: 数据为空
A: 可能是非交易日，或接口暂时不可用，稍后再试

#### Q: 编码错误
A: 确保Python版本>=3.8，系统支持UTF-8编码

## 测试安装

```bash
# 测试Akshare是否正常
python -c "import akshare; print(akshare.__version__)"

# 运行简单测试
python simple_test.py
```

## 开始使用

```python
from main import MasterReplaySystem

system = MasterReplaySystem()
report_path = system.generate_report()  # 生成今日报告
print(f"Report: {report_path}")
```
