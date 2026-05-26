# 제9회 전국동시지방선거 공약 아카이브 구현 계획

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 제9회 전국동시지방선거(2026-06-03) 전국 후보자 5대 공약을 수집해 GitHub Pages로 검색·필터 가능한 아카이브를 만든다.

**Architecture:** Python 스크립트 4개가 순차 실행돼 `data/*.json`을 생성한다. `index.html`은 이 JSON을 `fetch()`로 로드하는 순수 정적 페이지다. PDF는 로컬 전용, index.html은 NEC 원본 URL로 링크한다.

**Tech Stack:** Python 3.11+, requests, beautifulsoup4, aiohttp, tqdm, python-dotenv / Vanilla HTML+CSS+JS / GitHub Pages

---

### Task 1: 프로젝트 셋업

**Files:**
- Create: `collect/requirements.txt`
- Create: `collect/config.py`
- Create: `collect/.env.example`
- Create: `README.md`

- [ ] **Step 1: requirements.txt 작성**

`collect/requirements.txt`:
```
requests==2.32.3
beautifulsoup4==4.12.3
aiohttp==3.9.5
tqdm==4.66.4
python-dotenv==1.0.1
```

- [ ] **Step 2: config.py 작성**

`collect/config.py`:
```python
import os
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.environ["NEC_API_KEY"]
SG_ID = "20260603"
SG_TYPECODES = {
    "3": "광역단체장",
    "4": "교육감",
    "5": "기초단체장",
    "6": "광역의원",
    "7": "기초의원",
    "8": "비례대표",
}

CANDIDATE_API = "http://apis.data.go.kr/9760000/PofelcddInfoInqireService/getPoelpcddRegistSttusInfoInqire"
PLEDGE_API = "http://apis.data.go.kr/9760000/ElecPrmsInfoInqireService/getCnddtElecPrmsInfoInqire"
NEC_POLICY_BASE = "https://policy.nec.go.kr"

DATA_DIR = "../data"
```

- [ ] **Step 3: .env.example 작성**

`collect/.env.example`:
```
NEC_API_KEY=여기에_발급받은_키_입력
```

- [ ] **Step 4: README.md 작성**

`README.md`:
```markdown
# 제9회 전국동시지방선거 공약 아카이브

🔗 **라이브**: https://minskapo.github.io/nec-2026-pledges/

제9회 전국동시지방선거(2026-06-03) 전국 후보자 5대 공약 수집 및 GitHub Pages 아카이브.

## 데이터 수집

1. [data.go.kr](https://www.data.go.kr/data/15040587/openapi.do)에서 API 키 발급 후 `collect/.env` 파일에 `NEC_API_KEY=발급키` 저장
2. `cd collect && pip install -r requirements.txt`
3. `python 01_fetch_candidates.py` → data/candidates.json
4. `python 02_fetch_pledges.py` → data/pledges.json
5. `python 03_find_pdf_pattern.py` → data/pdf_urls.json
6. `python 04_download_pdfs.py` → pdfs/ (로컬 전용)

## 수집 일자
2026-05-26

## 데이터 출처
- [공공데이터포털 중앙선거관리위원회 후보자 정보 API](https://www.data.go.kr/data/15000908/openapi.do)
- [공공데이터포털 중앙선거관리위원회 선거공약 정보 API](https://www.data.go.kr/data/15040587/openapi.do)
- [중앙선거관리위원회 정책·공약마당](https://policy.nec.go.kr/)
```

- [ ] **Step 5: 의존성 설치**

```bash
cd /Users/minski/dev/nec-2026-pledges/collect
pip install -r requirements.txt
```

기대 출력: `Successfully installed ...`

- [ ] **Step 6: .env 생성 (API 키 입력)**

```bash
cd /Users/minski/dev/nec-2026-pledges/collect
cp .env.example .env
```

`.env` 파일을 열어 `NEC_API_KEY=발급받은실제키` 입력. 이 파일은 `.gitignore`에 포함돼 있어 커밋되지 않는다.

- [ ] **Step 7: 커밋**

```bash
cd /Users/minski/dev/nec-2026-pledges
git add collect/requirements.txt collect/config.py collect/.env.example README.md
git commit -m "chore: project setup — dependencies, config, README"
```

---

### Task 2: 후보자 목록 수집

**Files:**
- Create: `collect/probe_candidates.py` (임시 탐색용, 커밋 안 함)
- Create: `collect/01_fetch_candidates.py`
- Create: `data/candidates.json` (실행 결과)

