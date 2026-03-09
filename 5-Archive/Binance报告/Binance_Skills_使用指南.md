# Binance Skills 使用指南

## 📋 已安装的技能

### binance-web3 (6个技能)
- ✅ **query-token-info** - 代币详情查询（搜索、元数据、实时数据、K线）
- ✅ **query-address-info** - 钱包地址代币余额查询
- ✅ **query-token-audit** - 代币安全审计（检测诈骗、蜜罐、恶意合约）
- ✅ **crypto-market-rank** - 市场排名和排行榜
- ✅ **meme-rush** - Meme代币快速交易助手
- ✅ **trading-signal** - 聪明钱交易信号

### binance (1个技能)
- ✅ **spot** - Binance现货交易

## 🔧 配置说明

### 1. API 密钥配置
对于需要认证的技能（如 spot），请在 `~/.claude/settings.local.json` 中配置：

```json
{
  "env": {
    "BINANCE_API_KEY": "your_api_key_here",
    "BINANCE_API_SECRET": "your_api_secret_here"
  }
}
```

### 2. 技能启用状态
所有技能默认已启用。如需禁用某个技能，修改 `settings.local.json`：

```json
{
  "skills": {
    "binance-web3/query-token-info": {
      "enabled": false
    }
  }
}
```

## 🚀 使用示例

### 查询代币信息
```
/查询比特币的详细信息
/获取ETH在BSC链上的价格和交易量
/显示SOLANA的K线图（1小时间隔）
```

### 查询钱包余额
```
/查询地址0x123...456的所有代币持仓
/显示我的钱包在Base链上的资产
```

### 安全审计
```
/审计这个代币是否安全：0x55d398326f99059ff775485246999027b3197955
/检查这个合约是否有蜜罐风险
```

### 市场排名
```
/显示当前最热门的meme代币
/获取聪明钱流入最多的代币排名
/查看今日表现最好的交易者
```

### Meme交易
```
/获取Pump.fun上新发布的meme代币
/显示Four.meme上正在finalizing的代币
/查看当前市场热点话题
```

### 聪明钱信号
```
/获取最新的聪明钱买入信号
/显示BSC链上的大额交易信号
/订阅特定钱包的交易通知
```

### 现货交易
```
/获取我的Binance账户信息
/查询BTCUSDT的当前价格
/下单购买0.01 BTC
```

## ⚠️ 注意事项

1. **安全第一**: 所有交易相关操作都需要谨慎，建议先在testnet测试
2. **API限制**: 遵循Binance API的速率限制规则
3. **风险提示**: Meme代币和加密货币交易具有高风险，请谨慎投资
4. **数据延迟**: 实时数据可能有几秒到几分钟的延迟
5. **网络要求**: 需要能够访问Binance API端点

## 📞 故障排除

如果遇到问题：
1. 检查网络连接是否正常
2. 验证API密钥是否正确配置
3. 查看技能目录是否存在：`~/.claude/skills/binance-web3/`
4. 检查配置文件：`~/.claude/settings.local.json`

## 📚 支持的链

- **BSC** (chainId: 56)
- **Base** (chainId: 8453)
- **Solana** (chainId: CT_501)

## 🔄 更新技能

技能会定期更新。如需手动更新，重新运行安装脚本或从官方仓库同步最新版本。

---
*配置完成时间: 2026-03-05*