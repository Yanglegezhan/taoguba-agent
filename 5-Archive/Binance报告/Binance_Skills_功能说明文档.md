# Binance Skills 功能说明文档

## 技能概述

Binance Skills 提供了完整的加密货币数据查询和交易功能，包括：

- 代币信息查询
- 钱包余额查询
- 安全审计
- 市场排名
- Meme代币追踪
- 聪明钱信号
- 现货交易

## 技能列表

### 1. query-token-info (代币信息查询)

**功能**: 提供全面的代币信息，包括搜索、元数据、实时市场数据和K线图表。

#### API 1: 代币搜索
```python
# 示例请求
GET https://web3.binance.com/bapi/defi/v5/public/wallet-direct/buw/wallet/market/token/search
参数:
  - keyword: 比特币 (必需)
  - chainIds: 56,8453,CT_501 (可选)
  - orderBy: volume24h (可选)
```

**返回数据示例**:
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
      "holdersTop10Percent": "93.27",
      "links": [
        {"label": "website", "link": "https://bitcoin.org/"},
        {"label": "x", "link": "https://twitter.com/bitcoin"}
      ]
    }
  ],
  "success": true
}
```

#### API 2: 代币元数据
```python
# 示例请求
GET https://web3.binance.com/bapi/defi/v1/public/wallet-direct/buw/wallet/dex/market/token/meta/info
参数:
  - chainId: 56 (必需)
  - contractAddress: 0x55d398326f99059ff775485246999027b3197955 (必需)
```

**返回数据示例**:
```json
{
  "code": "000000",
  "data": {
    "tokenId": "CC1F457B",
    "name": "Binance USD",
    "symbol": "BUSD",
    "chainId": "56",
    "chainName": "BSC",
    "contractAddress": "0x55d398326f99059ff775485246999027b3197955",
    "decimals": 18,
    "icon": "/images/web3-data/public/token/logos/busd.png",
    "links": [
      {"label": "website", "link": "https://www.binance.com/"},
      {"label": "whitepaper", "link": "https://www.binance.com/resources/..."}
    ],
    "creatorAddress": "0x1234...",
    "description": "Binance USD (BUSD) is a stablecoin..."
  },
  "success": true
}
```

#### API 3: 代币动态数据
```python
# 示例请求
GET https://web3.binance.com/bapi/defi/v4/public/wallet-direct/buw/wallet/market/token/dynamic/info
参数:
  - chainId: 56 (必需)
  - contractAddress: 0x55d398326f99059ff775485246999027b3197955 (必需)
```

**返回数据示例**:
```json
{
  "code": "000000",
  "data": {
    "price": "48.006",
    "volume24h": "53803143.24",
    "volume24hBuy": "26880240.47",
    "volume24hSell": "26922902.76",
    "percentChange24h": "0.01",
    "marketCap": "162260777.94",
    "totalSupply": "3379998.56",
    "circulatingSupply": "3379998.25",
    "priceHigh24h": "48.595",
    "priceLow24h": "47.482",
    "holders": "78255",
    "liquidity": "13393863.15",
    "launchTime": 1600950241000,
    "top10HoldersPercentage": "93.26",
    "kolHolders": "17",
    "proHolders": "138"
  },
  "success": true
}
```

**关键字段说明**:
| 字段 | 类型 | 说明 |
|------|------|------|
| price | string | 当前价格(USD) |
| volume24h | string | 24小时交易量 |
| marketCap | string | 市值 |
| holders | string | 持有者数量 |
| liquidity | string | 流动性 |
| top10HoldersPercentage | string | 前10持有者占比 |

#### API 4: K线蜡烛图
```python
# 示例请求
GET https://dquery.sintral.io/u-kline/v1/k-line/candles
参数:
  - address: 0x55d398326f99059ff775485246999027b3197955 (必需)
  - platform: bsc (必需)
  - interval: 1h (必需)
  - limit: 100 (可选)
