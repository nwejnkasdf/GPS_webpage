from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from models.boj_game import BojGameProblem, BojGameRound, BojGameRoundProblem
from models.telepathy import (
    TelepathyOption,
    TelepathyRound,
    TelepathySubmission,
    TelepathySubmissionRole,
    TelepathyTeam,
)


DIFFICULTY_LABELS = {
    0: "Unknown",
    1: "Bronze V",
    2: "Bronze IV",
    3: "Bronze III",
    4: "Bronze II",
    5: "Bronze I",
    6: "Silver V",
    7: "Silver IV",
    8: "Silver III",
    9: "Silver II",
    10: "Silver I",
    11: "Gold V",
    12: "Gold IV",
    13: "Gold III",
    14: "Gold II",
    15: "Gold I",
    16: "Platinum V",
    17: "Platinum IV",
    18: "Platinum III",
    19: "Platinum II",
    20: "Platinum I",
    21: "Diamond V",
    22: "Diamond IV",
    23: "Diamond III",
    24: "Diamond II",
    25: "Diamond I",
    26: "Ruby V",
    27: "Ruby IV",
    28: "Ruby III",
    29: "Ruby II",
    30: "Ruby I",
}


def difficulty_label(level: int) -> str:
    return DIFFICULTY_LABELS.get(level, f"Level {level}")


def difficulty_tier(level: int) -> str:
    if level <= 0:
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


def ensure_default_telepathy_teams(db: Session, team_count: int = 6) -> None:
    existing = db.query(TelepathyTeam).count()
    if existing > 0:
        return

    for team_number in range(1, team_count + 1):
        db.add(
            TelepathyTeam(
                name=f"{team_number}조",
                display_order=team_number,
            )
        )
    db.commit()


def sort_telepathy_teams(teams: list[TelepathyTeam]) -> list[TelepathyTeam]:
    return sorted(teams, key=lambda team: (team.display_order, team.id))


def sort_telepathy_options(options: list[TelepathyOption]) -> list[TelepathyOption]:
    return sorted(options, key=lambda option: (option.display_order, option.id))


def _iso(value) -> str | None:
    if value is None:
        return None
    return value.isoformat()


def serialize_telepathy_team(team: TelepathyTeam) -> dict[str, Any]:
    return {
        "id": team.id,
        "name": team.name,
        "display_order": team.display_order,
    }


def telepathy_option_image_url(option: TelepathyOption) -> str | None:
    if option.image_data:
        return f"/api/v1/public/recreation/telepathy/options/{option.id}/image"
    return option.image_url


def serialize_telepathy_option(option: TelepathyOption) -> dict[str, Any]:
    return {
        "id": option.id,
        "name": option.name,
        "display_order": option.display_order,
        "image_url": telepathy_option_image_url(option),
    }


def _ranking_map(ranking: list[int]) -> dict[int, int]:
    return {option_id: index + 1 for index, option_id in enumerate(ranking)}


def _serialize_telepathy_submission(
    submission: TelepathySubmission | None,
    option_map: dict[int, TelepathyOption],
) -> dict[str, Any] | None:
    if submission is None:
        return None

    ranking = []
    for index, option_id in enumerate(submission.ranking or [], start=1):
        option = option_map.get(option_id)
        ranking.append(
            {
                "rank": index,
                "option_id": option_id,
                "name": option.name if option else f"Option {option_id}",
            }
        )

    return {
        "updated_at": _iso(submission.updated_at),
        "ranking": ranking,
    }


def telepathy_submission_is_complete(
    submission: TelepathySubmission | None,
    option_ids: list[int],
) -> bool:
    if submission is None:
        return False
    ranking = submission.ranking or []
    return len(ranking) == len(option_ids) and set(ranking) == set(option_ids)


def calculate_telepathy_round_score(
    representative_ranking: list[int],
    team_ranking: list[int],
) -> int:
    representative_map = _ranking_map(representative_ranking)
    team_map = _ranking_map(team_ranking)
    option_ids = representative_map.keys() & team_map.keys()
    return sum(abs(representative_map[option_id] - team_map[option_id]) for option_id in option_ids)