- [ ] **Step 1: API 응답 구조 확인 (probe)**

`collect/probe_candidates.py`:
```python
import json
import requests
from config import API_KEY, SG_ID, CANDIDATE_API

params = {
    "serviceKey": API_KEY,
    "sgId": SG_ID,
    "sgTypecode": "3",
    "pageNo": "1",
    "numOfRows": "3",
    "type": "json",
}
r = requests.get(CANDIDATE_API, params=params)
print("status:", r.status_code)
print(json.dumps(r.json(), indent=2, ensure_ascii=False)[:3000])
```

```bash
cd /Users/minski/dev/nec-2026-pledges/collect
python probe_candidates.py
```

응답의 `items.item[0]` 안에서 **후보자ID**, **성명**, **정당명**, **시도명**, **선거구명** 필드명을 확인한다. 일반적으로 `cnddtId`, `candNm`(또는 `name`), `partyNm`(또는 `partyName`), `sdName`, `sggName` 등이다. 확인한 실제 필드명으로 Step 2 코드의 `item.get(...)` 인자를 조정한다.

- [ ] **Step 2: 01_fetch_candidates.py 작성**

`collect/01_fetch_candidates.py`:
```python
import json
import os
import time

import requests

from config import API_KEY, SG_ID, SG_TYPECODES, CANDIDATE_API, DATA_DIR


def fetch_candidates_by_type(sg_typecode: str) -> list[dict]:
    candidates = []
    page = 1
    while True:
        params = {
            "serviceKey": API_KEY,
            "sgId": SG_ID,
            "sgTypecode": sg_typecode,
            "pageNo": str(page),
            "numOfRows": "1000",
            "type": "json",
        }
        r = requests.get(CANDIDATE_API, params=params, timeout=30)
        r.raise_for_status()
        body = r.json()

        try:
            items = body["response"]["body"]["items"]["item"]
        except (KeyError, TypeError):
            break

        if not items:
            break
        if isinstance(items, dict):
            items = [items]

        for item in items:
            # probe로 확인한 실제 필드명이 다르면 아래 get() 키를 수정할 것
            candidates.append({
                "cnddtId": item.get("cnddtId"),
                "name": item.get("candNm") or item.get("name"),
                "party": item.get("partyNm") or item.get("partyName"),
                "sido": item.get("sdName") or item.get("sdNm"),
                "sigungu": item.get("sggName") or item.get("sggNm") or "",
                "district": item.get("giName") or item.get("giNm") or "",
                "position": SG_TYPECODES[sg_typecode],
                "sgTypecode": sg_typecode,
            })

        total = int(body["response"]["body"].get("totalCount", 0))
        if len(candidates) >= total or len(items) < 1000:
            break
        page += 1
        time.sleep(0.1)

    return candidates


def main():
    all_candidates = []
    for code, label in SG_TYPECODES.items():
        print(f"수집 중: {label} (sgTypecode={code})")
        batch = fetch_candidates_by_type(code)
        print(f"  → {len(batch)}명")
        all_candidates.extend(batch)
        time.sleep(0.2)

    all_candidates = [c for c in all_candidates if c.get("cnddtId")]

    os.makedirs(DATA_DIR, exist_ok=True)
    out_path = os.path.join(DATA_DIR, "candidates.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(all_candidates, f, ensure_ascii=False, indent=2)

    print(f"\n완료: 총 {len(all_candidates)}명 → {out_path}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 3: 실행 및 검증**

```bash
cd /Users/minski/dev/nec-2026-pledges/collect
python 01_fetch_candidates.py
```

기대 출력:
```
수집 중: 광역단체장 (sgTypecode=3)
  → 30-70명
수집 중: 교육감 (sgTypecode=4)
  → 40-60명
