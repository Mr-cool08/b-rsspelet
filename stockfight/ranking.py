from math import floor
from typing import TypedDict


STARTING_ELO = 1000
K_FACTOR = 32

_LEAGUES = (
    (0, "Bronze"),
    (900, "Silver"),
    (1100, "Gold"),
    (1300, "Platinum"),
    (1500, "Diamond"),
    (1800, "Stock Legend"),
)


class LeagueProgress(TypedDict):
    league: str
    nextLeague: str | None
    nextElo: int | None
    progress: float


def rating_changes(a: int, b: int, score_a: float, *, k: int = K_FACTOR) -> tuple[int, int]:
    """Return both post-match Elo ratings for a score between zero and one."""
    if not 0 <= score_a <= 1:
        raise ValueError("Elo score must be between zero and one")

    # Work from the lower rating's perspective to avoid a positive exponent.
    lower_score = score_a if a <= b else 1 - score_a
    lower_odds = 10 ** (-abs(a - b) / 400)
    lower_expected = lower_odds / (1 + lower_odds)
    lower_delta = k * (lower_score - lower_expected)

    # Round once to keep the total rating constant, including at a half point.
    rounded_delta = floor(abs(lower_delta) + 0.5)
    if lower_delta < 0:
        rounded_delta = -rounded_delta
    if a > b:
        rounded_delta = -rounded_delta
    return a + rounded_delta, b - rounded_delta


def league_progress(elo: int) -> LeagueProgress:
    """Return the current league and percentage toward the next league."""
    lower_elo, league = _LEAGUES[0]
    for next_elo, next_league in _LEAGUES[1:]:
        if elo < next_elo:
            return {
                "league": league,
                "nextLeague": next_league,
                "nextElo": next_elo,
                "progress": max(0.0, (elo - lower_elo) / (next_elo - lower_elo) * 100),
            }
        lower_elo, league = next_elo, next_league
    return {"league": league, "nextLeague": None, "nextElo": None, "progress": 100.0}


def search_radius(wait_seconds: float) -> int:
    """Return the inclusive Elo difference allowed after this wait."""
    return 100 if wait_seconds < 15 else 200
