import argparse
import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.cidfonts import UnicodeCIDFont
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Image, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle


def _read_json(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _fmt_int(x: Any) -> str:
    try:
        return f"{int(x):d}"
    except Exception:
        return str(x)


def _fmt_float(x: Any, nd: int = 2) -> str:
    try:
        return f"{float(x):.{nd}f}"
    except Exception:
        return str(x)


def _fmt_yi(x: Any, nd: int = 2) -> str:
    try:
        return f"{float(x) / 1e8:.{nd}f}"
    except Exception:
        return str(x)


def _fmt_ratio_pct(x: Any, nd: int = 2) -> str:
    try:
        return f"{float(x) * 100:.{nd}f}%"
    except Exception:
        return str(x)


def _register_cjk_font() -> str:
    candidates = [
        Path("C:/Windows/Fonts/simhei.ttf"),
        Path("C:/Windows/Fonts/msyh.ttf"),
        Path("C:/Windows/Fonts/msyh.ttc"),
        Path("C:/Windows/Fonts/simsun.ttc"),
    ]

    for p in candidates:
        try:
            if p.exists():
                font_name = f"CJK_{p.stem}"
                if font_name not in pdfmetrics.getRegisteredFontNames():
                    pdfmetrics.registerFont(TTFont(font_name, str(p)))
                return font_name
        except Exception:
            continue

    # CID fallback that works without external TTF files
    try:
        cid_name = "STSong-Light"
        if cid_name not in pdfmetrics.getRegisteredFontNames():
            pdfmetrics.registerFont(UnicodeCIDFont(cid_name))
        return cid_name
    except Exception:
        return "Helvetica"


def _safe_get(d: Dict[str, Any], path: List[str], default: Any = None) -> Any:
    cur: Any = d
    for k in path:
        if not isinstance(cur, dict):
            return default
        cur = cur.get(k)
    return default if cur is None else cur


def _zfill6(code: Any) -> str:
    s = "" if code is None else str(code).strip()
    if not s:
        return ""
    return s.zfill(6)


def _build_code_name_map(dfs: List[Optional[pd.DataFrame]]) -> Dict[str, str]:
    m: Dict[str, str] = {}
    for df in dfs:
        if df is None or df.empty:
            continue
        if "code" not in df.columns:
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
    if c:
        return c
    return n0


def _add_table(
    elements: List[Any],
    title: str,
    df: pd.DataFrame,
    styles: Any,
    font_name: str,
    max_rows: int = 12,
    max_width: Optional[float] = None,
    col_widths: Optional[List[float]] = None,
) -> None:
    elements.append(Paragraph(title, styles["Heading3"]))

    if df is None or df.empty:
        elements.append(Paragraph("(空)", styles["Normal"]))
        elements.append(Spacer(1, 10))
        return

    df2 = df.head(max_rows).copy()
    data = [list(df2.columns)] + df2.astype(str).values.tolist()

    cw = None
    if max_width and len(df2.columns) > 0:
        if col_widths and len(col_widths) == len(df2.columns):
            s = float(sum(col_widths)) if sum(col_widths) else 0.0
            if s > 0:
                cw = [max_width * float(x) / s for x in col_widths]
        if cw is None:
            cw = [max_width / float(len(df2.columns))] * int(len(df2.columns))

    table = Table(data, repeatRows=1, colWidths=cw)
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f0f0f0")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.black),
                ("FONTNAME", (0, 0), (-1, -1), font_name),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cfcfcf")),
                ("FONTSIZE", (0, 0), (-1, -1), 8),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ]
        )
    )

    elements.append(table)
    elements.append(Spacer(1, 12))


def _can_load_image(path: Path) -> bool:
    try:
        ImageReader(str(path))
        return True
    except Exception:
        return False


def _split_llm_body_and_plan(text: str) -> tuple[str, str]:
    """Split llm output into (body_without_point7, point7_text).

    Heuristics:
    - Look for a line that starts with 7/七 numbering (Markdown headers allowed).
    - If found, everything from that line belongs to point7.
    """

    txt = (text or "").strip()
    if not txt:
        return "", ""

    lines = txt.splitlines()
    pat = re.compile(r"^\s*(#{0,6}\s*)?(\*\*\s*)?(7|七)\s*[\.、\)）:]\s*")

    cut = None
    for i, ln in enumerate(lines):
        if pat.match(str(ln or "")):
            cut = i
            break

    if cut is None:
        # fallback: find inline '7.' or '七、' markers
        m = re.search(r"\n\s*(#{0,6}\s*)?(\*\*\s*)?(7|七)\s*[\.、\)）:]\s*", "\n" + txt)
        if m:
            idx = m.start()
            body = ("\n" + txt)[:idx].strip()
            plan = ("\n" + txt)[idx:].strip()
            return body, plan
        return txt, ""

    body = "\n".join(lines[:cut]).strip()
    plan = "\n".join(lines[cut:]).strip()
    return body, plan