...
완료: 총 XXXX명 → ../data/candidates.json
```

결과 검증:
```bash
python -c "
import json
d = json.load(open('../data/candidates.json'))
print(f'{len(d)}명 수집')
print(json.dumps(d[0], ensure_ascii=False, indent=2))
"
```

`cnddtId`, `name`, `party`, `sido` 필드가 모두 채워져 있어야 한다. 비어있으면 probe에서 확인한 필드명으로 `01_fetch_candidates.py`의 `item.get()` 인자를 수정 후 재실행.

- [ ] **Step 4: 커밋**

```bash
cd /Users/minski/dev/nec-2026-pledges
git add collect/01_fetch_candidates.py data/candidates.json
git commit -m "feat: fetch all candidates via NEC public API"
```

---

### Task 3: 공약 텍스트 수집

**Files:**
- Create: `collect/probe_pledges.py` (임시 탐색용, 커밋 안 함)
- Create: `collect/02_fetch_pledges.py`
- Create: `data/pledges.json` (실행 결과)

- [ ] **Step 1: 공약 API 응답 구조 확인 (probe)**

`collect/probe_pledges.py`:
```python
import json
import requests
from config import API_KEY, SG_ID, PLEDGE_API

# candidates.json에서 첫 번째 cnddtId 가져오기
import os, sys
sys.path.insert(0, os.path.dirname(__file__))
candidates = json.load(open("../data/candidates.json"))
sample = candidates[0]

params = {
    "serviceKey": API_KEY,
    "sgId": SG_ID,
    "sgTypecode": sample["sgTypecode"],
    "cnddtId": sample["cnddtId"],
    "type": "json",
}
r = requests.get(PLEDGE_API, params=params)
print("status:", r.status_code)
print(json.dumps(r.json(), indent=2, ensure_ascii=False)[:3000])
```

```bash
cd /Users/minski/dev/nec-2026-pledges/collect
python probe_pledges.py
```

응답에서 **공약 순서**, **공약 제목**, **공약 내용**, **분야** 필드명을 확인한다. 일반적으로 `prmsOrd`, `prmsTitle`, `prmsCont`, `prmsRealmName` 등이다.

- [ ] **Step 2: 02_fetch_pledges.py 작성**

`collect/02_fetch_pledges.py`:
```python
import json
import os
import time

import requests
from tqdm import tqdm

from config import API_KEY, SG_ID, PLEDGE_API, DATA_DIR


def fetch_pledges(cnddt_id: str, sg_typecode: str) -> dict:
    params = {
        "serviceKey": API_KEY,
        "sgId": SG_ID,
        "sgTypecode": sg_typecode,
        "cnddtId": cnddt_id,
        "type": "json",
    }
    for attempt in range(3):
        try:
            r = requests.get(PLEDGE_API, params=params, timeout=30)
            r.raise_for_status()
            break
        except Exception:
            if attempt == 2:
                return {}
            time.sleep(1)

    body = r.json()
    try:
        items = body["response"]["body"]["items"]["item"]
    except (KeyError, TypeError):
        return {}

    if not items:
        return {}
    if isinstance(items, dict):
        items = [items]

    pledges = {}
    for item in items:
        # probe로 확인한 실제 필드명이 다르면 아래 get() 키를 수정할 것
        num = str(item.get("prmsOrd") or item.get("prmsOrdNo") or "")
        title = item.get("prmsTitle") or item.get("rmTtl") or ""
        content = item.get("prmsCont") or item.get("rmCont") or ""
        field = item.get("prmsRealmName") or item.get("prmsRealm") or ""
        if num:
            pledges[num] = {"title": title, "content": content, "field": field}
    return pledges


