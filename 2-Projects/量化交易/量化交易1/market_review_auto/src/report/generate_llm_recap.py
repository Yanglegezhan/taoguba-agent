import argparse
import json
import os
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

import pandas as pd


def _load_api_key() -> str:
    key = os.getenv("ZHIPUAI_API_KEY") or os.getenv("ZHIPU_API_KEY") or os.getenv("BIGMODEL_API_KEY")
    if key:
        return key.strip()

    # Windows: read from registry so `setx` works without restarting the parent process
    if os.name == "nt":
        try:
            import winreg  # type: ignore

            def read_env(root: int) -> Optional[str]:
                try:
                    with winreg.OpenKey(root, r"Environment") as k:
                        v, _t = winreg.QueryValueEx(k, "ZHIPUAI_API_KEY")
                        s = "" if v is None else str(v).strip()
                        return s or None
                except Exception:
                    return None

            v1 = read_env(winreg.HKEY_CURRENT_USER)
            if v1:
                return v1
            v2 = read_env(winreg.HKEY_LOCAL_MACHINE)
            if v2:
                return v2
        except Exception:
            pass

    return ""


def _read_json(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _zfill6(code: Any) -> str:
    s = "" if code is None else str(code).strip()
    if not s:
        return ""
    return s.zfill(6)


def _fmt_stock(code: Any, name: Any) -> str:
    c = _zfill6(code)
    n = "" if name is None else str(name).strip()
    if n and c:
        return f"{n}({c})"
    return n or c


def _fmt_delta(curr: Any, prev: Any, nd: int = 2) -> str:
    try:
        c = float(curr)
        p = float(prev)
        d = c - p
        sign = "+" if d >= 0 else ""
        return f"{p:.{nd}f}->{c:.{nd}f}({sign}{d:.{nd}f})"
    except Exception:
        return f"{prev}->{curr}"


def _fmt_delta_int(curr: Any, prev: Any) -> str:
    try:
        c = int(curr)
        p = int(prev)
        d = c - p
        sign = "+" if d >= 0 else ""
        return f"{p}->{c}({sign}{d})"
    except Exception:
        return f"{prev}->{curr}"


def _build_prompt(data_dir: Path, target_len: int = 4000) -> str:
    market_overview = _read_json(data_dir / "market_overview.json")
    market_compare = _read_json(data_dir / "market_compare.json")
    ladder_stats = _read_json(data_dir / "ladder_stats.json")
    anchors_marks = _read_json(data_dir / "anchors_marks.json")
    emotion_stats = _read_json(data_dir / "emotion_stats.json")

    prev_overview: Dict[str, Any] = {}
    prev_date = str(market_overview.get("prev_day", {}).get("date") or emotion_stats.get("prev_date") or "").strip()
    if prev_date:
        prev_dir = data_dir.parent / prev_date
        prev_overview = _read_json(prev_dir / "market_overview.json")

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

    date_str = str(market_overview.get("date", ""))

    idx = market_overview.get("indices", {}) or {}

    def idx_line(k: str, name: str) -> str:
        d = idx.get(k) or {}
        if not d:
            return ""
        o = d.get("open")
        h = d.get("high")
        l = d.get("low")
        c = d.get("close")
        return f"{name} O:{o} H:{h} L:{l} C:{c}"

    idx_lines = [
        s
        for s in [
            idx_line("SH000001", "上证"),
            idx_line("SZ399001", "深成"),
            idx_line("SZ399006", "创业板"),
        ]
        if s
    ]

    compare_line = ""
    if isinstance(market_compare.get("today"), dict) and isinstance(market_compare.get("prev"), dict):
        t = market_compare.get("today") or {}
        p = market_compare.get("prev") or {}
        compare_line = (
            f"对比前一交易日({p.get('date')}->{t.get('date')})："
            f"涨停 {_fmt_delta_int(t.get('limitup_count'), p.get('limitup_count'))}，"
            f"跌停 {_fmt_delta_int(t.get('limitdown_count'), p.get('limitdown_count'))}，"
            f"炸板数 {_fmt_delta_int(t.get('broken_count'), p.get('broken_count'))}，"
            f"炸板率 {_fmt_delta(t.get('broken_rate'), p.get('broken_rate'), nd=3)}，"
            f"2板及以上 {_fmt_delta_int(t.get('consecutive_ge2_count'), p.get('consecutive_ge2_count'))}。"
        )

    compare_detail_lines: List[str] = []
    if prev_overview:
        p_idx = prev_overview.get("indices", {}) or {}
        t_idx = market_overview.get("indices", {}) or {}

        def close_of(idx_map: Dict[str, Any], k: str) -> Any:
            d = idx_map.get(k) if isinstance(idx_map, dict) else None
            if isinstance(d, dict):
                return d.get("close")
            return None

        for k, name in [("SH000001", "上证"), ("SZ399001", "深成"), ("SZ399006", "创业板"), ("SH000688", "科创50")]:
            pc = close_of(p_idx, k)
            tc = close_of(t_idx, k)
            if pc is None or tc is None:
                continue
            compare_detail_lines.append(f"{name}收盘 {_fmt_delta(tc, pc, nd=2)}")

        compare_detail_lines.append(
            "涨跌家数 "
            + f"上涨{_fmt_delta_int(market_overview.get('up_count'), prev_overview.get('up_count'))} "
            + f"下跌{_fmt_delta_int(market_overview.get('down_count'), prev_overview.get('down_count'))} "
            + f"平盘{_fmt_delta_int(market_overview.get('flat_count'), prev_overview.get('flat_count'))}"
        )
        compare_detail_lines.append(
            "量能(成交额) " + _fmt_delta(market_overview.get("turnover"), prev_overview.get("turnover"), nd=0)
        )
        compare_detail_lines.append(
            "涨停/跌停 "
            + f"涨停{_fmt_delta_int(market_overview.get('limitup_count'), prev_overview.get('limitup_count'))} "
            + f"跌停{_fmt_delta_int(market_overview.get('limitdown_count'), prev_overview.get('limitdown_count'))}"
        )
        compare_detail_lines.append(
            "炸板 "
            + f"炸板数{_fmt_delta_int(market_overview.get('broken_count'), prev_overview.get('broken_count'))} "
            + f"炸板率{_fmt_delta(market_overview.get('broken_rate'), prev_overview.get('broken_rate'), nd=3)}"
        )
        if isinstance(market_compare.get("today"), dict) and isinstance(market_compare.get("prev"), dict):
            t = market_compare.get("today") or {}
            p = market_compare.get("prev") or {}
            compare_detail_lines.append(
                "2板及以上 " + _fmt_delta_int(t.get("consecutive_ge2_count"), p.get("consecutive_ge2_count"))
            )

    top_concepts = []
    if concept_day_stats is not None and not concept_day_stats.empty:
        cols = [c for c in ["concept_name", "up_count", "avg_pct_chg", "sum_amount"] if c in concept_day_stats.columns]
        df = concept_day_stats[cols].copy()
        if "up_count" in df.columns:
            df = df.sort_values(["up_count"], ascending=[False])
        for _, r in df.head(10).iterrows():
            top_concepts.append(
                f"{r.get('concept_name')} (上涨{r.get('up_count')}, 均涨{r.get('avg_pct_chg')}, 成交额{r.get('sum_amount')})"
            )

    leaders = []
    if consecutive_board is not None and not consecutive_board.empty:
        df = consecutive_board.copy()
        if "consecutive_days" in df.columns:
            df["consecutive_days"] = pd.to_numeric(df["consecutive_days"], errors="coerce")
            df = df.sort_values(["consecutive_days"], ascending=[False])
        for _, r in df.head(15).iterrows():
            leaders.append(
                f"{_fmt_stock(r.get('code'), r.get('name'))} 连板:{r.get('consecutive_days')} 首封:{r.get('first_limitup_time')} 终封:{r.get('final_seal_time')}"
            )

    limitups = []
    if limitup_events is not None and not limitup_events.empty:
        df = limitup_events.copy()
        if "amount" in df.columns:
            df["amount"] = pd.to_numeric(df["amount"], errors="coerce")
        if "consecutive_days" in df.columns:
            df["consecutive_days"] = pd.to_numeric(df["consecutive_days"], errors="coerce")
        sort_cols = [c for c in ["consecutive_days", "amount"] if c in df.columns]
        if sort_cols:
            df = df.sort_values(sort_cols, ascending=[False] * len(sort_cols))
        for _, r in df.head(25).iterrows():
            limitups.append(
                f"{_fmt_stock(r.get('code'), r.get('name'))} 高度:{r.get('consecutive_days')} 金额:{r.get('amount')} 首封:{r.get('first_limitup_time')} 终封:{r.get('final_seal_time')} 开板:{r.get('open_times')}"
            )

    events = []
    if event_topic_links is not None and not event_topic_links.empty:
        cols = [c for c in ["event_time", "event_title", "chain", "related_limitup"] if c in event_topic_links.columns]
        df = event_topic_links[cols].copy().head(12)
        for _, r in df.iterrows():
            title = str(r.get("event_title", "")).replace("\n", " ").strip()
            events.append(
                f"{r.get('event_time')} 题材:{r.get('chain')} 事件:{title} 关联涨停:{r.get('related_limitup')}"
            )
    elif events_enriched is not None and not events_enriched.empty:
        cols = [c for c in ["time_label", "title", "chains", "source"] if c in events_enriched.columns]
        df = events_enriched[cols].copy().head(12)
        for _, r in df.iterrows():
            title = str(r.get("title", "")).replace("\n", " ").strip()
            events.append(f"{r.get('time_label')} {r.get('chains')} {title} ({r.get('source')})")

    ladder = []
    if isinstance(ladder_stats.get("levels"), list):
        for lv in (ladder_stats.get("levels") or [])[:10]:
            ladder.append(
                f"{lv.get('from')}: 升级{lv.get('upgraded')}/{lv.get('total')} 炸板{lv.get('broken')} 升级率{lv.get('upgrade_rate')}"
            )

    anchors = []
    if isinstance(anchors_marks, dict) and anchors_marks:
        for k, v in list(anchors_marks.items())[:10]:
            if not isinstance(v, dict):
                continue
            anchors.append(
                f"{_zfill6(k)} first:{v.get('first_limitup')} final:{v.get('final_seal')} tail_backflow:{v.get('tail_backflow')}"
            )

    pieces = []
    pieces.append(f"日期：{date_str}")
    pieces.append("指数：" + "；".join(idx_lines))
    pieces.append(
        "市场统计："
        f"涨停{market_overview.get('limitup_count')} 跌停{market_overview.get('limitdown_count')} "
        f"炸板率{market_overview.get('broken_rate')} 成交额{market_overview.get('turnover')} "
        f"上涨{market_overview.get('up_count')} 下跌{market_overview.get('down_count')}"
    )
    if compare_line:
        pieces.append(compare_line)
    if compare_detail_lines:
        pieces.append("大盘对比(昨日->今日)：" + "；".join([x for x in compare_detail_lines if x]))
    if top_concepts:
        pieces.append("题材强度Top：" + "；".join(top_concepts))
    if leaders:
        pieces.append("连板梯队Top：" + "；".join(leaders))
    if limitups:
        pieces.append("涨停核心Top：" + "；".join(limitups))
    if events:
        pieces.append("事件归因：" + "；".join(events))
    if ladder:
        pieces.append("晋级率结构：" + "；".join(ladder))
    if anchors:
        pieces.append("锚定标的打点：" + "；".join(anchors))

    if isinstance(emotion_stats, dict) and emotion_stats:
        cycle = str(emotion_stats.get("cycle") or "").strip()
        node = str(emotion_stats.get("node") or "").strip()
        dkl = emotion_stats.get("dragon_kong_long") if isinstance(emotion_stats.get("dragon_kong_long"), dict) else {}
        sig = "" if not isinstance(dkl, dict) else str(dkl.get("signal") or "").strip()
        reason = "" if not isinstance(dkl, dict) else str(dkl.get("reason") or "").strip()
        pieces.append(f"情绪周期/节点：{cycle or '—'}；{node or '—'}")

        y = emotion_stats.get("yesterday") if isinstance(emotion_stats.get("yesterday"), dict) else {}
        p1 = y.get("prev_limitup_today_perf") if isinstance(y.get("prev_limitup_today_perf"), dict) else {}
        p2 = y.get("prev_broken_today_perf") if isinstance(y.get("prev_broken_today_perf"), dict) else {}
        if p1:
            pieces.append(
                "昨日涨停股今日反馈："
                f"红盘率{p1.get('pos_ratio')} 均值{p1.get('mean_pct')} 中位数{p1.get('median_pct')}"
                f" ≥+5%占比{p1.get('ge5_ratio')} ≤-5%占比{p1.get('le_5_ratio')}"
            )
        if p2:
            pieces.append(
                "昨日炸板股今日反馈："
                f"红盘率{p2.get('pos_ratio')} 均值{p2.get('mean_pct')} 中位数{p2.get('median_pct')}"
                f" ≥+5%占比{p2.get('ge5_ratio')} ≤-5%占比{p2.get('le_5_ratio')}"
            )
        if sig:
            pieces.append(f"龙空龙出手节点建议：{sig} 理由：{reason}")

    context = "\n".join(pieces)

    want_len = int(target_len) if target_len is not None else 0
    head = f"生成一份尽可能详细的《A股复盘报告》" if want_len <= 0 else f"生成一份约{want_len}字的《A股复盘报告》"
    len_rule = "" if want_len <= 0 else f"- 文字要连贯，避免大段口号；长度尽量接近{want_len}字（允许±15%）。\n"

    prompt = f"""你是A股短线复盘专家。请根据【数据摘要】{head}，使用中文，要求：

- 必须严格输出7个分点（编号1-7），每个分点都要有清晰标题。
- 每个分点都要引用【数据摘要】中的具体证据（数字、时间、代表个股、题材等），不要空泛。
- 必须包含：市场环境/指数与情绪、资金进攻顺序与主线、题材强度与证据、事件驱动归因、涨停结构与梯队、锚定个股与分时证据、明日预案与风险控制。
- 复盘风格要像人写的专业复盘：先结论后证据，再给出交易预案。
- 必须显式比较“昨日 vs 今日”的大盘变化：至少列出8个指标（指数、涨跌家数、成交额、涨停/跌停、炸板率、2板及以上、晋级率、情绪周期/节点等），并给出结论：整体是升温还是降温。
{len_rule}

- 必须单独回答：**“明日是否为龙空龙选手（龙头+空仓+龙头）的出手节点？”**
  - 先给结论：是 / 否 / 观察。
  - 再给依据：结合【情绪周期/情绪节点】、昨日涨停反馈、昨日炸板反馈、1→2晋级率、炸板率、跌停扩散等。
  - 最后给触发条件：满足哪些条件才从空仓切回龙头（例如：唯一龙头确立、分歧回封确认、风险温度计修复等）。

【数据摘要】
{context}
"""

    return prompt


def call_glm_chat(
    api_key: str,
    model: str,
    prompt: str,
    max_tokens: int = 6144,
    timeout_seconds: int = 240,
    retries: int = 2,
) -> str:
    url = "https://open.bigmodel.cn/api/paas/v4/chat/completions"
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": "你是专业的A股复盘助手。"},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.4,
        "top_p": 0.9,
        "max_tokens": int(max_tokens),
    }

    req = Request(
        url,
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )

    last_err: Optional[Exception] = None
    obj: Dict[str, Any] = {}

    for attempt in range(0, max(0, int(retries)) + 1):
        try:
            with urlopen(req, timeout=int(timeout_seconds)) as resp:
                body = resp.read().decode("utf-8", errors="replace")
            obj = json.loads(body)
            break
        except TimeoutError as e:
            last_err = e
        except (URLError, HTTPError) as e:
            last_err = e
        except Exception as e:
            last_err = e

        if attempt < int(retries):
            time.sleep(2.0 * (2**attempt))
            continue
        raise RuntimeError(f"GLM request failed after retries: {last_err}")

    choices = obj.get("choices") or []
    if not choices:
        raise RuntimeError(f"No choices in response: {obj}")
    msg = (choices[0] or {}).get("message") or {}
    content = msg.get("content")
    if not content:
        raise RuntimeError(f"No message content in response: {obj}")
    return str(content)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-dir", required=True)
    parser.add_argument("--model", default="glm-4.6")
    parser.add_argument("--out", default="")
    parser.add_argument("--length", type=int, default=4000, help="Target words; set 0 to remove length constraint")
    parser.add_argument("--max-tokens", type=int, default=6144)
    parser.add_argument("--timeout", type=int, default=240)
    parser.add_argument("--retries", type=int, default=2)
    args = parser.parse_args()

    data_dir = Path(args.data_dir).resolve()
    out_path = Path(args.out).resolve() if args.out else (data_dir / "llm_recap.txt")

    api_key = _load_api_key()
    if not api_key:
        raise RuntimeError(
            "Missing API key. Please set environment variable ZHIPUAI_API_KEY (recommended) or ZHIPU_API_KEY/BIGMODEL_API_KEY."
        )

    prompt = _build_prompt(data_dir, target_len=int(args.length))
    max_tokens = int(args.max_tokens)
    if max_tokens <= 0:
        max_tokens = 6144
    max_tokens = min(max_tokens, 8192)

    timeout_seconds = int(args.timeout)
    if timeout_seconds <= 0:
        timeout_seconds = 240
    retries = int(args.retries)
    if retries < 0:
        retries = 0

    text = call_glm_chat(
        api_key=api_key,
        model=str(args.model),
        prompt=prompt,
        max_tokens=max_tokens,
        timeout_seconds=timeout_seconds,
        retries=retries,
    )

    out_path.write_text(text, encoding="utf-8")
    print(str(out_path))


if __name__ == "__main__":
    main()
