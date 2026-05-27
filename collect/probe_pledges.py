import json
import requests
from config import PLEDGE_API_KEY, SG_ID, PLEDGE_API

candidates = json.load(open("../data/candidates.json"))
sample = candidates[0]  # 첫 번째 후보자

ELECTION_TYPE_TO_CODE = {
    "시·도지사선거": "3",
    "교육감선거": "4",
    "구·시·군의 장선거": "5",
    "시·도의회의원선거": "6",
    "구·시·군의회의원선거": "7",
    "광역의원비례대표선거": "8",
    "기초의원비례대표선거": "8",
    "국회의원선거": "2",
}
sg_typecode = ELECTION_TYPE_TO_CODE.get(sample["electionType"], "3")

print(f"후보자: {sample['name']} ({sample['electionType']}), cnddtId={sample['cnddtId']}, sgTypecode={sg_typecode}")

params = {
    "serviceKey": PLEDGE_API_KEY,
    "sgId": SG_ID,
    "sgTypecode": sg_typecode,
    "cnddtId": sample["cnddtId"],
    "type": "json",
}
r = requests.get(PLEDGE_API, params=params)
print("status:", r.status_code)
print("content-type:", r.headers.get("content-type"))
print("raw text:", r.text[:3000])
try:
    print(json.dumps(r.json(), indent=2, ensure_ascii=False)[:3000])
except Exception as e:
    print("JSON parse error:", e)