def main():
    with open(os.path.join(DATA_DIR, "candidates.json"), encoding="utf-8") as f:
        candidates = json.load(f)

    pledges_path = os.path.join(DATA_DIR, "pledges.json")
    existing = {}
    if os.path.exists(pledges_path):
        with open(pledges_path, encoding="utf-8") as f:
            existing = json.load(f)

    results = dict(existing)
    todo = [c for c in candidates if c["cnddtId"] not in results]
    print(f"공약 수집: {len(todo)}명 (기수집: {len(existing)}명)")

    for cnddt in tqdm(todo):
        cid = cnddt["cnddtId"]
        results[cid] = fetch_pledges(cid, cnddt["sgTypecode"])
        time.sleep(0.1)

        if len(results) % 200 == 0:
            with open(pledges_path, "w", encoding="utf-8") as f:
                json.dump(results, f, ensure_ascii=False, indent=2)

    with open(pledges_path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    non_empty = sum(1 for v in results.values() if v)
    print(f"완료: {len(results)}명, 공약 있음: {non_empty}명 → {pledges_path}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 3: 실행**

```bash
cd /Users/minski/dev/nec-2026-pledges/collect
python 02_fetch_pledges.py
```

tqdm 진행률 바 표시. ~8,000명 × 0.1초 = 약 15분 소요. 중단 후 재실행 시 이어서 수집됨.

- [ ] **Step 4: 검증**

```bash
python -c "
import json
d = json.load(open('../data/pledges.json'))
filled = {k:v for k,v in d.items() if v}
print(f'{len(d)}명 중 공약 있음: {len(filled)}명')
sample_id = list(filled.keys())[0]
print(json.dumps(filled[sample_id], ensure_ascii=False, indent=2))
"
```

샘플 출력에서 `title`, `content`, `field` 필드가 채워져 있어야 한다.

- [ ] **Step 5: 커밋**

```bash
cd /Users/minski/dev/nec-2026-pledges
git add collect/02_fetch_pledges.py data/pledges.json
git commit -m "feat: fetch candidate pledges via NEC public API"
```

---

### Task 4: 선거공보 PDF URL 수집

**Files:**
- Create: `collect/03_find_pdf_pattern.py`
- Create: `data/pdf_urls.json` (실행 결과)

- [ ] **Step 1: 03_find_pdf_pattern.py 작성**

`collect/03_find_pdf_pattern.py`:
```python
"""
policy.nec.go.kr에서 후보자별 선거공보 PDF URL을 수집한다.
전략: 샘플 후보자 10명 페이지를 파싱해 URL 패턴을 역산하고,
패턴이 일정하면 전체 cnddtId로 URL을 구성한다.
패턴 미발견 시 전체 페이지 개별 수집으로 fallback.
"""
import json
import os
import re
import time

import requests
from bs4 import BeautifulSoup
from tqdm import tqdm

from config import NEC_POLICY_BASE, DATA_DIR

CANDIDATE_PAGE_URL = f"{NEC_POLICY_BASE}/candidate/candidateView.do"


def get_session() -> requests.Session:
    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
                      "KHTML, like Gecko Chrome/124.0 Safari/537.36",
        "Referer": NEC_POLICY_BASE,
        "Accept-Language": "ko-KR,ko;q=0.9",
    })
    session.get(NEC_POLICY_BASE, timeout=30)
    return session


def fetch_page(session: requests.Session, cnddt_id: str, sg_typecode: str) -> str:
    params = {
        "electionId": "0020260603",
        "requestURI": "/candidate/candidateView.do",
        "topMenuId": "CP",
        "secondMenuId": "CPRI01",
        "cnddtId": cnddt_id,
        "sgTypecode": sg_typecode,
    }
    r = session.get(CANDIDATE_PAGE_URL, params=params, timeout=30)
    r.raise_for_status()
    return r.text


def extract_pdf_url(html: str) -> str | None:
    soup = BeautifulSoup(html, "html.parser")

    # 방법 1: href에 pdf/pamphlet 키워드
    for a in soup.find_all("a", href=True):
        href = a["href"]
        if re.search(r"\.(pdf)$", href, re.I) or re.search(r"pamphlet|gongbo|selectr", href, re.I):
            return href if href.startswith("http") else NEC_POLICY_BASE + href

    # 방법 2: onclick 속성
    for tag in soup.find_all(onclick=True):
        m = re.search(r"['\"]([^'\"]*\.pdf[^'\"]*)['\"]", tag["onclick"])
        if m:
            url = m.group(1)
            return url if url.startswith("http") else NEC_POLICY_BASE + url

    # 방법 3: <script> 내 PDF URL
    for script in soup.find_all("script"):
        text = script.string or ""
        m = re.search(r"['\"]([^'\"]*(?:pamphlet|gongbo|selectr)[^'\"]*\.pdf[^'\"]*)['\"]", text, re.I)
        if m:
            url = m.group(1)
            return url if url.startswith("http") else NEC_POLICY_BASE + url

    return None


def find_url_pattern(sample: list[tuple[str, str | None]]) -> str | None:
    """(cnddtId, pdf_url) 목록에서 URL 패턴 추출. cnddtId가 URL에 포함돼 있으면 패턴 반환."""
    for cnddt_id, url in sample:
        if url and cnddt_id in url:
            pattern = url.replace(cnddt_id, "{cnddtId}")
            print(f"  패턴 후보: {pattern}")
            return pattern
    return None


def main():
    with open(os.path.join(DATA_DIR, "candidates.json"), encoding="utf-8") as f:
        candidates = json.load(f)

    # 다양한 sgTypecode에서 샘플 선택
    samples = []
    seen_types: set[str] = set()
    for c in candidates:
        if c["sgTypecode"] not in seen_types and len(samples) < 10:
            samples.append(c)
            seen_types.add(c["sgTypecode"])

    print(f"샘플 {len(samples)}명으로 패턴 탐색 중...")
    session = get_session()
    sample_results: list[tuple[str, str | None]] = []

    for c in samples:
        print(f"  {c['name']} ({c['cnddtId']}, type={c['sgTypecode']}) ... ", end="", flush=True)
        try:
            html = fetch_page(session, c["cnddtId"], c["sgTypecode"])
            url = extract_pdf_url(html)
            print(url or "PDF 없음")
            sample_results.append((c["cnddtId"], url))
        except Exception as e:
            print(f"오류: {e}")
            sample_results.append((c["cnddtId"], None))
        time.sleep(0.5)

    pattern = find_url_pattern(sample_results)
    out_path = os.path.join(DATA_DIR, "pdf_urls.json")

    if pattern:
        print(f"\n✅ 패턴 발견: {pattern}")
        pdf_urls = {c["cnddtId"]: pattern.replace("{cnddtId}", c["cnddtId"]) for c in candidates}
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(pdf_urls, f, ensure_ascii=False, indent=2)
        print(f"✅ {len(pdf_urls)}개 URL 생성 → {out_path}")

    else:
        print("\n⚠️  패턴 미발견. 전체 페이지 개별 수집으로 전환합니다 (~40분)...")
        pdf_urls: dict[str, str] = {cid: url or "" for cid, url in sample_results}
        remaining = [c for c in candidates if c["cnddtId"] not in pdf_urls]

        for c in tqdm(remaining, desc="PDF URL 수집"):
            try:
                html = fetch_page(session, c["cnddtId"], c["sgTypecode"])
                pdf_urls[c["cnddtId"]] = extract_pdf_url(html) or ""
            except Exception:
                pdf_urls[c["cnddtId"]] = ""
            time.sleep(0.3)

        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(pdf_urls, f, ensure_ascii=False, indent=2)
        filled = sum(1 for v in pdf_urls.values() if v)
        print(f"완료: {filled}/{len(pdf_urls)}개 URL → {out_path}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: 실행**

```bash
cd /Users/minski/dev/nec-2026-pledges/collect
python 03_find_pdf_pattern.py
```

패턴 발견 시: 수 초 내 완료.  
패턴 미발견 시: 8,000명 × 0.3초 ≈ 40분 소요.

- [ ] **Step 3: 검증**

```bash
python -c "
import json
d = json.load(open('../data/pdf_urls.json'))
filled = {k:v for k,v in d.items() if v}
print(f'PDF URL: {len(filled)}/{len(d)}개')
sample = list(filled.items())[:2]
for cid, url in sample:
    print(f'  {cid}: {url}')
"
```

- [ ] **Step 4: 커밋**

```bash
cd /Users/minski/dev/nec-2026-pledges
git add collect/03_find_pdf_pattern.py data/pdf_urls.json
git commit -m "feat: collect election pamphlet PDF URLs from policy.nec.go.kr"
```

---

### Task 5: PDF 로컬 다운로드

**Files:**
- Create: `collect/04_download_pdfs.py`

- [ ] **Step 1: 04_download_pdfs.py 작성**

`collect/04_download_pdfs.py`:
```python
import asyncio
import json
import os

import aiohttp
from tqdm.asyncio import tqdm

from config import DATA_DIR

PDF_DIR = os.path.join(os.path.dirname(os.path.abspath(DATA_DIR)), "pdfs")
CONCURRENCY = 10


async def download_one(
    session: aiohttp.ClientSession,
    cnddt_id: str,
    url: str,
    semaphore: asyncio.Semaphore,
) -> tuple[str, bool]:
    out_path = os.path.join(PDF_DIR, f"{cnddt_id}.pdf")
    if os.path.exists(out_path):
        return cnddt_id, True

    async with semaphore:
        try:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=60)) as r:
                if r.status != 200:
                    return cnddt_id, False
                content = await r.read()
            with open(out_path, "wb") as f:
                f.write(content)
            return cnddt_id, True
        except Exception:
            return cnddt_id, False


