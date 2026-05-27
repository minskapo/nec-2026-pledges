"""
Hugging Face Datasets에 선거공보 PDF 및 데이터 업로드.

사용법:
    pip install huggingface_hub
    huggingface-cli login
    python 05_upload_huggingface.py

업로드 대상:
    - pdfs/*.pdf          → nec-2026-pledges/pdfs/
    - data/*.json         → nec-2026-pledges/data/
    - data/pledges.xlsx   → nec-2026-pledges/data/
"""

import os
import sys
from pathlib import Path

from huggingface_hub import HfApi, create_repo

REPO_ID = "minskapo/nec-2026-pledges"
REPO_TYPE = "dataset"

ROOT = Path(__file__).parent.parent
PDF_DIR = ROOT / "pdfs"
DATA_DIR = ROOT / "data"


def main():
    api = HfApi()

    # 토큰 확인
    try:
        user = api.whoami()
        print(f"로그인: {user['name']}")
    except Exception:
        print("로그인 필요: huggingface-cli login")
        sys.exit(1)

    # 저장소 생성 (이미 있으면 무시)
    try:
        create_repo(REPO_ID, repo_type=REPO_TYPE, exist_ok=True, private=False)
        print(f"저장소: https://huggingface.co/datasets/{REPO_ID}")
    except Exception as e:
        print(f"저장소 생성 오류: {e}")
        sys.exit(1)

    # data/ 파일 업로드
    data_files = list(DATA_DIR.glob("*.json")) + list(DATA_DIR.glob("*.xlsx"))
    print(f"\ndata/ 파일 업로드: {len(data_files)}개")
    for f in data_files:
        print(f"  {f.name} … ", end="", flush=True)
        api.upload_file(
            path_or_fileobj=str(f),
            path_in_repo=f"data/{f.name}",
            repo_id=REPO_ID,
            repo_type=REPO_TYPE,
        )
        print("완료")

    # pdfs/ 전체 폴더 업로드 (대용량 — upload_large_folder 사용)
    pdf_files = sorted(PDF_DIR.glob("*.pdf"))
    print(f"\npdfs/ 업로드: {len(pdf_files)}개 (총 ~34GB, 시간 소요)")
    print("중단 후 재실행해도 이어서 업로드됩니다.")

    # folder_path=ROOT + allow_patterns 로 pdfs/ 경로 유지
    api.upload_large_folder(
        folder_path=str(ROOT),
        repo_id=REPO_ID,
        repo_type=REPO_TYPE,
        allow_patterns="pdfs/*.pdf",
        num_workers=4,
        print_report=True,
        print_report_every=60,
    )

    print(f"\n업로드 완료: https://huggingface.co/datasets/{REPO_ID}")


if __name__ == "__main__":
    main()
