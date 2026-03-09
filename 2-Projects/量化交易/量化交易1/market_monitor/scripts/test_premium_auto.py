# -*- coding: utf-8 -*-
"""
自动测试溢价表生成（使用最新日期）
"""

import os
import sys
import pandas as pd

# 模拟用户输入（直接回车使用最新日期）
sys.stdin = open(os.devnull, 'r')

# 导入并运行main函数
from premium_table_v3 import main

if __name__ == "__main__":
    main()
