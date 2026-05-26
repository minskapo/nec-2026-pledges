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
