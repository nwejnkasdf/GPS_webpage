import asyncio
from datetime import datetime

import httpx
from bs4 import BeautifulSoup

from .rate_limiter import boj_limiter

BOJ_STATUS_URL = "https://www.acmicpc.net/status"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8",
    "Accept-Encoding": "gzip, deflate, br",
    "Referer": "https://www.acmicpc.net/",
    "Connection": "keep-alive",
}


class BOJScrapingError(Exception):
    pass


async def get_accepted_submissions(
    user_id: str,
    problem_id: int,
    max_retries: int = 3,
) -> list[datetime]:
    """
    Scrapes BOJ status page for accepted submissions (result_id=4).
    Returns sorted list of submission datetimes (oldest first).
    """
    params = {
        "problem_id": str(problem_id),
        "user_id": user_id,
        "result_id": "4",
    }

    for attempt in range(max_retries):
        await boj_limiter.acquire()
        try:
            async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
                response = await client.get(BOJ_STATUS_URL, params=params, headers=HEADERS)

                if response.status_code == 403:
                    raise BOJScrapingError(
                        f"BOJ 403 오류: {user_id} / 문제 {problem_id} - "
                        "봇 차단 가능성. 잠시 후 재시도하세요."
                    )
                if response.status_code == 429:
                    wait_sec = 30 * (attempt + 1)
                    await asyncio.sleep(wait_sec)
                    continue

                response.raise_for_status()
                return _parse_submission_times(response.text)

        except BOJScrapingError:
            raise
        except httpx.TimeoutException:
            if attempt == max_retries - 1:
                return []
            await asyncio.sleep(5 * (attempt + 1))
        except httpx.RequestError:
            if attempt == max_retries - 1:
                return []
            await asyncio.sleep(3)

    return []


def _parse_submission_times(html: str) -> list[datetime]:
    """
    Parse #status-table.
    Time is in <a class="real-time-update" data-timestamp="UNIX_SEC" title="YYYY-MM-DD HH:MM:SS">.
    """
    soup = BeautifulSoup(html, "lxml")
    table = soup.find("table", {"id": "status-table"})
    if not table:
        return []

    times = []
    for a in table.select("a.real-time-update"):
        # 1순위: data-timestamp (Unix seconds)
        ts = a.get("data-timestamp")
        if ts:
            try:
                ts_int = int(ts)
                if ts_int > 1_000_000_000_000:  # milliseconds → seconds
                    ts_int //= 1000
                times.append(datetime.fromtimestamp(ts_int))
                continue
            except (ValueError, OSError):
                pass
        # 2순위: title 속성 "YYYY-MM-DD HH:MM:SS"
        title = a.get("title", "")
        for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M"):
            try:
                times.append(datetime.strptime(title, fmt))
                break
            except ValueError:
                pass

    return sorted(times)


async def was_solved_before_deadline(
    user_id: str,
    problem_id: int,
    deadline: datetime,
) -> bool:
    """Returns True if there is an accepted submission at or before the deadline."""
    submissions = await get_accepted_submissions(user_id, problem_id)
    return any(t <= deadline for t in submissions)