def _build_recap_paragraphs(
    market_overview: Dict[str, Any],
    market_compare: Dict[str, Any],
    emotion_stats: Dict[str, Any],
    ladder_stats: Dict[str, Any],
    concept_day_stats: Optional[pd.DataFrame],
    events_enriched: Optional[pd.DataFrame],
    consecutive_board: Optional[pd.DataFrame],
    limitup_events: Optional[pd.DataFrame],
    anchors_marks: Dict[str, Any],
    code_to_name: Dict[str, str],
) -> List[str]:
    date_str = str(market_overview.get("date", ""))
    limitup = market_overview.get("limitup_count")
    limitdown = market_overview.get("limitdown_count")
    broken_rate = market_overview.get("broken_rate")

    up = market_overview.get("up_count")
    down = market_overview.get("down_count")
    flat = market_overview.get("flat_count")
    total = market_overview.get("total_count")
    turnover = market_overview.get("turnover")

    prev = market_overview.get("prev") or {}
    ladder = market_overview.get("ladder") or {}
    upgrade_12 = _safe_get(ladder, ["upgrade_rates", "1->2"], None)

    paragraphs: List[str] = []

    paragraphs.append(
        f"一、市场环境与策略定位：{date_str} 涨停{_fmt_int(limitup)} / 跌停{_fmt_int(limitdown)}，炸板率{_fmt_ratio_pct(broken_rate, 2)}。"
        f"个股涨跌：上涨{_fmt_int(up)}、下跌{_fmt_int(down)}、平盘{_fmt_int(flat)}（总计{_fmt_int(total)}）；两市成交额约{_fmt_yi(turnover, 2)}亿。"
    )

    idx = market_overview.get("indices", {}) or {}
    def idx_line(k: str, name: str) -> Optional[str]:
        d = idx.get(k) or {}
        if not d:
            return None
        return (
            f"{name} O:{_fmt_float(d.get('open'),2)} H:{_fmt_float(d.get('high'),2)} "
            f"L:{_fmt_float(d.get('low'),2)} C:{_fmt_float(d.get('close'),2)}"
        )

    idx_lines = [x for x in [idx_line("SH000001", "上证"), idx_line("SZ399001", "深成"), idx_line("SZ399006", "创业板")] if x]
    if idx_lines:
        paragraphs.append("指数概览：" + "；".join(idx_lines))

    if market_compare:
        # schema v2: {today:{...}, prev:{...}}
        if isinstance(market_compare.get("today"), dict) and isinstance(market_compare.get("prev"), dict):
            t = market_compare.get("today") or {}
            p = market_compare.get("prev") or {}
            paragraphs.append(
                "与前一交易日对比："
                f"涨停 {_fmt_int(t.get('limitup_count'))}->{_fmt_int(p.get('limitup_count'))}，"
                f"跌停 {_fmt_int(t.get('limitdown_count'))}->{_fmt_int(p.get('limitdown_count'))}；"
                f"2板及以上 {_fmt_int(t.get('consecutive_ge2_count'))}->{_fmt_int(p.get('consecutive_ge2_count'))}。"
            )
        else:
            # legacy schema support
            paragraphs.append(
                "与前一交易日对比（字段口径以文件为准）："
                f"涨停 {_fmt_int(market_compare.get('limitup_count_today'))}->{_fmt_int(market_compare.get('limitup_count_prev'))}，"
                f"跌停 {_fmt_int(market_compare.get('limitdown_count_today'))}->{_fmt_int(market_compare.get('limitdown_count_prev'))}；"
                f"2板及以上 {_fmt_int(market_compare.get('ge2_count_today'))}->{_fmt_int(market_compare.get('ge2_count_prev'))}。"
            )
    elif prev:
        paragraphs.append(
            "与前一交易日对比："
            f"涨停 {_fmt_int(limitup)}->{_fmt_int(prev.get('limitup_count'))}，"
            f"跌停 {_fmt_int(limitdown)}->{_fmt_int(prev.get('limitdown_count'))}。"
        )

    if upgrade_12 is not None:
        paragraphs.append(f"情绪结构：1→2晋级率 {_fmt_ratio_pct(upgrade_12, 2)}（低位延续性的重要风向）。")

    # Emotion cycle/node + yesterday feedback
    if isinstance(emotion_stats, dict) and emotion_stats:
        cycle = str(emotion_stats.get("cycle") or "").strip()
        node = str(emotion_stats.get("node") or "").strip()
        if cycle or node:
            paragraphs.append(f"情绪周期/节点：{cycle or '—'}；{node or '—'}。")

        y = emotion_stats.get("yesterday") if isinstance(emotion_stats.get("yesterday"), dict) else {}
        p1 = y.get("prev_limitup_today_perf") if isinstance(y.get("prev_limitup_today_perf"), dict) else {}
        p2 = y.get("prev_broken_today_perf") if isinstance(y.get("prev_broken_today_perf"), dict) else {}
        if p1:
            paragraphs.append(
                "昨日涨停股今日反馈："
                f"红盘率{_fmt_ratio_pct(p1.get('pos_ratio'),2)}，均值{_fmt_float(p1.get('mean_pct'),2)}%，"
                f"中位数{_fmt_float(p1.get('median_pct'),2)}%，"
                f"≥+5%占比{_fmt_ratio_pct(p1.get('ge5_ratio'),2)}，≤-5%占比{_fmt_ratio_pct(p1.get('le_5_ratio'),2)}。"
            )
        if p2:
            paragraphs.append(
                "昨日炸板股今日反馈："
                f"红盘率{_fmt_ratio_pct(p2.get('pos_ratio'),2)}，均值{_fmt_float(p2.get('mean_pct'),2)}%，"
                f"中位数{_fmt_float(p2.get('median_pct'),2)}%，"
                f"≥+5%占比{_fmt_ratio_pct(p2.get('ge5_ratio'),2)}，≤-5%占比{_fmt_ratio_pct(p2.get('le_5_ratio'),2)}。"
            )

    def pick_unique_focus() -> str:
        try:
            df = None
            if consecutive_board is not None and not consecutive_board.empty:
                df = consecutive_board.copy()
            elif limitup_events is not None and not limitup_events.empty:
                df = limitup_events.copy()
                if "consecutive_days" not in df.columns:
                    df["consecutive_days"] = 1
            if df is None or df.empty or "code" not in df.columns:
                return ""

            df["code"] = df["code"].astype(str).str.zfill(6)
            if "consecutive_days" in df.columns:
                df["consecutive_days"] = pd.to_numeric(df["consecutive_days"], errors="coerce").fillna(1).astype(int)
            else:
                df["consecutive_days"] = 1

            amt_map: Dict[str, float] = {}
            if limitup_events is not None and not limitup_events.empty and "code" in limitup_events.columns:
                le = limitup_events.copy()
                le["code"] = le["code"].astype(str).str.zfill(6)
                if "amount" in le.columns:
                    le["amount"] = pd.to_numeric(le["amount"], errors="coerce").fillna(0)
                for _, r in le.iterrows():
                    c = str(r.get("code") or "").zfill(6)
                    if not c:
                        continue
                    amt_map[c] = float(r.get("amount") or 0)

            df["amount"] = df["code"].map(lambda c: amt_map.get(str(c), 0.0))
            df = df.sort_values(["consecutive_days", "amount"], ascending=[False, False]).reset_index(drop=True)
            if df.shape[0] == 0:
                return ""
            top = df.iloc[0]
            second = df.iloc[1] if df.shape[0] >= 2 else None

            top_days = int(top.get("consecutive_days") or 1)
            top_amt = float(top.get("amount") or 0.0)
            top_code = str(top.get("code") or "").zfill(6)
            top_name = code_to_name.get(top_code, "")
            top_label = _fmt_stock(top_code, top_name, code_to_name)

            if top_days < 3:
                return "\n".join(
                    [
                        "明日是否存在唯一聚焦标的：当前连板高度不足以形成‘唯一核心’，建议按‘龙头+空仓+龙头’执行，等待最强者进一步确立。",
                    ]
                )

            if second is None:
                return f"明日唯一聚焦标的：{top_label}（高度领先）。"

            sec_days = int(second.get("consecutive_days") or 1)
            sec_amt = float(second.get("amount") or 0.0)
            clear_lead = (top_days >= sec_days + 1) or (top_days == sec_days and (top_amt >= 1.5 * max(1.0, sec_amt)))
            if not clear_lead:
                return "\n".join(
                    [
                        "明日是否存在唯一聚焦标的：暂未形成绝对唯一（高度/成交额差距不够拉开），建议只做‘确定性回封/分歧转一致’，其余时间空仓。",
                    ]
                )

            return "\n".join(
                [
                    f"明日唯一聚焦标的：{top_label}。",
                    "执行原则：不追一致加速；只做分歧回踩后回封确认/突破确认；一旦回封失败或跌破分歧低点，立即撤退并回到空仓。",
                ]
            )
        except Exception:
            return ""

    # Core themes (rule based)
    if concept_day_stats is not None and not concept_day_stats.empty and "concept_name" in concept_day_stats.columns:
        top = concept_day_stats.copy()
        if "limitup_count" in top.columns:
            top["limitup_count"] = pd.to_numeric(top["limitup_count"], errors="coerce")
            top = top.sort_values(["limitup_count"], ascending=[False])
        elif "up_count" in top.columns:
            top = top.sort_values(["up_count"], ascending=[False])
        top5 = top.head(5)

        items = []
        for _, r in top5.iterrows():
            name = str(r.get("concept_name", ""))
            upc = r.get("up_count")
            avg = r.get("avg_pct_chg")
            amt = r.get("sum_amount")
            lu = r.get("limitup_count")
            ld = r.get("limitdown_count")
            items.append(
                f"{name}(涨停{_fmt_int(lu)}/跌停{_fmt_int(ld)}, 上涨{_fmt_int(upc)}, 均涨{_fmt_float(avg,2)}%, 成交额{_fmt_yi(amt,2)}亿)"
            )

        paragraphs.append("二、核心题材与强度证据（题材强度Top）：" + "；".join(items))

    # Events
    if events_enriched is not None and not events_enriched.empty:
        df = events_enriched.copy()
        # keep only rows with chains identified
        if "chains" in df.columns:
            df2 = df[df["chains"].astype(str).str.contains("航天|机器人|低空|算力|数字", na=False)].copy()
        else:
            df2 = df
        df2 = df2.head(3)
        ev_items = []
        for _, r in df2.iterrows():
            t = str(r.get("time_label", ""))
            title = str(r.get("title", ""))
            title = title.replace("\n", " ").strip()[:60]
            ev_items.append(f"{t} {title}")
        if ev_items:
            paragraphs.append("三、事件驱动与因果线索（节选）：" + "；".join(ev_items))

    # Ladder
    if ladder_stats and isinstance(ladder_stats.get("levels"), list):
        levels = ladder_stats.get("levels") or []
        if levels:
            # show a compact line
            parts = []
            for lv in levels[:5]:
                fr = lv.get("from")
                tot = lv.get("total")
                upg = lv.get("upgraded")
                rate = lv.get("upgrade_rate")
                parts.append(f"{fr}: {upg}/{tot}({_fmt_float(rate,2)})")
            paragraphs.append("四、连板梯队与晋级率结构（节选）：" + "；".join(parts))

    # Anchors
    if isinstance(anchors_marks, dict) and anchors_marks:
        tail = [
            _fmt_stock(k, code_to_name.get(_zfill6(k), ""), code_to_name)
            for k, v in anchors_marks.items()
            if isinstance(v, dict) and v.get("tail_backflow")
        ]
        if tail:
            paragraphs.append("尾盘回流锚：" + "、".join(tail) + "（tail_backflow=true）")

    paragraphs.append(
        "五、明日预案（规则化）："
        "若主线锚不负反馈，优先围绕主线前排与回流锚寻找‘分歧转一致/回封确认’；"
        "若主线明显走弱，则只做并行强线的核心辨识度票，不追后排扩散；"
        "若跌停扩散/炸板继续高，降低频率，等待修复点。"
    )

    focus = pick_unique_focus()
    if focus:
        paragraphs.append(focus)

    # 龙空龙出手节点建议（非做空）
    if isinstance(emotion_stats, dict) and isinstance(emotion_stats.get("dragon_kong_long"), dict):
        dkl = emotion_stats.get("dragon_kong_long") or {}
        sig = str(dkl.get("signal") or "").strip()
        reason = str(dkl.get("reason") or "").strip()
        conds = dkl.get("conditions") if isinstance(dkl.get("conditions"), list) else []
        if sig:
            line = f"龙空龙出手节点判断：{sig}。"
            if reason:
                line += f"理由：{reason}"
            paragraphs.append(line)
        if conds:
            paragraphs.append("龙空龙出手条件（满足越多越适合切回龙头）：" + "；".join([str(x) for x in conds if str(x).strip()]))

    return paragraphs


