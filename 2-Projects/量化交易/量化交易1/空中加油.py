import tushare as ts
import pandas as pd
import numpy as np
import warnings
from tqdm import tqdm, trange
import matplotlib.pyplot as plt

warnings.filterwarnings("ignore")

# 1. 配置区
TOKEN = '5f4f5783867898c47ce50002876d52ca448b0cb9a29c202a7818bcd6' # <--- 请确保这里填入了你的Token
pro = ts.pro_api(TOKEN)

BOOM_VOL_MULT = 3
VOL_RATIO_MAX = 0.5
MA_BAND = 0.01
MID_TOL = 0.0

BOOM_PULLBACK_MIN = 0.02
BOOM_UPPER_SHADOW_RATIO_MIN = 0.4
BOOM_BREAK_YHIGH = 1.0

COST_ROUND_TRIP = 0.002
COOLDOWN_TDAYS = 10
HOLD_MAX_TDAYS = 10

def get_trade_dates(start_date, end_date):
    try:
        cal = pro.trade_cal(exchange='SSE', start_date=start_date, end_date=end_date, is_open=1, fields='cal_date')
        if cal is None or cal.empty:
            return []
        return cal['cal_date'].tolist()
    except Exception as e:
        print(f"获取交易日历失败: {e}")
        return []

def normalize_trade_date(date_str, direction='prev'):
    try:
        date_str = pd.to_datetime(date_str).strftime('%Y%m%d')
    except Exception:
        return date_str

    start = (pd.to_datetime(date_str) - pd.Timedelta(days=30)).strftime('%Y%m%d')
    end = (pd.to_datetime(date_str) + pd.Timedelta(days=30)).strftime('%Y%m%d')
    dates = get_trade_dates(start, end)
    if not dates:
        return date_str

    dates_sorted = sorted(dates)
    if direction == 'next':
        for d in dates_sorted:
            if d >= date_str:
                return d
        return dates_sorted[-1]

    for d in reversed(dates_sorted):
        if d <= date_str:
            return d
    return dates_sorted[0]

def tday_offset(date_str, offset, lookaround_days=420):
    date_str = normalize_trade_date(date_str, direction='prev')
    center = pd.to_datetime(date_str)
    start = (center - pd.Timedelta(days=lookaround_days)).strftime('%Y%m%d')
    end = (center + pd.Timedelta(days=lookaround_days)).strftime('%Y%m%d')
    dates = sorted(get_trade_dates(start, end))
    if not dates:
        return date_str

    try:
        i = dates.index(date_str)
    except ValueError:
        dates_prev = [d for d in dates if d <= date_str]
        if not dates_prev:
            i = 0
        else:
            i = dates.index(dates_prev[-1])

    j = i + int(offset)
    if j < 0:
        j = 0
    if j >= len(dates):
        j = len(dates) - 1
    return dates[j]

def get_index_codes(target_date, index_code):
    target_date = normalize_trade_date(target_date, direction='prev')
    start_dt = tday_offset(target_date, -90)
    try:
        w = pro.index_weight(index_code=index_code, start_date=start_dt, end_date=target_date, fields='trade_date,con_code')
        if w is None or w.empty:
            return []
        last_dt = w['trade_date'].max()
        return w[w['trade_date'] == last_dt]['con_code'].dropna().unique().tolist()
    except Exception as e:
        print(f"获取指数成分失败: {e}")
        return []

def get_index_codes_range(start_date, end_date, index_code):
    try:
        start_date = normalize_trade_date(start_date, direction='next')
        end_date = normalize_trade_date(end_date, direction='prev')
        w = pro.index_weight(index_code=index_code, start_date=start_date, end_date=end_date, fields='trade_date,con_code')
        if w is None or w.empty:
            return []
        return sorted(w['con_code'].dropna().unique().tolist())
    except Exception as e:
        print(f"获取指数成分失败: {e}")
        return []

def get_universe_codes(universe, target_date=None, start_date=None, end_date=None):
    if universe in ['hs300', '000300.SH']:
        if target_date is None:
            return get_index_codes_range(start_date, end_date, '000300.SH')
        return get_index_codes(target_date, '000300.SH')

    if universe in ['zz1000', '000852.SH']:
        if target_date is None:
            return get_index_codes_range(start_date, end_date, '000852.SH')
        return get_index_codes(target_date, '000852.SH')

    if universe in ['all', 'all_a', 'cn_a']:
        try:
            sb = pro.stock_basic(list_status='L', fields='ts_code')
            if sb is None or sb.empty:
                return []
            return sb['ts_code'].dropna().unique().tolist()
        except Exception as e:
            print(f"获取全A股票池失败: {e}")
            return []

    return []

def scan_period(start_date, end_date, universe='hs300', limit=None):
    dates = get_trade_dates(start_date, end_date)
    if limit is not None:
        dates = dates[:limit]

    all_rows = []
    for d in dates:
        picks = run_scanner(d, universe=universe)
        if isinstance(picks, pd.DataFrame) and not picks.empty:
            tmp = picks.copy()
            tmp['scan_date'] = d
            all_rows.append(tmp)

    if not all_rows:
        return pd.DataFrame()
    return pd.concat(all_rows, ignore_index=True)

