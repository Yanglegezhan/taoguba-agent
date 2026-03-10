# 淘股吧爬虫推送工具（简化版）

基于 Playwright 的淘股吧帖子爬取和干货提取工具。

## 项目结构

```
taoguba_agent/
├── main.py              # 主入口
├── crawler.py           # 爬虫模块
├── filter.py            # 过滤与干货提取
├── notifier.py          # 飞书推送
├── .env.local           # 配置文件（需创建）
├── .env.local.example   # 配置示例
└── requirements.txt     # 依赖
```

## 快速开始

### 1. 安装依赖

```bash
pip install playwright python-dotenv requests beautifulsoup4
playwright install chromium
```

### 2. 配置Cookie

复制配置文件：
```bash
cp .env.local.example .env.local
```

编辑 `.env.local`，填入你的淘股吧Cookie：
```bash
TAOGUBA_COOKIE=agree=enter; gdp_user_id=xxx; tgbuser=xxx; ...
```

获取Cookie的方法：
1. 登录淘股吧网站
2. 打开浏览器开发者工具 (F12)
3. 刷新页面，在Network中找到任意请求
4. 复制请求头中的Cookie字段

### 3. 运行

#### 抓取单个帖子并保存
```bash
python main.py pipeline https://www.tgb.cn/a/2pUTHRHi2tY --output 干货.md
```

#### 抓取并推送到飞书
```bash
python main.py pipeline https://www.tgb.cn/a/2pUTHRHi2tY --push
```

#### 仅获取用户帖子列表
```bash
python main.py user 12265811 --limit 10
```

## 命令说明

### pipeline（推荐）
完整流程：抓取 -> 过滤 -> 保存 -> 可选推送

```bash
python main.py pipeline <帖子URL> [选项]

选项:
  --output, -o    输出文件路径
  --max-pages     最大爬取页数（默认60）
  --push          同时推送到飞书
```

### fetch
仅抓取帖子

```bash
python main.py fetch <帖子URL> [--output 文件.md]
```

### user
获取用户帖子列表

```bash
python main.py user <UID> [--limit 数量]
```

### push
抓取并推送到飞书

```bash
python main.py push <帖子URL>
```

## 干货过滤规则

自动过滤以下内容：
- 纯数字（666、888等）
- 纯问候（来了、前排、打卡等）
- 纯表情（赞、牛逼等）
- 长度少于10字符的评论

优先保留：
- 博主回复
- 包含技术关键词的评论

关键词分类：
- 核心心法：择时大于一切、空仓、管住手、大道至简
- 超预期：超预期、符合预期、不及预期
- 辨识度：辨识度、前排、后排、龙头、杂毛
- 买卖点：打板、竞价、半路、扫板
- 炸板处理：炸板、烂板、回封、封单
- 板块分析：板块、回流、轮动、分歧
- 盘口：主动、被动、带动、放量、缩量

## 输出示例

生成的Markdown文档包含：
1. **经典语录** - 博主的简短精华观点
2. **分类干货** - 按主题分类的评论
3. **完整保留评论** - 所有筛选后的评论

## 注意事项

1. **Cookie有效期**：Cookie通常几天到几周有效，失效后需重新获取
2. **分页格式**：淘股吧分页使用 `-2`、`-3` 格式，不是 `?pageNo=2`
3. **爬取速度**：默认每页等待3秒，可根据网络调整
4. **飞书限制**：单条消息最多8000字符，超出会自动截断

## 技术栈

- **Playwright**: 浏览器自动化
- **BeautifulSoup**: HTML解析
- **python-dotenv**: 环境变量管理
- **requests**: HTTP请求（飞书推送）
