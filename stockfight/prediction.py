from __future__ import annotations

from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal
from math import ceil, isfinite
from statistics import median

from .engine import RuleError, Scenario
from .ranking import K_FACTOR


MAX_ROUNDS = 8
PREDICTION_STEP = 3
SIGNIFICANT_MOVE_BPS = 75
PREDICT_SECONDS = 20
REVEAL_SECONDS = 4
MIN_MOVE_BPS = -10_000
MAX_MOVE_BPS = 9_007_199_254_740_991


def validate_move_bps(move_bps: object) -> int:
    if type(move_bps) is not int or not MIN_MOVE_BPS <= move_bps <= MAX_MOVE_BPS:
        raise RuleError("Ogiltig kursförändring.")
    return move_bps


def price_move_bps(previous_price: Decimal, price: Decimal) -> int:
    actual_move = (price - previous_price) * 10_000 / previous_price
    return int(actual_move.to_integral_value(rounding=ROUND_HALF_UP))


def prediction_window_quality(moves: tuple[int, ...], preview_moves: int) -> int:
    """Prefer active windows where visible price momentum is useful."""
    actual_moves = moves[preview_moves:]
    opening = actual_moves[:4]
    if not opening:
        return 0
    increases = sum(move >= SIGNIFICANT_MOVE_BPS for move in actual_moves)
    decreases = sum(move <= -SIGNIFICANT_MOVE_BPS for move in actual_moves)

    # Measure a forecast that only uses the moves already visible at each round.
    trend_wins = []
    for index in range(preview_moves, len(moves)):
        history = moves[max(0, index - 3):index]
        guess = median(history) if history else 0
        actual = moves[index]
        trend_wins.append(abs(guess - actual) < abs(actual))

    return sum((
        increases >= 2 and decreases >= 2,
        (increases + decreases) * 4 >= len(actual_moves) * 3,
        min(opening) <= -SIGNIFICANT_MOVE_BPS and max(opening) >= SIGNIFICANT_MOVE_BPS,
        sum(trend_wins) * 2 > len(trend_wins) and sum(trend_wins[:4]) * 2 >= len(opening),
    ))


def revealed_prediction_bars(scenario: Scenario, revealed_count: int) -> list[dict]:
    return [
        {"time": index - (scenario.preview_count - 1), "close": format(bar.close, "f")}
        for index, bar in enumerate(scenario.bars[:revealed_count])
    ]


@dataclass(frozen=True, slots=True)
class PredictionMode:
    key: str = "prediction"
    rating_k: int = K_FACTOR
    starting_hp: int = 100


PREDICTION = PredictionMode()


@dataclass(slots=True)
class PredictionPlayer:
    name: str
    hp: int
    attack_damage: int = 0


@dataclass(frozen=True, slots=True)
class RoundOutcome:
    actual_move: int
    moves: dict[int, int]
    errors: dict[int, int]
    winner_id: int | None
    damage: int

    def public(self, user_id: int, opponent_id: int | None = None) -> dict:
        return {
            "actualMoveBps": self.actual_move,
            "selfMoveBps": self.moves.get(user_id),
            "opponentMoveBps": self.moves.get(opponent_id) if opponent_id is not None else None,
            "selfErrorBps": self.errors.get(user_id),
            "opponentErrorBps": self.errors.get(opponent_id) if opponent_id is not None else None,
            "winnerId": self.winner_id,
            "damage": self.damage,
        }


