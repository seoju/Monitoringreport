#!/usr/bin/env python3
"""요약 PDF를 첨부해 등록된 수신자에게 메일을 보낸다 (Gmail SMTP).

필요한 환경변수 (GitHub 저장소 Settings → Secrets and variables → Actions 에 등록):
  GMAIL_USER          보내는 Gmail 주소
  GMAIL_APP_PASSWORD  Gmail 앱 비밀번호 (16자리)
  MAIL_TO             받는 사람. 여러 명은 쉼표로 구분

사용법:
  python3 scripts/send_mail.py --date 2026-11-11
"""
import argparse
import html
import json
import os
import smtplib
import sys
from email.message import EmailMessage
from email.utils import formataddr
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CAT_ORDER = ["파워트레인", "전력변환", "시장·기타"]


def esc(s):
    return html.escape(str(s or ""), quote=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", required=True)
    ap.add_argument("--dry-run", action="store_true", help="보내지 않고 메일 내용만 출력")
    args = ap.parse_args()

    cfg = json.loads((ROOT / "config" / "report.json").read_text(encoding="utf-8"))
    data = json.loads((ROOT / "data" / "posts" / f"{args.date}.json").read_text(encoding="utf-8"))
    pdf = ROOT / "reports" / f"{args.date}.pdf"
    if not pdf.exists():
        sys.exit(f"PDF가 없습니다: {pdf}")

    items = sorted(data.get("items", []), key=lambda x: (-x["importance"], CAT_ORDER.index(x["category"]) if x["category"] in CAT_ORDER else 9, x["id"]))
    site = cfg["site_url"].rstrip("/") + "/"
    short = args.date[2:]

    rows = []
    for cat in CAT_ORDER:
        lst = [i for i in items if i["category"] == cat]
        if not lst:
            continue
        rows.append(f'<tr><td colspan="2" style="padding:14px 0 4px;font-weight:700;color:#0b2560;border-bottom:2px solid #8a8a8a">{esc(cat)}</td></tr>')
        for i in lst:
            st = "★" * i["importance"] + "☆" * (3 - i["importance"])
            color = "#d93025" if i["importance"] == 3 else "#d79a00"
            rows.append(
                f'<tr><td style="padding:6px 8px 6px 0;color:{color};white-space:nowrap;vertical-align:top">{st}</td>'
                f'<td style="padding:6px 0"><a href="{esc(i["source"]["url"])}" style="color:#0b57d0;font-weight:700">{esc(i["title"])}</a>'
                f'<div style="color:#555;font-size:13px">{esc(i["one_line"])} '
                f'<a href="{site}#/post/{esc(i["id"])}" style="color:#6b7a99">[게시판]</a></div></td></tr>'
            )
    if not items:
        rows.append(f'<tr><td colspan="2" style="padding:20px 0;color:#555">{esc(data.get("note") or "오늘은 주요 뉴스가 없습니다.")}</td></tr>')

    body_html = f"""<div style="font-family:'Malgun Gothic','Apple SD Gothic Neo',sans-serif;max-width:680px;color:#1d1d1f">
<div style="background:#0b2560;color:#fff;padding:14px 18px">
  <div style="font-size:13px;font-weight:700">{esc(cfg['brand'])} · {short}</div>
  <div style="font-size:22px;font-weight:700">{esc(cfg['title'])}</div>
</div>
<p style="margin:14px 0 4px">오늘의 글로벌 경쟁사 동향 <b>{len(items)}건</b>입니다. 자세한 내용은 첨부 PDF를 확인해 주세요.<br>
제목을 누르면 원문 기사가 열립니다.</p>
<table style="border-collapse:collapse;width:100%;font-size:14px">{''.join(rows)}</table>
<p style="margin-top:18px"><a href="{site}" style="background:#0b2560;color:#fff;padding:8px 14px;text-decoration:none;border-radius:4px">게시판에서 전체 보기</a></p>
<p style="font-size:12px;color:#777;margin-top:18px">{esc(cfg['footer'])}</p>
</div>"""

    text_lines = [f"{cfg['title']} {short} — {len(items)}건", ""]
    for i in items:
        text_lines.append(f"[{'★' * i['importance']}] {i['title']}\n  {i['one_line']}\n  {i['source']['url']}")
    text_lines += ["", f"게시판: {site}"]

    subject = cfg["mail_subject"].format(date=short, count=len(items))
    if args.dry_run:
        print("제목:", subject)
        print("\n".join(text_lines))
        return

    user = os.environ.get("GMAIL_USER", "").strip()
    pw = os.environ.get("GMAIL_APP_PASSWORD", "").replace(" ", "").strip()
    to = [a.strip() for a in os.environ.get("MAIL_TO", "").replace(";", ",").replace("\n", ",").split(",") if a.strip()]
    missing = [n for n, v in (("GMAIL_USER", user), ("GMAIL_APP_PASSWORD", pw), ("MAIL_TO", to)) if not v]
    if missing:
        sys.exit("메일 설정이 없습니다. GitHub Secrets 에 다음 값을 등록하세요: " + ", ".join(missing))

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = formataddr((cfg.get("mail_from_name", "Report"), user))
    msg["To"] = user  # 받는 사람끼리 주소가 보이지 않도록 본인에게 보내고 나머지는 숨은참조
    msg["Bcc"] = ", ".join(to)
    msg.set_content("\n".join(text_lines))
    msg.add_alternative(body_html, subtype="html")
    msg.add_attachment(pdf.read_bytes(), maintype="application", subtype="pdf",
                       filename=f"Global Competitor Trend_{args.date.replace('-', '')}.pdf")

    with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=60) as s:
        s.login(user, pw)
        s.send_message(msg)
    print(f"메일 발송 완료: {len(to)}명")


if __name__ == "__main__":
    main()
