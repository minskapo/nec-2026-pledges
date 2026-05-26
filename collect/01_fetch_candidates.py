"""
Fetch all candidates for the 9th nationwide simultaneous local election (2026-06-03)
by scraping the NEC election statistics system popup search.

Since the public API (data.go.kr) does not yet have 2026 data,
we scrape info.nec.go.kr popup search which reliably returns current candidate data.
"""
import json
import os
import re
import time
from bs4 import BeautifulSoup

import requests

from config import DATA_DIR, SG_TYPECODES

NEC_INFO = "https://info.nec.go.kr"
ELECTION_ID = "0020260603"

# Common Korean surnames that cover ~99% of all candidates
# Ordered by frequency; we deduplicate by candidate ID
COMMON_SURNAMES = [
    "김", "이", "박", "최", "정", "강", "조", "윤", "장", "임",
    "한", "오", "서", "신", "권", "황", "안", "송", "전", "홍",
    "유", "고", "문", "양", "손", "배", "백", "허", "노", "심",
    "하", "나", "곽", "성", "차", "주", "우", "구", "남", "진",
    "류", "원", "천", "방", "공", "지", "변", "민", "탁", "복",
    "라", "예", "봉", "국", "어", "엄", "용", "방", "석", "길",
    "모", "도", "위", "소", "신", "표", "두", "양", "계", "반",
    # Less common but important for completeness
    "가", "기", "능", "단", "담", "독", "동", "등", "락", "란",
    "림", "마", "망", "목", "무", "반", "보", "부", "분", "비",
    "사", "삼", "상", "세", "수", "순", "습", "승", "시", "아",
    "악", "야", "어", "여", "연", "영", "와", "왕", "요", "욱",
    "운", "을", "음", "의", "인", "일", "자", "재", "적", "제",
    "진", "창", "채", "초", "취", "태", "통", "파", "평", "포",
    "풍", "합", "해", "현", "형", "호", "화", "효", "훈", "흥",
]


def create_session():
    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    })
    # Initialize session
    session.get(f"{NEC_INFO}/bizcommon/popup/popup_search_candidateForm.xhtml",
                params={"electionId": ELECTION_ID}, timeout=30)
    session.headers["Referer"] = f"{NEC_INFO}/bizcommon/popup/popup_search_candidateForm.xhtml"
    return session


def parse_candidates_from_html(html: str) -> list[dict]:
    """Parse candidate data from the popup search HTML."""
    soup = BeautifulSoup(html, "html.parser")
    candidates = []
    seen_ids = set()

    # Find all h4 section headers (election type names)
    sections = soup.find_all(["h4", "ul"])

    current_section = ""
    for element in soup.find_all(["h4", "li"]):
        if element.name == "h4":
            current_section = element.get_text(strip=True)
        elif element.name == "li" and element.find("div", class_="path"):
            # This is a candidate list item
            # Get the path (district)
            path_div = element.find("div", class_="path")
            path = path_div.get_text(strip=True) if path_div else ""

            # Find each candidate block within this path
            man_blocks = element.find_all("ul", class_=lambda c: c and "man" in c)
            for block in man_blocks:
                # Extract candidate ID from fn_detailHbjPopUp call
                detail_link = block.find("a", href=re.compile(r"fn_detailHbjPopUp"))
                cnddt_id = None
                if detail_link:
                    id_match = re.search(r"fn_detailHbjPopUp\s*\(\s*['\"].*?['\"],\s*['\"](\d+)['\"]", str(detail_link))
                    if id_match:
                        cnddt_id = id_match.group(1)

                if not cnddt_id or cnddt_id in seen_ids:
                    continue
                seen_ids.add(cnddt_id)

                # Extract name
                name_el = block.find("i", class_="dd name")
                name = name_el.find("b").get_text(strip=True) if name_el and name_el.find("b") else ""

                # Extract party
                party_el = block.find("i", class_="bg part")
                party = party_el.get_text(strip=True) if party_el else ""

                # Extract sign/number
                sign_el = block.find("i", class_="bg sign")
                sign = sign_el.get_text(strip=True) if sign_el else ""

                # Extract birth/gender info
                info_el = block.find("i", class_="dd info")
                birth_info = info_el.get_text(strip=True) if info_el else ""

                # Extract address
                addr_el = block.find("i", class_="adrs")
                address = addr_el.get_text(strip=True) if addr_el else ""

                # Extract photo URL
                img_el = block.find("img")
                photo_url = img_el.get("src", "") if img_el else ""

                candidates.append({
                    "cnddtId": cnddt_id,
                    "name": name,
                    "party": party,
                    "sign": sign,
                    "electionType": current_section,
                    "sido": path.split()[0] if path else "",
                    "district": path,
                    "birthInfo": birth_info,
                    "address": address,
                    "photoUrl": photo_url,
                })

    return candidates


def fetch_by_surname(session: requests.Session, surname: str) -> list[dict]:
    """Fetch candidates whose name starts with the given surname."""
    try:
        r = session.post(
            f"{NEC_INFO}/bizcommon/popup/popup_search_candidate.xhtml",
            data={"electionId": ELECTION_ID, "searchName": surname},
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            timeout=60,
        )
        r.raise_for_status()

        # Quick count check
        count_match = re.search(r"총<i>(\d+)</i>건", r.text)
        count = int(count_match.group(1)) if count_match else 0

        if count == 0:
            return []

        return parse_candidates_from_html(r.text)
    except Exception as e:
        print(f"    ERROR for '{surname}': {e}")
        return []


def main():
    all_candidates = {}  # keyed by cnddtId for deduplication
    session = create_session()

    print(f"수집 시작: {len(COMMON_SURNAMES)}개 성씨 검색")
    print()

    for i, surname in enumerate(COMMON_SURNAMES):
        batch = fetch_by_surname(session, surname)
        new_count = 0
        for c in batch:
            if c["cnddtId"] not in all_candidates:
                all_candidates[c["cnddtId"]] = c
                new_count += 1

        if batch:
            print(f"[{i+1}/{len(COMMON_SURNAMES)}] '{surname}': {len(batch)}명 (신규 {new_count}명) → 누계 {len(all_candidates)}명")
        else:
            print(f"[{i+1}/{len(COMMON_SURNAMES)}] '{surname}': 없음")

        time.sleep(0.3)

        # Re-create session every 50 requests to avoid session expiry
        if (i + 1) % 50 == 0:
            session = create_session()
            time.sleep(1)

    result = list(all_candidates.values())
    print(f"\n수집 완료: 총 {len(result)}명")

    os.makedirs(DATA_DIR, exist_ok=True)
    out_path = os.path.join(DATA_DIR, "candidates.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print(f"저장: {out_path}")


if __name__ == "__main__":
    main()
