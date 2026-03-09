# 快速开始：使用 pywencai 获取同花顺热门股

## 3 步快速启用

### 步骤 1: 安装 pywencai

```bash
pip install pywencai
```

### 步骤 2: 测试功能

```bash
python test_wencai_hot_stocks.py
```

预期输出：
```
============================================================
测试1: 检查 pywencai 是否已安装
============================================================
✓ pywencai 已安装

============================================================
测试2: 初始化 WencaiClient
============================================================
✓ WencaiClient 初始化成功

============================================================
测试3: 获取同花顺热门股前20
============================================================
✓ 成功获取 20 只热门股

前10名热门股:
  1. 汉缆股份
  2. *ST立方
  3. 华胜天成
  ...
```

### 步骤 3: 在项目中使用

无需修改代码！系统会自动启用问财作为备选数据源。

如果想优先使用问财（速度更快），可以修改配置：

```python
from stage1.gene_pool_builder import GenePoolBuilder

# 问财优先模式
builder = GenePoolBuilder(config={
    'use_wencai': True,
    'wencai_fallback': True
})

# 构建基因池
gene_pool = builder.build_gene_pool(date="2026-02-13")
```

## 完成！

现在你的系统已经支持：
- ✓ 更快的数据获取速度（2-5秒 vs 15-30秒）
- ✓ 更高的稳定性（自动切换数据源）
- ✓ 更完整的数据（包含股票代码）

## 详细文档

- 安装说明：`INSTALL_WENCAI.md`
- 集成文档：`WENCAI_INTEGRATION.md`
- 改进总结：`WENCAI_IMPROVEMENT_SUMMARY.md`

## 常见问题

**Q: 如果不安装 pywencai 会怎样？**  
A: 系统会继续使用 kaipanla（原有方式），不影响功能。

**Q: 两个数据源有什么区别？**  
A: Pywencai 更快更稳定，Kaipanla 数据更准确。系统会智能选择。

**Q: 如何禁用问财？**  
A: 不安装 pywencai，或设置 `config={'wencai_fallback': False}`

**Q: 遇到问题怎么办？**  
A: 查看日志输出，或参考 `INSTALL_WENCAI.md` 的故障排查部分。
