# Binance Skills API 连接问题诊断

## 测试结果

### 网络连接测试 ❌

```bash
# 测试 Binance API
Test-NetConnection -ComputerName api.binance.com -Port 443

结果:
- PingSucceeded: False
- TcpTestSucceeded: False
- RemoteAddress: 31.13.96.193 (这实际上是 Facebook 的 IP)
```

### cURL 测试 ❌

```bash
# 测试 Binance 公共 API
curl --location "https://api.binance.com/api/v3/ticker/price?symbol=BTCUSDT" --max-time 10
错误: curl: (28) Connection timed out after 10001 milliseconds

# 测试 Google
curl -I https://www.google.com --max-time 5
错误: curl: (28) Connection timed out after 5001 milliseconds
```

## 问题分析

### 🔍 发现的问题

1. **DNS 解析错误**: `api.binance.com` 解析到了 `31.13.96.193`，这是 Facebook 的 IP 地址
2. **网络无法访问境外站点**: 即使配置了代理，系统层面可能仍然受限
3. **DNS 污染**: 可能存在 DNS 污染导致错误解析

### 正确的 Binance API 端点

根据官方文档，正确的端点应该是：
- 主网: `https://api.binance.com`
- 测试网: `https://testnet.binance.vision`
- Web3 API: `https://web3.binance.com` (可能需要特殊访问)

## 解决方案

### 方案 1: 配置 DNS

使用干净的 DNS 服务器：

```bash
# Windows PowerShell (管理员)
netsh interface ip set dns "WLAN" static 8.8.8.8
netsh interface ip add dns "WLAN" 8.8.4.4 index=2
```

### 方案 2: 配置系统代理

检查系统是否正确配置了代理：

```bash
# 查看当前代理设置
netsh winhttp show proxy

# 配置代理 (示例)
netsh winhttp set proxy proxy-server="http=127.0.0.1:7890;https=127.0.0.1:7890" bypass-list="localhost;127.0.0.1"
```

### 方案 3: 使用 HTTP_PROXY 环境变量

```bash
# PowerShell
$env:HTTP_PROXY="http://127.0.0.1:7890"
$env:HTTPS_PROXY="http://127.0.0.1:7890"
$env:NO_PROXY="localhost,127.0.0.1"
```

### 方案 4: 修改 hosts 文件

手动指定正确的 IP 地址：

```bash
# 获取正确 IP (可能需要使用代理工具)
# 然后添加到 C:\Windows\System32\drivers\etc\hosts

# 示例 (需要先获取正确 IP):
# 54.231.171.203 api.binance.com
# 54.231.171.203 web3.binance.com
```

### 方案 5: 使用第三方 API

如果无法访问 Binance 官方 API，可以考虑使用替代方案：

1. **CoinGecko API** (免费): `https://api.coingecko.com/api/v3`
2. **CoinMarketCap API** (有免费额度): `https://pro-api.coinmarketcap.com`
3. **DeFiPulse API**: `https://data-api.defipulse.com`

## 验证步骤

### 1. 验证 DNS 解析

```bash
# PowerShell
Resolve-DnsName api.binance.com
```

预期结果应该返回 Binance 的 CDN IP (如 AWS CloudFront)，而不是 Facebook 的 IP。

### 2. 验证代理设置

```bash
# PowerShell
netsh winhttp show proxy
```

### 3. 测试直连

如果代理配置正确，应该能够访问：

```bash
curl -v https://api.binance.com/api/v3/ping
```

预期响应:
```json
{}
```

## 临时解决方案

### 使用测试代码验证网络

创建测试脚本 `test_binance_api.py`:

```python
import requests
import os

# 配置代理 (如果需要)
proxies = {
    'http': 'http://127.0.0.1:7890',
    'https': 'http://127.0.0.1:7890'
}

# 测试 Binance 公共 API
try:
    response = requests.get(
        'https://api.binance.com/api/v3/ticker/price',
        params={'symbol': 'BTCUSDT'},
        proxies=proxies,
        timeout=10
    )
    print("API 测试成功!")
    print(response.json())
except Exception as e:
    print(f"API 测试失败: {e}")
```

运行:
```bash
python test_binance_api.py
```

## 总结

### 当前状态
- ❌ 技能配置文件已创建并启用
- ❌ 网络连接无法访问 Binance API
- ❌ 可能需要配置代理和 DNS

### 下一步
1. 配置正确的代理设置
2. 使用干净的 DNS (如 8.8.8.8)
3. 验证代理工具是否正在运行
4. 重新测试 API 连接

---

*诊断时间: 2026-03-05*
*问题类型: 网络连接问题 (DNS 污染/代理配置)*
