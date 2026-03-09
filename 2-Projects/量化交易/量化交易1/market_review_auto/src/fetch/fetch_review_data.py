import argparse
import gzip
import json
import os
import re
import ssl
import time
import urllib.parse
import urllib.request
import ast
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

import pandas as pd


EASTMONEY_UT = "7eea3edcaed734bea9cbfc24409ed989"


def http_get(url: str, params: Optional[Dict[str, Any]] = None, headers: Optional[Dict[str, str]] = None, timeout: int = 25) -> Tuple[int, Dict[str, str], bytes]:
    params = params or {}
    headers = headers or {}

    if params:
        query = urllib.parse.urlencode({k: "" if v is None else v for k, v in params.items()})
        full_url = url + ("&" if "?" in url else "?") + query
    else:
        full_url = url

    default_headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Accept": "application/json, text/plain, */*",
        "Accept-Encoding": "gzip",
        "Connection": "keep-alive",
    }
    default_headers.update(headers)

    req = urllib.request.Request(full_url, headers=default_headers, method="GET")

    ctx = ssl.create_default_context()
    ctx.check_hostname = True
    ctx.verify_mode = ssl.CERT_REQUIRED

    with urllib.request.urlopen(req, timeout=timeout, context=ctx) as resp:
        status = int(getattr(resp, "status", 200))
        resp_headers = {k.lower(): v for k, v in resp.headers.items()}
        data = resp.read()

    if resp_headers.get("content-encoding", "").lower() == "gzip":
        data = gzip.decompress(data)

    return status, resp_headers, data


def parse_json_maybe_jsonp(text: str) -> Any:
    s = text.strip()
    if not s:
        return None
    if s[0] in "{[":
        return json.loads(s)

    lparen = s.find("(")
    rparen = s.rfind(")")
    if lparen != -1 and rparen != -1 and rparen > lparen:
        inner = s[lparen + 1 : rparen].strip()
        if inner and inner[0] in "{[":
            return json.loads(inner)

    return json.loads(s)


def _extract_ldjson_items(html: str) -> List[Dict[str, Any]]:
    items: List[Dict[str, Any]] = []
    if not html:
        return items

    for m in re.finditer(r"<script[^>]*type=\"application/ld\+json\"[^>]*>(.*?)</script>", html, flags=re.S | re.I):
        block = m.group(1).strip()
        if not block:
            continue
        try:
            obj = json.loads(block)
        except Exception:
            continue
        if isinstance(obj, dict):
            items.append(obj)
        elif isinstance(obj, list):
            for x in obj:
                if isinstance(x, dict):
                    items.append(x)
    return items


def _html_to_text(html: str) -> str:
    if not html:
        return ""
    s = re.sub(r"<script[\s\S]*?</script>", " ", html, flags=re.I)
    s = re.sub(r"<style[\s\S]*?</style>", " ", s, flags=re.I)
    s = re.sub(r"<[^>]+>", " ", s)
    s = s.replace("&nbsp;", " ").replace("&amp;", "&")
    s = re.sub(r"\s+", " ", s).strip()
    return s


def _clean_event_title(title: str) -> str:
    t = re.sub(r"\s+", " ", (title or "")).strip()
    if not t:
        return ""
    t = re.sub(r"\sS\s.*$", "", t).strip()
    t = re.sub(r"\s\d{1,4}\s\d{1,4}\s\d{1,4}\s\d{1,4}.*$", "", t).strip()
    return t


def _normalize_event_time(t: Any) -> str:
    if t is None:
        return ""
    s = str(t).strip()
    if not s:
        return ""
    s = s.replace("T", " ").replace("Z", "")
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%d"):
        try:
            dt = datetime.strptime(s[: len(fmt)], fmt)
            return dt.strftime("%Y-%m-%d %H:%M:%S")
        except Exception:
            pass
    return s


def fetch_public_events(date_yyyymmdd: str, max_items: int = 30) -> pd.DataFrame:
    events: List[Dict[str, Any]] = []
    target_date = datetime.strptime(date_yyyymmdd, "%Y%m%d").strftime("%Y-%m-%d")

    sources = [
        ("jiuyangongshe", "https://www.jiuyangongshe.com/"),
        ("kaipanla", "https://www.kaipanla.com/latest-news/1"),
    ]

    for source, url in sources:
        html = http_get_text(url, headers={"Referer": url}, timeout=30)
        if not html:
            continue
        for obj in _extract_ldjson_items(html):
            t = obj.get("@type")
            if t in ("NewsArticle", "Article"):
                title = obj.get("headline") or obj.get("name")
                pub = obj.get("datePublished") or obj.get("dateModified")
                link = obj.get("url")
                if title:
                    events.append(
                        {
                            "time": _normalize_event_time(pub),
                            "title": str(title),
                            "related": "",
                            "source": source,
                            "url": link or url,
                        }
                    )
            if t == "ItemList" and isinstance(obj.get("itemListElement"), list):
                for it in obj.get("itemListElement"):
                    if not isinstance(it, dict):
                        continue
                    item = it.get("item") if isinstance(it.get("item"), dict) else it
                    title = item.get("name") or item.get("headline")
                    link = item.get("url")
                    pub = item.get("datePublished") or item.get("dateModified")
                    if title:
                        events.append(
                            {
                                "time": _normalize_event_time(pub),
                                "title": str(title),
                                "related": "",
                                "source": source,
                                "url": link or url,
                            }
                        )

        if len(events) >= max_items:
            break

        text = _html_to_text(html)

        if source == "jiuyangongshe":
            for m in re.finditer(r"(\d{4}-\d{2}-\d{2}\s\d{2}:\d{2}:\d{2})\s+([^\n]{8,160})", text):
                ts = m.group(1)
                if target_date not in ts:
                    continue
                title = _clean_event_title(m.group(2))
                if not title:
                    continue
                events.append({"time": ts, "title": title, "related": "", "source": source, "url": url})
                if len(events) >= max_items:
                    break

        if source == "kaipanla":
            for m in re.finditer(r"(\d{4}-\d{2}-\d{2})\s+([^\n]{8,160})", text):
                d = m.group(1)
                if target_date and target_date != d:
                    continue
                title = _clean_event_title(m.group(2))
                if not title:
                    continue
                events.append({"time": f"{d} 00:00:00", "title": title, "related": "", "source": source, "url": url})
                if len(events) >= max_items:
                    break

    def score(ev: Dict[str, Any]) -> int:
        t = ev.get("time", "")
        return 1 if (target_date and target_date in t) else 0

    dedup = {}
    for ev in events:
        key = (ev.get("time", ""), ev.get("title", ""), ev.get("source", ""))
        if key not in dedup:
            dedup[key] = ev
    events = list(dedup.values())
    events = sorted(events, key=score, reverse=True)[:max_items]
    df = pd.DataFrame(events)
    if df.empty:
        return pd.DataFrame([{ "time": "", "title": "", "related": "", "source": "", "url": "" }])
    if "time" not in df.columns:
        df["time"] = ""
    return df[["time", "title", "related", "source", "url"]]


def fetch_intraday_1m(code: str, date_yyyymmdd: str) -> pd.DataFrame:
    code = str(code).zfill(6)
    secid = f"1.{code}" if code.startswith("6") else f"0.{code}"
    url = "https://push2his.eastmoney.com/api/qt/stock/kline/get"
    params = {
        "secid": secid,
        "ut": "fa5fd1943c7b386f172d6893dbfba10b",
        "klt": "1",
        "fqt": "0",
        "beg": date_yyyymmdd,
        "end": date_yyyymmdd,
        "lmt": "1000",
        "fields1": "f1,f2,f3,f4,f5,f6",
        "fields2": "f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61",
    }
    status, _, body = http_get(url, params=params, headers={"Referer": "https://quote.eastmoney.com/"}, timeout=30)
    if status != 200:
        return pd.DataFrame([])
    raw = parse_json_maybe_jsonp(body.decode("utf-8", errors="ignore"))
    klines = (((raw or {}).get("data") or {}).get("klines") or [])
    if not klines:
        return pd.DataFrame([])

    rows = []
    for line in klines:
        parts = str(line).split(",")
        if len(parts) < 7:
            continue
        ts = parts[0]
        if ts.replace("-", "")[:8] != date_yyyymmdd:
            continue
        rows.append(
            {
                "datetime": ts,
                "open": float(parts[1]),
                "close": float(parts[2]),
                "high": float(parts[3]),
                "low": float(parts[4]),
                "volume": float(parts[5]),
                "amount": float(parts[6]),
            }
        )
    return pd.DataFrame(rows)


def select_anchor_codes(limitup_events: pd.DataFrame, consecutive_board: pd.DataFrame, top_k: int = 6) -> List[str]:
    anchors: List[str] = []
    if consecutive_board is not None and not consecutive_board.empty:
        cb = consecutive_board.sort_values("consecutive_days", ascending=False)
        anchors.extend(cb["code"].astype(str).tolist()[: max(3, top_k // 2)])
    if limitup_events is not None and not limitup_events.empty:
        le = limitup_events.copy()
        le["amount"] = pd.to_numeric(le["amount"], errors="coerce")
        le = le.sort_values("amount", ascending=False)
        anchors.extend(le["code"].astype(str).tolist()[: top_k])
    anchors = [str(x).zfill(6) for x in anchors if str(x).strip()]
    out: List[str] = []
    seen = set()
    for c in anchors:
        if c not in seen:
            out.append(c)
            seen.add(c)
    return out[: max(6, top_k)]

def http_get_text(url: str, params: Optional[Dict[str, Any]] = None, headers: Optional[Dict[str, str]] = None, timeout: int = 25) -> str:
    status, _, body = http_get(url, params=params, headers=headers, timeout=timeout)
    if status != 200:
        return ""
    return body.decode("utf-8", errors="ignore")


def _normalize_code(code: Any) -> str:
    s = "" if code is None else str(code).strip()
    return s.zfill(6) if s.isdigit() else s


def _is_st(name: Any) -> bool:
    if name is None:
        return False
    s = str(name).upper()
    return "ST" in s


def _to_yyyymmdd(d: date) -> str:
    return d.strftime("%Y%m%d")


def fetch_zt_pool(date_yyyymmdd: str, pagesize: int = 10000) -> List[Dict[str, Any]]:
    url = "http://push2ex.eastmoney.com/getTopicZTPool"
    params = {
        "ut": EASTMONEY_UT,
        "dpt": "wz.ztzt",
        "Pageindex": "0",
        "pagesize": str(pagesize),
        "sort": "fbt:asc",
        "date": date_yyyymmdd,
    }
    status, _, body = http_get(url, params=params, headers={"Referer": "http://quote.eastmoney.com/"})
    if status != 200:
        return []
    raw = parse_json_maybe_jsonp(body.decode("utf-8", errors="ignore"))
    pool = (((raw or {}).get("data") or {}).get("pool") or [])
    return pool if isinstance(pool, list) else []


def fetch_concept_board_list() -> pd.DataFrame:
    url = "https://push2.eastmoney.com/api/qt/clist/get"
    params = {
        "pn": "1",
        "pz": "2000",
        "po": "1",
        "np": "1",
        "ut": "bd1d9ddb04089700cf9c27f6f7426281",
        "fltt": "2",
        "invt": "2",
        "fid": "f3",
        "fs": "m:90+t:3",
        "fields": "f12,f14",
        "_": str(int(time.time() * 1000)),
    }
    status, _, body = http_get(url, params=params, headers={"Referer": "https://quote.eastmoney.com/center/gridlist.html"}, timeout=30)
    if status != 200:
        return pd.DataFrame([])
    raw = parse_json_maybe_jsonp(body.decode("utf-8", errors="ignore"))
    diff = (((raw or {}).get("data") or {}).get("diff") or [])
    if not isinstance(diff, list):
        return pd.DataFrame([])
    df = pd.DataFrame(diff)
    df.rename(columns={"f12": "concept_code", "f14": "concept_name"}, inplace=True)
    return df[["concept_code", "concept_name"]]


def fetch_concept_constituents(concept_code: str, pagesize: int = 1000) -> List[str]:
    url = "https://push2.eastmoney.com/api/qt/clist/get"
    params = {
        "pn": "1",
        "pz": str(pagesize),
        "po": "1",
        "np": "1",
        "ut": "bd1d9ddb04089700cf9c27f6f7426281",
        "fltt": "2",
        "invt": "2",
        "fid": "f3",
        "fs": f"b:{concept_code}+f:!50",
        "fields": "f12",
        "_": str(int(time.time() * 1000)),
    }
    status, _, body = http_get(url, params=params, headers={"Referer": "https://quote.eastmoney.com/center/gridlist.html"}, timeout=30)
    if status != 200:
        return []
    raw = parse_json_maybe_jsonp(body.decode("utf-8", errors="ignore"))
    diff = (((raw or {}).get("data") or {}).get("diff") or [])
    if not isinstance(diff, list):
        return []
    return [str(x.get("f12") or "").zfill(6) for x in diff if isinstance(x, dict) and str(x.get("f12") or "").strip()]


def fetch_dt_pool(date_yyyymmdd: str, pagesize: int = 10000) -> List[Dict[str, Any]]:
    url = "http://push2ex.eastmoney.com/getTopicDTPool"
    params = {
        "ut": EASTMONEY_UT,
        "dpt": "wz.ztzt",
        "Pageindex": "0",
        "pagesize": str(pagesize),
        "sort": "fund:asc",
        "date": date_yyyymmdd,
    }
    status, _, body = http_get(url, params=params, headers={"Referer": "http://quote.eastmoney.com/"})
    if status != 200:
        return []
    raw = parse_json_maybe_jsonp(body.decode("utf-8", errors="ignore"))
    pool = (((raw or {}).get("data") or {}).get("pool") or [])
    return pool if isinstance(pool, list) else []


def find_latest_trade_date(max_lookback_days: int = 14) -> str:
    today = datetime.now().date()

    for i in range(0, max_lookback_days):
        d = today - timedelta(days=i)
        if d.weekday() >= 5:
            continue
        ds = _to_yyyymmdd(d)
        pool = fetch_zt_pool(ds)
        if pool:
            return ds

    raise RuntimeError("Failed to find latest trade date from eastmoney within lookback")


def find_previous_trade_date(from_date_yyyymmdd: str, max_lookback_days: int = 30) -> Optional[str]:
    try:
        base = datetime.strptime(from_date_yyyymmdd, "%Y%m%d").date()
    except ValueError:
        return None

    for i in range(1, max_lookback_days + 1):
        d = base - timedelta(days=i)
        if d.weekday() >= 5:
            continue
        ds = _to_yyyymmdd(d)
        pool = fetch_zt_pool(ds)
        if pool:
            return ds
    return None


def fetch_all_a_snapshot() -> pd.DataFrame:
    url = "https://push2.eastmoney.com/api/qt/clist/get"
    base_params = {
        "po": "1",
        "np": "1",
        "ut": "bd1d9ddb04089700cf9c27f6f7426281",
        "fltt": "2",
        "invt": "2",
        "fid": "f3",
        # A-share universe (best-effort). Add t:80 segments for broader coverage.
        "fs": "m:0+t:6,m:0+t:13,m:0+t:80,m:1+t:2,m:1+t:23,m:1+t:80",
        "fields": "f12,f14,f2,f3,f4,f5,f6",
    }

    headers = {"Referer": "https://quote.eastmoney.com/center/gridlist.html"}

    rows: List[Dict[str, Any]] = []
    pn = 1
    # Eastmoney often caps pz; keep it moderate and rely on pagination.
    pz = 200
    max_pages = 80
    total = None

    while pn <= max_pages:
        params = dict(base_params)
        params.update({"pn": str(pn), "pz": str(pz)})
        status, _, body = http_get(url, params=params, headers=headers)
        if status != 200:
            break
        raw = parse_json_maybe_jsonp(body.decode("utf-8", errors="ignore"))
        data = (raw or {}).get("data") or {}
        diff = data.get("diff") or []
        if not isinstance(diff, list) or not diff:
            break
        if total is None:
            try:
                total = int(data.get("total")) if data.get("total") is not None else None
            except Exception:
                total = None
        rows.extend(diff)
        if total is not None and len(rows) >= total:
            break
        pn += 1

    if not rows:
        return pd.DataFrame([])

    df = pd.DataFrame(rows)
    df.rename(
        columns={
            "f12": "code",
            "f14": "name",
            "f2": "close",
            "f3": "pct_chg",
            "f4": "chg",
            "f5": "vol",
            "f6": "amount",
        },
        inplace=True,
    )
    df["code"] = df["code"].astype(str).str.zfill(6)
    return df[["code", "name", "close", "pct_chg", "chg", "vol", "amount"]]


def build_concept_map_from_board_page(
    date_yyyymmdd: str,
    target_codes: Iterable[str],
    max_per_stock: int = 2,
    sleep_seconds: float = 0.05,
) -> pd.DataFrame:
    target_set = {str(c).zfill(6) for c in target_codes}
    concept_by_stock: Dict[str, List[str]] = {c: [] for c in target_set}

    url = "https://push2.eastmoney.com/api/qt/clist/get"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Referer": "https://quote.eastmoney.com/center/gridlist.html",
    }

    params = {
        "pn": "1",
        "pz": "2000",
        "po": "1",
        "np": "1",
        "ut": "bd1d9ddb04089700cf9c27f6f7426281",
        "fltt": "2",
        "invt": "2",
        "fid": "f3",
        "fs": "m:90+t:3",
        "fields": "f12,f14",
        "_": str(int(time.time() * 1000)),
    }

    status, _, body = http_get(url, params=params, headers=headers, timeout=30)
    if status != 200:
        return pd.DataFrame([])
    raw = parse_json_maybe_jsonp(body.decode("utf-8", errors="ignore"))
    concept_list = (((raw or {}).get("data") or {}).get("diff") or [])
    if not isinstance(concept_list, list) or not concept_list:
        return pd.DataFrame([])

    def is_done() -> bool:
        if not target_set:
            return True
        if max_per_stock <= 0:
            return False
        return all(len(concept_by_stock[c]) >= max_per_stock for c in target_set)

    for concept_item in concept_list:
        if not isinstance(concept_item, dict):
            continue
        concept_code = concept_item.get("f12")
        concept_name = concept_item.get("f14")
        if not concept_code or not concept_name:
            continue
        if any(skip in str(concept_name) for skip in ["昨日", "涨停", "连板", "破板"]):
            continue

        stock_params = {
            "pn": "1",
            "pz": "1000",
            "po": "1",
            "np": "1",
            "ut": "bd1d9ddb04089700cf9c27f6f7426281",
            "fltt": "2",
            "invt": "2",
            "fid": "f3",
            "fs": f"b:{concept_code}+f:!50",
            "fields": "f12",
            "_": str(int(time.time() * 1000)),
        }

        s2, _, b2 = http_get(url, params=stock_params, headers=headers, timeout=30)
        if s2 != 200:
            continue
        r2 = parse_json_maybe_jsonp(b2.decode("utf-8", errors="ignore"))
        stocks = (((r2 or {}).get("data") or {}).get("diff") or [])
        if not isinstance(stocks, list) or not stocks:
            continue

        hit = False
        for s in stocks:
            if not isinstance(s, dict):
                continue
            code = str(s.get("f12") or "").zfill(6)
            if code in target_set:
                if max_per_stock > 0 and len(concept_by_stock[code]) >= max_per_stock:
                    continue
                concept_by_stock[code].append(str(concept_name))
                hit = True

        if hit and is_done():
            break

        if sleep_seconds:
            time.sleep(sleep_seconds)

    rows = []
    for code in sorted(target_set):
        rows.append({"date": date_yyyymmdd, "code": code, "concepts": concept_by_stock.get(code, [])})
    return pd.DataFrame(rows)


def get_stock_concepts_f184(stock_code: str) -> List[str]:
    stock_code = _normalize_code(stock_code)
    secid = f"1.{stock_code}" if stock_code.startswith("6") else f"0.{stock_code}"
    url = "https://push2.eastmoney.com/api/qt/stock/get"
    params = {
        "secid": secid,
        "fields": "f62,f184,f86",
        "ut": "fa5fd1943c7b386f172d6893dbfba10b",
    }
    status, _, body = http_get(url, params=params, headers={"Referer": "https://quote.eastmoney.com/"})
    if status != 200:
        return []

    raw = parse_json_maybe_jsonp(body.decode("utf-8", errors="ignore"))
    concept_str = (((raw or {}).get("data") or {}).get("f184") or "")
    if concept_str in (None, "", "-"):
        return []
    if isinstance(concept_str, (int, float)):
        return []

    parts = str(concept_str).replace("；", ";").replace("，", ";").split(";")
    return [p.strip() for p in parts if p.strip()]


def _normalize_time(value: Any) -> Optional[str]:
    if value is None:
        return None
    s = str(value).strip()
    if not s:
        return None

    if s.isdigit():
        if len(s) == 6:
            return f"{s[0:2]}:{s[2:4]}:{s[4:6]}"
        if len(s) == 4:
            return f"{s[0:2]}:{s[2:4]}:00"
        if len(s) == 5:
            s = s.zfill(6)
            return f"{s[0:2]}:{s[2:4]}:{s[4:6]}"
        if len(s) == 3:
            s = s.zfill(4)
            return f"{s[0:2]}:{s[2:4]}:00"

    for fmt in ("%H:%M:%S", "%H:%M"):
        try:
            return datetime.strptime(s, fmt).strftime("%H:%M:%S")
        except ValueError:
            pass

    return None


def build_limitup_events(date_yyyymmdd: str, zt_pool: List[Dict[str, Any]], exclude_st: bool) -> pd.DataFrame:
    rows = []
    for it in zt_pool:
        code = _normalize_code(it.get("c") or it.get("code"))
        name = it.get("n") or it.get("name")
        if exclude_st and _is_st(name):
            continue

        first_time = _normalize_time(it.get("fbt") or it.get("first_time") or it.get("firstTime"))
        final_time = _normalize_time(it.get("lbt") or it.get("last_time") or it.get("lastTime"))
        open_times = it.get("zbc") or it.get("open_times") or it.get("openTimes")
        try:
            open_times = int(open_times) if open_times is not None else None
        except Exception:
            open_times = None

        lbc = it.get("lbc")
        try:
            lbc = int(lbc) if lbc is not None else 1
        except Exception:
            lbc = 1

        rows.append(
            {
                "date": date_yyyymmdd,
                "code": code,
                "name": name,
                "first_limitup_time": first_time,
                "final_seal_time": final_time,
                "open_times": open_times,
                "is_one_word": None,
                "amount": it.get("amount") or it.get("f6"),
                "turnover_rate": it.get("hs") or it.get("turnover"),
                "consecutive_days": lbc,
                "raw": json.dumps(it, ensure_ascii=False),
            }
        )

    return pd.DataFrame(rows)


def build_limitdown_list(date_yyyymmdd: str, dt_pool: List[Dict[str, Any]], exclude_st: bool) -> pd.DataFrame:
    rows = []
    for it in dt_pool:
        code = _normalize_code(it.get("c") or it.get("code"))
        name = it.get("n") or it.get("name")
        if exclude_st and _is_st(name):
            continue
        rows.append({"date": date_yyyymmdd, "code": code, "name": name, "raw": json.dumps(it, ensure_ascii=False)})
    return pd.DataFrame(rows)


def build_consecutive_board(date_yyyymmdd: str, limitup_events: pd.DataFrame) -> pd.DataFrame:
    if limitup_events is None or limitup_events.empty:
        return pd.DataFrame([])
    df = limitup_events.copy()
    df = df[df["consecutive_days"].fillna(1).astype(int) >= 2]
    return df[["date", "code", "name", "consecutive_days"]].sort_values(["consecutive_days", "code"], ascending=[False, True])


def build_concept_map(date_yyyymmdd: str, stock_codes: Iterable[str], max_per_stock: int = 2) -> pd.DataFrame:
    codes = [str(_normalize_code(c)).zfill(6) for c in stock_codes]
    codes = sorted(set(codes))

    rows = []
    non_empty = 0
    for code in codes:
        concepts = get_stock_concepts_f184(code)
        if max_per_stock and len(concepts) > max_per_stock:
            concepts = concepts[:max_per_stock]
        if concepts:
            non_empty += 1
        rows.append({"date": date_yyyymmdd, "code": code, "concepts": concepts})

    df = pd.DataFrame(rows)
    coverage = (non_empty / len(codes)) if codes else 0.0

    if coverage < 0.2:
        df2 = build_concept_map_from_board_page(date_yyyymmdd, codes, max_per_stock=max_per_stock)
        if df2 is not None and not df2.empty:
            return df2

    return df


def build_concept_heat_timeseries(limitup_events: pd.DataFrame, concept_map: pd.DataFrame, freq_minutes: int = 5) -> pd.DataFrame:
    if limitup_events is None or limitup_events.empty or concept_map is None or concept_map.empty:
        return pd.DataFrame([])

    le = limitup_events.copy()
    le["code"] = le["code"].astype(str).str.zfill(6)
    cm = concept_map.copy()
    cm["code"] = cm["code"].astype(str).str.zfill(6)

    def to_min_bucket(t: Any) -> Optional[int]:
        if t is None or (isinstance(t, float) and pd.isna(t)):
            return None
        s = str(t).strip()
        if not s:
            return None
        if ":" in s:
            parts = s.split(":")
            if len(parts) >= 2:
                return int(parts[0]) * 60 + int(parts[1])
        if s.isdigit() and len(s) >= 4:
            return int(s[0:2]) * 60 + int(s[2:4])
        return None

    le["first_min"] = le["first_limitup_time"].apply(to_min_bucket)

    start = 9 * 60 + 30
    end = 15 * 60
    buckets = list(range(start, end + 1, freq_minutes))

    cm_exploded = cm.explode("concepts")
    cm_exploded = cm_exploded[cm_exploded["concepts"].notna()]
    cm_exploded.rename(columns={"concepts": "concept_name"}, inplace=True)

    le2 = le.merge(cm_exploded[["code", "concept_name"]], on="code", how="left")
    le2 = le2[le2["concept_name"].notna()]

    rows = []
    for b in buckets:
        hh = b // 60
        mm = b % 60
        tlabel = f"{hh:02d}:{mm:02d}:00"
        tmp = le2[(le2["first_min"].notna()) & (le2["first_min"] <= b)]
        if tmp.empty:
            continue
        g = tmp.groupby("concept_name")["code"].nunique().reset_index(name="limitup_count")
        g["time"] = tlabel
        rows.append(g)

    if not rows:
        return pd.DataFrame([])

    out = pd.concat(rows, ignore_index=True)
    return out[["time", "concept_name", "limitup_count"]]


def fetch_index_daily_klines(secid: str, lmt: int = 1) -> Optional[Dict[str, Any]]:
    url = "https://push2his.eastmoney.com/api/qt/stock/kline/get"
    params = {
        "secid": secid,
        "ut": "fa5fd1943c7b386f172d6893dbfba10b",
        "klt": "101",
        "fqt": "0",
        "beg": "0",
        "end": "20500101",
        "lmt": str(max(2, lmt)),
        "fields1": "f1,f2,f3,f4,f5,f6",
        "fields2": "f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61",
    }
    status, _, body = http_get(url, params=params, headers={"Referer": "https://quote.eastmoney.com/"})
    if status != 200:
        return None
    raw = parse_json_maybe_jsonp(body.decode("utf-8", errors="ignore"))
    klines = (((raw or {}).get("data") or {}).get("klines") or [])
    if not klines:
        return None
    line = str(klines[-1])
    parts = line.split(",")
    if len(parts) < 7:
        return None
    return {
        "date": parts[0],
        "open": float(parts[1]),
        "close": float(parts[2]),
        "high": float(parts[3]),
        "low": float(parts[4]),
        "volume": float(parts[5]),
        "amount": float(parts[6]),
    }


def fetch_index_daily_for_date(secid: str, date_yyyymmdd: str) -> Optional[Dict[str, Any]]:
    url = "https://push2his.eastmoney.com/api/qt/stock/kline/get"
    params = {
        "secid": secid,
        "ut": "fa5fd1943c7b386f172d6893dbfba10b",
        "klt": "101",
        "fqt": "0",
        "beg": "0",
        "end": date_yyyymmdd,
        "lmt": "2",
        "fields1": "f1,f2,f3,f4,f5,f6",
        "fields2": "f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61",
    }
    status, _, body = http_get(url, params=params, headers={"Referer": "https://quote.eastmoney.com/"})
    if status != 200:
        return None
    raw = parse_json_maybe_jsonp(body.decode("utf-8", errors="ignore"))
    klines = (((raw or {}).get("data") or {}).get("klines") or [])
    if not klines:
        return None
    for line in reversed(klines):
        parts = str(line).split(",")
        if len(parts) >= 7 and parts[0].replace("-", "") == date_yyyymmdd:
            return {
                "date": parts[0],
                "open": float(parts[1]),
                "close": float(parts[2]),
                "high": float(parts[3]),
                "low": float(parts[4]),
                "volume": float(parts[5]),
                "amount": float(parts[6]),
            }
    parts = str(klines[-1]).split(",")
    if len(parts) < 7:
        return None
    return {
        "date": parts[0],
        "open": float(parts[1]),
        "close": float(parts[2]),
        "high": float(parts[3]),
        "low": float(parts[4]),
        "volume": float(parts[5]),
        "amount": float(parts[6]),
    }


def compute_ladder_stats(today_limitup: pd.DataFrame, prev_limitup: pd.DataFrame) -> Dict[str, Any]:
    if today_limitup is None or today_limitup.empty or prev_limitup is None or prev_limitup.empty:
        return {"levels": [], "upgrade_rates": {}}

    t = today_limitup[["code", "consecutive_days"]].copy()
    p = prev_limitup[["code", "consecutive_days"]].copy()
    t["code"] = t["code"].astype(str).str.zfill(6)
    p["code"] = p["code"].astype(str).str.zfill(6)
    t["consecutive_days"] = t["consecutive_days"].fillna(1).astype(int)
    p["consecutive_days"] = p["consecutive_days"].fillna(1).astype(int)

    merged = p.merge(t, on="code", how="left", suffixes=("_prev", "_today"))

    levels = []
    upgrade_rates: Dict[str, float] = {}

    for n in range(1, 11):
        base = merged[merged["consecutive_days_prev"] == n]
        total = int(base.shape[0])
        if total == 0:
            continue
        upgraded = int((base["consecutive_days_today"] == n + 1).sum())
        still_limitup = int(base["consecutive_days_today"].notna().sum())
        broken = total - still_limitup
        levels.append(
            {
                "from": n,
                "total": total,
                "upgraded": upgraded,
                "broken": broken,
                "still_limitup": still_limitup,
                "upgrade_rate": upgraded / total,
            }
        )
        upgrade_rates[f"{n}->{n+1}"] = upgraded / total

    return {"levels": levels, "upgrade_rates": upgrade_rates}


def export_review_data(base_dir: Path, date_yyyymmdd: str, exclude_st: bool = True, freq_minutes: int = 5) -> Path:
    out_dir = base_dir / "review_data" / date_yyyymmdd
    out_dir.mkdir(parents=True, exist_ok=True)

    zt_pool = fetch_zt_pool(date_yyyymmdd)
    dt_pool = fetch_dt_pool(date_yyyymmdd)

    limitup_events = build_limitup_events(date_yyyymmdd, zt_pool, exclude_st=exclude_st)
    limitdown_list = build_limitdown_list(date_yyyymmdd, dt_pool, exclude_st=exclude_st)
    consecutive_board = build_consecutive_board(date_yyyymmdd, limitup_events)

    concept_map = build_concept_map(date_yyyymmdd, limitup_events["code"].astype(str).tolist(), max_per_stock=2)
    concept_timeseries = build_concept_heat_timeseries(limitup_events, concept_map, freq_minutes=freq_minutes)

    all_a = fetch_all_a_snapshot()
    if exclude_st and not all_a.empty:
        all_a = all_a[~all_a["name"].apply(_is_st)].copy()

    pct_all = pd.to_numeric(all_a.get("pct_chg"), errors="coerce") if not all_a.empty else pd.Series([], dtype=float)
    amt_all = pd.to_numeric(all_a.get("amount"), errors="coerce") if not all_a.empty else pd.Series([], dtype=float)
    valid_cnt = int(pct_all.notna().sum()) if not all_a.empty else None
    up_count = int((pct_all > 0).sum()) if not all_a.empty else None
    down_count = int((pct_all < 0).sum()) if not all_a.empty else None
    flat_count = int((pct_all == 0).sum()) if not all_a.empty else None
    turnover = float(amt_all.fillna(0).sum()) if not all_a.empty else None

    broken_count = int((limitup_events["open_times"].fillna(0).astype(int) > 0).sum()) if not limitup_events.empty else 0
    limitup_count = int(limitup_events.shape[0])
    broken_rate = float(broken_count / limitup_count) if limitup_count else 0.0

    indices = {
        "SH000001": fetch_index_daily_for_date("1.000001", date_yyyymmdd),
        "SZ399001": fetch_index_daily_for_date("0.399001", date_yyyymmdd),
        "SZ399006": fetch_index_daily_for_date("0.399006", date_yyyymmdd),
        "SH000688": fetch_index_daily_for_date("1.000688", date_yyyymmdd),
    }

    prev_date = find_previous_trade_date(date_yyyymmdd)
    prev_summary = None
    ladder_stats = None

    if prev_date:
        prev_zt_pool = fetch_zt_pool(prev_date)
        prev_dt_pool = fetch_dt_pool(prev_date)
        prev_limitup = build_limitup_events(prev_date, prev_zt_pool, exclude_st=exclude_st)
        prev_limitdown = build_limitdown_list(prev_date, prev_dt_pool, exclude_st=exclude_st)
        prev_broken = int((prev_limitup["open_times"].fillna(0).astype(int) > 0).sum()) if not prev_limitup.empty else 0
        prev_limitup_count = int(prev_limitup.shape[0])
        prev_broken_rate = float(prev_broken / prev_limitup_count) if prev_limitup_count else 0.0
        prev_consecutive_ge2 = int((prev_limitup["consecutive_days"].fillna(1).astype(int) >= 2).sum()) if not prev_limitup.empty else 0

        prev_summary = {
            "date": prev_date,
            "limitup_count": prev_limitup_count,
            "limitdown_count": int(prev_limitdown.shape[0]),
            "broken_count": prev_broken,
            "broken_rate": prev_broken_rate,
            "consecutive_ge2_count": prev_consecutive_ge2,
        }

        ladder_stats = compute_ladder_stats(limitup_events, prev_limitup)

    market_overview = {
        "date": date_yyyymmdd,
        "universe": "B" if exclude_st else "A",
        "turnover": turnover,
        "up_count": up_count,
        "down_count": down_count,
        "flat_count": flat_count,
        "total_count": valid_cnt,
        "limitup_count": limitup_count,
        "limitdown_count": int(limitdown_list.shape[0]),
        "broken_count": broken_count,
        "broken_rate": broken_rate,
        "indices": indices,
        "prev_day": prev_summary,
        "ladder": ladder_stats,
    }

    market_overview_path = out_dir / "market_overview.json"
    market_overview_path.write_text(json.dumps(market_overview, ensure_ascii=False, indent=2), encoding="utf-8")

    if prev_summary is not None:
        (out_dir / "market_compare.json").write_text(
            json.dumps(
                {
                    "today": {
                        "date": date_yyyymmdd,
                        "limitup_count": limitup_count,
                        "limitdown_count": int(limitdown_list.shape[0]),
                        "broken_count": broken_count,
                        "broken_rate": broken_rate,
                        "consecutive_ge2_count": int(consecutive_board.shape[0]),
                    },
                    "prev": prev_summary,
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )

    if ladder_stats is not None:
        (out_dir / "ladder_stats.json").write_text(json.dumps(ladder_stats, ensure_ascii=False, indent=2), encoding="utf-8")

    def perf_stats(title: str, codes: List[str]) -> Dict[str, Any]:
        codes2 = [str(x).zfill(6) for x in (codes or []) if str(x).strip()]
        codes2 = sorted(set(codes2))
        if all_a is None or all_a.empty or not codes2:
            return {"title": title, "count": int(len(codes2)), "valid": 0}
        snap = all_a.copy()
        snap["code"] = snap["code"].astype(str).str.zfill(6)
        pct = pd.to_numeric(snap.get("pct_chg"), errors="coerce")
        snap["pct_chg"] = pct
        sub = snap[snap["code"].isin(codes2)].copy()
        pct2 = pd.to_numeric(sub.get("pct_chg"), errors="coerce")
        pct2 = pct2[pct2.notna()]
        if pct2.empty:
            return {"title": title, "count": int(len(codes2)), "valid": 0}
        return {
            "title": title,
            "count": int(len(codes2)),
            "valid": int(pct2.shape[0]),
            "pos_ratio": float((pct2 > 0).mean()),
            "neg_ratio": float((pct2 < 0).mean()),
            "ge5_ratio": float((pct2 >= 5).mean()),
            "le_5_ratio": float((pct2 <= -5).mean()),
            "mean_pct": float(pct2.mean()),
            "median_pct": float(pct2.median()),
        }

    emotion: Dict[str, Any] = {
        "date": date_yyyymmdd,
        "prev_date": prev_date or "",
        "today": {
            "limitup_count": int(limitup_count),
            "limitdown_count": int(limitdown_list.shape[0]),
            "broken_rate": float(broken_rate),
            "turnover": turnover,
            "up_count": up_count,
            "down_count": down_count,
            "flat_count": flat_count,
            "total_count": valid_cnt,
        },
        "prev": prev_summary or {},
        "yesterday": {},
        "cycle": "",
        "node": "",
        "dragon_kong_long": {},
    }

    if prev_date and prev_summary is not None:
        prev_limitup_codes = prev_limitup["code"].astype(str).str.zfill(6).tolist() if prev_limitup is not None and not prev_limitup.empty else []
        prev_broken_codes = []
        try:
            if prev_limitup is not None and not prev_limitup.empty and "open_times" in prev_limitup.columns:
                prev_broken_codes = (
                    prev_limitup[pd.to_numeric(prev_limitup["open_times"], errors="coerce").fillna(0) > 0]["code"].astype(str).str.zfill(6).tolist()
                )
        except Exception:
            prev_broken_codes = []

        emotion["yesterday"]["prev_limitup_today_perf"] = perf_stats("昨日涨停股今日表现", prev_limitup_codes)
        emotion["yesterday"]["prev_broken_today_perf"] = perf_stats("昨日炸板股今日表现", prev_broken_codes)

        ur = (ladder_stats or {}).get("upgrade_rates") if isinstance((ladder_stats or {}).get("upgrade_rates"), dict) else {}
        upgrade_12 = ur.get("1->2")
        emotion["yesterday"]["upgrade_1_2"] = upgrade_12
        emotion["yesterday"]["ladder"] = ladder_stats or {}

        pos_ratio = float((emotion["yesterday"]["prev_limitup_today_perf"] or {}).get("pos_ratio") or 0.0)
        prev_lu = int((prev_summary or {}).get("limitup_count") or 0)
        prev_br = float((prev_summary or {}).get("broken_rate") or 0.0)

        cycle = ""
        node = ""
        signal = "观察"
        reason = ""
        conditions: List[str] = []

        if broken_rate >= 0.55 or int(limitdown_list.shape[0]) >= 25 or (upgrade_12 is not None and float(upgrade_12) < 0.18) or pos_ratio < 0.45:
            cycle = "退潮/冰点"
            node = "退潮延续（风险未出清）"
            signal = "否"
            reason = "炸板率/跌停/晋级率或昨日涨停反馈偏弱，说明情绪仍在出清。"
            conditions = [
                "跌停数显著下降，且炸板率明显回落",
                "昨日涨停股红盘率显著改善",
                "1→2晋级率回到相对健康区间（如≥20%）",
            ]
        elif (prev_lu > 0 and int(limitup_count) >= int(prev_lu)) and broken_rate <= 0.45 and pos_ratio >= 0.5:
            cycle = "修复/主升"
            node = "修复确认或分歧转一致"
            signal = "是"
            reason = "情绪反馈改善，涨停延续与昨日涨停反馈同步转强，具备龙空龙切回龙头的胜率基础。"
            conditions = [
                "唯一/最强龙头出现突破确认或分歧回封确认",
                "核心题材回流，前排封单稳定",
                "风险温度计（昨日空头风标）不再新低，市场跌停不扩散",
            ]
        else:
            cycle = "修复试探"
            node = "分歧修复（观察确认）"
            signal = "观察"
            reason = "情绪有修复迹象但一致性不足，优先等待唯一龙头确立与风险温度计转好。"
            conditions = [
                "确认唯一龙头（高度/成交额优势拉开）",
                "盘中回封成功且不反复开板",
                "跌停继续收敛、炸板率继续回落",
            ]

        if not cycle:
            cycle = "未知"
        if not node:
            node = ""

        emotion["cycle"] = cycle
        emotion["node"] = node
        emotion["dragon_kong_long"] = {
            "signal": signal,
            "reason": reason,
            "conditions": conditions,
            "prev_limitup_pos_ratio": pos_ratio,
            "prev_limitup_count": prev_lu,
            "prev_broken_rate": prev_br,
        }

    (out_dir / "emotion_stats.json").write_text(json.dumps(emotion, ensure_ascii=False, indent=2), encoding="utf-8")

    limitup_events.to_csv(out_dir / "limitup_events.csv", index=False, encoding="utf-8-sig")
    limitdown_list.to_csv(out_dir / "limitdown_list.csv", index=False, encoding="utf-8-sig")
    consecutive_board.to_csv(out_dir / "consecutive_board.csv", index=False, encoding="utf-8-sig")
    concept_map.to_csv(out_dir / "concept_map.csv", index=False, encoding="utf-8-sig")
    concept_timeseries.to_csv(out_dir / "concept_timeseries.csv", index=False, encoding="utf-8-sig")

    events_df = fetch_public_events(date_yyyymmdd, max_items=30)
    events_df.to_csv(out_dir / "events.csv", index=False, encoding="utf-8-sig")

    concept_board_df = fetch_concept_board_list()
    concept_name_to_code = dict(zip(concept_board_df.get("concept_name", []), concept_board_df.get("concept_code", []))) if not concept_board_df.empty else {}

    concept_map_exploded = concept_map.copy()

    def parse_concepts_cell(v: Any) -> List[str]:
        if isinstance(v, list):
            return [str(x) for x in v if str(x).strip()]
        if v is None or (isinstance(v, float) and pd.isna(v)):
            return []
        s = str(v).strip()
        if not s:
            return []
        try:
            obj = ast.literal_eval(s)
            if isinstance(obj, list):
                return [str(x) for x in obj if str(x).strip()]
        except Exception:
            pass
        return []

    concept_map_exploded["concepts"] = concept_map_exploded["concepts"].apply(parse_concepts_cell)
    concept_map_exploded = concept_map_exploded.explode("concepts")
    concept_map_exploded = concept_map_exploded[concept_map_exploded["concepts"].notna()].copy()
    concept_map_exploded.rename(columns={"concepts": "concept_name"}, inplace=True)
    top_concepts = (
        concept_map_exploded.groupby("concept_name")["code"].nunique().sort_values(ascending=False).head(12).index.tolist()
        if not concept_map_exploded.empty
        else []
    )

    concept_stats_rows = []
    for cname in top_concepts:
        ccode = concept_name_to_code.get(cname)
        if not ccode:
            continue
        codes = fetch_concept_constituents(str(ccode))
        if not codes:
            continue
        sub = all_a[all_a["code"].isin(codes)].copy() if all_a is not None and not all_a.empty else pd.DataFrame([])
        if sub.empty:
            continue

        pct = pd.to_numeric(sub.get("pct_chg"), errors="coerce")
        amt = pd.to_numeric(sub.get("amount"), errors="coerce")
        vol = pd.to_numeric(sub.get("vol"), errors="coerce")
        lu_cnt = 0
        if limitup_events is not None and not limitup_events.empty and "code" in limitup_events.columns:
            lu_cnt = int(limitup_events["code"].astype(str).str.zfill(6).isin(codes).sum())
        ld_cnt = 0
        if limitdown_list is not None and not limitdown_list.empty and "code" in limitdown_list.columns:
            ld_cnt = int(limitdown_list["code"].astype(str).str.zfill(6).isin(codes).sum())

        concept_stats_rows.append(
            {
                "date": date_yyyymmdd,
                "concept_name": cname,
                "constituents": int(sub.shape[0]),
                "limitup_count": lu_cnt,
                "limitdown_count": ld_cnt,
                "up_count": int((pct > 0).sum()),
                "down_count": int((pct < 0).sum()),
                "flat_count": int((pct == 0).sum()),
                "avg_pct_chg": float(pct.mean()),
                "sum_vol": float(vol.fillna(0).sum()) if vol is not None else 0.0,
                "sum_amount": float(amt.fillna(0).sum()),
            }
        )
        time.sleep(0.05)

    concept_day_stats = pd.DataFrame(concept_stats_rows).sort_values(["up_count", "avg_pct_chg"], ascending=[False, False]) if concept_stats_rows else pd.DataFrame([])
    concept_day_stats.to_csv(out_dir / "concept_day_stats.csv", index=False, encoding="utf-8-sig")

    anchors_dir = out_dir / "anchors_intraday"
    anchors_dir.mkdir(parents=True, exist_ok=True)

    name_by_code: Dict[str, str] = {}
    try:
        if all_a is not None and not all_a.empty and "code" in all_a.columns and "name" in all_a.columns:
            tmp = all_a.copy()
            tmp["code"] = tmp["code"].astype(str).str.zfill(6)
            tmp["name"] = tmp["name"].astype(str)
            name_by_code = {str(r["code"]): str(r["name"]) for _, r in tmp[["code", "name"]].iterrows() if str(r["code"]).strip()}
    except Exception:
        name_by_code = {}

    prev_bull_codes: List[str] = []
    prev_bear_codes: List[str] = []
    if prev_date:
        try:
            prev_limitup2 = prev_limitup.copy() if prev_limitup is not None else pd.DataFrame([])
            if not prev_limitup2.empty:
                prev_limitup2["code"] = prev_limitup2["code"].astype(str).str.zfill(6)
                prev_limitup2["consecutive_days"] = pd.to_numeric(prev_limitup2.get("consecutive_days"), errors="coerce").fillna(1).astype(int)
                prev_limitup2["amount"] = pd.to_numeric(prev_limitup2.get("amount"), errors="coerce").fillna(0)
                prev_bull_codes = (
                    prev_limitup2.sort_values(["consecutive_days", "amount"], ascending=[False, False])["code"].astype(str).tolist()[:3]
                )
        except Exception:
            prev_bull_codes = []

        try:
            prev_limitdown2 = prev_limitdown.copy() if prev_limitdown is not None else pd.DataFrame([])
            if not prev_limitdown2.empty:
                prev_limitdown2["code"] = prev_limitdown2["code"].astype(str).str.zfill(6)
                prev_bear_codes = prev_limitdown2["code"].astype(str).tolist()[:3]
        except Exception:
            prev_bear_codes = []

    anchor_plan: List[Dict[str, Any]] = []
    for c in prev_bull_codes:
        if str(c).strip():
            anchor_plan.append({"code": str(c).zfill(6), "tag": "昨日多头风标"})
    for c in prev_bear_codes:
        if str(c).strip():
            anchor_plan.append({"code": str(c).zfill(6), "tag": "昨日空头风标"})
    for c in select_anchor_codes(limitup_events, consecutive_board, top_k=8):
        if str(c).strip():
            anchor_plan.append({"code": str(c).zfill(6), "tag": "当日锚"})

    dedup_plan: List[Dict[str, Any]] = []
    seen_codes = set()
    for it in anchor_plan:
        code = str(it.get("code") or "").zfill(6)
        if not code or code in seen_codes:
            continue
        seen_codes.add(code)
        dedup_plan.append({"code": code, "tag": str(it.get("tag") or "")})

    anchor_meta = []
    for it in dedup_plan:
        code = str(it.get("code") or "").zfill(6)
        tag = str(it.get("tag") or "")
        name = str(name_by_code.get(code, "") or "")
        df_1m = fetch_intraday_1m(code, date_yyyymmdd)
        if df_1m.empty:
            continue
        outp = anchors_dir / f"{code}.csv"
        df_1m.to_csv(outp, index=False, encoding="utf-8-sig")
        anchor_meta.append({"code": code, "name": name, "file": str(outp.name), "rows": int(df_1m.shape[0]), "tag": tag})
        time.sleep(0.05)
    (out_dir / "anchors_intraday.json").write_text(json.dumps(anchor_meta, ensure_ascii=False, indent=2), encoding="utf-8")

    return out_dir


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-dir", default=".")
    parser.add_argument("--date", default="", help="YYYYMMDD; empty means latest trading day")
    parser.add_argument("--universe", default="B", choices=["A", "B"])
    parser.add_argument("--freq", default=5, type=int)
    args = parser.parse_args()

    date_yyyymmdd = args.date.strip() if args.date else ""
    if not date_yyyymmdd:
        date_yyyymmdd = find_latest_trade_date()

    exclude_st = args.universe.upper() == "B"

    out_dir = export_review_data(Path(args.base_dir).resolve(), date_yyyymmdd, exclude_st=exclude_st, freq_minutes=int(args.freq))
    print(str(out_dir))


if __name__ == "__main__":
    main()
