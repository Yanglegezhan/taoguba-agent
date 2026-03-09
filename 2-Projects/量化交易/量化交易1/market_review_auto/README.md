# market_review_auto

自动化A股复盘流水线（抓取东财数据 → 资金进攻顺序图 → 事件/题材归因 → 锚定分时打点 → 生成PDF → 邮件发送）。

## 目录结构

- `src/fetch/`：数据抓取（东财 + 补充数据）
- `src/plot/`：资金进攻顺序图
- `src/enrich/`：事件归因、锚定分时打点、主图标注
- `src/report/`：生成PDF
- `src/notify/`：邮件发送
- `src/app/`：入口脚本（串联全流程）
- `data/review_data/`：每日输出目录（自动生成）

## Anaconda环境

建议使用 `environment.yml` 创建独立环境。

1. 创建环境

在 Anaconda Prompt 中执行：

```bat
cd /d d:\pythonProject2\量化交易1\market_review_auto
conda env create -f environment.yml
```

2. 激活环境

```bat
conda activate market_review_auto
```

## 运行

- 仅生成复盘PDF（不发邮件）

```bat
python src\app\run_nightly_recap.py
```

- 生成并发邮件

```bat
python src\app\run_nightly_recap.py --send --email-to 2358638763@qq.com
```

## 邮件配置（安全）

不要把SMTP授权码写进代码或提交到仓库。

推荐方式：用环境变量（在当前Anaconda Prompt窗口有效）

```bat
set MAIL_USERNAME=你的邮箱
set MAIL_PASSWORD=你的SMTP授权码
set MAIL_FROM_ADDR=你的邮箱
```

或者复制 `email_config.example.json` 为 `email_config.json` 并填写（此文件建议不要提交）。

## 定时任务

使用 Windows 任务计划程序，在每日 19:00 触发，执行：

```bat
conda activate market_review_auto && python d:\pythonProject2\量化交易1\market_review_auto\src\app\run_nightly_recap.py --send --email-to 2358638763@qq.com
```
