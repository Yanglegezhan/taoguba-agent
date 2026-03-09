import argparse
import ast
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Set, Tuple

import matplotlib
import matplotlib.pyplot as plt
import pandas as pd


def _safe_parse_list_cell(cell: object) -> List[str]:
    if cell is None or (isinstance(cell, float) and pd.isna(cell)):
        return []
    if isinstance(cell, list):
        return [str(x) for x in cell if str(x).strip()]
    s = str(cell).strip()
    if not s:
        return []
    try:
        v = ast.literal_eval(s)
        if isinstance(v, list):
            return [str(x) for x in v if str(x).strip()]
    except Exception:
        pass
    return []


def _to_time_label(t: str) -> str:
    t = (t or "").strip()
    if not t:
        return ""
    if re.match(r"^\d{2}:\d{2}:\d{2}$", t):
        return t[:5]
    if re.match(r"^\d{2}:\d{2}$", t):
        return t
    if re.match(r"^\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}$", t):
        return t.split(" ", 1)[1][:5]
    return t


CHAIN_KEYWORDS: Dict[str, List[str]] = {
    "航天军工链": ["商业航天", "航天", "卫星", "火箭", "低轨", "星链", "卫星互联网", "大飞机", "军工", "军民融合", "蓝箭"],
    "低空经济链": ["低空", "通用航空", "无人机", "eVTOL", "飞行汽车"],
    "机器人链": ["机器人", "人形机器人", "具身智能", "执行器", "减速器", "机器视觉"],
    "AI/算力链": ["昇腾", "算力", "服务器", "液冷", "字节", "大模型", "AI芯片"],
    "金融支付链": ["数字人民币", "数字货币", "跨境支付", "稳定币", "互联金融"],
    "汽车链": ["新能源车", "华为汽车", "小米汽车", "热管理", "压铸", "特斯拉"],
    "光伏新技术链": ["光伏", "HIT", "钙钛矿"],
}


def infer_event_chains(title: str) -> Tuple[List[str], List[str]]:
    text = (title or "").strip()
    if not text:
        return [], []

    hit_chains: List[str] = []
    hit_keywords: List[str] = []

    for chain, kws in CHAIN_KEYWORDS.items():
        for kw in kws:
            if kw and kw in text:
                hit_keywords.append(kw)
                hit_chains.append(chain)
                break

    # de-dup preserve order
    seen = set()
    chains_out = []
    for c in hit_chains:
        if c not in seen:
            chains_out.append(c)
            seen.add(c)

    seen_kw = set()
    kws_out = []
    for k in hit_keywords:
        if k not in seen_kw:
            kws_out.append(k)
            seen_kw.add(k)

    return chains_out, kws_out


def _concept_to_chain(concept: str) -> Optional[str]:
    c0 = (concept or "").strip()
    if not c0:
        return None

    c = re.sub(r"\s+", "", c0)

    aerospace = {"商业航天", "商业火箭", "卫星互联网", "卫星通信", "大飞机", "军工", "军民融合", "航天航空", "航天"}
    low_alt = {"低空经济", "通用航空", "无人机", "飞行汽车(eVTOL)"}
    robotics = {"机器人概念", "人形机器人", "机器人执行器", "减速器", "机器视觉"}
    ai_compute = {"智谱AI", "华为昇腾", "华为欧拉", "远程办公", "软件开发"}
    pv = {"HIT电池", "钙钛矿电池", "光伏设备"}
    finance_pay = {"数字货币", "跨境支付", "互联金融"}
    auto_chain = {"新能源车", "华为汽车", "小米汽车", "汽车热管理", "汽车一体化压铸", "特斯拉"}

    if c in aerospace:
        return "航天军工链"
    if c in low_alt:
        return "低空经济链"
    if c in robotics:
        return "机器人链"
    if c in ai_compute:
        return "AI/算力链"
    if c in pv:
        return "光伏新技术链"
    if c in finance_pay:
        return "金融支付链"
    if c in auto_chain:
        return "汽车链"
    return None


