from datetime import UTC, datetime, timedelta
from decimal import Decimal

from .engine import Bar, RuleError, Scenario
from .prediction import price_move_bps, revealed_prediction_bars, validate_move_bps


PRACTICE_MODE = "prediction_practice"
PRACTICE_ROUNDS = 3
PREVIEW_BARS = 12


def _practice_scenario() -> Scenario:
    closes = (
        "100.00", "103.20", "106.45", "104.10", "109.05", "112.40",
        "108.10", "103.00", "98.30", "100.65", "105.10", "110.00",
        "119.35", "127.47", "111.54",
    )
    start = datetime(2024, 1, 8, 9, tzinfo=UTC)
    bars = []
    for index, value in enumerate(closes):
        close = Decimal(value)
        bars.append(Bar(start + timedelta(minutes=index), close, close, close, close, 0))
    return Scenario(
        "ÖVNING", "SE", "1m", "Stock Fight", True, tuple(bars), PREVIEW_BARS, "Ritduell",
    )


PRACTICE_SCENARIO = _practice_scenario()


class PredictionPractice:
    def __init__(self, match_id: str, user_id: int, name: str, now: float) -> None:
        self.id = match_id
        self.user_id = user_id
        self.name = name
        self.started_at = now
        self.reconnect_until: float | None = None
        self.round_number = 1
        self._outcomes: list[dict] = []

    def submit(self, round_number: object, move_bps: object) -> None:
        self._validate_round(round_number)
        guess = validate_move_bps(move_bps)
        if len(self._outcomes) == self.round_number:
            if self._outcomes[-1]["selfMoveBps"] == guess:
                return
            raise RuleError("Din prognos är redan låst.")

        index = PREVIEW_BARS + self.round_number - 1
        bars = PRACTICE_SCENARIO.bars
        actual = price_move_bps(bars[index - 1].close, bars[index].close)
        self._outcomes.append({
            "number": self.round_number,
            "actualMoveBps": actual,
            "selfMoveBps": guess,
            "selfErrorBps": abs(guess - actual),
        })

    def next_round(self, round_number: object) -> bool:
        if type(round_number) is int and 0 < round_number == self.round_number - 1:
            return False
        self._validate_round(round_number)
        if len(self._outcomes) != self.round_number:
            raise RuleError("Lås en prognos innan du går vidare.")
        if self.round_number == PRACTICE_ROUNDS:
            return True
        self.round_number += 1
        return False

    def _validate_round(self, round_number: object) -> None:
        if type(round_number) is not int or round_number != self.round_number:
            raise RuleError("Prognosen gäller inte den aktuella rundan.")

    def public(self, now: float) -> dict:
        revealed = PREVIEW_BARS + len(self._outcomes)
        outcome = self._outcomes[-1] if len(self._outcomes) == self.round_number else None
        return {
            **self._instrument(),
            "status": "active",
            "countdown": 0,
            "remaining": None,
            "elapsed": int(now - self.started_at),
            "roundLimit": PRACTICE_ROUNDS,
            "price": format(PRACTICE_SCENARIO.bars[revealed - 1].close, "f"),
            "bars": revealed_prediction_bars(PRACTICE_SCENARIO, revealed),
            "self": {"id": self.user_id, "name": self.name},
            "opponent": None,
            "round": {
                "number": self.round_number,
                "phase": "reveal" if outcome else "predict",
                "selfLocked": outcome is not None,
                "opponentLocked": False,
                "selfMoveBps": outcome["selfMoveBps"] if outcome else None,
                "outcome": outcome,
            },
        }

    def result(self, now: float) -> dict:
        return {
            **self._instrument(),
            "outcome": "completed",
            "duration": now - self.started_at,
            "roundsPlayed": len(self._outcomes),
            "rounds": list(self._outcomes),
            "periodStart": PRACTICE_SCENARIO.bars[0].timestamp.isoformat(),
            "periodEnd": PRACTICE_SCENARIO.bars[PREVIEW_BARS + len(self._outcomes) - 1].timestamp.isoformat(),
        }

    def _instrument(self) -> dict:
        return {
            "id": self.id,
            "mode": PRACTICE_MODE,
            "symbol": PRACTICE_SCENARIO.symbol,
            "name": PRACTICE_SCENARIO.name,
            "market": PRACTICE_SCENARIO.market,
            "interval": PRACTICE_SCENARIO.interval,
            "synthetic": True,
        }
