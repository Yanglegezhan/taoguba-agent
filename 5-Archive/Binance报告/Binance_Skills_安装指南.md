# Binance Skills 安装指南

> 获取自 https://developers.binance.com/en/skills
> 日期: 2026-03-05

---

## 可用的 Binance Skills

### 🟢 binance-web3 (6个技能)

| 技能名称 | 功能描述 | 使用场景 |
|---------|---------|---------|
| **crypto-market-rank** | Crypto市场排名和排行榜。查询趋势代币、热门搜索代币、Binance Alpha代币、代币化股票、社交热度情绪排名、聪明钱流入代币排名、Pulse launchpad顶级meme代币排名、顶级交易者PnL排行榜 | 当用户询问代币排名、市场趋势、社交热度、meme排名、突破meme代币或顶级交易者时使用 |
| **meme-rush** | Meme代币快速交易助手，具备两大核心功能：<br>1. Meme Rush - 实时meme代币列表（Pump.fun、Four.meme等launchpads），覆盖新发布、最终阶段和迁移阶段<br>2. Topic Rush - AI驱动的市场热点话题，关联代币按净流入排名 | 当用户询问新的meme代币、meme发布、bonding curve、迁移状态、pump.fun代币、four.meme代币、快速meme交易、市场热点话题或趋势叙事时使用 |
| **query-address-info** | 查询任何链上钱包地址的代币余额和持仓。检索指定钱包地址在指定链上的所有代币持仓，包括代币名称、符号、价格、24小时价格变化和持仓数量 | 当用户询问钱包余额、代币持仓、投资组合或任何区块链地址的资产持仓时使用 |
| **query-token-audit** | 查询代币安全审计，交易前检测诈骗、蜜罐和恶意合约。返回全面的安全分析，包括合约风险、交易风险和诈骗检测 | 当用户询问"这个代币安全吗？"、"检查代币安全性"、"审计代币"或任何交易前的安全验证时使用 |
| **query-token-info** | 通过关键词、合约地址或链查询代币详情。搜索代币，获取元数据和社交链接，检索实时市场数据（价格、价格趋势、交易量、持有者、流动性），并获取K线蜡烛图 | 当用户搜索代币、检查代币价格、查看市场数据或请求k线/蜡烛图时使用 |
| **trading-signal** | 订阅和获取链上聪明钱信号。监控聪明钱地址的交易活动，包括买卖信号、触发价格、当前价格、最大收益和退出率 | 当用户寻找投资机会时使用——聪明钱信号可以作为潜在交易的宝贵参考 |

### 🟡 binance (1个技能)

| 技能名称 | 功能描述 | 使用场景 |
|---------|---------|---------|
| **spot** | 使用Binance API进行现货请求。需要API密钥和密钥进行身份验证。支持测试网和主网 | 当需要进行Binance现货交易操作时使用 |

---

## 📥 安装方式

### 方法 1: 手动复制 SKILL.md

Binance Skills 目前**没有官方的自动安装命令**，需要手动操作：

**步骤 1: 克隆仓库**
```bash
git clone https://github.com/binance/binance-skills-hub.git
```

**步骤 2: 复制技能文件**
将技能目录复制到你的 Claude 配置目录：

```bash
# 示例：复制 query-token-info 技能
cp -r binance-skills-hub/skills/binance-web3/query-token-info/.claude/skills/

# 或者复制所有 binance-web3 技能
cp -r binance-skills-hub/skills/binance-web3/* ~/.claude/skills/
```

**步骤 3: 配置环境变量（如需要）**

部分技能可能需要 API 密钥：

```bash
export BINANCE_API_KEY="your_api_key"
export BINANCE_API_SECRET="your_api_secret"
```

---

## 🔍 详细技能文档

### query-token-info (示例技能)

这是最完整的技能示例，包含 4 个 API 端点：

#### 1. 代币搜索 (Token Search)
- **端点**: `GET /bapi/defi/v5/public/wallet-direct/buw/wallet/market/token/search`
- **参数**:
  - `keyword` (必需): 搜索关键词（名称/符号/合约地址）
  - `chainIds` (可选): 链ID，逗号分隔，如 `56,8453,CT_501`
  - `orderBy` (可选): 排序字段，如 `volume24h`
- **返回**: 代币列表，包含价格、24小时交易量、市值、流动性等

#### 2. 代币元数据 (Token Metadata)
- **端点**: `GET /bapi/defi/v1/public/wallet-direct/buw/wallet/dex/market/token/meta/info`
- **参数**:
  - `chainId` (必需): 链ID
  - `contractAddress` (必需): 代币合约地址
- **返回**: 代币详情、社交媒体链接、创建者地址等

#### 3. 代币动态数据 (Token Dynamic Data)
- **端点**: `GET /bapi/defi/v4/public/wallet-direct/buw/wallet/market/token/dynamic/info`
- **返回**: 实时价格、交易量、持有者数量、流动性等

#### 4. K线蜡烛图 (Token K-Line)
- **端点**: `GET /u-kline/v1/k-line/candles`
- **参数**:
  - `address` (必需): 代币合约地址
  - `platform` (必需): 链平台（eth/bsc/solana/base）
  - `interval` (必需): K线间隔（1s/1min/1h/1d等）
- **返回**: OHLCV蜡烛数据（开盘/最高/最低/收盘/交易量/时间戳/交易数）

---

## 📝 配置示例

在 `.claude/settings.local.json` 中添加:

```json
{
  "skills": {
    "binance-web3/query-token-info": {
      "enabled": true
    },
    "binance-web3/query-address-info": {
      "enabled": true
    }
  }
}
```

---

## ⚠️ 注意事项

1. **安全**: 部分技能（如 spot）需要 Binance API 密钥，确保妥善保管
2. **网络**: 技能调用需要访问 Binance API 端点，确保网络通畅
3. **速率限制**: 遵循 Binance API 的速率限制规则
4. **免责声明**: 所有技能仅供信息参考，不构成投资建议

---

## 🔗 相关链接

- GitHub 仓库: https://github.com/binance/binance-skills-hub
- 技能文档: 查看各技能目录下的 `SKILL.md` 文件
- Binance API: https://binance-docs.github.io/apidocs/
