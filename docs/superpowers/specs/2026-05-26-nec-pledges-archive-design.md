# 제9회 전국동시지방선거 공약 아카이브 설계

**날짜**: 2026-05-26  
**선거일**: 2026-06-03  
**GitHub 계정**: minskapo

---

## 목표

제9회 전국동시지방선거(2026-06-03) 전국 모든 후보자의 5대 공약 텍스트와 선거공보 PDF URL을 수집해 GitHub Pages 인덱스 페이지로 공개한다.

---

## 데이터 소스

| 데이터 | 소스 | 방식 |
|--------|------|------|
| 후보자 목록 | 공공데이터포털 API (`PofelcddInfoInqireService`) | REST API |
| 5대 공약 텍스트 | 공공데이터포털 API (`ElecPrmsInfoInqireService`) | REST API |
| 선거공보 PDF URL | policy.nec.go.kr HTML 파싱 → URL 패턴 역산 | requests + BeautifulSoup |
| 선거공보 PDF 파일 | policy.nec.go.kr | aiohttp 병렬 다운로드 (로컬 전용) |

**sgId**: `20260603`  
**sgTypecode**: 3(광역단체장), 4(교육감), 5(기초단체장), 6(광역의원), 7(기초의원), 8(비례대표)

---

## 디렉토리 구조

```
/Users/minski/dev/nec-2026-pledges/
├── collect/
│   ├── 01_fetch_candidates.py     # 후보자 목록 수집
│   ├── 02_fetch_pledges.py        # 공약 텍스트 수집
│   ├── 03_find_pdf_pattern.py     # PDF URL 패턴 역산 + pdf_urls.json 생성
│   ├── 04_download_pdfs.py        # PDF 로컬 다운로드
│   └── requirements.txt
├── data/
│   ├── candidates.json            # 전체 후보자 메타데이터
│   ├── pledges.json               # 후보자ID → 공약 1~5
│   └── pdf_urls.json              # 후보자ID → 선거공보 PDF URL
├── pdfs/                          # 로컬 전용 (.gitignore)
├── index.html                     # GitHub Pages 인덱스
├── .gitignore
└── README.md
```

---

## 스크립트별 설계

### 01_fetch_candidates.py
- 환경변수 `NEC_API_KEY`에서 서비스 키 읽기
- sgTypecode 3~8 순회, 페이지네이션(numOfRows=1000)으로 전체 수집
- 출력 필드: `cnddtId`, `sgId`, `sgTypecode`, `sdName`, `sggName`, `wiwName`, `partyName`, `name`, `gender`, `birthday`
- 결과: `data/candidates.json` (배열)

### 02_fetch_pledges.py
- `candidates.json`에서 `cnddtId` 읽기
- API `ElecPrmsInfoInqireService/getCnddtElecPrmsInfoInqire` 호출
- 공약이 없는 후보자는 빈 배열로 기록
- rate limit 대응: 요청 간 0.1초 sleep, 오류 시 3회 재시도
- 결과: `data/pledges.json` (`{cnddtId: {pledge1, pledge2, ...}}`)

### 03_find_pdf_pattern.py
- `candidates.json`에서 샘플 후보자 5명 선택
- `policy.nec.go.kr` 후보자 페이지 requests로 fetch (세션 유지)
- BeautifulSoup으로 PDF href 추출
- `cnddtId`와 URL 대조해 패턴 역산
- 패턴 발견 시: 전체 후보자 URL 생성 → `data/pdf_urls.json`
- 패턴 미발견 시: 에러 출력 후 Playwright fallback 안내

### 04_download_pdfs.py
- `pdf_urls.json` 읽기
- `asyncio` + `aiohttp`로 동시 10개 다운로드
- `pdfs/{cnddtId}.pdf`로 저장
- 진행률 tqdm 표시
- 실패 목록 `data/failed_downloads.json`에 기록

---

## 인덱스 페이지 (index.html)

- 순수 HTML + Vanilla JS (빌드 도구 없음)
- `candidates.json`과 `pledges.json`을 `fetch()`로 로드
- 기능:
  - 시도 / 직위 / 정당 드롭다운 필터
  - 이름 텍스트 검색
  - 50명씩 페이지네이션
  - 공약 accordion (행 클릭 시 공약 1~5 펼침)
  - 선거공보 링크 (pdf_urls.json의 URL, 새 탭)
- GitHub Pages 배포 (`main` 브랜치 루트)

---

## GitHub 리포지토리

- **이름**: `nec-2026-pledges`
- **공개 여부**: Public
- **배포**: GitHub Pages (main 브랜치 / root)
- **업로드 제외**: `pdfs/` 폴더, `.env`

---

## 제약 및 리스크

| 리스크 | 대응 |
|--------|------|
| API 10,000건/일 제한 | 후보자+공약 합산 ~16,000건 → 2일로 분할 또는 운영계정 신청 |
| PDF URL 패턴 없음 | 03 스크립트에서 감지 시 Playwright fallback 사용 안내 |
| policy.nec.go.kr 세션 필요 | requests.Session + 홈→후보자 순서로 쿠키 유지 |
| 선거 후 PDF 링크 소멸 | README에 수집일 명시, 로컬 백업 권장 |
