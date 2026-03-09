
# 导入函数库
from jqdata import *

# 初始化函数，设定基准等等
def initialize(context):
    # 设定沪深300作为基准
    set_benchmark('000300.XSHG')
    # 开启动态复权模式(真实价格)
    set_option('use_real_price', True)
    set_option("match_by_signal", True) 
    # 输出内容到日志 log.info()
    log.info('初始函数开始运行且全局只运行一次')
    # 过滤掉order系列API产生的比error级别低的log
    # log.set_level('order', 'error')
    # g 内置全局变量
    g.my_security = '510300.XSHG'
    g.help_stock = []
    set_universe([g.my_security])
    ### 股票相关设定 ###
    # 股票类每笔交易时的手续费是：买入时佣金万分之三，卖出时佣金万分之三加千分之一印花税, 每笔交易佣金最低扣5块钱
    set_order_cost(OrderCost(close_tax=0.001, open_commission=0.0003, close_commission=0.0003, min_commission=5), type='stock')

    ## 运行函数（reference_security为运行时间的参考标的；传入的标的只做种类区分，因此传入'000300.XSHG'或'510300.XSHG'是一样的）
      # 开盘前运行
    run_daily(before_market_open, time='before_open', reference_security='000300.XSHG')
      # 开盘时运行
    run_daily(market_open, time='every_bar', reference_security='000300.XSHG')
    #run_daily(market_run_sell, time='every_bar', reference_security='000300.XSHG')

      # 收盘后运行before_open
    #run_daily(after_market_close, time='after_close', reference_security='000300.XSHG')

def function_buy(stock, cash, context):
    stock_owner = context.portfolio.positions
    open_cash = 0
    orders = ''
    if len(stock_owner) == 0:
        open_cash = cash / 3
    elif len(stock_owner) == 1:
        open_cash = cash / 2
    elif len(stock_owner) == 2:
        open_cash = cash
    if stock not in stock_owner and open_cash > 20000:
        orders = order_value(stock, open_cash)
    return orders   

## 开盘时运行函数
def market_open(context):
    time_buy = context.current_dt.strftime('%H:%M:%S')
    aday = datetime.datetime.strptime('13:00:00', '%H:%M:%S').strftime('%H:%M:%S')
    now = context.current_dt
    zeroToday = now - datetime.timedelta(hours=now.hour, minutes=now.minute, seconds=now.second,microseconds=now.microsecond)
    lastToday = zeroToday + datetime.timedelta(hours=9, minutes=31, seconds=00)
    
    if len(g.help_stock) > 0 :
        for stock in g.help_stock:
            #log.info("当前时间 %s" % (context.current_dt))
            #log.info("股票 %s 的最新价: %f" % (stock, get_current_data()[stock].last_price))
            cash = context.portfolio.available_cash
            #print(cash)
            day_open_price = get_current_data()[stock].day_open
            current_price = get_current_data()[stock].last_price
            high_limit_price = get_current_data()[stock].high_limit
            df_panel_time = get_price(stock, start_date=lastToday, end_date=context.current_dt, frequency='minute', fields=['high','low','close','high_limit','money'])
            df_limit_one = df_panel_time[df_panel_time['close'] == df_panel_time['high_limit']]

            ##当前持仓有哪些股票
            if cash > 5000 :
                if current_price == high_limit_price and df_limit_one.shape[0] <= 3:
                    print("1."+stock+"买入金额"+str(cash))
                    orders = function_buy(stock, cash, context)
                    g.help_stock.remove(stock)

    time_sell = context.current_dt.strftime('%H:%M:%S')
    cday = datetime.datetime.strptime('14:55:00', '%H:%M:%S').strftime('%H:%M:%S')
    stock_owner = context.portfolio.positions
    if len(stock_owner) > 0:
        for stock_two in stock_owner:
            if context.portfolio.positions[stock_two].closeable_amount > 0:
                current_price_list = get_ticks(stock_two,start_dt=None, end_dt=context.current_dt, count=1, fields=['time', 'current', 'high', 'low', 'volume', 'money'])
                current_price = current_price_list['current'][0]
                day_open_price = get_current_data()[stock_two].day_open
                day_high_limit = get_current_data()[stock_two].high_limit 
                
                
                df_panel_allday = get_price(stock_two, start_date=lastToday, end_date=context.current_dt, frequency='minute', fields=['high','low','close','high_limit','money'])
                low_allday = df_panel_allday.loc[:,"low"].min()
                high_allday = df_panel_allday.loc[:,"high"].max()

                ##获取前一天的收盘价
                pre_date =  (context.current_dt + timedelta(days = -1)).strftime("%Y-%m-%d")
                df_panel = get_price(stock_two, count = 1,end_date=pre_date, frequency='daily', fields=['open', 'close','high_limit','money','low',])
                pre_low_price =df_panel['low'].values
                pre_close_price =df_panel['close'].values
                
                #平均持仓成本
                cost = context.portfolio.positions[stock_two].avg_cost
                if high_allday > pre_close_price * 1.07 and current_price < pre_close_price * 1.07:
                    print("1.卖出股票：大于7个点卖出"+str(stock_two))
                    order_target(stock_two, 0)
                elif current_price < day_high_limit and time_sell > cday:
                    print("2.卖出股票：尾盘14点50分卖出"+str(stock_two))
                    order_target(stock_two, 0)
                elif high_allday > pre_close_price * 1.098:
                    print("3.卖出股票：大于9.8个点卖出"+str(stock_two))
                    order_target(stock_two, 0)


