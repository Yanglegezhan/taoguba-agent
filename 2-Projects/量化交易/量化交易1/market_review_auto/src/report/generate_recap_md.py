import argparse
import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd


def _read_json(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _read_df(path: Path) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame([])
    try:
        return pd.read_csv(path)
    except Exception:
        try:
            return pd.read_csv(path, encoding="utf-8-sig")
        except Exception:
            return pd.DataFrame([])


def _zfill6(code: Any) -> str:
    s = "" if code is None else str(code).strip()
    if not s:
        return ""
    return s.zfill(6)


def _fmt_float(x: Any, nd: int = 2) -> str:
    try:
        return f"{float(x):.{nd}f}"
    except Exception:
        return ""


def _fmt_int(x: Any) -> str:
    try:
        return f"{int(float(x))}"
    except Exception:
        return ""


def _fmt_pct_point(x: Any, nd: int = 2) -> str:
    """pct_chg like 1.23 means +1.23%"""
    s = _fmt_float(x, nd)
    return f"{s}%" if s != "" else ""


def _fmt_ratio_pct(x: Any, nd: int = 2) -> str:
    """ratio like 0.1234 means 12.34%"""
    try:
        v = float(x)
    except Exception:
        return ""
    return f"{v * 100:.{nd}f}%"


def _fmt_yi(x: Any, nd: int = 2) -> str:
    try:
        return f"{float(x) / 1e8:.{nd}f}"
    except Exception:
        return ""


def _read_anchor_intraday(data_dir: Path, code: str) -> pd.DataFrame:
    c = str(code or "").zfill(6)
    f = data_dir / "anchors_intraday" / f"{c}.csv"
    if not f.exists():
        return pd.DataFrame([])
    df = _read_df(f)
    if df.empty:
        return pd.DataFrame([])
    if "datetime" in df.columns:
        df["datetime"] = pd.to_datetime(df["datetime"], errors="coerce")
        df = df[df["datetime"].notna()].copy()
        df.sort_values("datetime", inplace=True)
        df["time_label"] = df["datetime"].dt.strftime("%H:%M")
    for c0 in ["open", "close", "high", "low", "volume", "amount"]:
        if c0 in df.columns:
            df[c0] = pd.to_numeric(df[c0], errors="coerce")
    for c0 in ["close", "high", "low"]:
        if c0 in df.columns:
            df = df[df[c0].notna()].copy()
    return df


def _intraday_metrics(df: pd.DataFrame) -> Dict[str, Any]:
    if df is None or df.empty:
        return {}

    high = float(df["high"].max()) if "high" in df.columns else None
    low = float(df["low"].min()) if "low" in df.columns else None
    close_last = float(df["close"].iloc[-1]) if "close" in df.columns else None

    vwap = None
    if "amount" in df.columns and "volume" in df.columns:
        denom = float(df["volume"].fillna(0).sum())
        if denom > 0:
            vwap = float(df["amount"].fillna(0).sum()) / denom

    early = df
    if "time_label" in df.columns:
        early = df[df["time_label"] <= "10:00"].copy()
    early_high = float(early["high"].max()) if (not early.empty and "high" in early.columns) else None
    early_low = float(early["low"].min()) if (not early.empty and "low" in early.columns) else None

    return {
        "high": high,
        "low": low,
        "close": close_last,
        "vwap": vwap,
        "early_high": early_high,
        "early_low": early_low,
    }


def _md_table(headers: List[str], rows: List[List[str]]) -> str:
    hs = [h.replace("\n", " ").strip() for h in headers]
    out = []
    out.append("|" + "|".join(hs) + "|")
    out.append("|" + "|".join(["---"] * len(hs)) + "|")
    for r in rows:
        rr = [("" if c is None else str(c)).replace("\n", " ").strip() for c in r]
        out.append("|" + "|".join(rr) + "|")
    return "\n".join(out)


def _as_date_cn(date_yyyymmdd: str) -> str:
    s = (date_yyyymmdd or "").strip()
    if len(s) == 8 and s.isdigit():
        return f"{s[0:4]}年{s[4:6]}月{s[6:8]}日"
    return s


def _load_code_name_map(data_dir: Path) -> Dict[str, str]:
    m: Dict[str, str] = {}
    for p in [data_dir / "limitup_events.csv", data_dir / "consecutive_board.csv"]:
        df = _read_df(p)
        if df.empty or "code" not in df.columns:
            continue
        if "name" not in df.columns:
            continue
        for _, r in df[["code", "name"]].iterrows():
            c = _zfill6(r.get("code"))
            n = "" if r.get("name") is None else str(r.get("name")).strip()
            if c and n and c not in m:
                m[c] = n
    return m


def _fmt_stock(code: Any, name: Any, code_to_name: Dict[str, str]) -> str:
    c = _zfill6(code)
    n0 = "" if name is None else str(name).strip()
    n = n0 or (code_to_name.get(c, "") if c else "")
    if n and c:
        return f"{n}({c})"
    return n or c


def _render_anchor_gallery(anchors_meta: List[Dict[str, Any]], plots_dir_name: str = "anchors_intraday_plots") -> str:
    if not anchors_meta:
        return ""

    name_by_code: Dict[str, str] = {}
    for a in anchors_meta:
        if not isinstance(a, dict):
            continue
        c = str(a.get("code") or "").zfill(6)
        n = "" if a.get("name") is None else str(a.get("name")).strip()
        if c and n and c not in name_by_code:
            name_by_code[c] = n

    def group(tag: str) -> List[Dict[str, Any]]:
        return [a for a in anchors_meta if str(a.get("tag") or "") == tag]

    groups: List[Tuple[str, str, List[Dict[str, Any]]]] = [
        ("昨日多头风标", "昨日多头风标（3）", group("昨日多头风标")[:3]),
        ("昨日空头风标", "昨日空头风标（3）", group("昨日空头风标")[:3]),
        ("当日锚", "当日锚（节选）", group("当日锚")[:6]),
    ]

    parts: List[str] = []
    for _tag, title, items in groups:
        if not items:
            continue
        parts.append(f"### {title}")
        # Use HTML for compact layout
        parts.append("<table>")
        parts.append("<tr>")
        for it in items:
            code = str(it.get("code") or "").zfill(6)
            name = str(name_by_code.get(code, "") or "").strip()
            plot = f"{plots_dir_name}/{code}.png"
            label = f"{name}({code})" if name else code
            parts.append(
                "<td style=\"padding:4px; text-align:center;\">"
                f"<div><b>{label}</b></div>"
                f"<img src=\"{plot}\" width=\"320\"/>"
                "</td>"
            )
        parts.append("</tr>")
        parts.append("</table>")
        parts.append("")
    return "\n".join(parts)


def generate_markdown(data_dir: Path, out_path: Path) -> Path:
    market_overview = _read_json(data_dir / "market_overview.json")
    market_compare = _read_json(data_dir / "market_compare.json")
    ladder_stats = _read_json(data_dir / "ladder_stats.json")
    anchors_marks = _read_json(data_dir / "anchors_marks.json")

    concept_day_stats = _read_df(data_dir / "concept_day_stats.csv")
    events_enriched = _read_df(data_dir / "events_enriched.csv")
    event_topic_links = _read_df(data_dir / "event_topic_links.csv")

    consecutive_board = _read_df(data_dir / "consecutive_board.csv")
    limitup_events = _read_df(data_dir / "limitup_events.csv")
    limitdown_list = _read_df(data_dir / "limitdown_list.csv")

    anchors_meta_path = data_dir / "anchors_intraday.json"
    anchors_meta: List[Dict[str, Any]] = []
    if anchors_meta_path.exists():
        try:
            anchors_meta = json.loads(anchors_meta_path.read_text(encoding="utf-8"))
            if not isinstance(anchors_meta, list):
                anchors_meta = []
        except Exception:
            anchors_meta = []

    llm_recap_text = ""
    llm_recap_path = data_dir / "llm_recap.txt"
    if llm_recap_path.exists():
        llm_recap_text = llm_recap_path.read_text(encoding="utf-8", errors="ignore").strip()

    date_str = str(market_overview.get("date") or data_dir.name)
    title_date_cn = _as_date_cn(date_str)

    code_to_name = _load_code_name_map(data_dir)
    for a in anchors_meta:
        if not isinstance(a, dict):
            continue
        c = str(a.get("code") or "").zfill(6)
        n = "" if a.get("name") is None else str(a.get("name")).strip()
        if c and n and c not in code_to_name:
            code_to_name[c] = n

    out_path.parent.mkdir(parents=True, exist_ok=True)

    md: List[str] = []
    md.append(f"# A股复盘（{title_date_cn}）")
    md.append("")
    md.append("## 目录")
    md.append("- 0. 摘要")
    md.append("- 1. 市场环境与广度")
    md.append("- 2. 资金进攻顺序（板块/产业链）")
    md.append("- 3. 题材强度（板块统计）")
    md.append("- 4. 连板梯队与晋级率结构")
    md.append("- 5. 事件驱动与因果线索")
    md.append("- 6. 锚定分时（昨日风标 + 当日锚）")
    md.append("- 7. 明日预案（龙头选手 / 龙空龙选手）")
    md.append("- 附：LLM复盘正文")
    md.append("")

    # 0 summary
    md.append("## 0. 摘要")
    lu = market_overview.get("limitup_count")
    ld = market_overview.get("limitdown_count")
    br = market_overview.get("broken_rate")
    up = market_overview.get("up_count")
    down = market_overview.get("down_count")
    flat = market_overview.get("flat_count")
    total = market_overview.get("total_count")
    turnover = market_overview.get("turnover")

    md.append(f"- **涨停/跌停**：{_fmt_int(lu)} / {_fmt_int(ld)}")
    md.append(f"- **炸板率**：{_fmt_ratio_pct(br, 2)}")
    md.append(f"- **上涨/下跌/平盘/总计**：{_fmt_int(up)} / {_fmt_int(down)} / {_fmt_int(flat)} / {_fmt_int(total)}")
    md.append(f"- **两市成交额（估算）**：{_fmt_yi(turnover, 2)} 亿")

    # 1->2
    upgrade_12 = (((market_overview.get("ladder") or {}).get("upgrade_rates") or {}).get("1->2"))
    if upgrade_12 is None:
        upgrade_12 = ((ladder_stats.get("upgrade_rates") or {}).get("1->2"))
    md.append(f"- **1→2 晋级率**：{_fmt_ratio_pct(upgrade_12, 2)}")

    md.append("")

    # indices summary
    idx = market_overview.get("indices") or {}
    idx_rows = []
    for k, name in [("SH000001", "上证"), ("SZ399001", "深成"), ("SZ399006", "创业板"), ("SH000688", "科创50")]:
        d = idx.get(k) or {}
        if not isinstance(d, dict) or not d:
            continue
        idx_rows.append(
            [
                name,
                _fmt_float(d.get("open"), 2),
                _fmt_float(d.get("high"), 2),
                _fmt_float(d.get("low"), 2),
                _fmt_float(d.get("close"), 2),
                _fmt_yi(d.get("amount"), 2),
            ]
        )

    if idx_rows:
        md.append(_md_table(["指数", "开盘", "最高", "最低", "收盘", "成交额(亿)"], idx_rows))
        md.append("")

    # Compare
    if isinstance(market_compare.get("today"), dict) and isinstance(market_compare.get("prev"), dict):
        t = market_compare.get("today") or {}
        p = market_compare.get("prev") or {}
        md.append("- **与前一交易日对比**：")
        md.append(f"  - 涨停：{_fmt_int(p.get('limitup_count'))} → {_fmt_int(t.get('limitup_count'))}")
        md.append(f"  - 跌停：{_fmt_int(p.get('limitdown_count'))} → {_fmt_int(t.get('limitdown_count'))}")
        md.append(f"  - 炸板率：{_fmt_ratio_pct(p.get('broken_rate'), 2)} → {_fmt_ratio_pct(t.get('broken_rate'), 2)}")
        md.append(f"  - 2板及以上：{_fmt_int(p.get('consecutive_ge2_count'))} → {_fmt_int(t.get('consecutive_ge2_count'))}")
        md.append("")

    # 1 Market env
    md.append("## 1. 市场环境与广度")
    md.append("### 广度与情绪")
    md.append(
        _md_table(
            ["指标", "数值"],
            [
                ["上涨家数", _fmt_int(up)],
                ["下跌家数", _fmt_int(down)],
                ["平盘家数", _fmt_int(flat)],
                ["总计（有效样本）", _fmt_int(total)],
                ["涨停家数", _fmt_int(lu)],
                ["跌停家数", _fmt_int(ld)],
                ["炸板率", _fmt_ratio_pct(br, 2)],
                ["两市成交额（估算，亿）", _fmt_yi(turnover, 2)],
            ],
        )
    )
    md.append("")

    md.append("### 说明")
    md.append("- 上涨/下跌/平盘统计来自全市场快照 `pct_chg` 的数值化结果（已做缺失与类型容错）。")
    md.append("- 成交额统一折算为 **亿**（= 1e8）并保留两位小数；涨幅类指标保留两位小数。")
    md.append("")

    # 2 attack sequence
    md.append("## 2. 资金进攻顺序（板块/产业链）")
    chain_plot = data_dir / "attack_sequence_chain.png"
    chain_plot2 = data_dir / "attack_sequence_chain_annotated.png"
    if chain_plot.exists():
        md.append(f"![资金进攻顺序-产业链]({chain_plot.name})")
        md.append("")
    if chain_plot2.exists():
        md.append(f"![资金进攻顺序-主线标注]({chain_plot2.name})")
        md.append("")

    # Best-effort: list chains by latest cumulative limitups from concept_timeseries.csv mapped to chains
    ts = _read_df(data_dir / "concept_timeseries.csv")
    if not ts.empty and "concept_name" in ts.columns and "limitup_count" in ts.columns:
        ts2 = ts.copy()
        ts2["concept_name"] = ts2["concept_name"].astype(str)
        ts2["limitup_count"] = pd.to_numeric(ts2["limitup_count"], errors="coerce")
        ts2 = ts2[ts2["limitup_count"].notna()].copy()
        latest = ts2.groupby("concept_name")["limitup_count"].max().sort_values(ascending=False)
        top = latest.head(12)
        rows = [[k, _fmt_int(v)] for k, v in top.items()]
        if rows:
            md.append("### 题材线（原始概念）Top（按日内累计涨停数）")
            md.append(_md_table(["题材/板块", "累计涨停数"], rows))
            md.append("")

    md.append("## 3. 题材强度（板块统计）")
    if concept_day_stats is None or concept_day_stats.empty:
        md.append("(无 concept_day_stats.csv)")
        md.append("")
    else:
        df = concept_day_stats.copy()
        for c in [
            "constituents",
            "limitup_count",
            "limitdown_count",
            "up_count",
            "down_count",
            "flat_count",
            "avg_pct_chg",
            "sum_vol",
            "sum_amount",
        ]:
            if c in df.columns:
                df[c] = pd.to_numeric(df[c], errors="coerce")

        sort_cols = [c for c in ["limitup_count", "up_count", "avg_pct_chg"] if c in df.columns]
        if sort_cols:
            df = df.sort_values(sort_cols, ascending=[False] * len(sort_cols))

        rows = []
        for _, r in df.head(20).iterrows():
            rows.append(
                [
                    str(r.get("concept_name") or ""),
                    _fmt_int(r.get("limitup_count")),
                    _fmt_int(r.get("limitdown_count")),
                    _fmt_int(r.get("up_count")),
                    _fmt_int(r.get("down_count")),
                    _fmt_int(r.get("flat_count")),
                    _fmt_int(r.get("constituents")),
                    _fmt_pct_point(r.get("avg_pct_chg"), 2),
                    _fmt_yi(r.get("sum_vol"), 2),
                    _fmt_yi(r.get("sum_amount"), 2),
                ]
            )

        md.append(
            _md_table(
                ["板块", "涨停数", "跌停数", "上涨家数", "下跌家数", "平盘家数", "成分股数", "平均涨幅", "成交量(亿)", "成交额(亿)"],
                rows,
            )
        )
        md.append("")

    # 4 ladder
    md.append("## 4. 连板梯队与晋级率结构")
    lv = ladder_stats.get("levels") if isinstance(ladder_stats.get("levels"), list) else []
    if not lv:
        lv = (market_overview.get("ladder") or {}).get("levels") or []

    if isinstance(lv, list) and lv:
        rows = []
        for it in lv:
            fr = it.get("from")
            rows.append(
                [
                    f"{_fmt_int(fr)}→{_fmt_int((fr or 0) + 1)}" if fr is not None else "",
                    _fmt_int(it.get("upgraded")),
                    _fmt_int(it.get("total")),
                    _fmt_ratio_pct(it.get("upgrade_rate"), 2),
                    _fmt_int(it.get("broken")),
                    _fmt_int(it.get("still_limitup")),
                ]
            )
        md.append(_md_table(["晋级路径", "晋级数", "基数", "晋级率", "断板数", "仍涨停数"], rows))
        md.append("")
    else:
        md.append("(无 ladder_stats)")
        md.append("")

    # 5 events
    md.append("## 5. 事件驱动与因果线索")
    if events_enriched is None or events_enriched.empty:
        md.append("(无 events_enriched.csv)")
        md.append("")
    else:
        df = events_enriched.copy()
        cols = [c for c in ["time_label", "title", "chains", "keywords", "source"] if c in df.columns]
        df = df[cols].head(15)
        rows = []
        for _, r in df.iterrows():
            rows.append(
                [
                    str(r.get("time_label") or ""),
                    str(r.get("title") or "").replace("\n", " ")[:80],
                    str(r.get("chains") or "").replace("\n", " "),
                    str(r.get("keywords") or "").replace("\n", " "),
                ]
            )
        md.append(_md_table(["时间", "事件", "链条", "关键词"], rows))
        md.append("")

    if event_topic_links is not None and not event_topic_links.empty:
        md.append("### 事件-题材-涨停关联（节选）")
        df = event_topic_links.copy()
        df = df.head(10)
        rows = []
        for _, r in df.iterrows():
            rows.append(
                [
                    str(r.get("event_time") or "").replace("\n", " ")[:10],
                    str(r.get("chain") or ""),
                    str(r.get("event_title") or "").replace("\n", " ")[:50],
                ]
            )
        md.append(_md_table(["时间", "链条", "事件标题"], rows))
        md.append("")

    # 6 anchors
    md.append("## 6. 锚定分时（昨日风标 + 当日锚）")
    md.append(
        "- 锚定分时图片来自 `anchors_intraday_plots/`，已做紧凑尺寸优化，适合在 Markdown 中并排查看。"
    )
    md.append("")
    gallery = _render_anchor_gallery(anchors_meta)
    if gallery:
        md.append(gallery)
    else:
        md.append("(无锚定分时数据)")
        md.append("")

    # 7 plans
    md.append("## 7. 明日预案（龙头选手 / 龙空龙选手）")
    md.append("### 龙头选手（偏多）")

    if consecutive_board is not None and not consecutive_board.empty:
        cb = consecutive_board.copy()
        cb["code"] = cb["code"].astype(str).str.zfill(6)
        cb["consecutive_days"] = pd.to_numeric(cb.get("consecutive_days"), errors="coerce").fillna(0).astype(int)
        cb = cb.sort_values(["consecutive_days", "code"], ascending=[False, True]).head(8)

        le_map = {}
        if limitup_events is not None and not limitup_events.empty:
            le = limitup_events.copy()
            if "code" in le.columns:
                le["code"] = le["code"].astype(str).str.zfill(6)
                for _, r in le.iterrows():
                    le_map[str(r.get("code"))] = r

        for _, r in cb.iterrows():
            code = str(r.get("code") or "").zfill(6)
            name = str(r.get("name") or "").strip()
            days = int(r.get("consecutive_days") or 0)
            le_r = le_map.get(code)
            first_t = "" if le_r is None else str(le_r.get("first_limitup_time") or "")
            open_times = "" if le_r is None else _fmt_int(le_r.get("open_times"))

            intraday = _read_anchor_intraday(data_dir, code)
            met = _intraday_metrics(intraday)
            today_high = met.get("high")
            today_low = met.get("low")
            vwap = met.get("vwap")
            early_high = met.get("early_high")
            early_low = met.get("early_low")

            md.append(f"#### {_fmt_stock(code, name, code_to_name)}（{days}板）")
            md.append(f"- **当日结构**：首封时间 {first_t or '—'}；炸板次数 {open_times or '—'}。")
            if today_high and today_low:
                md.append(
                    "- **今日关键价位（由1分钟数据计算）**："
                    f"日高 {today_high:.2f} / 日低 {today_low:.2f}"
                    + (f" / VWAP {vwap:.2f}" if vwap else "")
                    + (f" / 10点前高 {early_high:.2f}" if early_high else "")
                    + (f" / 10点前低 {early_low:.2f}" if early_low else "")
                    + "。"
                )
            md.append("- **关注点（次日）**：")
            md.append("  - 若开盘即一致加速（高开秒板/快速封死），只观察不追；等待午后或次日的首次分歧回踩。")
            md.append("  - 若出现分歧（开板/炸板/回落），优先等 **回封确认**：回踩不破关键均线/不破分歧低点后再次上板，才考虑跟随。")
            md.append("  - 若分歧转弱（回封失败、量能放大但封不住、跌破分歧低点），优先撤退或不参与。")

            md.append("- **买点（条件单，尽量给出可量化位置）**：")
            if today_high and vwap and today_low:
                b1 = today_high * 1.003
                b2 = max(vwap, today_high * 0.995)
                sl = min(today_low, vwap) * 0.995
                md.append(
                    f"  - 突破确认：若明日放量突破 **今日高点上方约+0.3%（≈{b1:.2f}）**，"
                    f"回踩不破 **{b2:.2f} 附近（VWAP/突破位附近）** 再次转强，可小仓跟随。"
                )
                md.append(
                    f"  - 分歧回踩：若明日分歧回踩至 **VWAP附近（≈{vwap:.2f}）** 缩量企稳，"
                    "且板块/主线同步回流，再考虑‘分歧转一致’。")
                md.append(f"  - 止损触发：有效跌破 **{sl:.2f}（低点/VWAP下方）** 则退出，避免演化为大面。")
            else:
                md.append("  - 盘口回封：第一次开板后缩量回踩，二次上板并封单恢复、封板稳定（小仓试错）。")
                md.append("  - 弱转强：低开/平开后快速拉回分时均线之上，并再次挑战涨停价，且核心题材同步回流。")
                md.append("  - 止损：以分歧低点/回封失败为止损触发；宁可错过不追高。")

            md.append("- **仓位建议**：如果当日‘炸板率高/跌停扩散’，即使有买点也以小仓试错为主，等待确认后再加。")
            md.append("")
    else:
        md.append("(无连板梯队数据)")
        md.append("")

    md.append("### 龙空龙选手（龙头 + 空仓 + 龙头）")
    md.append("- 该风格的核心不是做空，而是：**只在龙头具备确定性时出手；其余时间坚决空仓等待**。")
    md.append("- 因此这里用‘昨日空头风标’作为**风险温度计**：观察它们今日是否继续恶化/是否出现修复，从而决定‘空仓’还是‘切回龙头’。")
    md.append("")

    bear = [a for a in anchors_meta if str(a.get("tag") or "") == "昨日空头风标"]
    if bear:
        md.append("#### 风险温度计：昨日空头风标（节选3只）")
        rows = []
        for it in bear[:3]:
            code = str(it.get("code") or "").zfill(6)
            name = code_to_name.get(code, "")
            intraday = _read_anchor_intraday(data_dir, code)
            met = _intraday_metrics(intraday)
            rows.append(
                [
                    _fmt_stock(code, name, code_to_name),
                    _fmt_float(met.get("early_high"), 2),
                    _fmt_float(met.get("early_low"), 2),
                    _fmt_float(met.get("vwap"), 2),
                    _fmt_float(met.get("high"), 2),
                    _fmt_float(met.get("low"), 2),
                    _fmt_float(met.get("close"), 2),
                ]
            )
        md.append(_md_table(["风标", "10点前高", "10点前低", "VWAP", "日高", "日低", "收盘"], rows))
        md.append("")

    md.append("#### 空仓与切回龙头：条件化执行")
    md.append("- **保持空仓（不切回龙头）**：")
    md.append("  - 若盘面继续出现‘跌停扩散/炸板高位不降/连板晋级率继续走低’，说明风险未出清：继续空仓等待。")
    md.append("  - 若风险温度计（空头风标）出现‘早盘反抽无力、跌破10点前低点后加速’：说明情绪仍偏弱，继续空仓。")
    md.append("- **从空仓切回龙头（只做最确定的一刀）**：")
    md.append("  - 风险温度计出现修复：至少多数风标能站上自身VWAP/不再破日内新低，市场跌停数明显下降；")
    md.append("  - 同时龙头出现确认信号：‘突破确认’或‘分歧回踩后回封确认’（上一节龙头个股的条件单）。")
    md.append("- **执行细节**：")
    md.append("  - 切回当天只做1只龙头、1次出手，仓位从小到大；若首笔失败，当日不再加码。")
    md.append("  - 若盘中再次出现情绪反杀（跌停快速回升、龙头回封失败）：立即回到空仓状态。")
    md.append("")

    md.append("### 总体仓位建议")
    md.append("- 当日若‘炸板率高 + 跌停扩散 + 1→2晋级率低’：以防守为主，降低仓位，等待确定性回流信号。")
    md.append("- 当日若‘主线回流 + 晋级率提升 + 核心龙头回封成功’：再逐步加仓，优先核心辨识度标的。")
    md.append("")

    # LLM
    md.append("## 附：LLM复盘正文")
    if llm_recap_text:
        md.append("```text")
        md.append(llm_recap_text)
        md.append("```")
    else:
        md.append("(无 llm_recap.txt)")

    out_path.write_text("\n".join(md).rstrip() + "\n", encoding="utf-8")
    return out_path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-dir", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()

    out = generate_markdown(Path(args.data_dir), Path(args.out))
    print(str(out))


if __name__ == "__main__":
    main()
