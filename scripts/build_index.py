#!/usr/bin/env python3
"""data/posts/*.json 을 검사하고 게시판용 data/index.json 을 만든다.

사용법:
  python3 scripts/build_index.py          # 검사 + index.json 생성
  python3 scripts/build_index.py --check  # 검사만 (오류 있으면 종료코드 1)
"""
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
POSTS = ROOT / "data" / "posts"
REPORTS = ROOT / "reports"
INDEX = ROOT / "data" / "index.json"

CATEGORIES = {"파워트레인", "전력변환", "시장·기타"}
REQUIRED = ["id", "category", "company", "event_type", "importance", "importance_reason",
            "title", "one_line", "content", "points", "implication", "source"]
BAD_URL = re.compile(r"(google\.[a-z.]+/search|news\.google\.com|bing\.com/search|search\.naver\.com)")
CAT_ORDER = {"파워트레인": 0, "전력변환": 1, "시장·기타": 2}


def validate(path: Path, data: dict) -> list[str]:
    errs = []
    date = path.stem
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", date):
        errs.append("파일 이름은 YYYY-MM-DD.json 이어야 합니다")
    if data.get("date") != date:
        errs.append(f"date 값({data.get('date')})이 파일 이름과 다릅니다")
    items = data.get("items")
    if not isinstance(items, list):
        return errs + ["items 는 배열이어야 합니다"]
    ids = set()
    prefix = date.replace("-", "") + "-"
    for i, it in enumerate(items):
        tag = f"items[{i}] ({it.get('id', '?')})"
        for k in REQUIRED:
            if it.get(k) in (None, "", []):
                errs.append(f"{tag}: '{k}' 값이 없습니다")
        iid = it.get("id", "")
        if iid in ids:
            errs.append(f"{tag}: id 중복")
        ids.add(iid)
        if iid and not iid.startswith(prefix):
            errs.append(f"{tag}: id는 {prefix}NN 형식이어야 합니다")
        if it.get("category") and it["category"] not in CATEGORIES:
            errs.append(f"{tag}: category는 {sorted(CATEGORIES)} 중 하나여야 합니다")
        if it.get("importance") not in (1, 2, 3):
            errs.append(f"{tag}: importance는 1, 2, 3 중 하나여야 합니다")
        pts = it.get("points") or []
        if not isinstance(pts, list):
            errs.append(f"{tag}: points 는 배열이어야 합니다")
        else:
            for p in pts:
                if not (isinstance(p, str) or (isinstance(p, dict) and p.get("text"))):
                    errs.append(f"{tag}: points 항목은 문자열 또는 {{text, sub}} 이어야 합니다")
        src = it.get("source") or {}
        url = src.get("url", "")
        if not url.startswith("http"):
            errs.append(f"{tag}: source.url 이 올바른 주소가 아닙니다")
        elif BAD_URL.search(url):
            errs.append(f"{tag}: source.url 이 검색결과 페이지입니다. 실제 기사 주소를 넣으세요")
        if not src.get("name"):
            errs.append(f"{tag}: source.name 이 없습니다")
        pub = src.get("published", "")
        if pub and not re.fullmatch(r"\d{4}-\d{2}-\d{2}", pub):
            errs.append(f"{tag}: source.published 는 YYYY-MM-DD 형식이어야 합니다")
        tbl = it.get("table")
        if tbl:
            hdr = tbl.get("headers") or []
            for r in tbl.get("rows") or []:
                if len(r) != len(hdr):
                    errs.append(f"{tag}: table 행의 칸 수가 headers 와 다릅니다")
                    break
    for t in data.get("top3") or []:
        if t not in ids:
            errs.append(f"top3 의 '{t}' 가 items 에 없습니다")
    return errs


def sort_items(items):
    return sorted(items, key=lambda x: (-x.get("importance", 0), CAT_ORDER.get(x.get("category"), 9), x.get("id", "")))


def load_all():
    days, problems = [], {}
    for p in sorted(POSTS.glob("*.json")):
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
        except json.JSONDecodeError as e:
            problems[p.name] = [f"JSON 형식 오류: {e}"]
            continue
        errs = validate(p, data)
        if errs:
            problems[p.name] = errs
        days.append((p, data))
    return days, problems


def main():
    check_only = "--check" in sys.argv
    days, problems = load_all()
    if problems:
        for name, errs in problems.items():
            print(f"[오류] {name}")
            for e in errs:
                print("   -", e)
        sys.exit(1)
    print(f"검사 통과: {len(days)}개 파일")
    if check_only:
        return

    out_days, out_items = [], []
    for p, data in sorted(days, key=lambda d: d[1]["date"], reverse=True):
        date = data["date"]
        items = sort_items(data.get("items", []))
        pdf = REPORTS / f"{date}.pdf"
        out_days.append({
            "date": date,
            "count": len(items),
            "stars": {str(s): sum(1 for i in items if i["importance"] == s) for s in (3, 2, 1)},
            "top3": data.get("top3", []),
            "note": data.get("note", ""),
            "pdf": f"reports/{date}.pdf" if pdf.exists() else None,
        })
        for it in items:
            out_items.append({
                "id": it["id"], "date": date, "category": it["category"], "company": it["company"],
                "product": it.get("product", ""), "event_type": it["event_type"], "importance": it["importance"],
                "title": it["title"], "one_line": it["one_line"],
                "source_name": it["source"]["name"], "source_url": it["source"]["url"],
                "published": it["source"].get("published", ""),
            })
    index = {
        "updated": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "days": out_days,
        "items": out_items,
    }
    INDEX.write_text(json.dumps(index, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"data/index.json 생성: {len(out_days)}일, {len(out_items)}건")


if __name__ == "__main__":
    main()
