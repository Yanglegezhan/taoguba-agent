import argparse
import ast
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Set, Tuple

import matplotlib
import matplotlib.pyplot as plt
import pandas as pd


CHAIN_KEYWORDS: Dict[str, List[str]] = {
    "航天军工链": ["商业航天", "航天", "卫星", "火箭", "低轨", "星链", "军工", "大飞机", "军民融合"],
    "低空经济链": ["低空", "通用航空", "无人机", "eVTOL", "飞行汽车", "飞行器"],
    "机器人链": ["机器人", "人形机器人", "具身智能", "执行器", "减速器", "机器视觉"],
    "AI/算力链": ["算力", "服务器", "液冷", "昇腾", "大模型", "AI", "国产软件", "数据中心"],
    "金融支付链": ["数字人民币", "数字货币", "跨境支付", "稳定币", "券商", "互联金融"],
    "半导体链": ["半导体", "芯片", "光刻", "EDA", "存储", "封测"],
    "医药链": ["医药", "创新药", "CRO", "医疗", "疫苗"],
    "消费链": ["消费", "白酒", "食品", "零售", "旅游", "免税"],
    "汽车链": ["新能源车", "汽车", "华为汽车", "小米汽车", "热管理", "压铸", "特斯拉"],
    "能源电力链": ["电力", "煤炭", "石油", "天然气", "储能"],
    "有色资源链": ["有色", "黄金", "稀土", "锂", "铜", "铝"],
    "光伏新技术链": ["光伏", "HIT", "钙钛矿"],
}


def _load_concept_ts(data_dir: Path) -> pd.DataFrame:
    concept_ts_path = data_dir / "concept_timeseries.csv"
    if not concept_ts_path.exists():
        raise FileNotFoundError(str(concept_ts_path))

    df = pd.read_csv(concept_ts_path)
    if df.empty:
        raise ValueError("concept_timeseries.csv is empty")

    df["time"] = pd.to_datetime(df["time"], format="%H:%M:%S", errors="coerce")
    df = df[df["time"].notna()].copy()
    df["time_label"] = df["time"].dt.strftime("%H:%M")

    df["limitup_count"] = pd.to_numeric(df["limitup_count"], errors="coerce")
    df = df[df["limitup_count"].notna()].copy()
    return df


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
    return [x.strip() for x in s.strip("[]").replace("'", "").replace('"', "").split(",") if x.strip()]


def _concept_to_chain(concept: str) -> Optional[str]:
    c0 = (concept or "").strip()
    c = "".join(c0.split())
    if not c:
        return None

    for chain, kws in CHAIN_KEYWORDS.items():
        for kw in kws:
            if kw and kw in c:
                return chain
    return None


def _build_chain_timeseries_from_limitups(data_dir: Path, freq_minutes: int = 5) -> pd.DataFrame:
    limitup_path = data_dir / "limitup_events.csv"
    concept_map_path = data_dir / "concept_map.csv"
    if not limitup_path.exists() or not concept_map_path.exists():
        raise FileNotFoundError("limitup_events.csv or concept_map.csv not found")

    le = pd.read_csv(limitup_path)
    cm = pd.read_csv(concept_map_path)
    le["code"] = le["code"].astype(str).str.zfill(6)
    cm["code"] = cm["code"].astype(str).str.zfill(6)
    cm["concepts"] = cm["concepts"].apply(_safe_parse_list_cell)

    def to_minute_bucket(s: object) -> Optional[int]:
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

    le["first_min"] = le["first_limitup_time"].apply(to_minute_bucket)
    le = le[le["first_min"].notna()].copy()
    le["first_min"] = le["first_min"].astype(int)

    merged = le.merge(cm[["code", "concepts"]], on="code", how="left")

    def code_to_chains(concepts: object) -> Set[str]:
        out: Set[str] = set()
        for c in _safe_parse_list_cell(concepts):
            g = _concept_to_chain(c)
            if g:
                out.add(g)
        return out

    chain_set_series = merged["concepts"].apply(code_to_chains)
    expanded_rows: List[Dict[str, Any]] = []
    for (_, row), chains in zip(merged.iterrows(), chain_set_series.tolist()):
        if not isinstance(chains, set) or not chains:
            continue
        for ch in chains:
            expanded_rows.append({"code": row["code"], "first_min": int(row["first_min"]), "chain_name": str(ch)})

    if not expanded_rows:
        return pd.DataFrame([])

    expanded = pd.DataFrame(expanded_rows)

    start = 9 * 60 + 30
    end = 15 * 60
    buckets = list(range(start, end + 1, int(freq_minutes)))

    rows = []
    for b in buckets:
        hh = b // 60
        mm = b % 60
        tlabel = f"{hh:02d}:{mm:02d}"
        tmp = expanded[expanded["first_min"] <= b]
        if tmp.empty:
            continue
        g = tmp.groupby("chain_name")["code"].nunique().reset_index(name="limitup_count")
        g["time_label"] = tlabel
        rows.append(g)

    if not rows:
        return pd.DataFrame([])
    out = pd.concat(rows, ignore_index=True)
    out.rename(columns={"chain_name": "concept_name"}, inplace=True)
    out["time"] = pd.to_datetime(out["time_label"] + ":00", format="%H:%M:%S", errors="coerce")
    return out[["time", "time_label", "concept_name", "limitup_count"]]


