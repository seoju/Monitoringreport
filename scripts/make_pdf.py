#!/usr/bin/env python3
"""일일 동향 데이터(data/posts/날짜.json)로 요약 PDF(reports/날짜.pdf)를 만든다.

사용법:
  python3 scripts/make_pdf.py                 # 가장 최근 날짜
  python3 scripts/make_pdf.py --date 2026-11-11
  python3 scripts/make_pdf.py --require-today # 오늘(KST) 데이터가 없으면 실패
  python3 scripts/make_pdf.py --html out.html # PDF 대신 HTML만 저장(디자인 확인용)
"""
import argparse
import html
import json
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
POSTS = ROOT / "data" / "posts"
REPORTS = ROOT / "reports"
KST = timezone(timedelta(hours=9))

CAT_ORDER = ["파워트레인", "전력변환", "시장·기타"]
CIRCLED = "①②③④⑤⑥⑦⑧⑨⑩"


def esc(s) -> str:
    return html.escape(str(s or ""), quote=True)


def stars(n: int) -> str:
    return "★" * n + "☆" * (3 - n)


def short_date(d: str) -> str:
    return d[2:]  # 2026-11-11 -> 26-11-11


def load(date: str | None, require_today: bool):
    files = sorted(POSTS.glob("*.json"))
    if not files:
        sys.exit("data/posts 에 데이터가 없습니다.")
    today = datetime.now(KST).strftime("%Y-%m-%d")
    if require_today:
        date = today
    if date:
        p = POSTS / f"{date}.json"
        if not p.exists():
            sys.exit(f"{date} 데이터가 없습니다. (data/posts/{date}.json) — 오늘 수집이 실행되지 않았을 수 있습니다.")
    else:
        p = files[-1]
    return json.loads(p.read_text(encoding="utf-8"))


def sort_items(items):
    return sorted(items, key=lambda x: (-x["importance"], CAT_ORDER.index(x["category"]) if x["category"] in CAT_ORDER else 9, x["id"]))


def render_points(points) -> str:
    out = []
    for i, p in enumerate(points):
        num = CIRCLED[i] if i < len(CIRCLED) else f"{i+1}."
        if isinstance(p, dict):
            text, subs = p.get("text", ""), p.get("sub") or []
        else:
            text, subs = p, []
        sub_html = "".join(f'<div class="sub">└ {esc(s)}</div>' for s in subs)
        out.append(f'<div class="pt"><span class="num">{num}</span><div><div>{esc(text)}</div>{sub_html}</div></div>')
    return "".join(out)


def render_table(t) -> str:
    if not t:
        return ""
    head = "".join(f"<th>{esc(h)}</th>" for h in t.get("headers", []))
    rows = "".join("<tr>" + "".join(f"<td>{esc(c)}</td>" for c in r) + "</tr>" for r in t.get("rows", []))
    cap = f'<div class="tcap">{esc(t["caption"])}</div>' if t.get("caption") else ""
    return f'{cap}<table class="data"><thead><tr>{head}</tr></thead><tbody>{rows}</tbody></table>'