def build_stock_chain_map(concept_map: pd.DataFrame) -> Dict[str, Set[str]]:
    cm = concept_map.copy()
    cm["code"] = cm["code"].astype(str).str.zfill(6)
    cm["concepts"] = cm["concepts"].apply(_safe_parse_list_cell)

    mapping: Dict[str, Set[str]] = {}
    for _, r in cm.iterrows():
        code = r.get("code")
        chains: Set[str] = set()
        for c in r.get("concepts", []) or []:
            g = _concept_to_chain(c)
            if g:
                chains.add(g)
        mapping[str(code)] = chains
    return mapping


def enrich_events(data_dir: Path) -> Tuple[pd.DataFrame, pd.DataFrame]:
    events_path = data_dir / "events.csv"
    limitups_path = data_dir / "limitup_events.csv"
    concept_map_path = data_dir / "concept_map.csv"

    events = pd.read_csv(events_path) if events_path.exists() else pd.DataFrame([])
    limitups = pd.read_csv(limitups_path) if limitups_path.exists() else pd.DataFrame([])
    concept_map = pd.read_csv(concept_map_path) if concept_map_path.exists() else pd.DataFrame([])

    if events.empty:
        return pd.DataFrame([]), pd.DataFrame([])

    stock_chain_map = build_stock_chain_map(concept_map) if not concept_map.empty else {}

    if not limitups.empty:
        limitups["code"] = limitups["code"].astype(str).str.zfill(6)
        limitups["consecutive_days"] = pd.to_numeric(limitups.get("consecutive_days"), errors="coerce").fillna(1).astype(int)
        limitups["amount"] = pd.to_numeric(limitups.get("amount"), errors="coerce").fillna(0)

    enriched_rows = []
    link_rows = []

    for _, r in events.iterrows():
        title = str(r.get("title") or "").strip()
        if not title:
            continue
        chains, kws = infer_event_chains(title)
        if not chains:
            chains = []
        enriched_rows.append(
            {
                "time": r.get("time", ""),
                "time_label": _to_time_label(str(r.get("time", ""))),
                "title": title,
                "source": r.get("source", ""),
                "url": r.get("url", ""),
                "chains": json.dumps(chains, ensure_ascii=False),
                "keywords": json.dumps(kws, ensure_ascii=False),
            }
        )

        if chains and not limitups.empty and stock_chain_map:
            for ch in chains:
                related = []
                for _, lr in limitups.iterrows():
                    code = str(lr.get("code"))
                    if ch in stock_chain_map.get(code, set()):
                        related.append(
                            {
                                "code": code,
                                "name": lr.get("name", ""),
                                "consecutive_days": int(lr.get("consecutive_days", 1)),
                                "amount": float(lr.get("amount", 0)),
                                "first_limitup_time": lr.get("first_limitup_time", ""),
                            }
                        )
                related = sorted(related, key=lambda x: (x["consecutive_days"], x["amount"]), reverse=True)[:8]
                link_rows.append(
                    {
                        "event_time": r.get("time", ""),
                        "event_title": title,
                        "chain": ch,
                        "related_limitup": json.dumps(related, ensure_ascii=False),
                    }
                )

    events_enriched = pd.DataFrame(enriched_rows)
    event_topic_links = pd.DataFrame(link_rows)
    return events_enriched, event_topic_links


