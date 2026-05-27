"""
pdfs/{cnddtId}.pdf → {선거명}-{지역}-{기호}번-{후보자명}({정당}).pdf

지역: 시도약칭[_구군][_선거구]  (언더스코어 구분)
특수 규칙:
  - 교육감: 정당 표시 없음
  - 비례대표: 후보자명 대신 정당명
  - 기초의원 복수기호: 1-나 → 1_나번
  - 제주/세종: sido가 도명 중복이라 district 필드로 선거구 추출
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


def _extract_sg_from_extra(extra: str) -> str:
    """'제주시 구좌읍·우도면선거구' 같은 district 잔여 문자열에서 선거구명 추출."""
    extra = extra.strip()
    if not extra:
        return ""
    last = extra.split()[-1]
    sg = last.replace("선거구", "").strip()
    sg = re.sub(r"^제(\d+)$", r"\1", sg)
    return sg


def parse_region(sido: str, district: str = "") -> str:
    """sido (+ 필요시 district)로부터 '시도약칭[_구군][_선거구]' 생성."""
    for full, abbr in _SIDO_SORTED:
        if not sido.startswith(full):
            continue

        rest = sido[len(full):]

        # ── 도명 중복 케이스 (제주특별자치도제주특별자치도, 세종특별자치시세종특별자치시…)
        if rest.startswith(full):
            rest2 = rest[len(full):]
            if rest2:
                # 세종: "제1선거구" 등 선거구 정보가 sido에 포함
                sg = rest2.replace("선거구", "").strip()
                sg = re.sub(r"^제(\d+)$", r"\1", sg)
                return f"{abbr}_{sg}" if sg else abbr
            else:
                # 제주: sido에 선거구 없음 → district fallback
                if district and district != sido:
                    extra = district[len(sido):].strip()
                    sg = _extract_sg_from_extra(extra)
                    return f"{abbr}_{sg}" if sg else abbr
                return abbr

        # ── 도명만 있는 경우 (광역단체장, 교육감 등)
        if not rest:
            return abbr

        # ── 일반 케이스: "중구제2선거구", "종로구나선거구", "춘천시제2선거구" 등
        m = re.match(r"^(.+?[구시군읍면])(.*)?$", rest)
        if m:
            district_name = m.group(1)
            sg = re.sub(r"선거구", "", m.group(2) or "").strip()
            sg = re.sub(r"^제(\d+)$", r"\1", sg)
            parts = [abbr, district_name]
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
    region   = parse_region(c.get("sido", ""), c.get("district", ""))
    sign     = make_sign(c.get("sign", ""))
    name     = INVALID_CHARS.sub("_", c.get("name", ""))
    party    = INVALID_CHARS.sub("_", c.get("party") or "무소속")

    if "교육감" in et:
        return f"{election}-{region}-{sign}-{name}.pdf"
    if "비례대표" in et:
        return f"{election}-{region}-{sign}-{party}.pdf"
    return f"{election}-{region}-{sign}-{name}({party}).pdf"


# ── 이전 버전 파일명 생성 (이미 rename된 파일 역추적용) ─────────────────────

def _parse_region_old(sido: str) -> str:
    """구 버전 parse_region (district 미사용, 중복 감지 없음)."""
    for full, abbr in _SIDO_SORTED:
        if sido.startswith(full):
            rest = sido[len(full):]
            if not rest:
                return abbr
            m = re.match(r"^(.+?[구시군읍면])(.*)?$", rest)
            if m:
                district = m.group(1)
                sg = re.sub(r"선거구", "", m.group(2) or "").strip()
                sg = re.sub(r"^제(\d+)$", r"\1", sg)
                parts = [abbr, district]
                if sg:
                    parts.append(sg)
                return "_".join(parts)
            return f"{abbr}_{rest}"
    return INVALID_CHARS.sub("_", sido)


def _make_filename_v1(c: dict) -> str:
    """최초 rename 버전: 교육감/비례 특수처리 없음, 추천N번 형식."""
    election = ELECTION_TYPE_MAP.get(c.get("electionType", ""), c.get("electionType", ""))
    region   = _parse_region_old(c.get("sido", ""))
    raw_sign = c.get("sign", "")
    if "기호" in raw_sign:
        sign = raw_sign.replace("기호", "").strip() + "번"
    elif "추천순위" in raw_sign:
        sign = "추천" + raw_sign.replace("추천순위", "").strip() + "번"
    else:
        n = raw_sign.strip()
        sign = f"{n}번" if n else "번호미상"
    name  = INVALID_CHARS.sub("_", c.get("name", ""))
    party = INVALID_CHARS.sub("_", c.get("party") or "무소속")
    return f"{election}-{region}-{sign}-{name}({party}).pdf"


def _make_filename_v2(c: dict) -> str:
    """두 번째 rename 버전: 교육감/비례 특수처리 + sign 대시→언더스코어, 단 district 미사용."""
    et       = c.get("electionType", "")
    election = ELECTION_TYPE_MAP.get(et, et)
    region   = _parse_region_old(c.get("sido", ""))
    sign     = make_sign(c.get("sign", ""))
    name     = INVALID_CHARS.sub("_", c.get("name", ""))
    party    = INVALID_CHARS.sub("_", c.get("party") or "무소속")
    if "교육감" in et:
        return f"{election}-{region}-{sign}-{name}.pdf"
    if "비례대표" in et:
        return f"{election}-{region}-{sign}-{party}.pdf"
    return f"{election}-{region}-{sign}-{name}({party}).pdf"


# ── 메인 ─────────────────────────────────────────────────────────────────────

def main(dry_run: bool = False):
    with open(DATA_DIR / "candidates.json", encoding="utf-8") as f:
        candidates = json.load(f)

    existing: dict[str, Path] = {p.name: p for p in PDF_DIR.glob("*.pdf")}

    renamed = skipped = error = 0
    seen: dict[str, int] = {}

    def unique_name(name: str) -> str:
        base, ext = name.rsplit(".", 1)
        if name not in seen:
            seen[name] = 1
            return name
        seen[name] += 1
        return f"{base}_{seen[name]}.{ext}"

    for cand in candidates:
        cid      = cand["cnddtId"]
        new_name = unique_name(make_filename(cand))

        src_path = None
        for old_name in (f"{cid}.pdf", _make_filename_v1(cand), _make_filename_v2(cand)):
            if old_name in existing:
                src_path = existing[old_name]
                break

        if src_path is None:
            continue

        if src_path.name == new_name:
            skipped += 1
            continue

        if dry_run:
            print(f"  {src_path.name}\n  → {new_name}\n")
            renamed += 1
            continue

        new_path = PDF_DIR / new_name
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