def build_html(data: dict, cfg: dict) -> str:
    date = data["date"]
    items = sort_items(data.get("items", []))
    site = cfg.get("site_url", "").rstrip("/") + "/"
    by_cat = {c: [i for i in items if i["category"] == c] for c in CAT_ORDER}
    top_ids = data.get("top3") or [i["id"] for i in items[:3]]
    top = [i for tid in top_ids for i in items if i["id"] == tid]

    # ---------- 표지 ----------
    top_html = "".join(
        f'<li><span class="stars s{i["importance"]}">{stars(i["importance"])}</span>'
        f'<a href="#{esc(i["id"])}">{esc(i["title"])}</a>'
        f'<div class="ol">{esc(i["one_line"])}</div></li>'
        for i in top
    )
    sections = []
    for cat in CAT_ORDER:
        lst = by_cat[cat]
        if not lst:
            continue
        rows = "".join(
            f'<div class="toc-row"><span class="stars s{i["importance"]}">{stars(i["importance"])}</span>'
            f'<a class="toc-link" href="#{esc(i["id"])}">{esc(i["title"])}</a>'
            f'<a class="ext" href="{esc(i["source"]["url"])}">원문↗</a></div>'
            for i in lst
        )
        sections.append(
            f'<section class="toc-sec"><div class="toc-list">{rows}</div>'
            f'<div class="toc-label"><div class="cat">{esc(cat)}</div><div class="cat-d">{esc(cfg["category_desc"].get(cat, ""))}</div></div></section>'
        )
    if not items:
        sections.append(f'<div class="empty">{esc(data.get("note") or "오늘은 주요 뉴스가 없습니다.")}</div>')
    note = f'<div class="note">※ {esc(data["note"])}</div>' if data.get("note") and items else ""
    cover = f"""
    <div class="cover">
      <div class="top3"><div class="h">오늘의 Top {len(top)}</div><ol>{top_html}</ol></div>
      {''.join(sections)}
      <div class="meta">수집 기간: {esc(data.get('window', ''))} · 총 {len(items)}건 ·
        <a href="{esc(site)}">게시판 바로가기</a>{(' · 검색 범위: ' + esc(data['searched'])) if data.get('searched') else ''}</div>
      {note}
    </div>"""

    # ---------- 상세 ----------
    details = []
    for i in items:
        src = i["source"]
        extra = "".join(f' · <a href="{esc(l["url"])}">{esc(l["name"])}↗</a>' for l in i.get("extra_links") or [])
        bg = f'<div class="ln arrow">→ 주요 배경 : {esc(i["background"])}</div>' if i.get("background") else ""
        chk = f'<div class="check">확인 필요: {esc(i["check_needed"])}</div>' if i.get("check_needed") else ""
        details.append(f"""
      <article class="item" id="{esc(i['id'])}">
        <div class="ititle">
          <a class="t" href="{esc(src['url'])}">{esc(i['title'])}</a>
          <span class="src">출처: {esc(src['name'])}</span>
        </div>
        <div class="chips"><span class="chip c-{CAT_ORDER.index(i['category']) if i['category'] in CAT_ORDER else 2}">{esc(i['category'])}</span>
          <span class="chip">{esc(i['company'])}</span>{f'<span class="chip">{esc(i["product"])}</span>' if i.get('product') else ''}
          <span class="chip">{esc(i['event_type'])}</span>
          <span class="stars s{i['importance']}">{stars(i['importance'])}</span><span class="why">{esc(i['importance_reason'])}</span></div>
        <div class="ln">- 내용 : {esc(i['content'])}</div>
        {bg}
        <div class="ln arrow">→ 주요 내용</div>
        <div class="points">{render_points(i.get('points') or [])}</div>
        {render_table(i.get('table'))}
        <div class="impl"><b>현대케피코 관점 시사점</b> {esc(i['implication'])}</div>
        {chk}
        <div class="links">원문: <a href="{esc(src['url'])}">{esc(src.get('original_title') or src['url'])}↗</a>
          ({esc(src.get('published', ''))}){extra} · <a href="{esc(site)}#/post/{esc(i['id'])}">게시판에서 보기</a> · <a href="#cover">목차로</a></div>
      </article>""")

    css = CSS
    return f"""<!DOCTYPE html><html lang="ko"><head><meta charset="utf-8">
<title>{esc(cfg['title'])} {esc(date)}</title><style>{css}</style></head><body>
<div class="hdr">
  <div class="brand">{esc(cfg['brand'])}</div>
  <div class="title">{esc(cfg['title'])}</div>
  <div class="date">{short_date(date)}</div>
  <div class="sub">{esc(cfg['board_title'])}</div>
</div>
<div class="ftr">{esc(cfg['footer'])}</div>
<table class="layout"><thead><tr><td><div class="hdr-space"></div></td></tr></thead>
<tfoot><tr><td><div class="ftr-space"></div></td></tr></tfoot>
<tbody><tr><td>
<div id="cover"></div>
{cover}
<div class="details">{''.join(details)}</div>
</td></tr></tbody></table>
</body></html>"""


