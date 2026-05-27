import json
import os
import time
import xml.etree.ElementTree as ET

import requests
from tqdm import tqdm

from config import PLEDGE_API_KEY, SG_ID, PLEDGE_API, DATA_DIR

ELECTION_TYPE_TO_CODE = {
    "시·도지사선거": "3",
    "구·시·군의 장선거": "4",  # API typecode: 3=광역단체장, 4=기초단체장 (교육감은 이 엔드포인트 미지원)
    "시·도의회의원선거": "6",
    "구·시·군의회의원선거": "7",
    "광역의원비례대표선거": "8",
    "기초의원비례대표선거": "8",
    "국회의원선거": "2",
}

# 5대 공약 제출 대상 선거 종류 (의원·비례대표는 제출 대상 아님, 교육감은 API 미지원)
PLEDGE_TARGET_TYPES = {"시·도지사선거", "구·시·군의 장선거"}


def fetch_pledges(cnddt_id: str, sg_typecode: str) -> dict:
    params = {
        "serviceKey": PLEDGE_API_KEY,
        "sgId": SG_ID,
        "sgTypecode": sg_typecode,
        "cnddtId": cnddt_id,
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

    try:
        root = ET.fromstring(r.content)
    except ET.ParseError:
        return {}

    result_code = root.findtext("header/resultCode") or ""
    if result_code != "INFO-00":
        return {}

    item = root.find("body/items/item")
    if item is None:
        return {}

    pledges = {}
    # 공약은 최대 10개: prmsOrd1..10, prmsTitle1..10, prmmCont1..10, prmsRealmName1..10
    for i in range(1, 11):
        ord_val = (item.findtext(f"prmsOrd{i}") or "").strip()
        title = (item.findtext(f"prmsTitle{i}") or "").strip()
        content = (item.findtext(f"prmmCont{i}") or "").strip()
        field = (item.findtext(f"prmsRealmName{i}") or "").strip()
        if ord_val and title:
            pledges[ord_val] = {
                "title": title,
                "content": content,
                "field": field,
            }

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
    # 의원·비례대표는 5대 공약 제출 대상이 아니므로 스킵
    targets = [c for c in candidates if c.get("electionType") in PLEDGE_TARGET_TYPES]
    todo = [c for c in targets if c["cnddtId"] not in results]
    print(f"공약 수집 대상: {len(targets)}명 (시도지사·교육감·기초단체장)")
    print(f"수집 예정: {len(todo)}명 (기수집: {len(existing)}명)")

    for cnddt in tqdm(todo):
        cid = cnddt["cnddtId"]
        sg_typecode = ELECTION_TYPE_TO_CODE.get(cnddt.get("electionType", ""), "3")
        results[cid] = fetch_pledges(cid, sg_typecode)
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
