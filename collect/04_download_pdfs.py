import asyncio
import json
import os

import aiohttp
from tqdm.asyncio import tqdm

from config import DATA_DIR

PDF_DIR = os.path.join(os.path.dirname(__file__), "..", "pdfs")
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
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
        "Referer": "https://policy.nec.go.kr",
    }
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
    print(f"저장 위치: {os.path.abspath(PDF_DIR)}/")


if __name__ == "__main__":
    asyncio.run(main())