CSS = r"""
@page { size: A4; margin: 0; }
* { box-sizing: border-box; }
html, body { margin: 0; padding: 0; }
body { font-family: "Noto Sans CJK KR", "Noto Sans KR", "Malgun Gothic", sans-serif; color: #1d1d1f;
       font-size: 10.2pt; line-height: 1.55; -webkit-print-color-adjust: exact; print-color-adjust: exact; }
a { color: #0b57d0; }
.hdr { position: fixed; top: 0; left: 0; right: 0; height: 27mm; color: #fff; padding: 4mm 9mm 0;
       background: #0b2560;
       background-image: radial-gradient(circle at 78% 40%, rgba(255,255,255,.10) 0 1.2px, transparent 1.6px),
                         linear-gradient(100deg, #0a2058 0%, #0d2b6b 60%, #163a84 100%);
       background-size: 9px 9px, 100% 100%; }
.hdr .brand { font-size: 14pt; font-weight: 700; letter-spacing: .2px; }
.hdr .title { font-size: 25pt; font-weight: 700; line-height: 1.15; margin-top: 1mm; }
.hdr .date { position: absolute; top: 4.5mm; right: 9mm; font-size: 13pt; font-weight: 700; }
.hdr .sub { position: absolute; bottom: 3.5mm; right: 9mm; font-size: 10.5pt; font-weight: 700; opacity: .95; }
.ftr { position: fixed; bottom: 0; left: 0; right: 0; height: 9mm; padding: 2mm 9mm 0; font-size: 7.6pt; color: #666;
       border-top: 0.3mm solid #ddd; background: #fff; }
.layout { width: 100%; border-collapse: collapse; }
.layout > thead td, .layout > tfoot td, .layout > tbody > tr > td { padding: 0; }
.hdr-space { height: 31mm; }
.ftr-space { height: 12mm; }
.layout > tbody > tr > td { padding: 0 9mm; }

/* 표지 */
.cover { break-after: page; }
.top3 { border: 0.4mm solid #0b2560; border-radius: 2mm; padding: 3mm 5mm 2mm; margin-bottom: 5mm; background: #f4f7fc; }
.top3 .h { font-weight: 700; color: #0b2560; font-size: 11.5pt; margin-bottom: 1mm; }
.top3 ol { margin: 0; padding-left: 5mm; }
.top3 li { margin: 1.2mm 0; }
.top3 li a { font-weight: 700; font-size: 11.5pt; }
.top3 .ol { color: #444; font-size: 9.5pt; margin-left: 0; }
.toc-sec { display: flex; gap: 5mm; border-top: 0.8mm solid #8a8a8a; padding: 4mm 0 5mm; break-inside: avoid; }
.toc-list { flex: 1; }
.toc-row { margin: 1.6mm 0; font-size: 12.5pt; line-height: 1.4; }
.toc-link { font-weight: 700; color: #0b57d0; text-decoration: underline; }
.toc-row .ext { font-size: 8.5pt; margin-left: 2mm; color: #6b7a99; text-decoration: none; border: 0.25mm solid #c5cde0; border-radius: 1mm; padding: 0 1.2mm; }
.toc-label { width: 42mm; text-align: right; }
.toc-label .cat { font-size: 15pt; font-weight: 800; color: #0b2560; }
.toc-label .cat-d { font-size: 8.5pt; color: #666; }
.stars { color: #d79a00; letter-spacing: -0.5px; margin-right: 1.8mm; font-size: 10pt; }
.stars.s3 { color: #d93025; }
.meta { border-top: 0.8mm solid #8a8a8a; padding-top: 3mm; font-size: 8.8pt; color: #555; }
.note { font-size: 8.8pt; color: #555; margin-top: 1mm; }
.empty { padding: 20mm 0; text-align: center; color: #555; font-size: 12pt; }

/* 상세 */
.item { break-inside: avoid; margin: 1mm 0 8mm; }
.ititle { display: flex; align-items: flex-end; gap: 4mm; border-bottom: 0.9mm solid #8a8a8a; padding-bottom: 1.2mm; }
.ititle .t { flex: 1; font-size: 14pt; font-weight: 800; color: #0b2560; text-decoration: none; line-height: 1.3; }
.ititle .src { font-size: 8.5pt; color: #333; white-space: nowrap; }
.chips { margin: 2mm 0 2.5mm; font-size: 8.4pt; display: flex; flex-wrap: wrap; align-items: center; gap: 1.4mm; }
.chip { border: 0.25mm solid #c5cde0; background: #f4f6fb; border-radius: 1mm; padding: 0.2mm 1.6mm; color: #2a3a5e; }
.chip.c-0 { background: #e6efff; border-color: #a9c1f0; }
.chip.c-1 { background: #e7f6ee; border-color: #9fd1b5; }
.chip.c-2 { background: #f3eefc; border-color: #c9b8ec; }
.why { color: #666; }
.ln { margin: 1mm 0 0.6mm 2mm; }
.ln.arrow { margin-left: 8mm; }
.points { margin: 0.5mm 0 2mm 12mm; }
.pt { display: flex; gap: 1.6mm; margin: 0.8mm 0; }
.pt .num { flex: none; }
.pt .sub { color: #444; margin-left: 2mm; font-size: 9.6pt; }
.tcap { margin: 2mm 0 1mm 12mm; font-weight: 700; font-size: 9.4pt; }
table.data { border-collapse: collapse; margin: 0 0 2.5mm 12mm; width: calc(100% - 12mm); font-size: 9.2pt; }
table.data th { background: #dcdcdc; font-weight: 700; border: 0.25mm solid #9a9a9a; padding: 1.2mm 2mm; }
table.data td { border: 0.25mm solid #9a9a9a; padding: 1.2mm 2mm; text-align: center; }
table.data td:first-child { font-weight: 700; background: #f2f2f2; }
.impl { margin: 2mm 0 1.5mm 8mm; background: #fff8e6; border-left: 1.2mm solid #f0b400; padding: 1.8mm 3mm; font-size: 9.6pt; }
.impl b { color: #7a5600; margin-right: 1.5mm; }
.check { margin: 0 0 1mm 8mm; font-size: 8.8pt; color: #b3261e; }
.links { margin: 1.5mm 0 0 8mm; font-size: 8.6pt; color: #555; word-break: break-all; }
"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--date")
    ap.add_argument("--require-today", action="store_true")
    ap.add_argument("--html")
    args = ap.parse_args()

    cfg = json.loads((ROOT / "config" / "report.json").read_text(encoding="utf-8"))
    data = load(args.date, args.require_today)
    doc = build_html(data, cfg)

    if args.html:
        Path(args.html).write_text(doc, encoding="utf-8")
        print(f"HTML 저장: {args.html}")
        return

    from playwright.sync_api import sync_playwright

    REPORTS.mkdir(exist_ok=True)
    out = REPORTS / f"{data['date']}.pdf"
    tmp = REPORTS / f".{data['date']}.html"
    tmp.write_text(doc, encoding="utf-8")
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page()
            page.goto(tmp.resolve().as_uri(), wait_until="load")
            page.pdf(path=str(out), format="A4", print_background=True, prefer_css_page_size=True, tagged=True, outline=False)
            browser.close()
    finally:
        tmp.unlink(missing_ok=True)
    print(f"PDF 생성: {out.relative_to(ROOT)} ({len(data.get('items', []))}건)")

    gh_out = os.environ.get("GITHUB_OUTPUT")
    if gh_out:
        with open(gh_out, "a", encoding="utf-8") as f:
            f.write(f"date={data['date']}\npdf={out.relative_to(ROOT)}\ncount={len(data.get('items', []))}\n")


if __name__ == "__main__":
    main()
