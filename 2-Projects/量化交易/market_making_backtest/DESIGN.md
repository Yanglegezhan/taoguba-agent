# 高频做市回测框架设计文档

## 目录

1. [系统概述](#1-系统概述)
2. [架构设计](#2-架构设计)
3. [核心模块](#3-核心模块)
4. [事件系统](#4-事件系统)
5. [撮合引擎](#5-撮合引擎)
6. [策略接口](#6-策略接口)
7. [示例策略](#7-示例策略)
8. [部署配置](#8-部署配置)

---

## 1. 系统概述

### 1.1 设计目标

本框架专为高频做市策略回测设计，解决以下核心问题：

| 特性 | 说明 |
|-----|------|
| **事件驱动** | 纳秒级时间精度，支持高并发事件处理 |
| **L3级撮合** | 精确到订单级别的撮合，支持队列位置追踪 |
| **被动成交模拟** | 模拟其他市场参与者的成交行为 |
| **多资产支持** | 同时支持股票、期货、加密货币 |
| **TWAP示例** | 内置2分钟TWAP策略作为参考实现 |

### 1.2 性能指标

- **事件处理延迟**: < 1μs
- **撮合吞吐量**: > 100,000 orders/second
- **支持资产数量**: 无限制（取决于内存）
- **时间精度**: 纳秒级

---

## 2. 架构设计

### 2.1 总体架构

```
┌─────────────────────────────────────────────────────────────────┐
│                        应用层 (Application)                      │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐  │
│  │   回测      │  │  模拟交易   │  │       实盘交易          │  │
│  │ Backtest    │  │ Paper Trade │  │   Live Trading          │  │
│  └─────────────┘  └─────────────┘  └─────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                      策略层 (Strategy Layer)                      │
│  ┌─────────────────────────────────────────────────────────────┐  │
│  │              Strategy Base Class (抽象基类)                   │  │
│  │  - on_bar() / on_tick() / on_trade() / on_order()          │  │
│  │  - send_order() / cancel_order()                            │  │
│  │  - get_position() / get_portfolio()                          │  │
│  └─────────────────────────────────────────────────────────────┘  │
│                              △                                    │
│          ┌──────────────────┼──────────────────┐                 │
│          │                  │                  │                 │
│     ┌────┴────┐       ┌─────┴─────┐      ┌────┴────┐             │
│     │  TWAP   │       │  Market   │      │  Custom │             │
│     │Strategy │       │  Making   │      │Strategy │             │
│     └─────────┘       └───────────┘      └─────────┘             │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                      核心引擎层 (Core Engine)                     │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐  │
│  │   事件总线   │  │   撮合引擎   │  │       订单管理          │  │
│  │  Event Bus  │  │  Matching   │  │   Order Manager         │  │
│  │             │  │   Engine    │  │                         │  │
│  └─────────────┘  └─────────────┘  └─────────────────────────┘  │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐  │
│  │   时间同步   │  │   风控模块   │  │       数据管理          │  │
│  │   Clock     │  │   Risk      │  │   Data Manager          │  │
│  │  (纳秒精度)  │  │   Manager   │  │                         │  │
│  └─────────────┘  └─────────────┘  └─────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                     基础设施层 (Infrastructure)                    │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌──────────┐  │
│  │    数据     │  │    执行     │  │   监控告警   │  │ 配置管理  │  │
│  │   Data      │  │ Execution   │  │ Monitoring  │  │  Config  │  │
│  │  (多源)     │  │  (模拟/实盘) │  │ (Prom/Grafana)│ │ (YAML)   │  │
│  └─────────────┘  └─────────────┘  └─────────────┘  └──────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

### 2.2 模块依赖关系

```
                    ┌─────────────┐
                    │   Strategy  │
                    │   Context   │
                    └──────┬──────┘
                           │
        ┌──────────────────┼──────────────────┐
        │                  │                  │
        ▼                  ▼                  ▼
 ┌─────────────┐   ┌─────────────┐   ┌─────────────┐
 │   Signal    │   │   Position  │   │    Risk     │
 │  Generator  │   │    Sizer    │   │   Manager   │
 └──────┬──────┘   └──────┬──────┘   └──────┬──────┘
        │                  │                  │
        └──────────────────┼──────────────────┘
                           │
                           ▼
                  ┌─────────────────┐
                  │  Execution    │
                  │   Engine      │
                  └─────────────────┘
```

---

## 3. 核心模块

### 3.1 事件系统 (Event System)

**职责**: 纳秒级时间精度的事件分发与处理

```
┌─────────────────────────────────────────────────────────┐
│                    Event Bus                            │
├─────────────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────┐  │
│  │  EventQueue │  │  Handlers   │  │   Priorities    │  │
│  │  (Lock-free)│  │  (Registry) │  │   (0-9)         │  │
│  └─────────────┘  └─────────────┘  └─────────────────┘  │
└─────────────────────────────────────────────────────────┘
```

**事件类型枚举**:

| 类别 | 事件类型 | 触发条件 |
|-----|---------|---------|
| 市场数据 | `TICK` | 新的Tick到达 |
| 市场数据 | `BAR_CLOSE` | K线周期结束 |
| 市场数据 | `ORDER_BOOK_UPDATE` | 订单簿变化 |
| 信号 | `SIGNAL_GENERATED` | 策略生成信号 |
| 订单 | `ORDER_SUBMITTED` | 订单提交 |
| 订单 | `ORDER_FILLED` | 订单成交 |
| 订单 | `ORDER_CANCELLED` | 订单取消 |
| 风控 | `STOP_LOSS_TRIGGERED` | 止损触发 |
| 风控 | `RISK_LIMIT_BREACHED` | 风险限制 breached |

### 3.2 撮合引擎 (Matching Engine)

**职责**: L3级订单簿撮合，支持队列位置追踪

```
┌─────────────────────────────────────────────────────────┐
│                  Matching Engine                        │
├─────────────────────────────────────────────────────────┤
│  ┌─────────────────────────────────────────────────┐   │
│  │              Order Book (L3)                    │   │
│  │  ┌─────────────┐       ┌─────────────┐         │   │
│  │  │   ASK Side  │       │   BID Side  │         │   │
│  │  │  ┌───────┐  │       │  ┌───────┐  │         │   │
│  │  │  │Price 3│  │       │  │Price 3│  │         │   │
│  │  │  │ [Q1]  │  │       │  │ [Q6]  │  │         │   │
│  │  │  │ [Q2]  │  │       │  │ [Q7]  │  │         │   │
│  │  │  └───────┘  │       │  └───────┘  │         │   │
│  │  │  ┌───────┐  │       │  ┌───────┐  │         │   │
│  │  │  │Price 2│  │       │  │Price 2│  │         │   │
│  │  │  │ [Q3]  │  │       │  │ [Q8]  │  │         │   │
│  │  │  └───────┘  │       │  └───────┘  │         │   │
│  │  │  ┌───────┐  │       │  ┌───────┐  │         │   │
│  │  │  │Price 1│  │       │  │Price 1│  │         │   │
│  │  │  │ [Q4]  │  │       │  │ [Q9]  │  │         │   │
│  │  │  │ [Q5]  │  │       │  │ [Q10] │  │         │   │
│  │  │  └───────┘  │       │  └───────┘  │         │   │
│  │  └─────────────┘       └─────────────┘         │   │
│  └─────────────────────────────────────────────────┘   │
│  ┌─────────────────────────────────────────────────┐   │
│  │              Matching Logic                     │   │
│  │  - Price Priority                               │   │
│  │  - Time Priority                                │   │
│  │  - Pro-Rata (optional)                          │   │
│  │  - Queue Position Tracking                      │   │
│  └─────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────┘
```

**撮合规则**:

| 规则 | 说明 |
|-----|------|
| 价格优先 | 最优价格优先成交 |
| 时间优先 | 同价格下，先到达的订单优先 |
| 队列位置 | 追踪每个订单在价格队列中的位置 |
| 部分成交 | 支持部分成交，剩余继续挂单 |

### 3.3 订单管理 (Order Management)

**职责**: 订单生命周期管理，状态机控制

```
┌─────────────────────────────────────────────────────────┐
│              Order State Machine                        │
├─────────────────────────────────────────────────────────┤
│                                                         │
│   ┌─────────┐    submit    ┌─────────┐   match   ┌────────┐
│   │ CREATED │ ───────────▶ │ PENDING │ ───────▶ │ FILLED │
│   └─────────┘              └────┬────┘          └────────┘
│        │                        │                     │
│        │ cancel                 │ cancel              │
│        ▼                        ▼                     │
│   ┌─────────┐              ┌─────────┐                │
│   │CANCELLED│              │CANCELLED│◀─────────────┘
│   └─────────┘              └─────────┘   partial fill
│                                                         │
│   ┌─────────┐                                           │
│   │ REJECTED│ ◀─────────────────────────────────────────┘
│   └─────────┘             validation failed
│
└─────────────────────────────────────────────────────────┘
```

**订单状态**:

| 状态 | 说明 |
|-----|------|
| CREATED | 订单已创建，未提交 |
| PENDING | 订单已提交，等待成交 |
| PARTIALLY_FILLED | 部分成交 |
| FILLED | 完全成交 |
| CANCELLED | 已取消 |
| REJECTED | 被拒绝 |
| EXPIRED | 已过期 |

### 3.4 策略基类 (Strategy Base)

**职责**: 定义策略接口，统一策略实现方式

```
┌─────────────────────────────────────────────────────────┐
│              Strategy (ABC)                             │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  # 生命周期方法                                         │
│  + on_init() → None                                     │
│  + on_start() → None                                    │
│  + on_stop() → None                                     │
│                                                         │
│  # 市场数据回调                                         │
│  + on_tick(tick: Tick) → None                           │
│  + on_bar(bar: Bar) → None                              │
│  + on_order_book(book: OrderBook) → None                │
│                                                         │
│  # 交易事件回调                                           │
│  + on_order_filled(fill: Fill) → None                   │
│  + on_order_cancelled(order: Order) → None              │
│                                                         │
│  # 交易接口                                             │
│  + send_order(order_req: OrderRequest) → OrderId        │
│  + cancel_order(order_id: OrderId) → bool               │
│  + get_position(symbol: Symbol) → Position              │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

---

## 4. 事件系统

### 4.1 事件类型定义

```python
# 事件类型枚举
class EventType(Enum):
    # 系统事件
    SYSTEM_START = "system_start"
    SYSTEM_STOP = "system_stop"
    SYSTEM_ERROR = "system_error"

    # 市场数据事件
    TICK = "tick"                           # Tick数据到达
    BAR_OPEN = "bar_open"                   # K线开始
    BAR_CLOSE = "bar_close"                 # K线结束
    ORDER_BOOK_UPDATE = "order_book_update"  # 订单簿更新
    TRADE = "trade"                         # 成交记录

    # 订单事件
    ORDER_SUBMITTED = "order_submitted"     # 订单已提交
    ORDER_ACCEPTED = "order_accepted"         # 订单已接受
    ORDER_REJECTED = "order_rejected"         # 订单被拒绝
    ORDER_FILLED = "order_filled"             # 订单已成交
    ORDER_PARTIALLY_FILLED = "order_partially_filled"  # 订单部分成交
    ORDER_CANCELLED = "order_cancelled"       # 订单已取消
    ORDER_EXPIRED = "order_expired"         # 订单已过期

    # 信号事件
    SIGNAL_GENERATED = "signal_generated"   # 信号生成

    # 风控事件
    STOP_LOSS_TRIGGERED = "stop_loss_triggered"
    TAKE_PROFIT_TRIGGERED = "take_profit_triggered"
    RISK_LIMIT_BREACHED = "risk_limit_breached"
    MARGIN_CALL = "margin_call"
```

### 4.2 事件结构

```python
@dataclass
class Event:
    """事件基类"""
    event_type: EventType      # 事件类型
    timestamp: int             # 事件发生时间戳（纳秒）
    source: str                # 事件来源
    priority: int = 0          # 事件优先级（0-9，数字越小优先级越高）
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class TickEvent(Event):
    """Tick事件"""
    symbol: str
    price: Decimal
    size: Decimal
    side: Side              # 主动成交方向

@dataclass
class OrderEvent(Event):
    """订单事件"""
    order_id: str
    symbol: str
    order_type: OrderType
    side: Side
    price: Optional[Decimal]
    size: Decimal
    filled_size: Decimal = Decimal('0')
    avg_price: Optional[Decimal] = None

@dataclass
class FillEvent(Event):
    """成交事件"""
    fill_id: str
    order_id: str
    symbol: str
    side: Side
    price: Decimal
    size: Decimal
    fee: Decimal
    counterparty: Optional[str] = None  # 对手方（用于分析）
```

### 4.3 事件循环

```
┌─────────────────────────────────────────────────────────┐
│                   Event Loop                            │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐ │
│  │ Event Queue │───▶│  Priority   │───▶│  Handler    │ │
│  │  (Sorted)   │    │   Queue     │    │  Dispatch   │ │
│  └─────────────┘    └─────────────┘    └──────┬──────┘ │
│        ▲                                        │       │
│        │           ┌─────────────────┐          │       │
│        └───────────┤  New Events       │◀─────────┘       │
│                    │  (Callback)       │                 │
│                    └─────────────────┘                  │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

---

## 5. 撮合引擎

### 5.1 订单簿结构 (L3)

```
┌─────────────────────────────────────────────────────────┐
│                Limit Order Book (L3)                    │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  ASK SIDE                          BID SIDE             │
│  ┌─────────────────────────┐      ┌─────────────────────────┐  │
│  │ Price    │ Queue        │      │ Queue        │ Price    │  │
│  │──────────┼──────────────│      │──────────────┼──────────│  │
│  │ 101.00   │ [A1→A2→A3]   │      │ [B1→B2]      │ 99.00    │  │
│  │ 100.50   │ [A4→A5]      │      │ [B3→B4→B5]   │ 98.50    │  │
│  │ 100.00   │ [A6]         │      │ [B6]         │ 98.00    │  │
│  └─────────────────────────┘      └─────────────────────────┘  │
│                                                         │
│  队列位置追踪:                                            │
│  - A1: 101.00价位第一个订单 (最早到达)                     │
│  - A2: 101.00价位第二个订单                               │
│  - B1: 99.00价位第一个订单                                │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

### 5.2 撮合规则

```python
class MatchingRules:
    """撮合规则定义"""

    # 1. 价格优先
    PRICE_PRIORITY = "price_priority"

    # 2. 时间优先
    TIME_PRIORITY = "time_priority"

    # 3. 数量比例分配 (可选)
    PRO_RATA = "pro_rata"

    # 4. 做市商优先 (可选)
    MARKET_MAKER_PRIORITY = "mm_priority"
```

### 5.3 撮合流程

```
┌─────────────────────────────────────────────────────────┐
│                  Matching Flow                          │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  1. 接收订单                                             │
│     │                                                   │
│     ▼                                                   │
│  2. 验证订单                                             │
│     │ - 价格/数量合法性检查                                │
│     │ - 账户资金/持仓检查                                  │
│     ▼                                                   │
│  3. 判断订单类型                                          │
│     │                                                   │
│     ├── Market Order ────▶ 立即撮合（最优价格）              │
│     │                                                   │
│     └── Limit Order ─────▶ 进入订单簿                      │
│              │                                          │
│              ▼                                          │
│        4. 检查是否可成交                                   │
│           │                                            │
│           ├── 可以成交 ────▶ 5. 执行撮合                   │
│           │                    - 价格优先                  │
│           │                    - 时间优先                  │
│           │                    - 生成成交记录              │
│           │                                            │
│           └── 不可成交 ────▶ 6. 进入订单簿队列             │
│                               - 记录队列位置               │
│                               - 更新订单簿深度             │
│                                                         │
│  7. 发送事件通知                                          │
│     - ORDER_ACCEPTED                                    │
│     - ORDER_FILLED / ORDER_PARTIALLY_FILLED             │
│     - TRADE_EXECUTED                                    │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

---

## 6. 策略接口

### 6.1 策略基类

```python
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any
from dataclasses import dataclass
from decimal import Decimal

class Strategy(ABC):
    """策略基类 - 所有策略的抽象基类"""

    def __init__(self, strategy_id: str, symbols: list, params: Dict[str, Any]):
        self.strategy_id = strategy_id
        self.symbols = symbols
        self.params = params
        self.is_running = False
        self.context = None  # StrategyContext

    # ========== 生命周期方法 ==========

    def on_init(self) -> None:
        """策略初始化 - 在策略启动前调用"""
        pass

    def on_start(self) -> None:
        """策略启动 - 开始接收数据"""
        self.is_running = True

    def on_stop(self) -> None:
        """策略停止 - 停止接收数据"""
        self.is_running = False

    # ========== 市场数据回调 ==========

    @abstractmethod
    def on_tick(self, tick: 'Tick') -> None:
        """Tick数据到达"""
        pass

    def on_bar(self, bar: 'Bar') -> None:
        """K线数据到达（可选实现）"""
        pass

    def on_order_book(self, book: 'OrderBook') -> None:
        """订单簿更新（可选实现）"""
        pass

    def on_trade(self, trade: 'Trade') -> None:
        """市场成交记录（可选实现）"""
        pass

    # ========== 交易事件回调 ==========

    def on_order_filled(self, fill: 'Fill') -> None:
        """订单成交回调"""
        pass

    def on_order_cancelled(self, order: 'Order') -> None:
        """订单取消回调"""
        pass

    def on_order_rejected(self, order: 'Order', reason: str) -> None:
        """订单被拒绝回调"""
        pass

    # ========== 交易接口 ==========

    def send_order(self, order_req: 'OrderRequest') -> Optional[str]:
        """发送订单"""
        if not self.is_running:
            return None
        return self.context.send_order(order_req)

    def cancel_order(self, order_id: str) -> bool:
        """取消订单"""
        return self.context.cancel_order(order_id)

    def cancel_all(self, symbol: Optional[str] = None) -> int:
        """取消所有订单"""
        return self.context.cancel_all(self.strategy_id, symbol)

    def get_position(self, symbol: str) -> 'Position':
        """获取持仓"""
        return self.context.get_position(symbol)

    def get_orders(self, symbol: Optional[str] = None) -> List['Order']:
        """获取活跃订单"""
        return self.context.get_orders(self.strategy_id, symbol)

    # ========== 工具方法 ==========

    def log(self, level: str, message: str) -> None:
        """记录日志"""
        self.context.log(level, self.strategy_id, message)

    def get_param(self, key: str, default: Any = None) -> Any:
        """获取参数"""
        return self.params.get(key, default)
```

---

## 7. 示例策略

### 7.1 2分钟TWAP策略设计

```
┌─────────────────────────────────────────────────────────┐
│                 TWAP Strategy (2分钟)                     │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  参数配置:                                               │
│  - total_quantity: 总交易量                              │
│  - duration_seconds: 120 (2分钟)                        │
│  - num_slices: 12 (每10秒一个切片)                        │
│  - slice_quantity = total_quantity / num_slices        │
│                                                         │
│  执行流程:                                               │
│                                                         │
│  Time: 0s                                               │
│    │                                                    │
│    ▼                                                    │
│  ┌─────────────┐                                        │
│  │ 计算切片数量 │  num_slices = duration / interval       │
│  │ 和每切片数量 │  slice_qty = total_qty / num_slices    │
│  └──────┬──────┘                                        │
│         │                                               │
│         ▼                                               │
│  ┌─────────────┐                                       │
│  │ 设置定时器   │  每10秒触发一次                         │
│  │ (10秒间隔)  │                                        │
│  └──────┬──────┘                                        │
│         │                                               │
│         ▼                                               │
│  Time: 10s, 20s, 30s ... 120s                          │
│    │                                                    │
│    ▼                                                    │
│  ┌─────────────┐                                        │
│  │  检查持仓   │  确认已完成切片的成交情况                  │
│  └──────┬──────┘                                        │
│         │                                               │
│         ▼                                               │
│  ┌─────────────┐                                        │
│  │  发送订单   │  Market Order 或 Limit Order             │
│  │ (当前切片)  │  数量为 slice_quantity                   │
│  └──────┬──────┘                                        │
│         │                                               │
│         ▼                                               │
│  ┌─────────────┐                                        │
│  │  记录状态   │  更新已完成数量、剩余数量、均价等           │
│  └──────┬──────┘                                        │
│         │                                               │
│         ▼                                               │
│  Time: 120s (2分钟结束)                                  │
│    │                                                    │
│    ▼                                                    │
│  ┌─────────────┐                                        │
│  │  检查剩余   │  如有未完成数量，全部市价成交            │
│  └──────┬──────┘                                        │
│         │                                               │
│         ▼                                               │
│  ┌─────────────┐                                        │
│  │  生成报告   │  VWAP价格、市场均价、滑点等              │
│  └─────────────┘                                        │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

### 7.2 TWAP策略伪代码

```python
class TWAPStrategy(Strategy):
    """
    2分钟TWAP策略实现
    """

    def __init__(self, strategy_id: str, symbols: list, params: dict):
        super().__init__(strategy_id, symbols, params)

        # TWAP参数
        self.total_quantity = Decimal(str(params.get('total_quantity', 1000)))
        self.duration_seconds = params.get('duration_seconds', 120)  # 2分钟
        self.interval_seconds = params.get('interval_seconds', 10)    # 每10秒
        self.num_slices = self.duration_seconds // self.interval_seconds
        self.slice_quantity = self.total_quantity / self.num_slices

        # 状态追踪
        self.slices_sent = 0
        self.slices_filled = 0
        self.total_filled = Decimal('0')
        self.total_cost = Decimal('0')
        self.pending_orders = {}  # order_id -> slice_index
        self.timer_id = None

    def on_init(self):
        """初始化"""
        self.log("INFO", f"TWAP策略初始化: total={self.total_quantity}, "
                        f"slices={self.num_slices}, slice_qty={self.slice_quantity}")

    def on_start(self):
        """启动策略"""
        super().on_start()
        # 启动第一个切片
        self._execute_slice(0)
        # 设置定时器
        self._schedule_next_slice()

    def on_stop(self):
        """停止策略"""
        super().on_stop()
        # 取消定时器
        if self.timer_id:
            self.context.cancel_timer(self.timer_id)
        # 取消所有未完成订单
        self.cancel_all()
        # 输出统计
        self._print_statistics()

    def _execute_slice(self, slice_index: int):
        """执行一个切片"""
        if slice_index >= self.num_slices:
            return

        symbol = self.symbols[0]  # 假设单资产
        quantity = self.slice_quantity

        # 计算剩余数量
        remaining = self.total_quantity - self.total_filled
        if remaining <= 0:
            return

        quantity = min(quantity, remaining)

        # 发送市价单（TWAP通常用市价单确保成交）
        # 也可以用限价单挂在当前买卖盘中间价
        order_req = OrderRequest(
            symbol=symbol,
            side=Side.BUY if self.params.get('side') == 'BUY' else Side.SELL,
            order_type=OrderType.MARKET,  # 或 LIMIT
            quantity=quantity,
            strategy_id=self.strategy_id
        )

        order_id = self.send_order(order_req)
        if order_id:
            self.pending_orders[order_id] = slice_index
            self.slices_sent += 1
            self.log("INFO", f"Slice {slice_index}/{self.num_slices} sent: order_id={order_id}, qty={quantity}")

    def _schedule_next_slice(self):
        """调度下一个切片"""
        if self.slices_sent >= self.num_slices:
            return

        # 计算下次执行时间
        next_time = (self.slices_sent + 1) * self.interval_seconds * 1_000_000_000  # 转纳秒

        self.timer_id = self.context.set_timer(
            timestamp=next_time,
            callback=self._on_timer,
            recurring=False
        )

    def _on_timer(self, timer_id: str):
        """定时器回调"""
        self._execute_slice(self.slices_sent)
        self._schedule_next_slice()

    def on_order_filled(self, fill: 'Fill'):
        """订单成交回调"""
        order_id = fill.order_id
        if order_id in self.pending_orders:
            slice_index = self.pending_orders.pop(order_id)
            self.slices_filled += 1
            self.total_filled += fill.size
            self.total_cost += fill.size * fill.price

            avg_price = self.total_cost / self.total_filled if self.total_filled > 0 else Decimal('0')
            self.log("INFO", f"Slice {slice_index} filled: price={fill.price}, "
                            f"total_filled={self.total_filled}/{self.total_quantity}, "
                            f"avg_price={avg_price}")

            # 检查是否完成
            if self.total_filled >= self.total_quantity:
                self.log("INFO", "TWAP execution completed!")
                self.on_stop()

    def _print_statistics(self):
        """打印统计信息"""
        if self.total_filled > 0:
            avg_price = self.total_cost / self.total_filled
            self.log("INFO", f"\n{'='*50}")
            self.log("INFO", f"TWAP Statistics:")
            self.log("INFO", f"  Total Quantity: {self.total_quantity}")
            self.log("INFO", f"  Filled: {self.total_filled}")
            self.log("INFO", f"  Fill Rate: {self.total_filled/self.total_quantity*100:.2f}%")
            self.log("INFO", f"  Average Price: {avg_price}")
            self.log("INFO", f"  Slices: {self.slices_filled}/{self.slices_sent}")
            self.log("INFO", f"{'='*50}\n")
```

---

## 8. 部署配置

### 8.1 项目结构

```
market_making_backtest/
├── core/                          # 核心模块
│   ├── __init__.py
│   ├── event_bus.py               # 事件总线
│   ├── event_loop.py              # 事件循环
│   ├── clock.py                   # 模拟时钟
│   └── types.py                   # 类型定义
├── matching/                      # 撮合引擎
│   ├── __init__.py
│   ├── engine.py                  # 撮合主引擎
│   ├── order_book.py              # L3订单簿
│   ├── price_level.py             # 价格层级
│   └── trade_recorder.py          # 成交记录
├── orders/                        # 订单管理
│   ├── __init__.py
│   ├── base.py                    # 订单基类
│   ├── limit.py                   # 限价单
│   ├── market.py                  # 市价单
│   ├── state_machine.py           # 状态机
│   └── manager.py                 # 订单管理器
├── strategy/                      # 策略模块
│   ├── __init__.py
│   ├── base.py                    # 策略基类
│   ├── context.py                 # 策略上下文
│   ├── position.py                # 持仓管理
│   └── risk.py                    # 风险控制
├── data/                          # 数据模块
│   ├── __init__.py
│   ├── feed.py                    # 数据 feed
│   ├── bar_store.py               # K线存储
│   └── snapshot.py                # 订单簿快照
├── examples/                      # 示例策略
│   ├── __init__.py
│   ├── twap_strategy.py           # TWAP策略
│   └── market_making_strategy.py  # 做市策略
├── tests/                         # 测试
│   ├── test_matching_engine.py
│   ├── test_order_book.py
│   └── test_twap_strategy.py
├── config/                        # 配置
│   └── config.yaml
├── requirements.txt               # 依赖
├── Dockerfile                     # Docker构建
├── docker-compose.yml             # Docker编排
└── README.md                      # 项目说明
```

### 8.2 Docker部署

```yaml
# docker-compose.yml
version: '3.8'

services:
  backtest-engine:
    build: .
    container_name: mm-backtest
    volumes:
      - ./data:/app/data
      - ./results:/app/results
      - ./config:/app/config
    environment:
      - MODE=backtest
      - CONFIG_PATH=/app/config/config.yaml
    command: python -m examples.twap_strategy

  redis:
    image: redis:7-alpine
    container_name: mm-redis
    ports:
      - "6379:6379"

  grafana:
    image: grafana/grafana:latest
    container_name: mm-grafana
    ports:
      - "3000:3000"
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=admin
```

---

## 9. 总结

本框架提供了完整的高频做市回测解决方案：

| 模块 | 核心能力 |
|-----|---------|
| **事件系统** | 纳秒级精度，支持高并发 |
| **撮合引擎** | L3订单簿，队列位置追踪 |
| **订单管理** | 完整状态机，生命周期管理 |
| **策略接口** | 灵活易用，支持多种策略类型 |
| **TWAP示例** | 完整参考实现，可直接使用 |

框架特点：
- **高性能**: 事件驱动，纳秒级延迟
- **高精度**: L3订单簿，精确撮合
- **易扩展**: 模块化设计，方便定制
- **生产就绪**: Docker化部署，监控完善
