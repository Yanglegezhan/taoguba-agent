# -*- coding: utf-8 -*-
"""
反包板策略 - 改进版
策略逻辑：选出连续涨停3天以上后断板(阴线)的股票，当再次封板时买入
改进内容：
1. 修复选股逻辑，真正统计连续涨停天数
2. 优化买入条件，增加封板质量判断
3. 添加止损止盈逻辑
4. 改进资金分配方式
5. 优化卖出时机
6. 增加成交额、换手率过滤
7. 添加市场环境判断
"""

from jqdata import *

# 初始化函数，设定基准等等
def initialize(context):
    # 设定沪深300作为基准
    set_benchmark('000300.XSHG')
    # 开启动态复权模式(真实价格)
    set_option('use_real_price', True)
    set_option("match_by_signal", True)

    log.info('===== 反包板策略 - 改进版启动 =====')

    # === 风控参数 ===
    g.max_positions = 3           # 最大持仓数
    g.max_loss_per_trade = 0.03   # 单笔最大亏损-3%
    g.max_hold_days = 3           # 最大持仓天数
    g.stop_buy_time = '14:00:00'  # 14点后不再开仓
    g.min_turnover = 500000000    # 最小成交额5亿
    g.min_turnover_rate = 0.08    # 最小换手率8%
    g.min_consecutive_limits = 3  # 最小连续涨停天数

    # 股票池
    g.help_stock = []
    g.stock_scores = {}           # 股票评分（连板天数等）

    ### 股票相关设定 ###
    set_order_cost(OrderCost(close_tax=0.001, open_commission=0.0003,
                             close_commission=0.0003, min_commission=5), type='stock')

    ## 运行函数
    run_daily(before_market_open, time='before_open', reference_security='000300.XSHG')
    run_daily(market_open, time='every_bar', reference_security='000300.XSHG')
    run_daily(after_market_close, time='after_close', reference_security='000300.XSHG')


def function_buy(stock, cash, context):
    """买入函数 - 根据连板高度动态分配资金"""
    stock_owner = context.portfolio.positions
    positions_count = len(stock_owner)

    # 获取该股票的连板评分
    score = g.stock_scores.get(stock, 3)

    # 动态仓位分配：连板越高，仓位越大
    if positions_count == 0:
        weight = 0.4 if score >= 5 else 0.35
    elif positions_count == 1:
        weight = 0.5 if score >= 5 else 0.4
    elif positions_count == 2:
        weight = 0.7 if score >= 5 else 0.6
    else:
        weight = 1.0

    open_cash = cash * weight

    if stock not in stock_owner and open_cash > 20000:
        log.info(f"买入 {stock}: 金额{open_cash:.0f}, 连板高度{score}板")
        orders = order_value(stock, open_cash)
        return orders
    return None


def get_consecutive_limit_days(stock, context):
    """获取连续涨停天数"""
    end_date = (context.current_dt + timedelta(days=-1)).strftime("%Y-%m-%d")
    try:
        df = get_price(stock, count=15, end_date=end_date,
                       frequency='daily', fields=['close', 'high_limit', 'pre_close'])

        consecutive_limits = 0
        closes = df['close'].values
        limits = df['high_limit'].values
        pre_closes = df['pre_close'].values

        # 从昨天往前统计连续涨停
        for i in range(len(closes)-1, -1, -1):
            # 检查是否涨停（考虑误差）
            if closes[i] >= limits[i] * 0.995 and closes[i] > pre_closes[i] * 1.09:
                consecutive_limits += 1
            elif i == len(closes)-1:
                # 昨天可能是阴板，继续往前看
                continue
            else:
                break
        return consecutive_limits
    except:
        return 0


def check_limit_quality(stock, context):
    """检查封板质量"""
    try:
        now = context.current_dt
        zero_today = now.replace(hour=0, minute=0, second=0, microsecond=0)
        last_today = zero_today + timedelta(hours=9, minutes=31)

        df_today = get_price(stock, start_date=last_today, end_date=now,
                             frequency='minute', fields=['close', 'high_limit'])

        if len(df_today) == 0:
            return False, 0

        high_limit = df_today['high_limit'].iloc[-1]
        max_close = df_today['close'].max()

        # 检查是否炸过板（涨停后回落超过2%）
        has_broken = max_close > high_limit * 0.98

        # 当前涨幅
        current_data = get_current_data()[stock]
        current_price = current_data.last_price
        day_open = current_data.day_open
        change_pct = (current_price - day_open) / day_open if day_open > 0 else 0

        return not has_broken, change_pct
    except:
        return True, 0


