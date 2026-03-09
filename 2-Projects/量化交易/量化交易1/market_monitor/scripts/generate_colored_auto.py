# -*- coding: utf-8 -*-
"""
自动生成彩色溢价表（使用最新日期）
"""

import sys
sys.path.append('.')

from premium_table_v3_colored import main

if __name__ == "__main__":
    # 使用自动模式，不询问日期
    main(auto_mode=True)
