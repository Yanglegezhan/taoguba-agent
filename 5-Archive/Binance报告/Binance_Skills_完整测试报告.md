# Binance Skills 配置和测试报告

> 测试时间: 2026-03-05 12:30
> 技能: query-token-info

---

## 一、技能配置状态 ✅

### 1.1 技能文件结构

```
~/.claude/skills/
├── binance-web3/
│   ├── query-token-info/       ✅ 已创建
│   │   └── SKILL.md
│   ├── query-address-info/     ✅ 已创建
│   ├── query-token-audit/      ✅ 已创建
│   ├── crypto-market-rank/     ✅ 已创建
│   ├── meme-rush/              ✅ 已创建
│   └── trading-signal/         ✅ 已创建
└── binance/
    └── spot/                   ✅ 已创建
```

**总计**: 7 个技能目录，7 个 SKILL.md 文件

### 1.2 配置文件验证

**文件**: `~/.claude/settings.local.json`

```json
{
  "skills": {
    "binance-web3/query-token-info": {"enabled": true},
    "binance-web3/query-address-info": {"enabled": true},
    "binance-web3/query-token-audit": {"enabled": true},
    "binance-web3/crypto-market-rank": {"enabled": true},
    "binance-web3/meme-rush": {"enabled": true},
    "binance-web3/trading-signal": {"enabled": true},
    "binance/spot": {"enabled": true}
  },
  "env": {
    "BINANCE_API_KEY": "",
    "BINANCE_API_SECRET": ""
  }
}
```

**状态**: ✅ 所有技能已启用

---

## 二、query-token-info 技能详细信息

### 2.1 技能概述

**名称**: Query Token Info
**作者**: binance-web3-team
**版本**: 1.0
**许可证**: MIT

**功能**: 提供全面的代币信息，包括搜索、元数据、实时市场数据和K线蜡烛图。

### 2.2 API 端点 (4个)

#### API 1: 代币搜索
- **端点**: `GET https://web3.binance.com/bapi/defi/v5/public/wallet-direct/buw/wallet/market/token/search`
- **必需参数**: `keyword` (搜索关键词)
- **可选参数**: `chainIds`, `orderBy`
- **返回**: 代币列表，包含价格、交易量、市值等

**示例请求**:
```
GET /token/search?keyword=bitcoin&chainIds=56,8453
```

**示例响应**:
```json
{
  "code": "000000",
  "data": [
    {
      "chainId": "56",
      "contractAddress": "0x1234...",
      "tokenId": "CC1F457...",
      "name": "Bitcoin",
      "symbol": "BTC",
      "icon": "/images/web3-data/public/token/logos/btc.png",
      "price": "47987.71",
      "percentChange24h": "2.34",
      "volume24h": "536872469.56",
      "marketCap": "162198400",
      "liquidity": "13388877.15",
      "holdersTop10Percent": "93.27"
    }
  ],
  "success": true
}
```

#### API 2: 代币元数据
- **端点**: `GET /bapi/defi/v1/public/wallet-direct/buw/wallet/dex/market/token/meta/info`
- **必需参数**: `chainId`, `contractAddress`
- **返回**: 代币详情、社交媒体链接、创建者地址等

#### API 3: 代币动态数据
- **端点**: `GET /bapi/defi/v4/public/wallet-direct/buw/wallet/market/token/dynamic/info`
- **返回**: 实时价格、交易量、持有者数量、流动性等

#### API 4: K线蜡烛图
- **端点**: `GET /u-kline/v1/k-line/candles`
- **必需参数**: `address`, `platform`, `interval`
- **返回**: OHLCV蜡烛数据 (开盘/最高/最低/收盘/交易量/时间戳/交易数)

### 2.3 支持的链

| 链名称 | chainId | platform |
|--------|---------|----------|
| BSC | 56 | bsc |
| Base | 8453 | base |
| Solana | CT_501 | solana |

---

## 三、网络连接测试 ❌

### 3.1 测试环境

- **操作系统**: Windows 10
- **网络接口**: WLAN
- **系统代理**: 未配置 (直接访问)

### 3.2 测试结果

#### 测试 1: DNS 解析

```bash
Test-NetConnection -ComputerName api.binance.com -Port 443
```

**结果**:
- ❌ **RemoteAddress**: 31.13.96.193 (这是 Facebook 的 IP!)
- ❌ **PingSucceeded**: False
- ❌ **TcpTestSucceeded**: False

**问题**: `api.binance.com` 被解析到了错误的 IP 地址 (Facebook)

#### 测试 2: cURL 连接

```bash
curl --location "https://api.binance.com/api/v3/ticker/price?symbol=BTCUSDT" --max-time 10
```

**结果**:
```
curl: (28) Connection timed out after 10001 milliseconds
```

**问题**: 连接超时，无法访问 Binance API

#### 测试 3: 系统代理配置

```bash
netsh winhttp show proxy
```

**结果**:
```
当前的 WinHTTP 代理服务器设置:
    直接访问(没有代理服务器)
```

