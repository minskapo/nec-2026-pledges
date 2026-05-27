"""
policy.nec.go.kr에서 후보자별 선거공보 PDF URL 수집

API 구조:
  POST /plc/commiment/initUCACommimentList.do
  params: sgId=20260603, subSgId={typecode+date}, sgTypecode=1, hRegionId=임의값
  응답: { totalCnt: N, list: [ { huboid, hbjname, fileinfo, ... }, ... ] }

fileinfo 형식:
  "선거공보||{path}.pdf||...페이지수...||...,선거공약서||{path2}.pdf||..."
  PDF URL = https://policy.nec.go.kr/policy_pdf/{path}

huboid = cnddtId (candidates.json과 동일)
"""

import json
import os
import time

import requests

from config import NEC_POLICY_BASE, DATA_DIR

LIST_URL = f"{NEC_POLICY_BASE}/plc/commiment/initUCACommimentList.do"
PDF_BASE = f"{NEC_POLICY_BASE}/policy_pdf/"

# 선거 유형별 subSgId (typecode+date)
ELECTION_TYPES = {
    "시·도지사선거":       "320260603",
    "교육감선거":          "1120260603",
    "구·시·군의 장선거":   "420260603",
    "시·도의회의원선거":   "520260603",
    "구·시·군의회의원선거": "620260603",
    "광역의원비례대표선거": "820260603",
    "기초의원비례대표선거": "920260603",
    "국회의원선거":        "220260603",
}


def get_session() -> requests.Session:
    session = requests.Session()
    session.headers.update({
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 KHTML, like Gecko Chrome/124.0 Safari/537.36"
        ),
        "Accept-Language": "ko-KR,ko;q=0.9",
        "Referer": f"{NEC_POLICY_BASE}/plc/commiment/initUCACommiment.do?menuId=CNDDT25",
        "X-Requested-With": "XMLHttpRequest",
    })
    # 세션 쿠키 획득
    session.get(NEC_POLICY_BASE, timeout=30)
    session.get(
        f"{NEC_POLICY_BASE}/plc/commiment/initUCACommiment.do?menuId=CNDDT25",
        timeout=30,
    )
    return session


def fetch_candidates_for_type(session: requests.Session, sub_sg_id: str) -> list[dict]:
    """한 선거 유형의 전체 후보자 목록 + fileinfo 반환"""
    params = {
        "sgId": "20260603",
        "subSgId": sub_sg_id,
        "sgTypecode": "1",
        "hRegionId": "1100",   # 임의 지역 (서울) — API는 전체 데이터를 반환함
        "hGuId": "",
        "hSggId": "",
        "pageIndex": "1",
        "phGuId": "",
        "elecEndYn": "N",
    }
    r = session.post(LIST_URL, data=params, timeout=30)
    r.raise_for_status()
    data = r.json()
    return data.get("list") or []


def extract_pamphlet_pdf_url(fileinfo: str) -> str:
    """
    fileinfo에서 선거공보 PDF URL 추출.
    형식: "선거공보||path.pdf||pages||...||Y||...,선거공약서||..."
    """
    if not fileinfo:
        return ""
    # 콤마로 파일 유형들 분리
    parts = fileinfo.split(",")
    for part in parts:
        subparts = part.split("||")
        file_type = subparts[0] if subparts else ""
        file_path = subparts[1] if len(subparts) > 1 else ""
        if file_type == "선거공보" and file_path:
            return PDF_BASE + file_path
    return ""


def main():
    out_path = os.path.join(DATA_DIR, "pdf_urls.json")

    # 기존 데이터 로드
    existing: dict[str, str] = {}
    if os.path.exists(out_path):
        with open(out_path, encoding="utf-8") as f:
            existing = json.load(f)

    session = get_session()
    results: dict[str, str] = dict(existing)
    stats: dict[str, tuple[int, int]] = {}  # name -> (total, with_pdf)

    for election_type, sub_sg_id in ELECTION_TYPES.items():
        print(f"\n[{election_type}] subSgId={sub_sg_id} 수집 중...")
        try:
            items = fetch_candidates_for_type(session, sub_sg_id)
        except Exception as e:
            print(f"  오류: {e}")
            continue

        with_pdf = 0
        for item in items:
            huboid = item.get("huboid")
            if not huboid:
                continue
            cid = str(huboid)
            fileinfo = item.get("fileinfo") or ""
            pdf_url = extract_pamphlet_pdf_url(fileinfo)
            results[cid] = pdf_url
            if pdf_url:
                with_pdf += 1

        stats[election_type] = (len(items), with_pdf)
        print(f"  {len(items)}명 수집, PDF URL {with_pdf}개")
        time.sleep(0.5)

    # 저장
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    # 요약
    total = len(results)
    filled = sum(1 for v in results.values() if v)
    print(f"\n=== 완료 ===")
    print(f"총 {filled}/{total}개 PDF URL 수집 → {out_path}")
    print("\n유형별 요약:")
    for et, (cnt, pdfs) in stats.items():
        print(f"  {et}: {cnt}명, PDF {pdfs}개")

    # 샘플 출력
    print("\n샘플 URL (처음 3개):")
    sample_count = 0
    for cid, url in results.items():
        if url:
            print(f"  {cid}: {url}")
            sample_count += 1
            if sample_count >= 3:
                break


if __name__ == "__main__":
    main()