def event_study(
    start_date,
    end_date,
    universe='hs300',
    max_stocks=None,
    cooldown_tdays=COOLDOWN_TDAYS,
    cost_round_trip=COST_ROUND_TRIP,
    stop_losses=None,
    take_profits=None,
    support_mode='S2',
    hold_max_tdays=HOLD_MAX_TDAYS,
    sell_block_limit_up=True,
    stop_mode='pct',
    stop_abs=0.02,
    stop_low_buffer=0.02,
    stop_low_buffers=None,
    vol_ratio_max=VOL_RATIO_MAX,
    ma_band=MA_BAND,
    max_positions=10,
    daily_max_entries=5,
    plot_report=True,
    plot_sl=None,
    plot_tp=None,
):
    start_date = normalize_trade_date(start_date, direction='next')
    end_date = normalize_trade_date(end_date, direction='prev')

    codes = get_universe_codes(universe, start_date=start_date, end_date=end_date)

    if max_stocks is not None:
        codes = codes[:max_stocks]

    try:
        names = pro.stock_basic(list_status='L', fields='ts_code,name')
        name_map = dict(zip(names['ts_code'], names['name'])) if names is not None and not names.empty else {}
    except Exception as e:
        print(f"获取股票名称失败: {e}")
        name_map = {}

    start_dt = tday_offset(start_date, -260)
    end_dt = tday_offset(end_date, 25)

    def _pct_to_decimal(x):
        if x is None:
            return None
        try:
            v = float(x)
        except Exception:
            return None

        v = abs(v)
        if v > 1:
            return v / 100
        return v

    def _limit_up_threshold(ts_code):
        if isinstance(ts_code, str) and (ts_code.startswith('300') or ts_code.startswith('688')):
            return 19.8
        return 9.8

    def _is_limit_up(pct_chg, up_th):
        return pd.notna(pct_chg) and pct_chg >= up_th

    def _support_price(df0, boom_pos, entry_pos):
        if support_mode == 'S1':
            return (df0.at[boom_pos, 'high'] + df0.at[boom_pos, 'low']) / 2
        if support_mode == 'S2':
            return df0.at[boom_pos, 'low']
        if support_mode == 'S3':
            return df0.at[entry_pos, 'low']
        return df0.at[boom_pos, 'low']

    def _simulate_exit(df0, boom_pos, entry_pos, sl, tp, up_th, stop_low_buffer_local=None):
        entry_price = df0.at[entry_pos, 'close']
        sup = _support_price(df0, boom_pos, entry_pos)

        sl = _pct_to_decimal(sl)
        tp = _pct_to_decimal(tp)

        exit_pos = None
        exit_reason = None
        exit_price = None

        mfe = 0.0
        mae = 0.0

        prev_boom = boom_pos - 1
        prev_low = df0.at[prev_boom, 'low'] if prev_boom >= 0 else np.nan
        stop_px = np.nan
        if stop_mode == 'prev_low_abs':
            stop_px = (prev_low - float(stop_abs)) if pd.notna(prev_low) else np.nan
        elif stop_mode == 'prev_low_pct':
            buf = stop_low_buffer if stop_low_buffer_local is None else stop_low_buffer_local
            stop_px = (prev_low * (1 - float(buf))) if pd.notna(prev_low) else np.nan

        sl_px = (entry_price * (1 - float(sl))) if (sl is not None) else np.nan
        tp_px = (entry_price * (1 + float(tp))) if (tp is not None) else np.nan

        max_pos = min(entry_pos + int(hold_max_tdays), len(df0) - 1)
        for pos in range(entry_pos + 1, max_pos + 1):
            day_open = df0.at[pos, 'open']
            day_high = df0.at[pos, 'high']
            day_low = df0.at[pos, 'low']
            day_close = df0.at[pos, 'close']
            pct = df0.at[pos, 'pct_chg']

            r_high = day_high / entry_price - 1
            r_low = day_low / entry_price - 1
            if pd.notna(r_high):
                mfe = max(mfe, float(r_high))
            if pd.notna(r_low):
                mae = min(mae, float(r_low))

            if stop_mode == 'none':
                hit_sl = False
            elif stop_mode in ['prev_low_abs', 'prev_low_pct']:
                hit_sl = pd.notna(stop_px) and pd.notna(day_low) and day_low <= stop_px
            else:
                hit_sl = (sl is not None) and pd.notna(sl_px) and pd.notna(day_low) and day_low <= sl_px

            hit_tp = (tp is not None) and pd.notna(tp_px) and pd.notna(day_high) and day_high >= tp_px
            hit_sup = pd.notna(sup) and pd.notna(day_low) and day_low <= sup
            hit_time = (pos == max_pos)

            if not (hit_sl or hit_sup or hit_tp or hit_time):
                continue

            # 同日多条件触发时：优先止盈 (B)
            if hit_tp:
                desired_reason = 'tp'
                trigger_px = tp_px
                if pd.notna(day_open) and pd.notna(trigger_px) and day_open >= trigger_px:
                    desired_exit_price = float(day_open)
                else:
                    desired_exit_price = float(trigger_px)
            elif hit_sl:
                desired_reason = 'sl_prev_low_abs' if stop_mode == 'prev_low_abs' else ('sl_prev_low_pct' if stop_mode == 'prev_low_pct' else 'sl')
                trigger_px = stop_px if stop_mode in ['prev_low_abs', 'prev_low_pct'] else sl_px
                if pd.notna(day_open) and pd.notna(trigger_px) and day_open <= trigger_px:
                    desired_exit_price = float(day_open)
                else:
                    desired_exit_price = float(trigger_px)
            elif hit_sup:
                desired_reason = 'support'
                trigger_px = sup
                if pd.notna(day_open) and pd.notna(trigger_px) and day_open <= trigger_px:
                    desired_exit_price = float(day_open)
                else:
                    desired_exit_price = float(trigger_px)
            else:
                desired_reason = 'time'
                desired_exit_price = float(day_close)

            if sell_block_limit_up and _is_limit_up(pct, up_th):
                continue

            exit_pos = pos
            exit_reason = desired_reason
            exit_price = desired_exit_price
            break

        if exit_pos is None:
            for pos in range(max_pos + 1, len(df0)):
                pct = df0.at[pos, 'pct_chg']
                if sell_block_limit_up and _is_limit_up(pct, up_th):
                    continue

                day_high = df0.at[pos, 'high']
                day_low = df0.at[pos, 'low']
                day_close = df0.at[pos, 'close']

                r_high = day_high / entry_price - 1
                r_low = day_low / entry_price - 1
                if pd.notna(r_high):
                    mfe = max(mfe, float(r_high))
                if pd.notna(r_low):
                    mae = min(mae, float(r_low))

                exit_pos = pos
                exit_reason = 'time'
                exit_price = float(day_close)
                break

        if exit_pos is None:
            exit_pos = len(df0) - 1
            exit_reason = 'end'

        if exit_price is None:
            exit_price = float(df0.at[exit_pos, 'close'])

        exit_date = df0.at[exit_pos, 'trade_date']
        hold_days = exit_pos - entry_pos
        gross_ret = exit_price / entry_price - 1
        net_ret = gross_ret - cost_round_trip if (cost_round_trip is not None and cost_round_trip > 0) else gross_ret
        return {
            'exit_date': exit_date,
            'exit_close': exit_price,
            'hold_days': hold_days,
            'exit_reason': exit_reason,
            'ret': gross_ret,
            'net_ret': net_ret,
            'exit_pos': exit_pos,
            'mfe': mfe,
            'mae': mae,
        }

    def _perf_metrics(nav, daily_ret, trade_rets=None, trade_hold_days=None, exposure=None, rf=0.0):
        nav = nav.dropna()
        daily_ret = daily_ret.reindex(nav.index).fillna(0)
        n = len(daily_ret)
        if n == 0:
            return pd.DataFrame()

        total_ret = float(nav.iloc[-1] - 1)
        ann_ret = float(nav.iloc[-1] ** (252 / n) - 1)
        ann_vol = float(daily_ret.std(ddof=0) * np.sqrt(252))
        sharpe = float((ann_ret - rf) / ann_vol) if ann_vol > 0 else np.nan

        roll_max = nav.cummax()
        dd = nav / roll_max - 1
        max_dd = float(dd.min())
        calmar = float(ann_ret / abs(max_dd)) if max_dd < 0 else np.nan

        winrate_day = float((daily_ret > 0).mean())

        out = {
            'total_return': total_ret,
            'annual_return': ann_ret,
            'annual_vol': ann_vol,
            'sharpe': sharpe,
            'max_drawdown': max_dd,
            'calmar': calmar,
            'winrate_day': winrate_day,
            'days': n,
        }

        if exposure is not None:
            out['exposure'] = float(exposure)

        if trade_rets is not None and len(trade_rets) > 0:
            tr = pd.Series(trade_rets).dropna()
            if len(tr) > 0:
                out['trades'] = int(len(tr))
                out['winrate_trade'] = float((tr > 0).mean())
                out['avg_trade_ret'] = float(tr.mean())
                out['median_trade_ret'] = float(tr.median())
                pos = tr[tr > 0].sum()
                neg = -tr[tr < 0].sum()
                out['profit_factor'] = float(pos / neg) if neg > 0 else np.nan

        if trade_hold_days is not None and len(trade_hold_days) > 0:
            hd = pd.Series(trade_hold_days).dropna()
            if len(hd) > 0:
                out['avg_hold_days'] = float(hd.mean())
                out['median_hold_days'] = float(hd.median())

        return pd.DataFrame([out]).T.rename(columns={0: 'value'})

    def _build_nav_from_trades(df_by_code, trades, start_date0, end_date0, use_net=False):
        tdays = get_trade_dates(start_date0, end_date0)
        idx = pd.to_datetime(pd.Series(tdays), format='%Y%m%d')
        sum_ret = pd.Series(0.0, index=idx)
        cnt = pd.Series(0.0, index=idx)
        cost_half = (cost_round_trip / 2) if (cost_round_trip is not None and cost_round_trip > 0) else 0.0

        for tr in trades:
            code = tr['code']
            entry_pos = int(tr['entry_pos'])
            exit_pos = int(tr['exit_pos'])
            df0 = df_by_code.get(code)
            if df0 is None:
                continue
            if exit_pos <= entry_pos:
                continue

            exit_px = tr.get('exit_close', None)
            try:
                exit_px = float(exit_px) if exit_px is not None else None
            except Exception:
                exit_px = None

            for pos in range(entry_pos + 1, exit_pos + 1):
                d = df0.at[pos, 'trade_date']
                dt = pd.to_datetime(d, format='%Y%m%d')
                if dt < idx.min() or dt > idx.max():
                    continue
                if pos == exit_pos and exit_px is not None and pd.notna(exit_px):
                    r = exit_px / df0.at[pos - 1, 'close'] - 1
                else:
                    r = df0.at[pos, 'close'] / df0.at[pos - 1, 'close'] - 1
                if use_net and cost_half > 0:
                    if pos == entry_pos + 1:
                        r -= cost_half
                    if pos == exit_pos:
                        r -= cost_half
                sum_ret.at[dt] += float(r)
                cnt.at[dt] += 1

        daily_ret = sum_ret.copy()
        daily_ret[cnt > 0] = sum_ret[cnt > 0] / cnt[cnt > 0]
        daily_ret[cnt == 0] = 0.0
        nav = (1 + daily_ret).cumprod()
        dd = nav / nav.cummax() - 1
        exposure = float((cnt > 0).mean())
        return nav, daily_ret, dd, exposure

    def _apply_portfolio_constraints(trades_df0):
        if trades_df0 is None or trades_df0.empty:
            return trades_df0

        df1 = trades_df0.copy()
        if 'score' not in df1.columns:
            df1['score'] = 0.0
        if 'mkt_cap' not in df1.columns:
            df1['mkt_cap'] = np.nan
        df1['mkt_cap'] = df1['mkt_cap'].astype(float).fillna(np.inf)
        df1 = df1.sort_values(['signal_date', 'score'], ascending=[True, False]).copy()
        df1['entry_date'] = df1['signal_date']

        active = []
        accepted_idx = []
        ever_bought = False

        for d, g in df1.groupby('entry_date', sort=True):
            active = [p for p in active if p['exit_date'] >= d]
            slots = int(max_positions) - len(active)
            if slots <= 0:
                continue

            cap = int(daily_max_entries)
            if (not ever_bought) and len(active) == 0:
                cap = int(max_positions)

            if cap <= 0:
                continue

            take_n = min(slots, cap, len(g))
            if take_n <= 0:
                continue

            chosen = g.sort_values(['score', 'mkt_cap'], ascending=[False, True]).head(take_n)
            accepted_idx.extend(chosen.index.tolist())
            for _, r in chosen.iterrows():
                active.append({'code': r['code'], 'exit_date': r['exit_date']})
            ever_bought = True

        return trades_df0.loc[accepted_idx].copy()

    events = []
    strat_events = []
    price_cache = {}
    for code in tqdm(codes, desc='Downloading & Scanning'):
        nm = name_map.get(code, '')
        if isinstance(nm, str) and ('ST' in nm or '*ST' in nm or '退' in nm):
            continue

        try:
            df = ts.pro_bar(ts_code=code, adj='qfq', start_date=start_dt, end_date=end_dt)
        except Exception:
            continue

        if df is None or df.empty:
            continue

        df = df.sort_values('trade_date').reset_index(drop=True)
        df.rename(columns={'vol': 'volume'}, inplace=True)

        if 'amount' in df.columns and df['amount'].notna().any():
            df['amount_yuan'] = df['amount'] * 1000
        else:
            df['amount_yuan'] = df['close'] * df['volume'] * 100

        df['ma5'] = df['close'].rolling(5).mean()
        df['ma10'] = df['close'].rolling(10).mean()
        df['ma20'] = df['close'].rolling(20).mean()
        df['v_ma20'] = df['volume'].rolling(20).mean()
        df['v_ma60'] = df['volume'].rolling(60).mean()
        df['amt_ma20'] = df['amount_yuan'].rolling(20).mean()
        df['pct_chg'] = df['close'].pct_change() * 100
        up_th = _limit_up_threshold(code)

        price_cache[code] = df

        rng = (df['high'] - df['low']).replace(0, np.nan)
        body_top = df[['open', 'close']].max(axis=1)
        upper_shadow_ratio = (df['high'] - body_top) / rng
        pullback_from_high = (df['high'] - df['close']) / df['high'].replace(0, np.nan)

        prev_is_limit_up = df['pct_chg'].shift(1) >= up_th
        boom_pullback = (pullback_from_high >= BOOM_PULLBACK_MIN) & (upper_shadow_ratio >= BOOM_UPPER_SHADOW_RATIO_MIN)
        boom_break_yhigh = df['high'] >= df['high'].shift(1) * BOOM_BREAK_YHIGH

        df['is_boom'] = (df['volume'] > df['volume'].shift(1)) & \
                        (df['volume'] >= df['v_ma20'] * BOOM_VOL_MULT) & \
                        (df['volume'] >= df['v_ma60'] * BOOM_VOL_MULT) & \
                        prev_is_limit_up & \
                        boom_break_yhigh & \
                        boom_pullback

        in_year = (df['trade_date'] >= start_date) & (df['trade_date'] <= end_date)
        boom_idx = df.index[df['is_boom'] & in_year].tolist()

        last_sig_pos = None

        for j in boom_idx:
            if pd.isna(df.at[j, 'amt_ma20']) or df.at[j, 'amt_ma20'] < 5e7:
                continue

            if last_sig_pos is not None and cooldown_tdays is not None and cooldown_tdays > 0:
                if j - last_sig_pos <= int(cooldown_tdays):
                    continue

            for k in range(j + 1, min(j + 6, len(df))):
                sig_date = df.at[k, 'trade_date']
                if sig_date < start_date or sig_date > end_date:
                    continue

                if _is_limit_up(df.at[k, 'pct_chg'], up_th):
                    continue

                t_vol = df.at[j, 'volume']
                prev_j = j - 1
                if prev_j < 0:
                    continue
                prev_mid = (df.at[prev_j, 'high'] + df.at[prev_j, 'low']) / 2
                close_px = df.at[k, 'close']
                sig_low = df.at[k, 'low']

                cond_vol = df.at[k, 'volume'] <= t_vol * float(vol_ratio_max)
                cond_price = sig_low >= prev_mid * (1 - MID_TOL)

                ma_vals = [df.at[k, 'ma5'], df.at[k, 'ma10'], df.at[k, 'ma20']]
                cond_ma = any((m > 0) and (close_px >= m) and (close_px <= m * (1 + float(ma_band))) for m in ma_vals if pd.notna(m))

                vol_ratio = (df.at[k, 'volume'] / t_vol) if (t_vol and pd.notna(t_vol)) else np.nan
                support_gap = (sig_low / prev_mid - 1) if (prev_mid and pd.notna(prev_mid)) else np.nan
                ma_gaps = []
                for m in ma_vals:
                    if pd.notna(m) and m > 0:
                        ma_gaps.append(close_px / m - 1)
                min_gap = np.min(ma_gaps) if len(ma_gaps) > 0 else np.nan

                score = 0.0
                if pd.notna(vol_ratio):
                    score += float(1 - vol_ratio) * 2.0
                if pd.notna(min_gap):
                    score += float(max(0.0, 1 - abs(min_gap) / max(float(ma_band), 1e-6))) * 1.0
                if pd.notna(support_gap):
                    score += float(max(0.0, 1 - support_gap / 0.05)) * 1.0
                if pd.notna(df.at[j, 'v_ma20']) and df.at[j, 'v_ma20'] > 0:
                    score += float(np.log1p(t_vol / df.at[j, 'v_ma20'])) * 0.5
                if pd.notna(df.at[j, 'v_ma60']) and df.at[j, 'v_ma60'] > 0:
                    score += float(np.log1p(t_vol / df.at[j, 'v_ma60'])) * 0.5

                if not (cond_vol and cond_price and cond_ma):
                    continue

                row = {
                    'code': code,
                    't_date': df.at[j, 'trade_date'],
                    'signal_date': sig_date,
                    'entry_close': close_px,
                    'mkt_cap': np.nan,
                    'score': score,
                    'sig_vol/t_vol': vol_ratio,
                    'support_gap': support_gap,
                    'min_close_vs_ma': min_gap,
                }

                for n in [1, 3, 5, 10]:
                    if k + n < len(df):
                        row[f'ret_{n}d'] = df.at[k + n, 'close'] / close_px - 1
                    else:
                        row[f'ret_{n}d'] = np.nan

                if cost_round_trip is not None and cost_round_trip > 0:
                    for n in [1, 3, 5, 10]:
                        v = row.get(f'ret_{n}d', np.nan)
                        row[f'net_ret_{n}d'] = v - cost_round_trip if pd.notna(v) else np.nan

                events.append(row)

                if stop_losses is not None and take_profits is not None:
                    buffers = stop_low_buffers if (stop_low_buffers is not None) else [stop_low_buffer]
                    for sl in stop_losses:
                        for tp in take_profits:
                            for buf in buffers:
                                sim = _simulate_exit(df, j, k, sl=sl, tp=tp, up_th=up_th, stop_low_buffer_local=buf)
                                strat_events.append({
                                    'code': code,
                                    't_date': df.at[j, 'trade_date'],
                                    'signal_date': sig_date,
                                    'entry_close': close_px,
                                    'entry_pos': k,
                                    'sl': _pct_to_decimal(sl),
                                    'tp': _pct_to_decimal(tp),
                                    'support_mode': support_mode,
                                    'stop_mode': stop_mode,
                                    'stop_low_buffer': float(buf) if buf is not None else np.nan,
                                    'mkt_cap': np.nan,
                                    'score': score,
                                    'sig_vol/t_vol': vol_ratio,
                                    'support_gap': support_gap,
                                    'min_close_vs_ma': min_gap,
                                    **sim,
                                })

                last_sig_pos = k
                break

    events_df = pd.DataFrame(events)
    if events_df.empty:
        print("年度区间内未找到任何信号")
        return events_df, pd.DataFrame()

    def _summarize(df, cols):
        summary = {}
        for c in cols:
            if c not in df.columns:
                continue
            s = df[c].dropna()
            if len(s) == 0:
                continue
            summary[c] = {
                'mean': s.mean(),
                'median': s.median(),
                'winrate': (s > 0).mean(),
                'count': len(s),
            }
        return pd.DataFrame(summary).T

    gross_cols = ['ret_1d', 'ret_3d', 'ret_5d', 'ret_10d']
    net_cols = ['net_ret_1d', 'net_ret_3d', 'net_ret_5d', 'net_ret_10d']

    summary_df = _summarize(events_df, gross_cols)
    print("\n--- 区间事件研究汇总 (未扣成本) ---")
    print(summary_df)
    if any(c in events_df.columns for c in net_cols):
        net_summary_df = _summarize(events_df, net_cols)
        print("\n--- 区间事件研究汇总 (扣除成本后) ---")
        print(net_summary_df)
    print(f"事件数: {len(events_df)}")

    events_df['year'] = events_df['signal_date'].astype(str).str[:4]
    by_year = []
    for y, g in events_df.groupby('year'):
        s = _summarize(g, gross_cols)
        if not s.empty:
            s.insert(0, 'year', y)
            by_year.append(s.reset_index().rename(columns={'index': 'metric'}))
    if by_year:
        by_year_df = pd.concat(by_year, ignore_index=True)
        print("\n--- 分年汇总 (未扣成本) ---")
        print(by_year_df.pivot(index='metric', columns='year', values='mean'))

    if strat_events:
        strat_df = pd.DataFrame(strat_events)
        strat_df['year'] = strat_df['signal_date'].astype(str).str[:4]

        def _summarize_by_group(df0):
            s = df0['ret'].dropna()
            mfe_s = df0['mfe'].dropna() if 'mfe' in df0.columns else pd.Series(dtype=float)
            mae_s = df0['mae'].dropna() if 'mae' in df0.columns else pd.Series(dtype=float)
            return pd.Series({
                'mean': s.mean() if len(s) else np.nan,
                'median': s.median() if len(s) else np.nan,
                'winrate': (s > 0).mean() if len(s) else np.nan,
                'avg_mfe': mfe_s.mean() if len(mfe_s) else np.nan,
                'avg_mae': mae_s.mean() if len(mae_s) else np.nan,
                'count': len(s),
            })

        def _summarize_by_group_net(df0):
            s = df0['net_ret'].dropna()
            mfe_s = df0['mfe'].dropna() if 'mfe' in df0.columns else pd.Series(dtype=float)
            mae_s = df0['mae'].dropna() if 'mae' in df0.columns else pd.Series(dtype=float)
            return pd.Series({
                'mean': s.mean() if len(s) else np.nan,
                'median': s.median() if len(s) else np.nan,
                'winrate': (s > 0).mean() if len(s) else np.nan,
                'avg_mfe': mfe_s.mean() if len(mfe_s) else np.nan,
                'avg_mae': mae_s.mean() if len(mae_s) else np.nan,
                'count': len(s),
            })

        if stop_mode == 'prev_low_pct':
            grid_keys = ['stop_low_buffer', 'tp']
        else:
            grid_keys = ['sl', 'tp']

        print("\n--- 策略化出场汇总 (未扣成本) ---")
        grid_gross = strat_df.groupby(grid_keys).apply(_summarize_by_group).reset_index()
        print(grid_gross.sort_values(grid_keys))

        print("\n--- 策略化出场汇总 (扣除成本后) ---")
        grid_net = strat_df.groupby(grid_keys).apply(_summarize_by_group_net).reset_index()
        print(grid_net.sort_values(grid_keys))

        print("\n--- 策略化出场分年均值 (扣除成本后, net_ret) ---")
        by_year_net = strat_df.groupby(grid_keys + ['year'])['net_ret'].mean().reset_index()
        print(by_year_net.pivot_table(index=grid_keys, columns='year', values='net_ret'))

        if plot_report:
            constrained_rank = []
            if stop_mode == 'prev_low_pct':
                rank_keys = ['stop_low_buffer', 'tp']
            else:
                rank_keys = ['sl', 'tp']

            for key_vals, g0 in strat_df.groupby(rank_keys):
                g1 = _apply_portfolio_constraints(g0)
                v = g1['net_ret'].dropna().mean() if g1 is not None and not g1.empty else np.nan
                mfe_v = g1['mfe'].dropna().mean() if g1 is not None and (not g1.empty) and ('mfe' in g1.columns) else np.nan
                mae_v = g1['mae'].dropna().mean() if g1 is not None and (not g1.empty) and ('mae' in g1.columns) else np.nan
                row = {k: (float(vv) if k != 'tp' else float(vv)) for k, vv in zip(rank_keys, key_vals if isinstance(key_vals, tuple) else (key_vals,))}
                row.update({'net_mean_constrained': v, 'avg_mfe': mfe_v, 'avg_mae': mae_v, 'count': 0 if g1 is None else int(len(g1))})
                constrained_rank.append(row)
            constrained_rank_df = pd.DataFrame(constrained_rank).sort_values('net_mean_constrained', ascending=False)

            print("\n--- 策略化出场汇总 (组合约束后, 扣除成本后) ---")
            print(constrained_rank_df)

            if plot_sl is None or plot_tp is None:
                best = constrained_rank_df.iloc[0]
                if 'sl' in best:
                    plot_sl = float(best['sl'])
                plot_tp = float(best['tp'])
                plot_buf = float(best['stop_low_buffer']) if 'stop_low_buffer' in best else None
            else:
                plot_buf = None

            if stop_mode == 'prev_low_pct':
                if plot_buf is None:
                    plot_buf = float(stop_low_buffer)
                sub = strat_df[(strat_df['tp'] == float(plot_tp)) & (strat_df['stop_low_buffer'] == float(plot_buf))].copy()
            else:
                sub = strat_df[(strat_df['sl'] == float(plot_sl)) & (strat_df['tp'] == float(plot_tp))].copy()
            if not sub.empty:
                sub = _apply_portfolio_constraints(sub)
                print(f"\n组合约束参数: max_positions={int(max_positions)}, daily_max_entries={int(daily_max_entries)} (首次建仓日不受每日上限)")
                print(f"约束后交易数: {len(sub)}")
                nav_gross, dr_gross, dd_gross, exposure = _build_nav_from_trades(price_cache, sub.to_dict('records'), start_date, end_date, use_net=False)
                nav_net, dr_net, dd_net, exposure_net = _build_nav_from_trades(price_cache, sub.to_dict('records'), start_date, end_date, use_net=True)

                m_gross = _perf_metrics(nav_gross, dr_gross, trade_rets=sub['ret'], trade_hold_days=sub['hold_days'], exposure=exposure)
                m_net = _perf_metrics(nav_net, dr_net, trade_rets=sub['net_ret'], trade_hold_days=sub['hold_days'], exposure=exposure_net)

                print("\n--- 聚宽式回测指标 (未扣成本) ---")
                print(m_gross)
                print("\n--- 聚宽式回测指标 (扣除成本后) ---")
                print(m_net)

                monthly = (1 + dr_net).resample('ME').prod() - 1
                ym = monthly.to_frame('ret')
                ym['year'] = ym.index.year
                ym['month'] = ym.index.month
                pivot = ym.pivot(index='year', columns='month', values='ret')

                fig = plt.figure(figsize=(14, 10))
                ax1 = plt.subplot2grid((3, 1), (0, 0))
                ax2 = plt.subplot2grid((3, 1), (1, 0))
                ax3 = plt.subplot2grid((3, 1), (2, 0))

                ax1.plot(nav_net.index, nav_net.values, label='NAV (net)')
                ax1.plot(nav_gross.index, nav_gross.values, label='NAV (gross)', alpha=0.5)
                if stop_mode == 'prev_low_pct':
                    ax1.set_title(f'NAV Curve | universe={universe} | S={support_mode} | stop_buf={plot_buf} | TP={plot_tp}')
                else:
                    ax1.set_title(f'NAV Curve | universe={universe} | S={support_mode} | SL={plot_sl} | TP={plot_tp}')
                ax1.legend()
                ax1.grid(True, alpha=0.3)

                ax2.fill_between(dd_net.index, dd_net.values, 0, color='tab:red', alpha=0.3)
                ax2.set_title('Drawdown (net)')
                ax2.grid(True, alpha=0.3)

                im = ax3.imshow(pivot.fillna(0).values, aspect='auto', cmap='RdYlGn', vmin=-0.2, vmax=0.2)
                ax3.set_yticks(range(len(pivot.index)))
                ax3.set_yticklabels(pivot.index.astype(str))
                ax3.set_xticks(range(12))
                ax3.set_xticklabels([str(i) for i in range(1, 13)])
                ax3.set_title('Monthly Returns (net)')
                fig.colorbar(im, ax=ax3, fraction=0.046, pad=0.04)

                plt.tight_layout()
                if stop_mode == 'prev_low_pct':
                    out_png = f"backtest_report_{universe}_{start_date}_{end_date}_S{support_mode}_buf{plot_buf}_tp{plot_tp}.png"
                else:
                    out_png = f"backtest_report_{universe}_{start_date}_{end_date}_S{support_mode}_sl{plot_sl}_tp{plot_tp}.png"
                plt.savefig(out_png, dpi=160)
                plt.close(fig)
                print(f"\n回测图已保存: {out_png}")

    return events_df, summary_df

