"""
pdfs/{cnddtId}.pdf → {선거명}-{지역}-{기호}번-{후보자명}({정당}).pdf

지역: 시도약칭[_구군][_선거구]
특수 규칙:
  - 교육감: 정당 표시 없음  → 교육감-서울-번호미상-홍길동.pdf
  - 비례대표: 정당이 주체  → 광역비례-서울-1번-더불어민주당.pdf
  - 기초의원 복수기호: 1-나 → 1_나번 (대시 → 언더스코어)
"""

import json
import re
from pathlib import Path

PDF_DIR  = Path(__file__).parent.parent / "pdfs"
DATA_DIR = Path(__file__).parent.parent / "data"

ELECTION_TYPE_MAP = {
    "시·도지사선거":         "광역단체장",
    "구·시·군의 장선거":     "기초단체장",
    "시·도의회의원선거":     "광역의원",
    "구·시·군의회의원선거":  "기초의원",
    "광역의원비례대표선거":  "광역비례",
    "기초의원비례대표선거":  "기초비례",
    "교육감선거":            "교육감",
    "국회의원선거":          "국회의원",
}

SIDO_ABBR = {
    "전남광주통합특별시":   "전남광주",
    "서울특별시":           "서울",
    "부산광역시":           "부산",
    "인천광역시":           "인천",
    "광주광역시":           "광주",
    "대구광역시":           "대구",
    "대전광역시":           "대전",
    "울산광역시":           "울산",
    "세종특별자치시":       "세종",
    "세종시":               "세종",
    "경기도":               "경기",
    "강원특별자치도":       "강원",
    "강원도":               "강원",
    "충청북도":             "충북",
    "충청남도":             "충남",
    "전북특별자치도":       "전북",
    "전라북도":             "전북",
    "전라남도":             "전남",
    "경상북도":             "경북",
    "경상남도":             "경남",
    "제주특별자치도":       "제주",
}
_SIDO_SORTED = sorted(SIDO_ABBR.items(), key=lambda x: -len(x[0]))

INVALID_CHARS = re.compile(r'[/\\:*?"<>|\s]')


def parse_region(sido: str) -> str:
    for full, abbr in _SIDO_SORTED:
        if sido.startswith(full):
            rest = sido[len(full):]
            if not rest:
                return abbr
            m = re.match(r'^(.+?[구시군읍면])(.*)?$', rest)
            if m:
                district = m.group(1)
                sg = re.sub(r'선거구', '', m.group(2) or '').strip()
                sg = re.sub(r'^제(\d+)$', r'\1', sg)
                parts = [abbr, district]
                if sg:
                    parts.append(sg)
                return "_".join(parts)
            return f"{abbr}_{rest}"
    return INVALID_CHARS.sub("_", sido)


def make_sign(raw: str) -> str:
    """기호 파싱. 대시는 언더스코어로 변환."""
    if "기호" in raw:
        num = raw.replace("기호", "").strip().replace("-", "_")
        return f"{num}번"
    if "추천순위" in raw:
        num = raw.replace("추천순위", "").strip()
        return f"{num}번"
    n = raw.strip()
    return f"{n}번" if n else "번호미상"


def make_filename(c: dict) -> str:
    et       = c.get("electionType", "")
    election = ELECTION_TYPE_MAP.get(et, et)
    region   = parse_region(c.get("sido", ""))
    sign     = make_sign(c.get("sign", ""))
    name     = INVALID_CHARS.sub("_", c.get("name", ""))
    party    = INVALID_CHARS.sub("_", c.get("party") or "무소속")

    if "교육감" in et:
        return f"{election}-{region}-{sign}-{name}.pdf"
    if "비례대표" in et:
        return f"{election}-{region}-{sign}-{party}.pdf"
    return f"{election}-{region}-{sign}-{name}({party}).pdf"


# ── 이전 버전(v1) 파일명 생성 (이미 rename된 파일 역추적용) ────────────────
def _make_sign_v1(raw: str) -> str:
    if "기호" in raw:
        return raw.replace("기호", "").strip() + "번"
    if "추천순위" in raw:
        return "추천" + raw.replace("추천순위", "").strip() + "번"
    n = raw.strip()
    return f"{n}번" if n else "번호미상"


def _make_filename_v1(c: dict) -> str:
    election = ELECTION_TYPE_MAP.get(c.get("electionType", ""), c.get("electionType", ""))
    region   = parse_region(c.get("sido", ""))
    sign     = _make_sign_v1(c.get("sign", ""))
    name     = INVALID_CHARS.sub("_", c.get("name", ""))
    party    = INVALID_CHARS.sub("_", c.get("party") or "무소속")
    return f"{election}-{region}-{sign}-{name}({party}).pdf"


def main(dry_run: bool = False):
    with open(DATA_DIR / "candidates.json", encoding="utf-8") as f:
        candidates = json.load(f)

    id_to_cand = {c["cnddtId"]: c for c in candidates}

    # 현재 pdfs/ 파일 목록
    existing: dict[str, Path] = {p.name: p for p in PDF_DIR.glob("*.pdf")}

    renamed = skipped = error = 0
    seen: dict[str, int] = {}

    def unique_name(name: str) -> str:
        base, ext = name.rsplit(".", 1)
        key = name
        if key in seen:
            seen[key] += 1
            key = f"{base}_{seen[key]}.{ext}"
        else:
            seen[key] = 1
        return key

    for cid, cand in id_to_cand.items():
        new_name = unique_name(make_filename(cand))

        # 후보: (1) cnddtId.pdf → 직접 rename
        #       (2) v1 descriptive name → re-rename
        src_path = None
        if f"{cid}.pdf" in existing:
            src_path = existing[f"{cid}.pdf"]
        else:
            v1_name = _make_filename_v1(cand)
            if v1_name in existing:
                src_path = existing[v1_name]

        if src_path is None:
            continue  # PDF 없음

        new_path = PDF_DIR / new_name

        if src_path.name == new_name:
            skipped += 1
            continue

        if dry_run:
            print(f"  {src_path.name}\n  → {new_name}\n")
            renamed += 1
            continue

        if new_path.exists():
            skipped += 1
            continue
        try:
            src_path.rename(new_path)
            renamed += 1
        except Exception as e:
            print(f"  오류: {src_path.name}: {e}")
            error += 1

    print(f"{'[DRY RUN] ' if dry_run else ''}완료: 변환 {renamed} / 건너뜀 {skipped} / 오류 {error}")


if __name__ == "__main__":
    import sys
    main(dry_run="--dry-run" in sys.argv)
