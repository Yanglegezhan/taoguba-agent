# Binance Skills 测试报告

> 测试时间: 2026-03-05
> 测试技能: query-token-info

---

## 测试环境

- **技能目录**: `~/.claude/skills/binance-web3/query-token-info/`
- **配置状态**: ✅ 已启用
- **API端点**: `https://web3.binance.com/bapi/defi/v5/public/wallet-direct/buw/wallet/market/token/search`

---

## 测试结果

### 🔴 网络连接问题

在测试 API 端点时遇到连接问题：

```bash
curl --location "https://web3.binance.com/bapi/defi/v5/public/wallet-direct/buw/wallet/market/token/search?keyword=bitcoin&chainIds=56" --header "Accept-Encoding: identity"
```

**错误信息**:
```
curl: (28) Failed to connect to web3.binance.com port 443 after 21061 ms: Could not connect to server
```

或

```
curl: (35) Recv failure: Connection was reset
```

### 可能原因

1. **网络限制**: 本地网络可能限制访问境外站点
2. **域名解析**: `web3.binance.com` 可能需要特殊DNS配置
3. **防火墙**: 本地防火墙或企业网络策略可能阻止连接
4. **API变更**: Binance API端点可能已更新

---

## 技能配置验证 ✅

### 技能文件结构
```
~/.claude/skills/binance-web3/query-token-info/
└── SKILL.md (已创建)
```

### 配置文件验证
```
~/.claude/settings.local.json
{
  "skills": {
    "binance-web3/query-token-info": {
      "enabled": true  ✅
    }
  }
}
```

### 技能文档内容 ✅

技能包含完整的API文档：

#### 1. 代币搜索 (Token Search)
- **端点**: `GET /bapi/defi/v5/public/wallet-direct/buw/wallet/market/token/search`
- **参数**:
  - `keyword` (必需): 搜索关键词
  - `chainIds` (可选): 链ID (56=BSC, 8453=Base, CT_501=Solana)
  - `orderBy` (可选): 排序字段

#### 2. 代币元数据 (Token Metadata)
- **端点**: `GET /bapi/defi/v1/public/wallet-direct/buw/wallet/dex/market/token/meta/info`
- **参数**: `chainId`, `contractAddress`

#### 3. 代币动态数据 (Token Dynamic Data)
- **端点**: `GET /bapi/defi/v4/public/wallet-direct/buw/wallet/market/token/dynamic/info`
- **参数**: `chainId`, `contractAddress`

#### 4. K线蜡烛图 (Token K-Line)
- **端点**: `GET /u-kline/v1/k-line/candles`
- **参数**: `address`, `platform`, `interval`

---

## 解决方案

### 方案 1: 检查网络连接

```bash
# 测试基本网络连接
ping www.binance.com

# 测试 HTTPS 连接
curl -I https://www.binance.com

# 测试特定端点
curl -I https://web3.binance.com
```

### 方案 2: 使用代理或VPN

如果网络受限，配置代理：

```bash
# Windows PowerShell
$env:HTTPS_PROXY="http://proxy-server:port"
$env:HTTP_PROXY="http://proxy-server:port"
```

### 方案 3: 更新API端点

根据Binance官方文档验证正确的API端点：

- 访问: https://binance-docs.github.io/apidocs/
- 查找最新的 Web3 API 文档
- 更新技能中的URL

### 方案 4: 本地测试

创建测试脚本来验证技能配置：

```python
import os
import json

# 检查技能配置
skills_dir = os.path.expanduser("~/.claude/skills/binance-web3/query-token-info")
config_file = os.path.expanduser("~/.claude/settings.local.json")

print(f"技能目录存在: {os.path.exists(skills_dir)}")
print(f"配置文件存在: {os.path.exists(config_file)}")

if os.path.exists(config_file):
    with open(config_file, 'r', encoding='utf-8') as f:
        config = json.load(f)
        enabled = config.get('skills', {}).get('binance-web3/query-token-info', {}).get('enabled', False)
        print(f"技能已启用: {enabled}")
```

---

## 建议的后续步骤

1. **网络诊断**: 检查本地网络是否能够访问 Binance 域名
2. **API验证**: 访问 Binance 官方文档确认API端点是否正确
3. **代理配置**: 如有需要，配置网络代理
4. **功能测试**: 网络正常后，使用实际代币查询测试完整功能

---

## 技能已就绪 ✅

虽然API连接测试失败（可能是网络问题），但技能配置本身已完成：

- ✅ 技能文件已创建
- ✅ 配置已启用
- ✅ 文档完整
- ⚠️ 等待网络连接恢复后进行完整功能测试

---

*报告生成时间: 2026-03-05*