def should_sell(context, stock, stock_data):
    """判断是否应该卖出"""
    current_data = get_current_data()[stock]
    current_price = current_data.last_price
    day_open = current_data.day_open
    high_limit = current_data.high_limit

    # 获取持仓信息
    position = context.portfolio.positions[stock]
    cost = position.avg_cost
    current_return = (current_price - cost) / cost

    # 获取当日数据
    now = context.current_dt
    zero_today = now.replace(hour=0, minute=0, second=0, microsecond=0)
    last_today = zero_today + timedelta(hours=9, minutes=31)
    df_today = get_price(stock, start_date=last_today, end_date=now,
                         frequency='minute', fields=['high', 'low', 'close'])

    if len(df_today) == 0:
        return False, "未知"

    intraday_high = df_today['high'].max()
    intraday_low = df_today['low'].min()

    # 获取前一日收盘价
    pre_date = (now + timedelta(days=-1)).strftime("%Y-%m-%d")
    df_pre = get_price(stock, count=1, end_date=pre_date,
                       frequency='daily', fields=['close'])
    pre_close = df_pre['close'].values[0]

    time_str = now.strftime('%H:%M:%S')

    # ===== 止损条件 =====

    # 1. 硬止损：亏损超过3%
    if current_return < -g.max_loss_per_trade:
        return True, f"硬止损: 亏损{current_return*100:.2f}%"

    # 2. 时间止损：持仓超过3天
    if hasattr(position, 'init_date'):
        hold_days = (now.date() - position.init_date).days
    else:
        hold_days = 0
    if hold_days >= g.max_hold_days:
        return True, f"时间止损: 持仓{hold_days}天"

    # 3. 涨停失败：多次冲板未封
    times_touched = len(df_today[df_today['high'] >= high_limit * 0.99])
    if times_touched >= 2 and current_price < high_limit * 0.97:
        return True, f"冲板未封: 触碰{times_touched}次"

    # ===== 止盈条件 =====

    # 4. 高位回落止盈
    if intraday_high > pre_close * 1.07:
        # 冲高超过7%后回落
        if current_price < pre_close * 1.05:
            return True, f"冲高回落: 最高{intraday_high:.2f}, 当前{current_price:.2f}"

    # 5. 尾盘不板止盈
    if time_str > '14:30:00' and current_price < high_limit:
        # 检查是否曾经涨停
        if intraday_high >= high_limit * 0.98:
            return True, "尾盘炸板: 曾经涨停"
        elif current_price < day_open * 1.05:
            return True, "尾盘弱势: 涨幅不足5%"

    # 6. 午后加速离场
    if time_str > '13:30:00' and current_price < high_limit * 0.95:
        return True, "午后弱势: 无法冲击涨停"

    # 7. 早盘冲高回落
    if '09:55:00' < time_str < '11:30:00':
        if intraday_high > high_limit * 0.98 and current_price < high_limit * 0.95:
            return True, f"早盘冲高回落: 最高{intraday_high:.2f}"

    # 8. 接近但无法封板
    if intraday_high > pre_close * 1.098 and current_price < pre_close * 1.09:
        return True, "接近涨停未封"

    return False, ""


