import httpx
from .rate_limiter import solved_limiter

SOLVED_AC_BASE = "https://solved.ac/api/v3"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; BOJAttendanceChecker/1.0)",
    "Accept": "application/json",
}

DIFFICULTY_LABELS = {
    0: "미확인",
    1: "Bronze V", 2: "Bronze IV", 3: "Bronze III", 4: "Bronze II", 5: "Bronze I",
    6: "Silver V", 7: "Silver IV", 8: "Silver III", 9: "Silver II", 10: "Silver I",
    11: "Gold V", 12: "Gold IV", 13: "Gold III", 14: "Gold II", 15: "Gold I",
    16: "Platinum V", 17: "Platinum IV", 18: "Platinum III", 19: "Platinum II", 20: "Platinum I",
    21: "Diamond V", 22: "Diamond IV", 23: "Diamond III", 24: "Diamond II", 25: "Diamond I",
    26: "Ruby V", 27: "Ruby IV", 28: "Ruby III", 29: "Ruby II", 30: "Ruby I",
}


def difficulty_label(level: int) -> str:
    return DIFFICULTY_LABELS.get(level, f"Level {level}")


def difficulty_tier(level: int) -> str:
    """Returns tier name for CSS class: bronze/silver/gold/platinum/diamond/ruby/unknown"""
    if level == 0:
        return "unknown"
    if level <= 5:
        return "bronze"
    if level <= 10:
        return "silver"
    if level <= 15:
        return "gold"
    if level <= 20:
        return "platinum"
    if level <= 25:
        return "diamond"
    return "ruby"


def is_gold_or_higher(level: int) -> bool:
    return level >= 11


async def fetch_problem_difficulty(problem_id: int) -> int:
    """Returns solved.ac level (0 if unknown/error)."""
    await solved_limiter.acquire()
    url = f"{SOLVED_AC_BASE}/problem/show?problemId={problem_id}"
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(url, headers=HEADERS)
            if response.status_code == 404:
                return 0
            response.raise_for_status()
            data = response.json()
            return data.get("level", 0)
    except Exception:
        return 0