def generate_pdf(data_dir: Path, out_path: Path) -> Path:
    styles = getSampleStyleSheet()

    font_name = _register_cjk_font()
    for k in ["Normal", "Title", "Heading3"]:
        if k in styles.byName:
            styles[k].fontName = font_name

    market_overview = _read_json(data_dir / "market_overview.json")
    market_compare = _read_json(data_dir / "market_compare.json")
    ladder_stats = _read_json(data_dir / "ladder_stats.json")
    emotion_stats = _read_json(data_dir / "emotion_stats.json")

    concept_day_stats = None
    if (data_dir / "concept_day_stats.csv").exists():
        concept_day_stats = pd.read_csv(data_dir / "concept_day_stats.csv")

    events_enriched = None
    if (data_dir / "events_enriched.csv").exists():
        events_enriched = pd.read_csv(data_dir / "events_enriched.csv")

    event_topic_links = None
    if (data_dir / "event_topic_links.csv").exists():
        event_topic_links = pd.read_csv(data_dir / "event_topic_links.csv")

    consecutive_board = None
    if (data_dir / "consecutive_board.csv").exists():
        consecutive_board = pd.read_csv(data_dir / "consecutive_board.csv")

    limitup_events = None
    if (data_dir / "limitup_events.csv").exists():
        limitup_events = pd.read_csv(data_dir / "limitup_events.csv")

    code_to_name = _build_code_name_map([limitup_events, consecutive_board])

    anchors_meta: List[Dict[str, Any]] = []
    anchors_meta_path = data_dir / "anchors_intraday.json"
    if anchors_meta_path.exists():
        try:
            v = json.loads(anchors_meta_path.read_text(encoding="utf-8"))
            if isinstance(v, list):
                anchors_meta = v
        except Exception:
            anchors_meta = []

    anchor_name_map: Dict[str, str] = {}
    try:
        for it in anchors_meta:
            if not isinstance(it, dict):
                continue
            c = _zfill6(it.get("code"))
            n = "" if it.get("name") is None else str(it.get("name")).strip()
            if c and n and c not in anchor_name_map:
                anchor_name_map[c] = n
    except Exception:
        anchor_name_map = {}

    llm_recap_path = data_dir / "llm_recap.txt"
    llm_recap_text = ""
    if llm_recap_path.exists():
        llm_recap_text = llm_recap_path.read_text(encoding="utf-8", errors="ignore").strip()

    llm_body_text, llm_plan_text = _split_llm_body_and_plan(llm_recap_text)

    anchors_marks = _read_json(data_dir / "anchors_marks.json")

    out_path.parent.mkdir(parents=True, exist_ok=True)

    doc = SimpleDocTemplate(
        str(out_path),
        pagesize=A4,
        title="A股复盘",
        leftMargin=26,
        rightMargin=26,
        topMargin=22,
        bottomMargin=22,
    )

    elements: List[Any] = []

    date_str = str(market_overview.get("date", ""))
    elements.append(Paragraph(f"A股复盘（{date_str}）", styles["Title"]))
    elements.append(Spacer(1, 10))

    idx = market_overview.get("indices", {}) or {}
    sh = idx.get("SH000001") or {}
    sz = idx.get("SZ399001") or {}
    cyb = idx.get("SZ399006") or {}

    summary_lines = [
        f"涨停: {_fmt_int(market_overview.get('limitup_count'))}  跌停: {_fmt_int(market_overview.get('limitdown_count'))}  炸板率: {_fmt_ratio_pct(market_overview.get('broken_rate'), 2)}",
        f"上涨: {_fmt_int(market_overview.get('up_count'))}  下跌: {_fmt_int(market_overview.get('down_count'))}  平盘: {_fmt_int(market_overview.get('flat_count'))}  总计: {_fmt_int(market_overview.get('total_count'))}",
        f"两市成交额(亿): {_fmt_yi(market_overview.get('turnover'), 2)}",
        f"上证: {_fmt_float(sh.get('close'))}  深成: {_fmt_float(sz.get('close'))}  创业板: {_fmt_float(cyb.get('close'))}",
        f"1->2晋级率: {_fmt_ratio_pct(((market_overview.get('ladder') or {}).get('upgrade_rates') or {}).get('1->2'), 2)}",
    ]
    for line in summary_lines:
        elements.append(Paragraph(line, styles["Normal"]))
        elements.append(Spacer(1, 4))
    elements.append(Spacer(1, 8))

    # 7-point recap (text + evidence)
    paras = _build_recap_paragraphs(
        market_overview,
        market_compare,
        emotion_stats,
        ladder_stats,
        concept_day_stats,
        events_enriched,
        consecutive_board,
        limitup_events,
        anchors_marks,
        code_to_name,
    )
    sec1 = [
        p
        for p in paras
        if p.startswith("一、")
        or p.startswith("指数概览")
        or p.startswith("与前一交易日对比")
        or p.startswith("情绪结构")
        or p.startswith("情绪周期/节点")
        or p.startswith("昨日涨停股今日反馈")
        or p.startswith("昨日炸板股今日反馈")
    ]
    sec3 = [p for p in paras if p.startswith("二、")]
    sec4 = [p for p in paras if p.startswith("三、")]
    sec5 = [p for p in paras if p.startswith("四、")]
    sec7 = [
        p
        for p in paras
        if p.startswith("五、")
        or p.startswith("明日是否存在唯一聚焦标的")
        or p.startswith("明日唯一聚焦标的")
        or p.startswith("龙空龙出手节点判断")
        or p.startswith("龙空龙出手条件")
    ]

    def add_section(title: str, lines: List[str]) -> None:
        elements.append(Paragraph(title, styles["Heading3"]))
        elements.append(Spacer(1, 6))
        for ln in lines:
            elements.append(Paragraph(ln, styles["Normal"]))
            elements.append(Spacer(1, 6))

    add_section("1. 市场环境与策略定位（文字）", sec1)

    if event_topic_links is not None and not event_topic_links.empty:
        elements.append(Paragraph("4. 事件驱动与题材归因（表格）", styles["Heading3"]))
        elements.append(Spacer(1, 6))
        for ln in sec4:
            elements.append(Paragraph(ln, styles["Normal"]))
            elements.append(Spacer(1, 6))
        cols = [c for c in ["event_time", "event_title", "chain", "related_limitup"] if c in event_topic_links.columns]
        df_et0 = event_topic_links[cols].copy()
        for c in ["event_time", "event_title", "chain", "related_limitup"]:
            if c in df_et0.columns:
                df_et0[c] = df_et0[c].astype(str)

        def uniq_join(series: pd.Series, sep: str = "/") -> str:
            items = []
            seen = set()
            for x in series.tolist():
                s = str(x).strip()
                if not s or s in {"nan", "None"}:
                    continue
                if s not in seen:
                    items.append(s)
                    seen.add(s)
            return sep.join(items)

        df_et = (
            df_et0.groupby(["event_time", "event_title"], as_index=False)
            .agg({
                "chain": lambda s: uniq_join(s, sep="/"),
                "related_limitup": lambda s: uniq_join(s, sep="；"),
            })
            .copy()
        )
        df_et["event_title"] = df_et["event_title"].astype(str).str.slice(0, 50)
        df_et["related_limitup"] = df_et["related_limitup"].astype(str).str.slice(0, 110)
        df_et.rename(columns={"event_time": "时间", "event_title": "事件", "chain": "题材/链条", "related_limitup": "关联涨停"}, inplace=True)
        _add_table(
            elements,
            "事件→题材→涨停关联（去重合并）",
            df_et[[c for c in ["时间", "事件", "题材/链条", "关联涨停"] if c in df_et.columns]],
            styles=styles,
            font_name=font_name,
            max_rows=10,
            max_width=doc.width,
            col_widths=[0.14, 0.44, 0.14, 0.28],
        )

    if consecutive_board is not None and not consecutive_board.empty:
        elements.append(Paragraph("5. 涨停结构与连板梯队（表格）", styles["Heading3"]))
        elements.append(Spacer(1, 6))
        for ln in sec5:
            elements.append(Paragraph(ln, styles["Normal"]))
            elements.append(Spacer(1, 6))
        df_cb = consecutive_board.copy()
        if "code" in df_cb.columns:
            df_cb["code"] = df_cb["code"].apply(_zfill6)
        if "name" in df_cb.columns and "code" in df_cb.columns:
            df_cb["个股"] = df_cb.apply(lambda r: _fmt_stock(r.get("code"), r.get("name"), code_to_name), axis=1)
        if "consecutive_days" in df_cb.columns:
            df_cb["consecutive_days"] = pd.to_numeric(df_cb["consecutive_days"], errors="coerce")
        sort_cols = [c for c in ["consecutive_days", "amount"] if c in df_cb.columns]
        if sort_cols:
            df_cb = df_cb.sort_values(sort_cols, ascending=[False] * len(sort_cols))
        df_cb2 = df_cb.copy()
        rename_map = {
            "code": "代码",
            "name": "名称",
            "consecutive_days": "连板数",
            "first_limitup_time": "首封",
            "final_seal_time": "终封",
            "open_times": "炸板次数",
            "个股": "个股",
        }
        df_cb2.rename(columns={k: v for k, v in rename_map.items() if k in df_cb2.columns}, inplace=True)
        cols = [c for c in ["个股", "代码", "名称", "连板数", "首封", "终封", "炸板次数"] if c in df_cb2.columns]
        _add_table(elements, "连板梯队核心（Top）", df_cb2[cols], styles=styles, font_name=font_name, max_rows=15, max_width=doc.width)

    if limitup_events is not None and not limitup_events.empty:
        df_lu = limitup_events.copy()
        if "code" in df_lu.columns:
            df_lu["code"] = df_lu["code"].apply(_zfill6)
        if "name" in df_lu.columns and "code" in df_lu.columns:
            df_lu["个股"] = df_lu.apply(lambda r: _fmt_stock(r.get("code"), r.get("name"), code_to_name), axis=1)
        for c in ["consecutive_days", "amount", "open_times"]:
            if c in df_lu.columns:
                df_lu[c] = pd.to_numeric(df_lu[c], errors="coerce")
        sort_cols = [c for c in ["consecutive_days", "amount"] if c in df_lu.columns]
        if sort_cols:
            df_lu = df_lu.sort_values(sort_cols, ascending=[False] * len(sort_cols))
        df_lu2 = df_lu.copy()
        if "amount" in df_lu2.columns:
            df_lu2["amount"] = pd.to_numeric(df_lu2["amount"], errors="coerce")
            df_lu2["成交额(亿)"] = df_lu2["amount"].apply(lambda x: _fmt_yi(x, 2))
        rename_map = {
            "code": "代码",
            "name": "名称",
            "consecutive_days": "连板数",
            "first_limitup_time": "首封",
            "final_seal_time": "终封",
            "open_times": "炸板次数",
            "个股": "个股",
        }
        df_lu2.rename(columns={k: v for k, v in rename_map.items() if k in df_lu2.columns}, inplace=True)
        cols = [c for c in ["个股", "代码", "名称", "连板数", "成交额(亿)", "首封", "终封", "炸板次数"] if c in df_lu2.columns]
        _add_table(elements, "涨停核心（按高度/成交额排序）", df_lu2[cols], styles=styles, font_name=font_name, max_rows=20, max_width=doc.width)

    main_img = None
    for name in ["attack_sequence_chain_annotated.png", "attack_sequence_chain.png", "attack_sequence.png"]:
        p = data_dir / name
        if p.exists():
            main_img = p
            break

    if main_img:
        elements.append(Paragraph("2. 资金进攻顺序主图（图片）", styles["Heading3"]))
        elements.append(Spacer(1, 6))
        if _can_load_image(main_img):
            elements.append(Image(str(main_img), width=doc.width, height=280))
            elements.append(Spacer(1, 12))

    if concept_day_stats is not None:
        elements.append(Paragraph("3. 核心题材与强度证据（文字+表格）", styles["Heading3"]))
        elements.append(Spacer(1, 6))
        for ln in sec3:
            elements.append(Paragraph(ln, styles["Normal"]))
            elements.append(Spacer(1, 6))
        df_cs = concept_day_stats.copy()
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
            if c in df_cs.columns:
                df_cs[c] = pd.to_numeric(df_cs[c], errors="coerce")
        if "sum_amount" in df_cs.columns:
            df_cs["成交额(亿)"] = df_cs["sum_amount"].apply(lambda x: _fmt_yi(x, 2))
        if "sum_vol" in df_cs.columns:
            df_cs["成交量(亿)"] = df_cs["sum_vol"].apply(lambda x: _fmt_yi(x, 2))
        if "avg_pct_chg" in df_cs.columns:
            df_cs["平均涨幅(%)"] = df_cs["avg_pct_chg"].apply(lambda x: _fmt_float(x, 2))

        rename_map = {
            "concept_name": "板块",
            "constituents": "成分股数",
            "limitup_count": "涨停数",
            "limitdown_count": "跌停数",
            "up_count": "上涨家数",
            "down_count": "下跌家数",
            "flat_count": "平盘家数",
        }
        df_cs.rename(columns={k: v for k, v in rename_map.items() if k in df_cs.columns}, inplace=True)

        sort_cols = [c for c in ["涨停数", "上涨家数", "平均涨幅(%)"] if c in df_cs.columns]
        if sort_cols:
            df_cs = df_cs.sort_values(sort_cols, ascending=[False] * len(sort_cols))
        cols = [
            c
            for c in [
                "板块",
                "涨停数",
                "跌停数",
                "上涨家数",
                "下跌家数",
                "平盘家数",
                "成分股数",
                "平均涨幅(%)",
                "成交量(亿)",
                "成交额(亿)",
            ]
            if c in df_cs.columns
        ]
        _add_table(elements, "题材强度（Top）", df_cs[cols], styles=styles, font_name=font_name, max_rows=12, max_width=doc.width)

    if events_enriched is not None and not events_enriched.empty:
        cols = [c for c in ["time_label", "title", "chains", "keywords", "source"] if c in events_enriched.columns]
        df_e = events_enriched[cols].copy()
        df_e["title"] = df_e["title"].astype(str).str.slice(0, 80)
        _add_table(elements, "事件/舆情（自动归因Top）", df_e, styles=styles, font_name=font_name, max_rows=10, max_width=doc.width)

    if ladder_stats:
        levels = ladder_stats.get("levels") or []
        if isinstance(levels, list) and levels:
            df_l = pd.DataFrame(levels)
            if "upgrade_rate" in df_l.columns:
                df_l["晋级率(%)"] = pd.to_numeric(df_l["upgrade_rate"], errors="coerce").apply(lambda x: _fmt_ratio_pct(x, 2))
            if "from" in df_l.columns:
                df_l["梯队"] = pd.to_numeric(df_l["from"], errors="coerce").apply(lambda x: _fmt_int(x))
            rename_map = {"total": "基数", "upgraded": "晋级数", "broken": "断板数"}
            df_l.rename(columns=rename_map, inplace=True)
            cols = [c for c in ["梯队", "基数", "晋级数", "断板数", "晋级率(%)"] if c in df_l.columns]
            _add_table(elements, "晋级率结构", df_l[cols], styles=styles, font_name=font_name, max_rows=12, max_width=doc.width)

    if isinstance(anchors_marks, dict) and anchors_marks:
        elements.append(Paragraph("6. 锚定个股打点与分时证据（表格+图片）", styles["Heading3"]))
        elements.append(Spacer(1, 6))
        df_a = pd.DataFrame(
            [
                {
                    "code": _zfill6(k),
                    "name": (code_to_name.get(_zfill6(k), "") or anchor_name_map.get(_zfill6(k), "")),
                    "个股": _fmt_stock(k, (code_to_name.get(_zfill6(k), "") or anchor_name_map.get(_zfill6(k), "")), code_to_name),
                    "first": (v or {}).get("first_limitup") or "未封板",
                    "final": (v or {}).get("final_seal") or "未封板",
                    "tail_backflow": (v or {}).get("tail_backflow"),
                }
                for k, v in anchors_marks.items()
            ]
        )
        df_a2 = df_a.copy()
        df_a2.rename(
            columns={
                "code": "代码",
                "name": "名称",
                "first": "首封",
                "final": "终封",
                "tail_backflow": "尾盘回流",
                "个股": "个股",
            },
            inplace=True,
        )
        cols = [c for c in ["个股", "代码", "名称", "首封", "终封", "尾盘回流"] if c in df_a2.columns]
        _add_table(elements, "锚定标的打点", df_a2[cols], styles=styles, font_name=font_name, max_rows=12, max_width=doc.width)

        plot_dir = data_dir / "anchors_intraday_plots"
        if plot_dir.exists():
            elements.append(Paragraph("锚定分时图（节选）", styles["Heading3"]))
            elements.append(Spacer(1, 6))
            for code in df_a["code"].astype(str).tolist()[:4]:
                p = plot_dir / f"{code}.png"
                if p.exists() and _can_load_image(p):
                    elements.append(Image(str(p), width=doc.width, height=150))
                    elements.append(Spacer(1, 8))

    # LLM正文 + LLM第7点明日预案
    if llm_body_text or llm_plan_text:
        elements.append(Spacer(1, 10))
        elements.append(Paragraph("LLM复盘正文（约4000字）", styles["Heading3"]))
        elements.append(Spacer(1, 6))
        # prevent extreme lengths from breaking PDF layout (but do not truncate overall length)
        txt = llm_body_text or ""
        for part in [p.strip() for p in txt.splitlines()]:
            if not part:
                continue
            if len(part) > 600:
                # split long lines
                for i in range(0, len(part), 600):
                    elements.append(Paragraph(part[i : i + 600], styles["Normal"]))
                    elements.append(Spacer(1, 6))
            else:
                elements.append(Paragraph(part, styles["Normal"]))
                elements.append(Spacer(1, 6))

    # Section 7 should come from LLM, displayed after LLM body
    llm_sec7_lines: List[str] = []
    if llm_plan_text:
        llm_sec7_lines = [x.strip() for x in llm_plan_text.splitlines() if str(x).strip()]
    if not llm_sec7_lines:
        # fallback: use rule-based plan if LLM doesn't provide point-7
        llm_sec7_lines = sec7

    add_section("7. 明日预案（LLM）", llm_sec7_lines)

    doc.build(elements)
    return out_path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-dir", required=True)
    parser.add_argument("--out", default="")
    args = parser.parse_args()

    data_dir = Path(args.data_dir).resolve()
    out_path = Path(args.out).resolve() if args.out else (data_dir / "recap.pdf")
    p = generate_pdf(data_dir, out_path)
    print(str(p))


if __name__ == "__main__":
    main()