def serialize_telepathy_round(
    round_obj: TelepathyRound,
    teams: list[TelepathyTeam],
) -> dict[str, Any]:
    options = sort_telepathy_options(list(round_obj.options))
    option_ids = [option.id for option in options]
    option_map = {option.id: option for option in options}

    submission_lookup: dict[tuple[int, TelepathySubmissionRole], TelepathySubmission] = {}
    for submission in round_obj.submissions:
        submission_lookup[(submission.team_id, submission.role)] = submission

    results = []
    for team in teams:
        representative_submission = submission_lookup.get((team.id, TelepathySubmissionRole.REPRESENTATIVE))
        team_submission = submission_lookup.get((team.id, TelepathySubmissionRole.TEAM))
        representative_complete = telepathy_submission_is_complete(representative_submission, option_ids)
        team_complete = telepathy_submission_is_complete(team_submission, option_ids)

        round_score = None
        if representative_complete and team_complete:
            round_score = calculate_telepathy_round_score(
                representative_submission.ranking,
                team_submission.ranking,
            )

        results.append(
            {
                "team_id": team.id,
                "team_name": team.name,
                "representative_submitted": representative_submission is not None,
                "team_submitted": team_submission is not None,
                "representative_complete": representative_complete,
                "team_complete": team_complete,
                "round_score": round_score,
                "representative": _serialize_telepathy_submission(representative_submission, option_map),
                "team": _serialize_telepathy_submission(team_submission, option_map),
            }
        )

    return {
        "id": round_obj.id,
        "title": round_obj.title,
        "prompt": round_obj.prompt,
        "is_active": round_obj.is_active,
        "is_revealed": round_obj.is_revealed,
        "created_at": _iso(round_obj.created_at),
        "updated_at": _iso(round_obj.updated_at),
        "options": [serialize_telepathy_option(option) for option in options],
        "results": results,
    }


def build_telepathy_state(db: Session) -> dict[str, Any]:
    ensure_default_telepathy_teams(db)
    teams = sort_telepathy_teams(db.query(TelepathyTeam).all())
    rounds = db.query(TelepathyRound).order_by(TelepathyRound.created_at, TelepathyRound.id).all()

    round_payloads = [serialize_telepathy_round(round_obj, teams) for round_obj in rounds]
    scoreboard = {
        team.id: {
            "team_id": team.id,
            "team_name": team.name,
            "total_score": 0,
            "completed_rounds": 0,
        }
        for team in teams
    }

    for round_payload in round_payloads:
        if not round_payload["is_revealed"]:
            continue
        for result in round_payload["results"]:
            if result["round_score"] is None:
                continue
            scoreboard[result["team_id"]]["total_score"] += result["round_score"]
            scoreboard[result["team_id"]]["completed_rounds"] += 1

    scoreboard_rows = list(scoreboard.values())
    scoreboard_rows.sort(key=lambda row: (-row["completed_rounds"], row["total_score"], row["team_name"]))

    current_rank = 0
    last_score = None
    for index, row in enumerate(scoreboard_rows, start=1):
        if row["total_score"] != last_score:
            current_rank = index
            last_score = row["total_score"]
        row["rank"] = current_rank

    active_round = next((round_payload for round_payload in round_payloads if round_payload["is_active"]), None)
    return {
        "teams": [serialize_telepathy_team(team) for team in teams],
        "rounds": list(reversed(round_payloads)),
        "active_round": active_round,
        "scoreboard": scoreboard_rows,
    }


def serialize_boj_problem(problem: BojGameProblem) -> dict[str, Any]:
    return {
        "id": problem.id,
        "problem_number": problem.problem_number,
        "title": problem.title,
        "difficulty": problem.difficulty,
        "difficulty_label": difficulty_label(problem.difficulty),
        "difficulty_tier": difficulty_tier(problem.difficulty),
        "image_url": (
            f"/api/v1/public/recreation/boj/problems/{problem.id}/image"
            if problem.image_data
            else None
        ),
        "created_at": _iso(problem.created_at),
    }


def serialize_boj_round_problem(problem: BojGameRoundProblem) -> dict[str, Any]:
    return {
        "id": problem.id,
        "problem_number": problem.problem_number,
        "title": problem.title,
        "difficulty": problem.difficulty,
        "difficulty_label": difficulty_label(problem.difficulty),
        "difficulty_tier": difficulty_tier(problem.difficulty),
        "image_url": (
            f"/api/v1/public/recreation/boj/round-problems/{problem.id}/image"
            if problem.image_data
            else None
        ),
        "display_order": problem.display_order,
    }


def serialize_boj_round(round_obj: BojGameRound) -> dict[str, Any]:
    problems = sorted(round_obj.problems, key=lambda problem: (problem.display_order, problem.id))
    return {
        "id": round_obj.id,
        "title": round_obj.title,
        "is_active": round_obj.is_active,
        "last_result_status": round_obj.last_result_status,
        "last_submitted_order": round_obj.last_submitted_order,
        "last_attempt_at": _iso(round_obj.last_attempt_at),
        "created_at": _iso(round_obj.created_at),
        "problems": [serialize_boj_round_problem(problem) for problem in problems],
    }


def build_boj_state(db: Session) -> dict[str, Any]:
    pool_problems = (
        db.query(BojGameProblem)
        .order_by(BojGameProblem.created_at.desc(), BojGameProblem.id.desc())
        .all()
    )
    rounds = (
        db.query(BojGameRound)
        .order_by(BojGameRound.created_at.desc(), BojGameRound.id.desc())
        .all()
    )
    round_payloads = [serialize_boj_round(round_obj) for round_obj in rounds]
    current_round = next((round_payload for round_payload in round_payloads if round_payload["is_active"]), None)

    return {
        "pool_problems": [serialize_boj_problem(problem) for problem in pool_problems],
        "rounds": round_payloads,
        "current_round": current_round,
    }