def plot_anchor_with_marks(data_dir: Path) -> Dict[str, Any]:
    anchors_meta_path = data_dir / "anchors_intraday.json"
    anchors_dir = data_dir / "anchors_intraday"
    limitups_path = data_dir / "limitup_events.csv"

    if not anchors_meta_path.exists() or not anchors_dir.exists() or not limitups_path.exists():
        return {}

    anchors_meta = json.loads(anchors_meta_path.read_text(encoding="utf-8"))
    limitups = pd.read_csv(limitups_path)
    limitups["code"] = limitups["code"].astype(str).str.zfill(6)

    lu_map = {
        str(r["code"]): {
            "first": str(r.get("first_limitup_time") or ""),
            "final": str(r.get("final_seal_time") or ""),
            "open_times": r.get("open_times"),
            "consecutive_days": r.get("consecutive_days"),
            "name": r.get("name"),
        }
        for _, r in limitups.iterrows()
    }

    out_dir = data_dir / "anchors_intraday_plots"
    out_dir.mkdir(parents=True, exist_ok=True)

    matplotlib.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "Arial Unicode MS", "DejaVu Sans"]
    matplotlib.rcParams["axes.unicode_minus"] = False

    marks: Dict[str, Any] = {}

    for a in anchors_meta:
        code = str(a.get("code") or "").zfill(6)
        tag = str(a.get("tag") or "").strip()
        meta_name = str(a.get("name") or "").strip()
        f = anchors_dir / str(a.get("file"))
        if not f.exists():
            continue
        df = pd.read_csv(f)
        if df.empty:
            continue
        df["datetime"] = pd.to_datetime(df["datetime"], errors="coerce")
        df = df[df["datetime"].notna()].copy()
        df.sort_values("datetime", inplace=True)
        df["time_label"] = df["datetime"].dt.strftime("%H:%M")
        df["close"] = pd.to_numeric(df["close"], errors="coerce")
        df = df[df["close"].notna()].copy()

        info = lu_map.get(code, {})
        info_name = str(info.get("name") or "").strip() or meta_name
        first_t = _to_time_label(info.get("first", ""))
        final_t = _to_time_label(info.get("final", ""))

        # tail backflow heuristic: last 20 minutes close - 14:30 close
        tail_mark = None
        try:
            c1430 = df[df["time_label"] >= "14:30"]["close"].iloc[0]
            clast = df["close"].iloc[-1]
            if c1430 > 0 and (clast - c1430) / c1430 >= 0.02:
                tail_mark = "14:30+回流"
        except Exception:
            tail_mark = None

        fig, ax = plt.subplots(figsize=(5.6, 2.4), dpi=200)
        ax.plot(df["time_label"], df["close"], linewidth=1.25, color="#1f77b4")

        base = f"{info_name}({code})" if info_name else f"{code}"
        title = f"{tag} {base}" if tag else base
        ax.set_title(title)
        ax.set_xlabel("")
        ax.set_ylabel("")

        def vline(t: str, label: str, color: str):
            if t and t in set(df["time_label"].tolist()):
                ax.axvline(t, color=color, linestyle="--", linewidth=1)
                ax.text(t, df["close"].max(), label, rotation=90, va="top", ha="right", fontsize=8, color=color)

        vline(first_t, "首封", "#d62728")
        vline(final_t, "终封", "#2ca02c")
        if tail_mark:
            vline("14:30", "尾盘回流", "#9467bd")

        xticks = list(range(0, len(df["time_label"]), max(1, len(df["time_label"]) // 6)))
        ax.set_xticks([df["time_label"].iloc[i] for i in xticks])
        ax.grid(True, linestyle="--", alpha=0.2)

        out_path = out_dir / f"{code}.png"
        fig.tight_layout(pad=0.6)
        fig.savefig(out_path)
        plt.close(fig)

        marks[code] = {
            "first_limitup": first_t,
            "final_seal": final_t,
            "tail_backflow": bool(tail_mark),
            "plot": str(out_path.name),
        }

    (data_dir / "anchors_marks.json").write_text(json.dumps(marks, ensure_ascii=False, indent=2), encoding="utf-8")
    return marks


def plot_chain_attack_annotated(data_dir: Path, out_name: str = "attack_sequence_chain_annotated.png") -> Path:
    # Rebuild chain time series from limitups+concept_map (dedup by stock)
    limitups_path = data_dir / "limitup_events.csv"
    concept_map_path = data_dir / "concept_map.csv"

    le = pd.read_csv(limitups_path)
    cm = pd.read_csv(concept_map_path)
    le["code"] = le["code"].astype(str).str.zfill(6)
    cm["code"] = cm["code"].astype(str).str.zfill(6)
    cm["concepts"] = cm["concepts"].apply(_safe_parse_list_cell)

    def to_min_bucket(s: Any) -> Optional[int]:
        if s is None or (isinstance(s, float) and pd.isna(s)):
            return None
        t = str(s).strip()
        if not t:
            return None
        if ":" in t:
            hh, mm = t.split(":", 1)[0:2]
            try:
                return int(hh) * 60 + int(mm)
            except Exception:
                return None
        if t.isdigit() and len(t) >= 4:
            try:
                return int(t[0:2]) * 60 + int(t[2:4])
            except Exception:
                return None
        return None

    le["first_min"] = le["first_limitup_time"].apply(to_min_bucket)
    le = le[le["first_min"].notna()].copy()
    le["first_min"] = le["first_min"].astype(int)

    merged = le.merge(cm[["code", "concepts"]], on="code", how="left")

    expanded_rows = []
    for _, r in merged.iterrows():
        chains: Set[str] = set()
        for c in r.get("concepts", []) or []:
            g = _concept_to_chain(c)
            if g:
                chains.add(g)
        for ch in chains:
            expanded_rows.append({"code": r["code"], "first_min": int(r["first_min"]), "chain": ch})

    expanded = pd.DataFrame(expanded_rows)
    if expanded.empty:
        # fallback: build from concept_timeseries by mapping concept_name -> chain
        ts_path = data_dir / "concept_timeseries.csv"
        if not ts_path.exists():
            raise ValueError("no chain expanded rows")
        ts = pd.read_csv(ts_path)
        if ts.empty:
            raise ValueError("no chain expanded rows")
        ts["time_label"] = ts["time"].astype(str).str.slice(0, 5)
        ts["chain"] = ts["concept_name"].astype(str).apply(_concept_to_chain)
        ts = ts[ts["chain"].notna()].copy()
        ts["limitup_count"] = pd.to_numeric(ts["limitup_count"], errors="coerce")
        ts = ts[ts["limitup_count"].notna()].copy()
        pivot = ts.pivot_table(index="time_label", columns="chain", values="limitup_count", aggfunc="max").sort_index()
        latest = ts.groupby("chain")["limitup_count"].max().sort_values(ascending=False)
        chains = ["航天军工链", "低空经济链", "机器人链", "AI/算力链", "金融支付链", "汽车链"]
        chains = [c for c in chains if c in pivot.columns]
        pivot = pivot[chains]

        matplotlib.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "Arial Unicode MS", "DejaVu Sans"]
        matplotlib.rcParams["axes.unicode_minus"] = False
        fig, ax = plt.subplots(figsize=(15, 8), dpi=170)
        for c in pivot.columns:
            lw = 3.2 if c in {"航天军工链", "低空经济链", "机器人链"} else 2.0
            ax.step(pivot.index, pivot[c], where="post", linewidth=lw, label=f"{c}({int(latest.get(c, 0))})")
        ax.set_title("资金进攻顺序图（产业链合并：主线标注版）")
        ax.set_xlabel("时间")
        ax.set_ylabel("累计涨停数")
        anchors = {"神剑股份8板首封": "09:30", "航天发展分支确认": "10:12", "中国卫星尾盘回流": "14:52"}
        for label, t in anchors.items():
            if t in pivot.index:
                ax.axvline(t, color="#444444", linestyle="--", linewidth=1, alpha=0.55)
                ax.text(t, ax.get_ylim()[1], label, rotation=90, va="top", ha="right", fontsize=8, color="#222222")
        xticks = list(range(0, len(pivot.index), max(1, len(pivot.index) // 10)))
        ax.set_xticks([pivot.index[i] for i in xticks])
        ax.grid(True, linestyle="--", alpha=0.25)
        ax.legend(loc="upper left", bbox_to_anchor=(1.02, 1.0), borderaxespad=0.0)
        out_path = data_dir / out_name
        fig.tight_layout()
        fig.savefig(out_path)
        plt.close(fig)
        return out_path

    start = 9 * 60 + 30
    end = 15 * 60
    buckets = list(range(start, end + 1, 5))

    rows = []
    for b in buckets:
        hh = b // 60
        mm = b % 60
        tlabel = f"{hh:02d}:{mm:02d}"
        tmp = expanded[expanded["first_min"] <= b]
        if tmp.empty:
            continue
        g = tmp.groupby("chain")["code"].nunique().reset_index(name="limitup_count")
        g["time_label"] = tlabel
        rows.append(g)

    df = pd.concat(rows, ignore_index=True)

    latest = df.groupby("chain")["limitup_count"].max().sort_values(ascending=False)
    chains = ["航天军工链", "低空经济链", "机器人链", "AI/算力链", "金融支付链", "汽车链"]
    chains = [c for c in chains if c in latest.index]
    df = df[df["chain"].isin(chains)].copy()

    pivot = df.pivot_table(index="time_label", columns="chain", values="limitup_count", aggfunc="max").sort_index()

    matplotlib.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "Arial Unicode MS", "DejaVu Sans"]
    matplotlib.rcParams["axes.unicode_minus"] = False

    fig, ax = plt.subplots(figsize=(15, 8), dpi=170)

    for c in pivot.columns:
        lw = 3.2 if c in {"航天军工链", "低空经济链", "机器人链"} else 2.0
        ax.step(pivot.index, pivot[c], where="post", linewidth=lw, label=f"{c}({int(latest.get(c, 0))})")

    ax.set_title("资金进攻顺序图（产业链合并：主线标注版）")
    ax.set_xlabel("时间")
    ax.set_ylabel("累计涨停数")

    # Key anchor times
    anchors = {
        "神剑股份8板首封": "09:30",
        "航天发展分支确认": "10:12",
        "中国卫星尾盘回流": "14:52",
    }
    for label, t in anchors.items():
        if t in pivot.index:
            ax.axvline(t, color="#444444", linestyle="--", linewidth=1, alpha=0.55)
            ax.text(t, ax.get_ylim()[1], label, rotation=90, va="top", ha="right", fontsize=8, color="#222222")

    xticks = list(range(0, len(pivot.index), max(1, len(pivot.index) // 10)))
    ax.set_xticks([pivot.index[i] for i in xticks])
    ax.grid(True, linestyle="--", alpha=0.25)
    ax.legend(loc="upper left", bbox_to_anchor=(1.02, 1.0), borderaxespad=0.0)

    out_path = data_dir / out_name
    fig.tight_layout()
    fig.savefig(out_path)
    plt.close(fig)
    return out_path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-dir", required=True)
    args = parser.parse_args()

    data_dir = Path(args.data_dir)

    events_enriched, event_topic_links = enrich_events(data_dir)
    if not events_enriched.empty:
        events_enriched.to_csv(data_dir / "events_enriched.csv", index=False, encoding="utf-8-sig")
    else:
        (data_dir / "events_enriched.csv").write_text("", encoding="utf-8")

    if not event_topic_links.empty:
        event_topic_links.to_csv(data_dir / "event_topic_links.csv", index=False, encoding="utf-8-sig")
    else:
        (data_dir / "event_topic_links.csv").write_text("", encoding="utf-8")

    plot_anchor_with_marks(data_dir)
    plot_chain_attack_annotated(data_dir)

    print("OK")


if __name__ == "__main__":
    main()