class PredictionMatch:
    mode = PREDICTION

    def __init__(
        self,
        match_id: str,
        players: dict[int, str],
        scenario: Scenario,
        now: float,
        *,
        countdown: float = 3.0,
    ) -> None:
        if len(players) != 2:
            raise ValueError("En match behöver två spelare.")
        if not 1 <= scenario.preview_count <= len(scenario.bars) - MAX_ROUNDS:
            raise ValueError("Scenariot behöver förhandsvisning och en kursstapel per runda.")
        if any(not bar.close.is_finite() or bar.close <= 0 for bar in scenario.bars):
            raise ValueError("Scenariot behöver positiva, ändliga stängningskurser.")
        if not isfinite(now) or not isfinite(countdown) or countdown < 0:
            raise ValueError("Matchens starttid och nedräkning måste vara giltiga.")

        self.id = match_id
        self.scenario = scenario
        self.players = {
            user_id: PredictionPlayer(name, self.mode.starting_hp)
            for user_id, name in players.items()
        }
        self.status = "countdown" if countdown else "active"
        self.winner_id: int | None = None
        self.end_reason: str | None = None
        self.duration = 0.0
        self.revealed_count = scenario.preview_count
        self._now = now
        self._starts_at = now + countdown
        self._phase_ends_at = self._starts_at + PREDICT_SECONDS
        self._round_number = 1
        self._moves: dict[int, int] = {}
        self._outcomes: list[RoundOutcome] = []
        self._revealing = False
        self._event: dict | None = None

    @property
    def price(self) -> Decimal:
        return self.scenario.bars[self.revealed_count - 1].close

    def advance(self, now: float) -> bool:
        if not isfinite(now):
            raise ValueError("Matchtiden måste vara ändlig.")
        if self.status == "finished" or now < self._now:
            return False

        previous_now = self._now
        previous_elapsed = int(self.duration)
        self._now = now
        if now < self._starts_at:
            return self._countdown(now) != self._countdown(previous_now)

        changed = self.status == "countdown"
        previous_remaining = self._remaining(previous_now)
        self.status = "active"
        while now >= self._phase_ends_at:
            changed = True
            phase_end = self._phase_ends_at
            if not self._revealing:
                self._reveal(phase_end)
            elif self._match_over():
                self.status = "finished"
                self.end_reason = "knockout" if any(player.hp == 0 for player in self.players.values()) else "round_limit"
                self.duration = phase_end - self._starts_at
                return True
            else:
                self._round_number += 1
                self._moves = {}
                self._revealing = False
                self._event = None
                self._phase_ends_at = phase_end + PREDICT_SECONDS

        self.duration = now - self._starts_at
        return changed or int(self.duration) != previous_elapsed or self._remaining(now) != previous_remaining

    def submit(self, user_id: int, round_number: int, move_bps: int, now: float) -> None:
        self._player(user_id)
        self.advance(now)
        if self.status != "active" or self._revealing:
            raise RuleError("Rundan är stängd för prognoser.")
        if type(round_number) is not int or round_number != self._round_number:
            raise RuleError("Prognosen gäller inte den aktuella rundan.")
        if user_id in self._moves:
            raise RuleError("Din prognos är redan låst.")
        self._moves[user_id] = validate_move_bps(move_bps)
        if len(self._moves) == len(self.players):
            self._reveal(self._now)

    def _reveal(self, now: float) -> None:
        previous_price = self.price
        self.revealed_count += 1
        actual_bps = price_move_bps(previous_price, self.price)
        errors = {user_id: abs(move - actual_bps) for user_id, move in self._moves.items()}

        winner_id = None
        damage = 0
        if len(set(errors.values())) > 1 or len(errors) == 1:
            winner_id = min(errors, key=errors.__getitem__)
            loser_id, loser = self._opponent(winner_id)
            # Every full 20 basis points of error subtracts 1 HP from the attack.
            damage = min(loser.hp, max(5, 30 - errors[winner_id] // 20))
            loser.hp -= damage
            self.players[winner_id].attack_damage += damage
            self._event = {
                "id": self._round_number,
                "type": "attack" if loser.hp else "ko",
                "actorId": winner_id,
                "targetId": loser_id,
                "damage": damage,
            }

        self._outcomes.append(RoundOutcome(actual_bps, self._moves, errors, winner_id, damage))
        self._revealing = True
        self._phase_ends_at = now + REVEAL_SECONDS
        if self._match_over():
            (first_id, first), (second_id, second) = self.players.items()
            if first.hp != second.hp:
                self.winner_id = first_id if first.hp > second.hp else second_id

    def _match_over(self) -> bool:
        return self._round_number == MAX_ROUNDS or any(player.hp == 0 for player in self.players.values())

    def _player(self, user_id: int) -> PredictionPlayer:
        try:
            return self.players[user_id]
        except KeyError:
            raise RuleError("Du deltar inte i den här matchen.") from None

    def _opponent(self, user_id: int) -> tuple[int, PredictionPlayer]:
        return next((other_id, player) for other_id, player in self.players.items() if other_id != user_id)

    def _countdown(self, now: float) -> int:
        return max(0, ceil(self._starts_at - now)) if self.status == "countdown" else 0

    def _remaining(self, now: float) -> int:
        if self.status == "finished":
            return 0
        return max(0, ceil(self._phase_ends_at - max(now, self._starts_at)))

    def public(self, user_id: int, now: float) -> dict:
        player = self._player(user_id)
        opponent_id, opponent = self._opponent(user_id)
        now = max(now, self._now)
        scenario = self.scenario
        return {
            "id": self.id,
            "mode": self.mode.key,
            "status": self.status,
            "roundLimit": MAX_ROUNDS,
            "countdown": self._countdown(now),
            "remaining": self._remaining(now),
            "elapsed": int(self.duration),
            "symbol": scenario.symbol,
            "name": scenario.name,
            "market": scenario.market,
            "interval": scenario.interval,
            "synthetic": scenario.synthetic,
            "price": format(self.price, "f"),
            "bars": revealed_prediction_bars(scenario, self.revealed_count),
            "self": {"id": user_id, "name": player.name, "hp": player.hp},
            "opponent": {"id": opponent_id, "name": opponent.name, "hp": opponent.hp},
            "event": self._event.copy() if self._event is not None else None,
            "round": {
                "number": self._round_number,
                "phase": "reveal" if self._revealing else "predict",
                "selfLocked": user_id in self._moves,
                "opponentLocked": opponent_id in self._moves,
                "selfMoveBps": self._moves.get(user_id),
                "outcome": self._outcomes[-1].public(user_id, opponent_id) if self._revealing else None,
            },
        }

    def summary(self, user_id: int) -> dict:
        player = self._player(user_id)
        opponent_id, opponent = self._opponent(user_id)
        end_actor = None
        if self.end_reason == "knockout":
            end_actor = "self" if self.winner_id == user_id else "opponent"
        return {
            "hp": player.hp,
            "opponentHp": opponent.hp,
            "opponentName": opponent.name,
            "endReason": self.end_reason,
            "endActor": end_actor,
            "attackDamage": player.attack_damage,
            "roundsPlayed": len(self._outcomes),
            "lastRound": self._outcomes[-1].public(user_id, opponent_id) if self._outcomes else None,
            "rounds": [
                {"number": number, **outcome.public(user_id, opponent_id)}
                for number, outcome in enumerate(self._outcomes, start=1)
            ],
        }
