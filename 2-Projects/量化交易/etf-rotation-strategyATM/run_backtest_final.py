# -*- coding: utf-8 -*-
"""
Final simplified backtest script - real data using tushare
"""

import os
os.environ['NO_PROXY'] = '1'

import tushare as ts
import backtrader as bt
import numpy as np
import pandas as pd
from datetime import datetime
from pathlib import Path
import logging
import json

# Tushare API token
TUSHARE_TOKEN = '5f4f5783867898c47ce50002876d52ca448b040cb9a29c202a7818bcd6'

# Set tushare token
ts.set_token(TUSHARE_TOKEN)

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Backtest parameters
START_DATE = '20200101'
END_DATE = datetime.now().strftime('%Y%m%d')
INITIAL_CASH = 1000000
COMMISSION_RATE = 0.0005
SLIPPAGE_RATE = 0.0005

# ETF pool (simplified) - using tushare fund codes with .SZ/.SH suffix
ETF_POOL = {
    '159915.SZ': '创业板ETF',
    '510300.SH': '沪深300ETF',
    '512880.SH': '证券ETF',
    '515050.SH': '5GETF',
    '159949.SZ': '消费ETF',
    '510500.SH': '中证500ETF',
    '512100.SH': '中证1000ETF',
    '159928.SZ': '消费ETF',
    '510880.SH': '国债ETF',
}


class SimpleMomentumStrategy(bt.Strategy):
    params = (
        ('lookback', 60),
        ('top_n', 5),
    )

    def __init__(self):
        super().__init__()
        self.rebalance_day = None

    def next(self):
        if not self.data.datetime:
            return

        current_date = self.data.datetime.date(0)
        current_weekday = current_date.weekday()

        if current_weekday != 4:
            return

        if self.rebalance_day == current_date:
            return

        self.rebalance_day = current_date

        scores = self._calculate_momentum_scores()

        if not scores:
            return

        top_etfs = sorted(scores.items(), key=lambda x: x[1], reverse=True)[:self.p.top_n]

        logger.info(f"Date {current_date}: Selected {top_etfs}")

        target_weights = {code: 1.0 / len(top_etfs) for code, _ in top_etfs}

        self._rebalance(target_weights)

    def _calculate_momentum_scores(self):
        scores = {}

        for code, name in ETF_POOL.items():
            try:
                data = getattr(self, code, None)
                if data is None or len(data) < self.p.lookback:
                    continue

                if len(data) >= self.p.lookback:
                    momentum = (data.close[0] / data.close[-self.p.lookback] - 1)
                    scores[code] = momentum

            except Exception as e:
                logger.warning(f"Failed to calculate {code} momentum: {e}")

        return scores

    def _rebalance(self, target_weights):
        for code, weight in target_weights.items():
            try:
                data = getattr(self, code, None)
                if data is None:
                    continue

                target_value = self.broker.getvalue() * weight
                current_value = self.getposition(data).size * data.close[0]

                diff = target_value - current_value

                if diff > self.broker.getvalue() * 0.01:
                    if diff > 0:
                        self.buy(data=data, size=diff / data.close[0])
                    else:
                        self.sell(data=data, size=abs(diff) / data.close[0])

            except Exception as e:
                logger.warning(f"Failed to rebalance {code}: {e}")


def fetch_etf_data(etf_code, start_date, end_date):
    try:
        logger.info(f"Fetching {etf_code} data: {start_date} - {end_date}")

        pro = ts.pro_api()

        # Get ETF daily data using tushare
        df = pro.fund_daily(ts_code=etf_code, start_date=start_date, end_date=end_date)

        if df is None or df.empty:
            logger.warning(f"{etf_code} data is empty")
            return None

        logger.info(f"Available columns for {etf_code}: {df.columns.tolist()}")

        # Rename columns for backtrader
        df = df.rename(columns={
            'trade_date': 'datetime',
            'open': 'open',
            'high': 'high',
            'low': 'low',
            'close': 'close',
            'vol': 'volume',
        })

        # Convert datetime
        df['datetime'] = pd.to_datetime(df['datetime'])

        # Filter out NaN values
        df = df.dropna(subset=['close'])

        df = df.sort_values('datetime').reset_index(drop=True)

        logger.info(f"Fetched {len(df)} records for {etf_code}")

        return df

    except Exception as e:
        logger.error(f"Failed to fetch {etf_code} data: {e}")
        return None