```

**返回数据示例**:
```json
{
  "data": [
    [0.10779318, 0.10779318, 0.10778039, 0.10778039, 2554.06, 1772125800000, 3],
    [0.10778039, 0.10781213, 0.10770104, 0.10770104, 2994.53, 1772125920000, 3]
  ],
  "status": {
    "timestamp": "2026-02-28T05:52:25.717Z",
    "error_code": "0",
    "error_message": "SUCCESS"
  }
}
```

**K线数据格式** (7个元素的数组):
| 索引 | 字段 | 类型 | 说明 |
|------|------|------|------|
| 0 | open | number | 开盘价 |
| 1 | high | number | 最高价 |
| 2 | low | number | 最低价 |
| 3 | close | number | 收盘价 |
| 4 | volume | number | 交易量 |
| 5 | timestamp | number | 时间戳(ms) |
| 6 | count | number | 交易数 |

### 2. query-address-info (钱包地址查询)

**功能**: 查询任何链上钱包地址的代币余额和持仓。

```python
# 示例请求
GET https://web3.binance.com/bapi/defi/v5/public/wallet-direct/buw/wallet/market/token/holdings
参数:
  - address: 0x1234567890abcdef1234567890abcdef12345678 (必需)
  - chainId: 56 (可选)
```

**返回数据示例**:
```json
{
  "code": "000000",
  "data": [
    {
      "tokenName": "Bitcoin",
      "tokenSymbol": "BTC",
      "tokenAddress": "0x55d398326f99059ff775485246999027b3197955",
      "chainId": "56",
      "balance": "0.25",
      "price": "47987.71",
      "priceChange24h": "2.34",
      "valueUSD": "11996.93"
    }
  ],
  "success": true
}
```

### 3. query-token-audit (代币安全审计)

**功能**: 检测代币是否为诈骗、蜜罐或恶意合约。

```python
# 示例请求
GET /token/audit?chainId=56&contractAddress=0x55d398326f99059ff775485246999027b3197955
```

**返回数据示例**:
```json
{
  "isHoneypot": false,
  "isBlacklisted": false,
  "scamScore": 5,
  "riskLevel": "low",
  "warnings": [],
  "buyTax": "0",
  "sellTax": "0",
  "liquidityLock": true
}
```

**风险等级**:
- **low**: 安全，可以交易
- **medium**: 中等风险，谨慎交易
- **high**: 高风险，避免交易
- **critical**: 极度危险，不要交易

### 4. crypto-market-rank (市场排名)

提供8种不同的市场排名：
- 趋势代币
- 热门搜索代币
- Binance Alpha代币
- 代币化股票
- 社交热度
- 聪明钱流入
- Meme代币排名
- 交易者PnL排行榜

### 5. meme-rush (Meme代币助手)

提供两类信息：
- **Meme Rush**: Pump.fun、Four.meme等launchpad上的实时meme代币
- **Topic Rush**: AI驱动的市场热点话题和相关代币

### 6. trading-signal (聪明钱信号)

监控聪明钱地址的交易活动，提供：
- 买卖信号
- 触发价格
- 当前价格
- 最大收益
- 退出率
- 信心分数

### 7. spot (现货交易)

Binance现货交易功能，需要API密钥认证。

---

## 使用建议

### 常见查询模式

1. **查询代币基本信息**
   ```
   /搜索比特币
   /获取ETH的详情
   /查询BUSD的价格
   ```

2. **查看钱包资产**
   ```
   /查询地址0x123...的持仓
   /显示我的钱包余额
   ```

3. **安全检查**
   ```
   /审计这个代币：0x55d398326...
   /检查合约安全性
   ```

4. **技术分析**
   ```
   /获取BTC的1小时K线
   /显示最近24小时的价格走势
   /查看5分钟级别的蜡烛图
   ```

5. **市场研究**
   ```
   /显示当前最热门的代币
   /获取聪明钱流入最多的项目
   /查看最新的meme代币
   ```

---

## 技术细节

### 支持的链

| 链名称 | chainId | platform |
|--------|---------|----------|
| BSC | 56 | bsc |
| Base | 8453 | base |
| Solana | CT_501 | solana |

### 数据格式

- 所有数值字段返回为 **string** 类型
- 时间戳单位：**毫秒**
- 价格单位：**USD**
- Icon URL 需要拼接前缀：`https://bin.bnbstatic.com` + icon路径

### 请求头

所有API都需要：
```
Accept-Encoding: identity
```

---

*文档版本: 1.0*
*最后更新: 2026-03-05*