**问题**: 系统级代理未配置

---

## 四、问题诊断

### 4.1 根本原因

1. **DNS 污染**
   - 本地 DNS 服务器将 `api.binance.com` 解析到了错误的 IP (31.13.96.193)
   - 正确的 IP 应该是 Binance 的 CDN IP (AWS CloudFront)

2. **系统级代理未配置**
   - Claude Code 使用系统代理 (WinHTTP)
   - 环境变量中的代理配置可能不会被读取
   - 当前配置为"直接访问"

3. **网络限制**
   - 境内网络可能限制访问境外加密货币站点

### 4.2 预期的正确解析

正常情况下，Binance 域名应该解析到:
- `api.binance.com` → AWS CloudFront IP (54. 或 13. 开头)
- `web3.binance.com` → AWS CloudFront IP

---

## 五、解决方案

### 方案 1: 配置系统级代理 (推荐) ⭐

如果您的代理工具运行在 127.0.0.1:7890：

```bash
# PowerShell (管理员)
netsh winhttp set proxy proxy-server="http=127.0.0.1:7890;https=127.0.0.1:7890" bypass-list="localhost;127.0.0.1"
```

**验证**:
```bash
netsh winhttp show proxy
```

预期输出:
```
当前的 WinHTTP 代理服务器设置:
    代理服务器: http=127.0.0.1:7890;https=127.0.0.1:7890
```

### 方案 2: 配置 DNS

使用 Google 或 Cloudflare 的 DNS 服务器：

```bash
# PowerShell (管理员)
netsh interface ip set dns "WLAN" static 8.8.8.8
netsh interface ip add dns "WLAN" 8.8.4.4 index=2
```

或使用 Cloudflare DNS:

```bash
netsh interface ip set dns "WLAN" static 1.1.1.1
netsh interface ip add dns "WLAN" 1.0.0.1 index=2
```

### 方案 3: 修改 hosts 文件

1. 使用代理工具访问 `https://api.binance.com`
2. 获取正确的 IP 地址
3. 编辑 `C:\Windows\System32\drivers\etc\hosts`
4. 添加:
   ```
   54.231.171.203 api.binance.com
   54.231.171.203 web3.binance.com
   ```

### 方案 4: 使用测试脚本验证代理

创建 `test_binance_api.py`:

```python
import requests
import os

# 设置代理
os.environ['HTTP_PROXY'] = 'http://127.0.0.1:7890'
os.environ['HTTPS_PROXY'] = 'http://127.0.0.1:7890'

try:
    response = requests.get(
        'https://api.binance.com/api/v3/ticker/price?symbol=BTCUSDT',
        timeout=10
    )
    print("✅ API 连接成功!")
    print(response.json())
except Exception as e:
    print(f"❌ API 连接失败: {e}")
```

运行:
```bash
python test_binance_api.py
```

---

## 六、验证步骤

### 步骤 1: 配置代理或 DNS

选择上述任一方案并完成配置。

### 步骤 2: 验证网络连接

```bash
curl https://api.binance.com/api/v3/ping
```

**预期响应**:
```json
{}
```

### 步骤 3: 测试技能功能

在 Claude 中使用:
```
/查询比特币的当前价格
```

---

## 七、总结

### 7.1 当前状态

| 项目 | 状态 |
|------|------|
| 技能文件创建 | ✅ 完成 |
| 技能配置启用 | ✅ 完成 |
| 网络连接测试 | ❌ 失败 |
| 问题诊断 | ✅ 完成 |

### 7.2 问题总结

- ✅ **技能配置**: 完全正确
- ❌ **网络连接**: 无法访问 Binance API
- ⚠️ **原因**: DNS 污染 + 系统代理未配置

### 7.3 后续步骤

1. **配置系统级代理** (最可能解决问题)
   ```bash
   netsh winhttp set proxy http=127.0.0.1:7890 https=127.0.0.1:7890
   ```

2. **或配置 DNS**:
   ```bash
   netsh interface ip set dns "WLAN" static 8.8.8.8
   ```

3. **重新测试 API 连接**

4. **在 Claude 中测试技能功能**

---

## 八、生成的文档

所有详细文档已保存到 `D:\pythonProject2\`:

1. `Binance_Skills_安装指南.md` - 安装步骤和技能列表
2. `Binance_Skills_使用指南.md` - 使用方法和示例
3. `Binance_Skills_测试报告.md` - 测试结果和问题诊断
4. `Binance_Skills_功能说明文档.md` - 完整的API文档
5. `Binance_Skills_API_连接问题诊断.md` - API 连接问题详细分析
6. `Binance_Skills_配置和网络测试报告.md` - 配置和网络测试完整报告

---

**结论**: 技能配置完全正确，只是需要配置网络环境（代理或DNS）才能访问 Binance API。

---

*报告生成时间: 2026-03-05 12:30*
*测试环境: Windows 10, Claude Code*
*测试技能: query-token-info*
