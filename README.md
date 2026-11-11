# 글로벌 경쟁사 뉴스 모니터링 (Global Competitor Trend)

현대케피코 관점의 글로벌 경쟁사 뉴스를 매일 수집해 **게시판**에 올리고, **요약 PDF를 메일로 발송**하는 시스템입니다.

- 게시판 주소: https://seoju.github.io/Monitoringreport/

## 동작 흐름

| 순서 | 시각 (KST, 평일) | 누가 | 하는 일 |
|---|---|---|---|
| 1 | 06:47 | Claude 예약 작업 | `prompts/collect.md` 지침대로 웹 검색 → `data/posts/날짜.json` 작성 → push |
| 2 | push 직후 | GitHub Actions | PDF 생성(`reports/날짜.pdf`), 게시판 목록 갱신·배포 (메일 없음) |
| 3 | 08:10 | GitHub Actions | 오늘 데이터로 PDF를 다시 만들어 등록된 수신자에게 메일 발송 |

- 오늘 데이터가 없으면 08:10 발송 작업이 **실패로 표시**되고, GitHub이 저장소 주인에게 실패 알림 메일을 보냅니다.
- **테스트 발송 버튼**: 저장소 **Actions** 탭 → `Daily report (PDF · 메일 · 게시판 배포)` → **Run workflow** → (날짜 비우면 최신) → Run.

## 처음 한 번만 하는 설정

### 1) 게시판(GitHub Pages) 켜기
Settings → Pages → **Source** 를 **GitHub Actions** 로 선택.

### 2) 메일 설정 (Gmail 앱 비밀번호)
1. Google 계정 → 보안 → **2단계 인증** 켜기
2. https://myaccount.google.com/apppasswords 에서 앱 비밀번호(16자리) 생성
3. 저장소 Settings → Secrets and variables → Actions → **New repository secret** 으로 3개 등록

| 이름 | 값 |
|---|---|
| `GMAIL_USER` | 보내는 Gmail 주소 |
| `GMAIL_APP_PASSWORD` | 위에서 만든 16자리 앱 비밀번호 |
| `MAIL_TO` | 받는 사람 주소. 여러 명은 쉼표(,)로 구분 |

받는 사람 주소는 Secrets에만 저장되므로 공개 저장소에 노출되지 않습니다. 메일은 받는 사람끼리 주소가 보이지 않게 숨은참조로 발송됩니다.

## 자주 바꾸는 곳

| 바꾸고 싶은 것 | 파일 |
|---|---|
| 모니터링 기업·검색어·요일 | `config/companies.json` |
| 주요 뉴스 기준·작성 규칙 | `prompts/collect.md` |
| 제목·메일 제목·하단 문구 | `config/report.json` |
| 메일 발송 시각 | `.github/workflows/daily-report.yml` 의 `cron` (UTC 기준, KST −9시간) |
| PDF 디자인 | `scripts/make_pdf.py` |
| 게시판 디자인 | `index.html`, `assets/` |

## 폴더 구조

```
data/posts/YYYY-MM-DD.json   하루치 게시글 (Claude가 작성)
data/index.json              게시판 목록 (자동 생성)
reports/YYYY-MM-DD.pdf       요약 PDF (자동 생성)
scripts/                     검사·PDF·메일 스크립트
```
