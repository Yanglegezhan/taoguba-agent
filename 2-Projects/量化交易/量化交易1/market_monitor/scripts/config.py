# -*- coding: utf-8 -*-
"""
市场监控系统配置文件
"""

# 数据更新配置
INITIAL_DAYS = 730  # 初始化时获取2年数据
UPDATE_DAYS = 5     # 增量更新时获取最近5天数据

# 涨跌停判断阈值
LIMIT_UP_THRESHOLD = 0.095    # 涨停阈值 9.5%（考虑误差）
LIMIT_DOWN_THRESHOLD = -0.095  # 跌停阈值 -9.5%

# 创业板和科创板涨跌停阈值
CYB_KCYB_LIMIT_UP = 0.195     # 20%涨停
CYB_KCYB_LIMIT_DOWN = -0.195  # 20%跌停

# 板块识别
MIN_BOARD_COUNT = 2  # 最小连板数（2板以上）
HIGH_BOARD_COUNT = 4  # 高位板标准（4板以上）

# 数据存储路径
DATA_DIR = "data"
OUTPUT_DIR = "output"

# 市场板块代码
MARKET_CODES = {
    'main': '000001.SH',      # 上证指数
    'cyb': '399006.SZ',       # 创业板指
    'kcb': '000688.SH'        # 科创50
}

# akshare数据列名映射（实际列名）
COLUMN_MAPPING = {
    '日期': '日期',
    '开盘': '开盘',
    '收盘': '收盘',
    '最高': '最高',
    '最低': '最低',
    '成交量': '成交量',
    '成交额': '成交额',
    '涨跌幅': '涨跌幅',  # 百分比形式
    '涨跌额': '涨跌额',
    '振幅': '振幅',
    '换手率': '换手率',
    '股票代码': '股票代码'
}