def market_open(context):
    """盘中交易逻辑"""
    time_str = context.current_dt.strftime('%H:%M:%S')

    # ===== 买入逻辑 =====
    if time_str < g.stop_buy_time and len(g.help_stock) > 0:
        cash = context.portfolio.available_cash

        for stock in g.help_stock[:]:  # 使用切片复制，避免迭代时修改
            # 检查持仓数量限制
            if len(context.portfolio.positions) >= g.max_positions:
                break

            if cash < 20000:
                break

            try:
                current_data = get_current_data()[stock]
                current_price = current_data.last_price
                high_limit = current_data.high_limit
                day_open = current_data.day_open

                # 判断是否涨停（允许0.5%误差）
                price_diff = abs(current_price - high_limit) / high_limit if high_limit > 0 else 1
                is_limit = price_diff < 0.005

                if is_limit:
                    # 检查封板质量
                    quality_ok, change_pct = check_limit_quality(stock, context)

                    if quality_ok:
                        # 执行买入
                        orders = function_buy(stock, cash, context)
                        if orders:
                            g.help_stock.remove(stock)
                            cash = context.portfolio.available_cash
                            log.info(f"成功买入 {stock} 封板时间 {time_str}")
                    else:
                        log.info(f"{stock} 封板质量不佳，跳过买入")
            except Exception as e:
                log.error(f"处理 {stock} 时出错: {e}")

    # ===== 卖出逻辑 =====
    stock_owner = context.portfolio.positions
    if len(stock_owner) > 0:
        for stock in list(stock_owner.keys()):
            if context.portfolio.positions[stock].closeable_amount > 0:
                should_sell_flag, reason = should_sell(context, stock, None)

                if should_sell_flag:
                    log.info(f"卖出 {stock}: {reason}")
                    order_target(stock, 0)


def check_market_strength(context):
    """检查大盘强度（涨跌停比例）"""
    date = (context.current_dt + timedelta(days=-1)).strftime("%Y-%m-%d")

    # 获取所有主板股票（排除科创板、创业板）
    all_stocks = list(get_all_securities(['stock']).index)
    main_stocks = [s for s in all_stocks if s[0:3] not in ['688', '300', '301']]

    try:
        # 获取包含涨跌停价的数据
        df = get_price(main_stocks, end_date=date, count=1,
                       frequency='daily', fields=['close', 'high_limit', 'low_limit'])

        limit_up_count = 0
        limit_down_count = 0

        for stock in main_stocks:
            try:
                close = df['close'][stock].values[0]
                high_limit = df['high_limit'][stock].values[0]
                low_limit = df['low_limit'][stock].values[0]

                # 涨停：收盘价 >= 涨停价（允许0.5%误差）
                if close >= high_limit * 0.995:
                    limit_up_count += 1
                # 跌停：收盘价 <= 跌停价（允许0.5%误差）
                elif close <= low_limit * 1.005:
                    limit_down_count += 1
            except:
                continue

        total = limit_up_count + limit_down_count
        if total == 0:
            return 0.5

        # 强度 = 涨停家数 / (涨停家数 + 跌停家数)
        strength = limit_up_count / total
        log.info(f"大盘强度: {strength:.3f} (涨停{limit_up_count}家, 跌停{limit_down_count}家)")
        return strength

    except Exception as e:
        log.error(f"检查大盘强度出错: {e}")
        return 0.5


def pick_yinban_stocks(stocks, end_date):
    """
    选出昨天是阴板的股票
    阴板定义：最高价触及涨停，但收盘价低于涨停价，且涨幅超过5%
    """
    df_panel = get_price(stocks, count=15, end_date=end_date,
                         frequency='daily', fields=['close', 'high', 'high_limit', 'money', 'pre_close'])

    yinban_stocks = []
    g.stock_scores = {}

    for stock in stocks:
        # 排除创业板、科创板
        if stock[0:2] == '30' or stock[0:3] == '688':
            continue

        try:
            closes = df_panel['close'][stock].values
            highs = df_panel['high'][stock].values
            limits = df_panel['high_limit'][stock].values
            pre_closes = df_panel['pre_close'][stock].values

            if len(closes) < 3:
                continue

            # 检查最近一天（昨天）是否是阴板
            last_high = highs[-1]
            last_close = closes[-1]
            last_limit = limits[-1]
            last_pre_close = pre_closes[-1]

            # 阴板条件：
            # 1. 最高价触及涨停
            # 2. 收盘价低于涨停价
            # 3. 涨幅超过5%
            is_yinban = (last_high >= last_limit * 0.995 and
                        last_close < last_limit * 0.995 and
                        last_close > last_pre_close * 1.05)

            if not is_yinban:
                continue

            # 统计前面连续涨停天数
            consecutive_limits = 0
            for i in range(len(closes)-2, -1, -1):
                # 涨停判断：收盘价 >= 涨停价*0.995（允许0.5%误差）
                if closes[i] >= limits[i] * 0.995:
                    consecutive_limits += 1
                else:
                    break

            # 至少N连板后断板
            if consecutive_limits >= g.min_consecutive_limits:
                yinban_stocks.append(stock)
                g.stock_scores[stock] = consecutive_limits
                log.info(f"选出阴板: {stock}, {consecutive_limits}连板后断板")

        except Exception as e:
            continue

    return yinban_stocks