def get_data(ts_code, target_date):
    """获取指定日期前约40天的数据"""
    # 稍微多取一点数据确保均线计算准确
    target_date = normalize_trade_date(target_date, direction='prev')
    start_dt = tday_offset(target_date, -160)
    end_dt = tday_offset(target_date, 30)
    try:
        df = ts.pro_bar(ts_code=ts_code, adj='qfq', start_date=start_dt, end_date=end_dt)
        if df is None or len(df) < 80: return None
        return df.sort_values('trade_date').reset_index(drop=True)
    except:
        return None

def get_hs300_codes(target_date):
    target_date = normalize_trade_date(target_date, direction='prev')
    start_dt = tday_offset(target_date, -90)
    try:
        w = pro.index_weight(index_code='000300.SH', start_date=start_dt, end_date=target_date, fields='trade_date,con_code')
        if w is None or w.empty:
            return None
        last_dt = w['trade_date'].max()
        return w[w['trade_date'] == last_dt]['con_code'].tolist()
    except Exception as e:
        print(f"获取沪深300成分失败: {e}")
        return None

def run_scanner(date_str, universe='hs300'):
    print(f"--- 开始执行扫描: {date_str} ---")
    
    # 获取全市场快照（为了市值和基本过滤）
    try:
        snapshot = pro.daily_basic(trade_date=date_str, fields='ts_code,total_mv')
        prices = pro.daily(trade_date=date_str, fields='ts_code,pct_chg,vol,close')
        market = pd.merge(snapshot, prices, on='ts_code')
    except Exception as e:
        print(f"获取市场快照失败: {e}")
        return

    try:
        names = pro.stock_basic(list_status='L', fields='ts_code,name')
        market = pd.merge(market, names, on='ts_code', how='left')
    except Exception as e:
        print(f"获取股票名称失败: {e}")
        return

    market = market[market['pct_chg'] < 9.8]
    market = market[~market['ts_code'].str.endswith('.BJ')]
    market = market[~market['ts_code'].str.startswith('300')]
    market = market[~market['ts_code'].str.startswith('688')]
    market = market[~market['name'].fillna('').str.contains('ST|\*ST|退', regex=True)]

    if universe == 'hs300':
        hs300 = get_hs300_codes(date_str)
        if hs300:
            market = market[market['ts_code'].isin(set(hs300))]
            print(f"使用沪深300成分股股票池: {len(hs300)}")
        else:
            print("沪深300成分获取失败，改用当前过滤后的全市场股票池")

    candidates = []
    # 限制扫描前200只（测试用），正式跑可以去掉 [:200]
    test_pool = market.sort_values('vol', ascending=False).head(500)
    print(f"计划扫描 {len(test_pool)} 只个股...")
    
    count_t_day = 0
    count_logic = 0
    count_amt_ok = 0
    count_t_has = 0
    sig_pass_vol = 0
    sig_pass_price = 0
    sig_pass_ma = 0
    sig_pass_all = 0
    debug_rows = []
    boom_any_last5 = 0
    boom_c1_last5 = 0
    boom_c2_last5 = 0
    boom_c3_last5 = 0
    boom_c4_last5 = 0

    for idx, row in tqdm(test_pool.iterrows()):
        code = row['ts_code']
        df = get_data(code, date_str)
        if df is None: continue
        
        # 字段映射
        df.rename(columns={'vol': 'volume'}, inplace=True)

        if 'amount' in df.columns and df['amount'].notna().any():
            df['amount_yuan'] = df['amount'] * 1000
        else:
            df['amount_yuan'] = df['close'] * df['volume'] * 100
        
        # 计算指标
        df['ma5'] = df['close'].rolling(5).mean()
        df['ma10'] = df['close'].rolling(10).mean()
        df['ma20'] = df['close'].rolling(20).mean()
        df['v_ma20'] = df['volume'].rolling(20).mean()
        df['v_ma60'] = df['volume'].rolling(60).mean()
        df['amt_ma20'] = df['amount_yuan'].rolling(20).mean()
        df['pct_chg'] = df['close'].pct_change() * 100

        date_idx = df.index[df['trade_date'] == date_str]
        if len(date_idx) == 0:
            continue
        i = int(date_idx[0])

        if pd.isna(df.at[i, 'amt_ma20']) or df.at[i, 'amt_ma20'] < 5e7:
            continue
        count_amt_ok += 1
        
        # T日判断 (爆量)
        up_th = 9.8
        rng = (df['high'] - df['low']).replace(0, np.nan)
        body_top = df[['open', 'close']].max(axis=1)
        upper_shadow_ratio = (df['high'] - body_top) / rng
        pullback_from_high = (df['high'] - df['close']) / df['high'].replace(0, np.nan)

        prev_is_limit_up = df['pct_chg'].shift(1) >= up_th
        boom_pullback = (pullback_from_high >= BOOM_PULLBACK_MIN) & (upper_shadow_ratio >= BOOM_UPPER_SHADOW_RATIO_MIN)
        boom_break_yhigh = df['high'] >= df['high'].shift(1) * BOOM_BREAK_YHIGH

        df['is_T_day'] = (df['volume'] > df['volume'].shift(1)) & \
                         (df['volume'] >= df['v_ma20'] * BOOM_VOL_MULT) & \
                         (df['volume'] >= df['v_ma60'] * BOOM_VOL_MULT) & \
                         prev_is_limit_up & \
                         boom_break_yhigh & \
                         boom_pullback

        w_start = max(i - 5, 1)
        w_end = i - 1
        if w_end >= w_start:
            w = df.loc[w_start:w_end].copy()
            c1 = (w['volume'] > df['volume'].shift(1).loc[w_start:w_end])
            c2 = (w['volume'] >= w['v_ma20'] * BOOM_VOL_MULT)
            c3 = (w['volume'] >= w['v_ma60'] * BOOM_VOL_MULT)
            c4 = (w['high'] >= df['high'].shift(1).loc[w_start:w_end])
            boom_c1_last5 += int(c1.any())
            boom_c2_last5 += int(c2.any())
            boom_c3_last5 += int(c3.any())
            boom_c4_last5 += int(c4.any())
            boom_any_last5 += int((c1 & c2 & c3 & c4).any())
        
        # 寻找最近5天内的T日
        found_t = False
        for lookback in trange(1, 6):
            t_idx = i - lookback
            if t_idx >= 0 and df.at[t_idx, 'is_T_day']:
                found_t = True
                t_vol = df.at[t_idx, 'volume']
                prev_t = t_idx - 1
                if prev_t < 0:
                    continue
                prev_mid = (df.at[prev_t, 'high'] + df.at[prev_t, 'low']) / 2
                
                # 判定: 缩量0.5 + 不破位 + 均线1%
                cond_vol = df.at[i, 'volume'] <= t_vol * VOL_RATIO_MAX
                cond_price = df.at[i, 'low'] >= prev_mid * (1 - MID_TOL)
                
                # 均线支持
                ma_vals = [df.at[i, 'ma5'], df.at[i, 'ma10'], df.at[i, 'ma20']]
                close_px = df.at[i, 'close']
                cond_ma = any((m > 0) and (close_px >= m) and (close_px <= m * (1 + MA_BAND)) for m in ma_vals if pd.notna(m))

                count_t_has += 1
                sig_pass_vol += int(cond_vol)
                sig_pass_price += int(cond_price)
                sig_pass_ma += int(cond_ma)
                sig_pass_all += int(cond_vol and cond_price and cond_ma)

                if len(debug_rows) < 20:
                    vol_ratio = (df.at[i, 'volume'] / t_vol) if (t_vol and pd.notna(t_vol)) else np.nan
                    close_vs_mid = (df.at[i, 'low'] / prev_mid - 1) if (prev_mid and pd.notna(prev_mid)) else np.nan
                    ma_gaps = []
                    for m in ma_vals:
                        if pd.notna(m) and m > 0:
                            ma_gaps.append(close_px / m - 1)
                    min_gap = np.min(ma_gaps) if len(ma_gaps) > 0 else np.nan
                    debug_rows.append({
                        'code': code,
                        't_date': df.at[t_idx, 'trade_date'],
                        'signal_date': df.at[i, 'trade_date'],
                        't_vol': t_vol,
                        'sig_vol': df.at[i, 'volume'],
                        'sig_vol/t_vol': vol_ratio,
                        'close': close_px,
                        't_mid': prev_mid,
                        'close_vs_mid': close_vs_mid,
                        'min_close_vs_ma': min_gap,
                        'pass_vol': cond_vol,
                        'pass_price': cond_price,
                        'pass_ma': cond_ma,
                    })
                
                if cond_vol and cond_price and cond_ma:
                    fwd = {}
                    for n in [1, 3, 5, 10]:
                        if i + n < len(df):
                            fwd[f'ret_{n}d'] = df.at[i + n, 'close'] / close_px - 1
                        else:
                            fwd[f'ret_{n}d'] = np.nan
                    vol_ratio = (df.at[i, 'volume'] / t_vol) if (t_vol and pd.notna(t_vol)) else np.nan
                    support_gap = (df.at[i, 'low'] / prev_mid - 1) if (prev_mid and pd.notna(prev_mid)) else np.nan
                    score = 0.0
                    if pd.notna(vol_ratio):
                        score += float(1 - vol_ratio) * 2.0
                    if pd.notna(min_gap):
                        score += float(max(0.0, 1 - abs(min_gap) / max(MA_BAND, 1e-6))) * 1.0
                    if pd.notna(support_gap):
                        score += float(max(0.0, 1 - support_gap / 0.05)) * 1.0
                    if pd.notna(df.at[t_idx, 'v_ma20']) and df.at[t_idx, 'v_ma20'] > 0:
                        score += float(np.log1p(t_vol / df.at[t_idx, 'v_ma20'])) * 0.5
                    if pd.notna(df.at[t_idx, 'v_ma60']) and df.at[t_idx, 'v_ma60'] > 0:
                        score += float(np.log1p(t_vol / df.at[t_idx, 'v_ma60'])) * 0.5

                    candidates.append({
                        'code': code,
                        'mkt_cap': row['total_mv'],
                        'close': close_px,
                        't_date': df.at[t_idx, 'trade_date'],
                        'signal_date': df.at[i, 'trade_date'],
                        'sig_vol/t_vol': vol_ratio,
                        'support_gap': support_gap,
                        'min_close_vs_ma': min_gap,
                        'score': score,
                        **fwd
                    })
                    count_logic += 1
                break
        if found_t: count_t_day += 1

    print(f"扫描完成！成交额过滤后剩余: {count_amt_ok} 只")
    print(f"扫描完成！近5日满足爆量子条件的股票数: c1量增={boom_c1_last5}, c2>={BOOM_VOL_MULT}xMA20={boom_c2_last5}, c3>={BOOM_VOL_MULT}xMA60={boom_c3_last5}, c4盘中>=昨高={boom_c4_last5}, 四项同时满足={boom_any_last5}")
    print(f"扫描完成！找到 T日爆量个股: {count_t_day} 只，最终符合买入逻辑: {len(candidates)} 只")

    if count_t_has > 0:
        print(f"扫描完成！近5日存在T日的股票: {count_t_has} 只；信号子条件通过数: 缩量={sig_pass_vol}, 守中点={sig_pass_price}, 贴均线={sig_pass_ma}, 三项同时={sig_pass_all}")
        if debug_rows:
            dbg = pd.DataFrame(debug_rows)
            print("\n--- T日候选诊断 (最多20条) ---")
            print(dbg[['code','t_date','signal_date','sig_vol/t_vol','close_vs_mid','min_close_vs_ma','pass_vol','pass_price','pass_ma']])
    
    if candidates:
        res_df = pd.DataFrame(candidates)
        res_df = res_df.sort_values(['score', 'mkt_cap'], ascending=[False, True])
        print("\n--- 最终入选清单 (按信号质量score排序, 市值为次级排序) ---")
        show_cols = [c for c in ['code', 'mkt_cap', 'score', 'sig_vol/t_vol', 'support_gap', 'min_close_vs_ma', 't_date', 'signal_date'] if c in res_df.columns]
        print(res_df[show_cols].head(10))

        ret_cols = [c for c in ['ret_1d', 'ret_3d', 'ret_5d', 'ret_10d'] if c in res_df.columns]
        if ret_cols:
            summary = {}
            for c in ret_cols:
                s = res_df[c].dropna()
                if len(s) == 0:
                    continue
                summary[c] = {
                    'mean': s.mean(),
                    'median': s.median(),
                    'winrate': (s > 0).mean(),
                    'count': len(s),
                }
            if summary:
                print("\n--- 信号后收益统计 (未扣成本) ---")
                print(pd.DataFrame(summary).T)
        return res_df
    else:
        print("\n今日无符合条件的股票，建议检查参数是否过严。")
        return pd.DataFrame()

# --- 这里是真正的入口 ---
if __name__ == "__main__":
    mode = 'year'
    if mode == 'year':
        events_df, summary_df = event_study(
    '20220101', '20251231',
    universe='zz1000',
    support_mode='S2',
    stop_mode='prev_low_pct',
    stop_low_buffer=0.02,
    stop_losses=[-0.05],
    take_profits=[10, 15, 20, 30],
    hold_max_tdays=10,
    sell_block_limit_up=True,   # H2
    max_positions=10,
    daily_max_entries=5,
    plot_report=True,           # 生成图+指标
    )   # 'all' 'hs300' 'zz1000'
    else:
        target = '20240320'
        run_scanner(target, universe='hs300')