def _select_top(df: pd.DataFrame, top_n: int) -> Tuple[pd.DataFrame, pd.Series]:
    latest = df.sort_values("time").groupby("concept_name")["limitup_count"].max().sort_values(ascending=False)
    top = latest.head(int(top_n)).index.tolist()
    return df[df["concept_name"].isin(top)].copy(), latest


def plot_attack_sequence(
    data_dir: Path,
    top_n: int = 10,
    out_name: str = "attack_sequence_recap.png",
    mode: str = "chain",
    freq_minutes: int = 5,
) -> Path:
    if mode == "chain":
        df = _build_chain_timeseries_from_limitups(data_dir, freq_minutes=freq_minutes)
        if df.empty:
            df = _load_concept_ts(data_dir)
    else:
        df = _load_concept_ts(data_dir)

    df, latest = _select_top(df, top_n=top_n)
    if df.empty:
        raise ValueError("No data after selecting top lines")

    pivot = df.pivot_table(index="time_label", columns="concept_name", values="limitup_count", aggfunc="max")
    pivot = pivot.sort_index()

    matplotlib.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "Arial Unicode MS", "DejaVu Sans"]
    matplotlib.rcParams["axes.unicode_minus"] = False

    fig, ax = plt.subplots(figsize=(15, 8), dpi=160)

    main_order = pivot.columns.tolist()
    strong_set = set(latest.head(3).index.tolist())
    for c in main_order:
        lw = 3.0 if c in strong_set else 2.0
        ax.step(pivot.index, pivot[c], where="post", linewidth=lw, label=f"{c}({int(latest.get(c, 0))})")

    title_mode = "产业链合并" if mode == "chain" else "题材原始"
    ax.set_title(f"资金进攻顺序图（{title_mode} Top{top_n}：累计涨停数随时间）")
    ax.set_xlabel("时间")
    ax.set_ylabel("累计涨停数")

    key_times = ["09:30", "10:00", "13:00", "14:50"]
    for kt in key_times:
        if kt in pivot.index:
            ax.axvline(kt, color="#999999", linestyle="--", linewidth=1, alpha=0.5)

    xticks = list(range(0, len(pivot.index), max(1, len(pivot.index) // 10)))
    ax.set_xticks([pivot.index[i] for i in xticks])
    ax.tick_params(axis="x", rotation=0)

    ax.grid(True, linestyle="--", alpha=0.25)
    ax.legend(loc="upper left", bbox_to_anchor=(1.02, 1.0), borderaxespad=0.0, ncol=1)

    out_path = data_dir / out_name
    fig.tight_layout()
    fig.savefig(out_path)
    plt.close(fig)
    return out_path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-dir", required=True, help="Directory containing concept_timeseries.csv")
    parser.add_argument("--top", type=int, default=10)
    parser.add_argument("--out", default="attack_sequence_recap.png")
    parser.add_argument("--mode", choices=["chain", "concept"], default="chain")
    parser.add_argument("--freq", type=int, default=5)
    args = parser.parse_args()

    out_path = plot_attack_sequence(Path(args.data_dir), top_n=args.top, out_name=args.out, mode=args.mode, freq_minutes=int(args.freq))
    print(str(out_path))


if __name__ == "__main__":
    main()