def run_backtest():
    logger.info("=" * 60)
    logger.info("Starting backtest")
    logger.info("=" * 60)
    logger.info(f"Backtest period: {START_DATE} - {END_DATE}")
    logger.info(f"Initial cash: CNY {INITIAL_CASH:,}")
    logger.info(f"Commission: {COMMISSION_RATE*1000:.1f} per mil")
    logger.info(f"Slippage: {SLIPPAGE_RATE*1000:.1f} per mil")
    logger.info("")

    cerebro = bt.Cerebro()
    cerebro.broker.setcash(INITIAL_CASH)

    cerebro.broker.setcommission(bt.CommissionInfo(
        commission=COMMISSION_RATE
    ))

    cerebro.broker.set_slippage_perc(SLIPPAGE_RATE)

    data_added = 0
    for code, name in ETF_POOL.items():
        try:
            logger.info(f"Loading {code} ({name})...")

            df = fetch_etf_data(code, START_DATE, END_DATE)

            if df is None or df.empty:
                logger.warning(f"Skipping {code} (no data)")
                continue

            data = bt.feeds.PandasData(
                dataname=code,
                datetime=df['datetime'],
                open=df['open'],
                high=df['high'],
                low=df['low'],
                close=df['close'],
                volume=df['volume'].fillna(1),  # Use volume or close as proxy
                openinterest=None,
            )

            cerebro.adddata(data)
            data_added += 1

        except Exception as e:
            logger.error(f"Failed to add {code} data: {e}")

    logger.info(f"Successfully added {data_added} ETF data")
    logger.info("")

    if data_added == 0:
        logger.error("No data added, backtest failed")
        return

    cerebro.addstrategy(SimpleMomentumStrategy)

    logger.info("Starting backtest run...")
    try:
        results = cerebro.run()
    except Exception as e:
        logger.error(f"Backtest run failed: {e}")
        return

    strat = results[0]

    if cerebro.broker.getvalue() == 0:
        logger.error("Final value is 0, backtest may have failed")
        return

    final_value = cerebro.broker.getvalue()
    total_return = (final_value / INITIAL_CASH - 1) * 100

    years = (datetime.strptime(END_DATE, '%Y%m%d') - datetime.strptime(START_DATE, '%Y%m%d')).days / 365.25
    annual_return = ((final_value / INITIAL_CASH) ** (1/years)) - 1

    logger.info("=" * 60)
    logger.info("Backtest Results")
    logger.info("=" * 60)
    logger.info(f"Final value: CNY {final_value:,.2f}")
    logger.info(f"Total return: {total_return:.2f}%")
    logger.info(f"Annual return: {annual_return*100:.2f}%")
    logger.info(f"Backtest period: {years:.1f} years")
    logger.info("")

    output_dir = Path('reports')
    output_dir.mkdir(parents=True, exist_ok=True)

    result_json = {
        'start_date': START_DATE,
        'end_date': END_DATE,
        'initial_cash': INITIAL_CASH,
        'final_value': final_value,
        'total_return': total_return,
        'annual_return': annual_return * 100,
        'years': years,
        'etf_count': len(ETF_POOL),
        'commission': COMMISSION_RATE * 1000,
        'slippage': SLIPPAGE_RATE * 1000,
    }

    json_file = output_dir / 'backtest_final_results.json'
    with open(json_file, 'w', encoding='utf-8') as f:
        json.dump(result_json, f, indent=2, ensure_ascii=False)

    logger.info(f"Results saved to {json_file}")
    logger.info("=" * 60)

    report_lines = [
        "# ETF轮动策略回测报告",
        "",
        f"**Generated at**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"**Backtest period**: {START_DATE} - {END_DATE}",
        f"**Initial cash**: CNY {INITIAL_CASH:,}",
        f"**Commission**: {COMMISSION_RATE*1000:.1f}‰",
        f"**Slippage**: {SLIPPAGE_RATE*1000:.1f}‰",
        "",
        "## Backtest Results",
        "",
        f"- Final value: CNY {final_value:,.2f}",
        f"- Total return: {total_return:.2f}%",
        f"- Annual return: {annual_return*100:.2f}%",
        f"- Backtest period: {years:.1f} years",
        f"- ETF count: {len(ETF_POOL)}",
        "",
        "## Strategy Description",
        "",
        "- **Strategy name**: Simple momentum rotation strategy",
        "- **Selection logic**: Select top 5 ETFs by 60-day momentum",
        "- **Rebalance frequency**: Every Friday close",
        "- **Weight allocation**: Equal weight",
        "",
        "## ETFs in portfolio",
        "",
    ]

    for code, name in ETF_POOL.items():
        report_lines.append(f"- {name} ({code})")

    report_lines.extend([
        "",
        "## Data Source",
        "",
        "- **API**: tushare (fund_daily)",
        "- **Data type**: Real historical NAV data",
        "",
        "## Notes",
        "",
        "- This report uses real tushare data for backtest",
        "- Backtest period: 2020-01-01 to current date",
        "- Commission: 0.5‰",
        "- Slippage: 0.5‰",
        "",
        "---",
        "",
        f"*Report generated at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*",
    ])

    md_file = output_dir / 'backtest_final_report.md'
    with open(md_file, 'w', encoding='utf-8') as f:
        f.write('\n'.join(report_lines))

    logger.info(f"Report saved to {md_file}")
    logger.info("Backtest complete!")


if __name__ == '__main__':
    run_backtest()