## 选出连续涨停超过3天的，最近一天是阴板的
def before_market_open(context):
    date_now =  (context.current_dt + timedelta(days = -1)).strftime("%Y-%m-%d")#'2021-01-15'#datetime.datetime.now()
    yesterday = (context.current_dt + timedelta(days = -90)).strftime("%Y-%m-%d")
    trade_date = get_trade_days(start_date=yesterday, end_date=date_now, count=None)
    stocks = list(get_all_securities(['stock']).index)
    end_date = trade_date[trade_date.size-1]
    pre_date = trade_date[trade_date.size-3]
    #选出昨天是涨停板的个股
    continuous_price_limit = pick_high_limit(stocks,end_date,pre_date)

    filter_st_stock = filter_st(continuous_price_limit)
    g.help_stock = filter_stock_by_days(context,filter_st_stock,10)
    print("选出的连扳股票")
    print(g.help_stock)
    
            
##选出打板的股票
def pick_high_limit(stocks,end_date,pre_date):
    df_panel = get_price(stocks, count = 2,end_date=end_date, frequency='daily', fields=['high', 'close','high_limit','money','pre_close'])
    df_high = df_panel['high']
    df_high_limit = df_panel['high_limit']
    df_pre_close = df_panel['pre_close']
    df_close = df_panel['close']
    
    high_limit_stock = []
    for stock in (stocks):
        if(stock[0:2] == '30'):
            continue
        if df_high_limit[stock].values[0] == df_close[stock].values[0] and df_close[stock].values[1] < df_high_limit[stock].values[1] and df_high[stock].values[1] > df_close[stock].values[1] * 1.07:
            high_limit_stock.append(stock)
    return high_limit_stock


    
##去除st的股票
def filter_st(codelist):
    current_data = get_current_data()
    codelist = [code for code in codelist if not current_data[code].is_st]
    return codelist

##过滤上市时间不满1080天的股票
def filter_stock_by_days(context, stock_list, days):
    tmpList = []
    for stock in stock_list :
        days_public=(context.current_dt.date() - get_security_info(stock).start_date).days
        if days_public > days:
            tmpList.append(stock)
    return tmpList


## 收盘后运行函数
def after_market_close(context):
    g.help_stock = []
    log.info(str('函数运行时间(after_market_close):'+str(context.current_dt.time())))
    #得到当天所有成交记录
    trades = get_trades()
    for _trade in trades.values():
        log.info('成交记录：'+str(_trade))
    log.info('一天结束')
    log.info('##############################################################')