def filter_st(codelist):
    """去除ST股票"""
    current_data = get_current_data()
    return [code for code in codelist if not current_data[code].is_st]


def filter_stock_by_days(context, stock_list, days):
    """过滤上市时间不足days天的股票"""
    tmp_list = []
    for stock in stock_list:
        try:
            days_public = (context.current_dt.date() - get_security_info(stock).start_date).days
            if days_public > days:
                tmp_list.append(stock)
        except:
            continue
    return tmp_list


def filter_by_turnover(context, stock_list, min_amount):
    """过滤成交额低于min_amount的股票"""
    date = (context.current_dt + timedelta(days=-1)).strftime("%Y-%m-%d")
    try:
        df = get_price(stock_list, end_date=date, count=1,
                       frequency='daily', fields=['money'])
        return [s for s in stock_list if df['money'][s].values[0] > min_amount]
    except:
        return stock_list


def filter_by_turnover_rate(context, stock_list, min_rate):
    """过滤换手率过低的股票"""
    date = (context.current_dt + timedelta(days=-1)).strftime("%Y-%m-%d")
    try:
        df = get_turnover_rate(stock_list, end_date=date, count=1)
        return [s for s in stock_list if df[s].values[0] > min_rate]
    except:
        return stock_list


def before_market_open(context):
    """开盘前选股"""
    log.info(f"===== {context.current_dt.date()} 开盘前选股开始 =====")

    date_now = (context.current_dt + timedelta(days=-1)).strftime("%Y-%m-%d")

    # 检查大盘环境
    market_strength = check_market_strength(context)

    # 弱市降低仓位或暂停操作
    if market_strength < 0.15:
        log.info("大盘极弱，今日暂停操作")
        g.help_stock = []
        g.max_positions = 0
        return
    elif market_strength < 0.3:
        log.info("大盘弱势，降低仓位")
        g.max_positions = 1
    else:
        g.max_positions = 3

    # 获取所有股票
    stocks = list(get_all_securities(['stock']).index)

    # 选出阴板股票
    yinban_stocks = pick_yinban_stocks(stocks, date_now)

    # 过滤ST股票
    filter_st_stock = filter_st(yinban_stocks)

    # 过滤新股
    filter_days_stock = filter_stock_by_days(context, filter_st_stock, 10)

    # 过滤成交额
    filter_turnover_stock = filter_by_turnover(context, filter_days_stock, g.min_turnover)

    # 过滤换手率
    filter_rate_stock = filter_by_turnover_rate(context, filter_turnover_stock, g.min_turnover_rate)

    g.help_stock = filter_rate_stock

    log.info(f"今日选出 {len(g.help_stock)} 只股票: {g.help_stock}")
    log.info(f"股票评分: {g.stock_scores}")


def after_market_close(context):
    """收盘后处理"""
    log.info(f"===== {context.current_dt.date()} 收盘后 =====")

    # 清空待买入列表
    g.help_stock = []

    # 输出持仓
    positions = context.portfolio.positions
    if len(positions) > 0:
        log.info(f"当前持仓: {list(positions.keys())}")
        for stock, pos in positions.items():
            log.info(f"  {stock}: 成本{pos.avg_cost:.2f}, 数量{pos.total_amount}, "
                    f"市值{pos.value:.0f}, 盈亏{(pos.value - pos.total_cost)/pos.total_cost*100:.2f}%")

    # 输出成交记录
    trades = get_trades()
    if len(trades) > 0:
        log.info("今日成交:")
        for trade in trades.values():
            log.info(f"  {trade}")

    # 输出账户状态
    portfolio = context.portfolio
    log.info(f"总资产: {portfolio.total_value:.0f}, "
            f"持仓市值: {portfolio.positions_value:.0f}, "
            f"可用资金: {portfolio.available_cash:.0f}")

    log.info('============================================================')
