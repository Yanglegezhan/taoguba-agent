from __future__ import annotations

import re
from pathlib import Path
from typing import Dict, List, Tuple

from etf_rotation.config import UniverseItem


def _parse_markdown_table_rows(lines: List[str]) -> List[List[str]]:
    rows: List[List[str]] = []
    for ln in lines:
        s = ln.strip()
        if not s.startswith("|"):
            continue
        # separator row
        if re.match(r"^\|\s*-+\s*\|", s):
            continue
        cols = [c.strip() for c in s.strip("|").split("|")]
        if len(cols) < 2:
            continue
        rows.append(cols)
    return rows


def _is_header_row(cols: List[str]) -> bool:
    if not cols:
        return True
    head = cols[0]
    return any(k in head for k in ["主题", "地区", "商品", "债券", "约束项"]) or head in ["主题", "商品", "地区"]


def _extract_code(cols: List[str]) -> Tuple[str | None, int | None]:
    for i, c in enumerate(cols):
        if re.fullmatch(r"\d{6}", c):
            return c, i
    return None, None


def load_universe_from_plan(md_path: Path) -> List[UniverseItem]:
    text = md_path.read_text(encoding="utf-8")
    lines = text.splitlines()

    replace_map = {
        "159826": {"code": "159566", "name": "储能电池ETF"},
        "159894": {"code": "512170", "name": "医疗ETF"},
        "159746": {"code": "159697", "name": "油气ETF"},
    }

    current_section = ""
    raw_items: List[Dict[str, str]] = []

    for idx, ln in enumerate(lines):
        m = re.match(r"^###\s+(.+)$", ln.strip())
        if m:
            current_section = m.group(1).strip()
            continue

        if "|" not in ln:
            continue

        # read only current line as row; robust enough because we only need data rows
        cols = [c.strip() for c in ln.strip().strip("|").split("|")] if ln.strip().startswith("|") else []
        if not cols:
            continue
        if re.match(r"^\|\s*-+\s*\|", ln.strip()):
            continue
        if _is_header_row(cols):
            continue

        code, code_i = _extract_code(cols)
        if not code or code_i is None:
            continue

        # theme is typically first col (e.g. 上证50/半导体/黄金)
        theme = cols[0] if cols[0] else current_section
        # name is usually next to code
        name = cols[code_i + 1] if code_i + 1 < len(cols) else code
        if not name:
            name = code

        if code in replace_map:
            rep = replace_map[code]
            raw_items.append({"code": rep["code"], "name": rep["name"], "theme": theme})
        else:
            raw_items.append({"code": code, "name": name, "theme": theme})

    # de-dup by code keep first
    seen = set()
    universe: List[UniverseItem] = []
    for it in raw_items:
        c = it["code"]
        if c in seen:
            continue
        seen.add(c)
        universe.append(UniverseItem(code=c, name=it["name"], theme=it["theme"]))

    return universe