async def main():
    with open(os.path.join(DATA_DIR, "pdf_urls.json"), encoding="utf-8") as f:
        pdf_urls = json.load(f)

    todo = {k: v for k, v in pdf_urls.items() if v}
    os.makedirs(PDF_DIR, exist_ok=True)
    print(f"다운로드 시작: {len(todo)}개 (동시 {CONCURRENCY}개)")

    semaphore = asyncio.Semaphore(CONCURRENCY)
    headers = {"User-Agent": "Mozilla/5.0"}
    failed = []

    async with aiohttp.ClientSession(headers=headers) as session:
        tasks = [download_one(session, cid, url, semaphore) for cid, url in todo.items()]
        results = await tqdm.gather(*tasks, desc="PDF 다운로드")

    for cid, ok in results:
        if not ok:
            failed.append(cid)

    with open(os.path.join(DATA_DIR, "failed_downloads.json"), "w") as f:
        json.dump(failed, f)

    print(f"\n완료: 성공 {len(todo) - len(failed)}, 실패 {len(failed)}")
    print(f"저장 위치: {PDF_DIR}/")


if __name__ == "__main__":
    asyncio.run(main())
```

- [ ] **Step 2: 실행**

```bash
cd /Users/minski/dev/nec-2026-pledges/collect
python 04_download_pdfs.py
```

병렬 10개 다운로드. 기대 소요: 1-2시간.

- [ ] **Step 3: 커밋**

```bash
cd /Users/minski/dev/nec-2026-pledges
git add collect/04_download_pdfs.py
git commit -m "feat: async PDF bulk downloader (local only)"
```

---

### Task 6: 인덱스 페이지 (index.html)

**Files:**
- Create: `index.html`

- [ ] **Step 1: index.html 작성**

`index.html`:
```html
<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>제9회 전국동시지방선거 공약 아카이브</title>
<style>
* { box-sizing: border-box; margin: 0; padding: 0; }
body { font-family: -apple-system, 'Malgun Gothic', sans-serif; font-size: 14px; color: #222; background: #f5f7fa; }
header { background: #1a4b8c; color: white; padding: 16px 24px; }
header h1 { font-size: 18px; font-weight: 700; }
header p { font-size: 12px; opacity: 0.75; margin-top: 4px; }
.controls { background: white; padding: 10px 24px; border-bottom: 1px solid #dde3ed; display: flex; gap: 8px; flex-wrap: wrap; align-items: center; }
.controls select, .controls input { padding: 6px 10px; border: 1px solid #ccc; border-radius: 4px; font-size: 13px; background: white; }
.controls input[type=search] { flex: 1; min-width: 140px; }
.count { padding: 6px 24px; font-size: 12px; color: #666; background: white; border-bottom: 1px solid #eee; }
.table-wrap { overflow-x: auto; }
table { width: 100%; border-collapse: collapse; background: white; }
th { background: #eef2fa; text-align: left; padding: 8px 12px; font-size: 12px; color: #555; border-bottom: 2px solid #d0d9ed; white-space: nowrap; }
td { padding: 8px 12px; border-bottom: 1px solid #eee; vertical-align: middle; }
tr.data-row:hover td { background: #f5f8ff; cursor: pointer; }
tr.data-row.open td { background: #eef2ff; }
tr.pledge-row { display: none; }
tr.pledge-row.visible { display: table-row; }
tr.pledge-row td { background: #f7f9ff; padding: 12px 20px 12px 36px; }
.pledge-list { list-style: none; }
.pledge-list li { padding: 6px 0; border-bottom: 1px solid #e5eaf5; line-height: 1.6; }
.pledge-list li:last-child { border: none; }
.pledge-num { display: inline-flex; align-items: center; justify-content: center; width: 22px; height: 22px; background: #1a4b8c; color: white; border-radius: 50%; font-size: 11px; margin-right: 8px; flex-shrink: 0; }
.pledge-content { margin: 4px 0 2px 30px; color: #444; font-size: 13px; }
.pledge-field { margin-left: 30px; font-size: 11px; color: #888; }
.badge { display: inline-block; padding: 2px 8px; border-radius: 10px; font-size: 11px; background: #e8edf8; color: #333; }
.btn { display: inline-block; padding: 3px 9px; border-radius: 4px; font-size: 11px; text-decoration: none; border: 1px solid #ccc; color: #333; cursor: pointer; background: white; margin-right: 4px; white-space: nowrap; }
.btn:hover { background: #f0f4fa; }
.btn-pdf { border-color: #1a4b8c; color: #1a4b8c; }
.btn-pdf:hover { background: #eef2ff; }
.no-pledge { color: #bbb; font-size: 12px; }
.pagination { display: flex; gap: 6px; justify-content: center; padding: 14px; background: white; border-top: 1px solid #eee; flex-wrap: wrap; }
.pagination button { padding: 5px 12px; border: 1px solid #ccc; border-radius: 4px; background: white; cursor: pointer; font-size: 13px; }
.pagination button.active { background: #1a4b8c; color: white; border-color: #1a4b8c; }
.pagination button:disabled { opacity: 0.35; cursor: default; }
#loading { text-align: center; padding: 60px; color: #888; font-size: 15px; }
</style>
</head>
<body>
<header>
  <h1>제9회 전국동시지방선거 후보자 공약 아카이브</h1>
  <p id="meta-info">데이터 로딩 중...</p>
</header>
<div class="controls">
  <select id="f-sido"><option value="">시도 전체</option></select>
  <select id="f-type"><option value="">직위 전체</option></select>
  <select id="f-party"><option value="">정당 전체</option></select>
  <input type="search" id="f-name" placeholder="이름 검색...">
</div>
<div class="count" id="count-info"></div>
<div id="loading">📂 데이터 로딩 중...</div>
<div class="table-wrap">
  <table id="main-table" style="display:none">
    <thead>
      <tr><th>이름</th><th>시도</th><th>선거구</th><th>직위</th><th>정당</th><th>공약 / 공보</th></tr>
    </thead>
    <tbody id="tbody"></tbody>
  </table>
</div>
<div class="pagination" id="pag"></div>

<script>
const PAGE = 50;
let all = [], pledges = {}, pdfUrls = {}, filtered = [], page = 1;

async function load() {
  const [cr, pr, ur] = await Promise.all([
    fetch('data/candidates.json'),
    fetch('data/pledges.json'),
    fetch('data/pdf_urls.json').catch(() => null),
  ]);
  all = await cr.json();
  pledges = await pr.json();
  pdfUrls = ur ? await ur.json() : {};
  document.getElementById('meta-info').textContent =
    `총 ${all.length.toLocaleString()}명 · 수집일: 2026-05-26 · 출처: 중앙선거관리위원회`;
  initFilters();
  applyFilter();
  document.getElementById('loading').style.display = 'none';
  document.getElementById('main-table').style.display = '';
}

function initFilters() {
  const uniq = (arr) => [...new Set(arr.filter(Boolean))].sort();
  const fill = (id, vals) => {
    const el = document.getElementById(id);
    vals.forEach(v => { const o = document.createElement('option'); o.value = o.textContent = v; el.appendChild(o); });
  };
  fill('f-sido', uniq(all.map(c => c.sido)));
  fill('f-type', uniq(all.map(c => c.position)));
  fill('f-party', uniq(all.map(c => c.party)));
}

function applyFilter() {
  const sido = document.getElementById('f-sido').value;
  const type = document.getElementById('f-type').value;
  const party = document.getElementById('f-party').value;
  const q = document.getElementById('f-name').value.trim();
  filtered = all.filter(c =>
    (!sido || c.sido === sido) &&
    (!type || c.position === type) &&
    (!party || c.party === party) &&
    (!q || (c.name || '').includes(q))
  );
  page = 1;
  document.getElementById('count-info').textContent =
    `${filtered.length.toLocaleString()}명 표시 (전체 ${all.length.toLocaleString()}명)`;
  render();
}

function render() {
  const rows = filtered.slice((page - 1) * PAGE, page * PAGE);
  const tbody = document.getElementById('tbody');
  tbody.innerHTML = '';
  rows.forEach((c, i) => {
    const rid = `r${(page-1)*PAGE+i}`;
    const pd = pledges[c.cnddtId] || {};
    const pdf = pdfUrls[c.cnddtId] || '';
    const hasPledge = Object.keys(pd).length > 0;

    const tr = document.createElement('tr');
    tr.className = 'data-row';
    tr.innerHTML = `
      <td>${c.name||''}</td>
      <td>${c.sido||''}</td>
      <td>${[c.sigungu,c.district].filter(Boolean).join(' ')}</td>
      <td>${c.position||''}</td>
      <td><span class="badge">${c.party||''}</span></td>
      <td>
        ${hasPledge
          ? `<button class="btn" onclick="toggle('${rid}',event)">공약 ▼</button>`
          : '<span class="no-pledge">공약없음</span>'}
        ${pdf ? `<a class="btn btn-pdf" href="${pdf}" target="_blank" rel="noopener">공보 ↗</a>` : ''}
      </td>`;
    tbody.appendChild(tr);

    if (hasPledge) {
      const pr = document.createElement('tr');
      pr.className = 'pledge-row';
      pr.id = rid + '-p';
      const items = Object.entries(pd)
        .sort(([a],[b]) => +a - +b)
        .map(([n,p]) => `<li>
          <span class="pledge-num">${n}</span><strong>${p.title||''}</strong>
          ${p.content ? `<div class="pledge-content">${p.content}</div>` : ''}
          ${p.field ? `<div class="pledge-field">${p.field}</div>` : ''}
        </li>`).join('');
      pr.innerHTML = `<td colspan="6"><ul class="pledge-list">${items}</ul></td>`;
      tbody.appendChild(pr);
    }
  });
  renderPag();
}

function toggle(rid, e) {
  e.stopPropagation();
  const el = document.getElementById(rid+'-p');
  if (!el) return;
  const open = el.classList.toggle('visible');
  e.target.textContent = open ? '공약 ▲' : '공약 ▼';
}

function renderPag() {
  const total = Math.ceil(filtered.length / PAGE);
  const pag = document.getElementById('pag');
  pag.innerHTML = '';
  const btn = (label, handler, disabled, active) => {
    const b = document.createElement('button');
    b.textContent = label;
    b.disabled = disabled;
    if (active) b.className = 'active';
    b.onclick = handler;
    return b;
  };
  pag.appendChild(btn('← 이전', () => { page--; render(); scrollTo(0,0); }, page===1));
  const s = Math.max(1, page-2), e = Math.min(total, s+4);
  for (let i=s; i<=e; i++) {
    pag.appendChild(btn(i, ((p)=>()=>{page=p;render();scrollTo(0,0);})(i), false, i===page));
  }
  pag.appendChild(btn('다음 →', () => { page++; render(); scrollTo(0,0); }, page===total));
}

['f-sido','f-type','f-party'].forEach(id =>
  document.getElementById(id).addEventListener('change', applyFilter));
document.getElementById('f-name').addEventListener('input', applyFilter);

load().catch(e => { document.getElementById('loading').textContent = '로딩 실패: ' + e.message; });
</script>
</body>
</html>
```

- [ ] **Step 2: 로컬 테스트**

```bash
cd /Users/minski/dev/nec-2026-pledges
python -m http.server 8080
```

브라우저에서 `http://localhost:8080` 접속. 후보자 테이블, 필터, 공약 accordion, PDF 링크 동작 확인.

- [ ] **Step 3: 커밋**

```bash
cd /Users/minski/dev/nec-2026-pledges
git add index.html
git commit -m "feat: GitHub Pages index with filter, search, pledge accordion"
```

---

### Task 7: GitHub 리포지토리 생성 및 Pages 배포

**Files:**
- Modify: `README.md` (Pages URL 반영)

- [ ] **Step 1: GitHub 리포 생성 및 푸시**

```bash
cd /Users/minski/dev/nec-2026-pledges
gh repo create nec-2026-pledges --public --source=. --remote=origin --push
```

기대 출력:
```
✓ Created repository minskapo/nec-2026-pledges on GitHub
✓ Pushed commits to https://github.com/minskapo/nec-2026-pledges
```

- [ ] **Step 2: GitHub Pages 활성화**

```bash
gh api repos/minskapo/nec-2026-pledges/pages \
  --method POST \
  -f "source[branch]=main" \
  -f "source[path]=/"
```

기대 출력: `"status": "queued"` 포함 JSON.

- [ ] **Step 3: README Pages URL 추가**

`README.md` 맨 위 두 번째 줄에 아래 내용이 이미 있는지 확인:
```
🔗 **라이브**: https://minskapo.github.io/nec-2026-pledges/
```
이미 있으면 skip. 없으면 추가 후:

```bash
cd /Users/minski/dev/nec-2026-pledges
git add README.md
git commit -m "docs: add live GitHub Pages URL"
git push origin main
```

- [ ] **Step 4: 배포 확인 (1-3분 대기)**

```bash
gh run list --limit 3
```

Actions 완료 후:
```bash
open https://minskapo.github.io/nec-2026-pledges/
```

페이지가 정상 로드되고 필터·검색이 동작하면 완료.
