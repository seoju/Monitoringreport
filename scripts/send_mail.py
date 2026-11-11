#!/usr/bin/env python3
"""요약 PDF를 첨부해 등록된 수신자에게 메일을 보낸다 (SMTP: 네이버·Gmail 등).

필요한 환경변수 (GitHub 저장소 Settings → Secrets and variables → Actions 에 등록):
  SMTP_HOST      메일 서버. 네이버 smtp.naver.com / Gmail smtp.gmail.com (비우면 Gmail)
  SMTP_USER      보내는 메일 주소 (예: abc@naver.com)
  SMTP_PASSWORD  비밀번호 (네이버: 계정 비밀번호 또는 애플리케이션 비밀번호 / Gmail: 앱 비밀번호)
  MAIL_TO        받는 사람. 여러 명은 쉼표로 구분
  (예전 이름 GMAIL_USER, GMAIL_APP_PASSWORD 도 그대로 인식)

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

    env = lambda *names: next((os.environ[n] for n in names if os.environ.get(n, "").strip()), "")
    host = env("SMTP_HOST").strip() or "smtp.gmail.com"
    user = env("SMTP_USER", "GMAIL_USER").strip().strip('"\'<>').strip()
    pw = env("SMTP_PASSWORD", "GMAIL_APP_PASSWORD").strip().strip('"\'')
    if "gmail" in host:
        pw = "".join(pw.split())  # Gmail 앱 비밀번호의 띄어쓰기 제거
    to = [a.strip() for a in os.environ.get("MAIL_TO", "").replace(";", ",").replace("\n", ",").split(",") if a.strip()]
    missing = [n for n, v in (("SMTP_USER", user), ("SMTP_PASSWORD", pw), ("MAIL_TO", to)) if not v]
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

    # 비밀값은 출력하지 않고 형식만 점검
    hint = " ← Gmail 앱 비밀번호는 영문 16자입니다" if "gmail" in host and not (len(pw) == 16 and pw.isalpha()) else ""
    print(f"메일 서버: {host} / 보내는 계정: ***@{user.split('@')[-1] if '@' in user else '(주소 형식 아님)'}"
          f" / 비밀번호 길이: {len(pw)}자{hint} / 받는 사람: {len(to)}명")

    # 네이버는 로그인 아이디만(@naver.com 제외) 받는 경우가 있어 둘 다 시도
    logins = [user]
    if "naver" in host and "@" in user:
        logins.append(user.split("@")[0])

    errors = []
    for login in logins:
        try:
            with smtplib.SMTP_SSL(host, 465, timeout=60) as s:
                s.login(login, pw)
                s.send_message(msg, from_addr=user)
            print(f"메일 발송 완료: {len(to)}명 (로그인 형식: {'아이디만' if '@' not in login else '전체 주소'})")
            return
        except smtplib.SMTPAuthenticationError as e:
            errors.append(f"{'아이디만' if '@' not in login else '전체 주소'} 로그인 거부 {e.smtp_code}: {e.smtp_error.decode(errors='ignore')}")
        except (smtplib.SMTPServerDisconnected, OSError) as e:
            errors.append(f"{login.split('@')[-1] if '@' in login else '아이디'}: {e}")
            break
    if errors and all("로그인 거부" in x for x in errors):
        sys.exit("메일 서버가 로그인을 거부했습니다.\n" + "\n".join(errors) +
                 "\n→ SMTP_USER·SMTP_PASSWORD 값, 네이버 'POP3/SMTP 사용' 설정, 2단계 인증 사용 시 애플리케이션 비밀번호 여부를 확인하세요.")

    for mode in ("ssl465", "starttls587"):
        try:
            if mode == "ssl465":
                s = smtplib.SMTP_SSL(host, 465, timeout=60)
            else:
                s = smtplib.SMTP(host, 587, timeout=60)
                s.ehlo(); s.starttls(); s.ehlo()
            with s:
                s.login(user, pw)
                s.send_message(msg)
            print(f"메일 발송 완료: {len(to)}명 ({mode})")
            return
        except smtplib.SMTPAuthenticationError as e:
            sys.exit(f"메일 서버 로그인 거부({e.smtp_code}): SMTP_USER 주소와 SMTP_PASSWORD 가 맞는지 확인하세요. "
                     "네이버는 메일 환경설정에서 'POP3/SMTP 사용'을 켜야 합니다.\n" + e.smtp_error.decode(errors="ignore"))
        except (smtplib.SMTPServerDisconnected, OSError) as e:
            errors.append(f"{mode}: {e}")
    sys.exit(f"메일 서버({host})가 로그인 중 연결을 끊었습니다.\n" + "\n".join(errors) +
             "\n→ 보내는 계정 메일함에 '보안 알림/로그인 차단' 메일이 있으면 '본인 맞음'으로 확인한 뒤 다시 실행하세요."
             "\n→ 비밀번호를 새로 만들어 SMTP_PASSWORD 를 덮어쓰기 해 보세요.")


if __name__ == "__main__":
    main()
