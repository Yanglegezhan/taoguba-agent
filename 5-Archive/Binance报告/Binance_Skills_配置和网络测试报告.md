# Binance Skills 配置和网络测试报告

## 1. 技能配置状态 ✅

### 已安装的技能 (7个)

| 技能名称 | 状态 | 路径 |
|---------|------|------|
| query-token-info | ✅ 已启用 | `~/.claude/skills/binance-web3/query-token-info/` |
| query-address-info | ✅ 已启用 | `~/.claude/skills/binance-web3/query-address-info/` |
| query-token-audit | ✅ 已启用 | `~/.claude/skills/binance-web3/query-token-audit/` |
| crypto-market-rank | ✅ 已启用 | `~/.claude/skills/binance-web3/crypto-market-rank/` |
| meme-rush | ✅ 已启用 | `~/.claude/skills/binance-web3/meme-rush/` |
| trading-signal | ✅ 已启用 | `~/.claude/skills/binance-web3/trading-signal/` |
| spot | ✅ 已启用 | `~/.claude/skills/binance/spot/` |

### 配置文件

```json
// ~/.claude/settings.local.json
{
  "skills": {
    "binance-web3/query-token-info": {"enabled": true},
    "binance-web3/query-address-info": {"enabled": true},
    ...
  },
  "env": {
    "BINANCE_API_KEY": "",
    "BINANCE_API_SECRET": ""
  }
}
```

---

## 2. 网络连接测试 ❌

### 测试 1: DNS 解析问题

```bash
Test-NetConnection -ComputerName api.binance.com -Port 443

结果:
- RemoteAddress: 31.13.96.193  ← 这是 Facebook 的 IP！
- PingSucceeded: False
- TcpTestSucceeded: False
```

**问题**: `api.binance.com` 被解析到了错误的 IP 地址 (Facebook)

### 测试 2: cURL 连接超时

```bash
curl --location "https://api.binance.com/api/v3/ticker/price?symbol=BTCUSDT" --max-time 10

结果:
curl: (28) Connection timed out after 10001 milliseconds
```

### 测试 3: 系统代理配置

```bash
netsh winhttp show proxy

结果:
直接访问(没有代理服务器)
```

---

## 3. 问题诊断

### 根本原因

1. **DNS 污染**: 你的本地 DNS 服务器将 `api.binance.com` 解析到了错误的 IP
2. **无系统代理**: 系统层面没有配置代理，即使有代理工具也可能无法工作
3. **网络限制**: 境内网络可能限制访问境外加密货币站点

### 预期的正确解析

正常情况下，`api.binance.com` 应该解析到 Binance 的 CDN IP (AWS CloudFront):
- IP 范围: 通常以 54. 开头或 13. 开头的 AWS IP

---

## 4. 解决方案

### 方案 A: 配置系统级代理 (推荐)

如果使用代理工具（如 Clash、Surge 等），需要配置系统代理：

```bash
# 配置 WinHTTP 代理 (PowerShell 管理员)
netsh winhttp set proxy proxy-server="http=127.0.0.1:7890;https=127.0.0.1:7890" bypass-list="localhost;127.0.0.1"

# 验证
netsh winhttp show proxy
```

### 方案 B: 配置 DNS

使用可靠的 DNS 服务器：

```bash
# PowerShell 管理员
netsh interface ip set dns "WLAN" static 8.8.8.8
netsh interface ip add dns "WLAN" 8.8.4.4 index=2

# 或使用 Cloudflare DNS
netsh interface ip set dns "WLAN" static 1.1.1.1
netsh interface ip add dns "WLAN" 1.0.0.1 index=2
```

### 方案 C: 修改 hosts 文件

手动指定正确的 IP：

1. 使用代理工具访问 `api.binance.com` 并获取正确的 IP
2. 编辑 `C:\Windows\System32\drivers\etc\hosts`
3. 添加:
   ```
   54.231.171.203 api.binance.com
   54.231.171.203 web3.binance.com
   ```

### 方案 D: 在代码中配置代理

创建测试脚本验证代理配置：

```python
# test_proxy.py
import requests
import os

# 设置代理
os.environ['HTTP_PROXY'] = 'http://127.0.0.1:7890'
os.environ['HTTPS_PROXY'] = 'http://127.0.0.1:7890'

try:
    response = requests.get('https://api.binance.com/api/v3/ticker/price?symbol=BTCUSDT', timeout=10)
    print("✅ 连接成功!")
    print(response.json())
except Exception as e:
    print(f"❌ 连接失败: {e}")
```

运行测试:
```bash
python test_proxy.py
```

---

## 5. 验证步骤

### 步骤 1: 检查代理工具
确保你的代理工具（如 Clash、V2Ray 等）正在运行

### 步骤 2: 配置系统代理
```bash
netsh winhttp set proxy http=127.0.0.1:7890 https=127.0.0.1:7890
```

### 步骤 3: 测试连接
```bash
curl https://api.binance.com/api/v3/ping
```

预期响应:
```json
{}
```

### 步骤 4: 测试技能
在 Claude 中使用:
```
/查询比特币的价格
```

---

## 6. 总结

### 当前状态
- ✅ 技能文件: 已创建，配置正确
- ✅ 技能启用: 所有技能已启用
- ❌ 网络连接: 无法访问 Binance API
- ⚠️ 问题: DNS 污染 + 无系统代理配置

### 需要的操作
1. **确认代理工具正在运行**
2. **配置系统级代理** (`netsh winhttp set proxy`)
3. **或配置 DNS** (使用 8.8.8.8 或 1.1.1.1)
4. **重新测试 API 连接**

### 备注
技能配置本身没有问题，只是网络环境限制了对 Binance API 的访问。配置好代理或 DNS 后，技能应该可以正常工作。

---

*报告生成时间: 2026-03-05 12:30*
*测试环境: Windows 10, Claude Code*
