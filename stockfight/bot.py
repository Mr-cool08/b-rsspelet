from random import Random

from .engine import Match, PlayerState, Position
from .ranking import STARTING_ELO


class TradingBot:
    """Trade from revealed prices with reaction times and risk tuned to Ranked Elo."""

    def __init__(self, elo: int, rng: Random) -> None:
        self.elo = elo
        self._rng = rng
        rating_offset = elo - STARTING_ELO
        self._skill = max(0.0, min(1.0, (rating_offset + 400) / 1400))
        self._last_revealed_count = 0
        self._last_close_at = float("-inf")

    def act(self, match: Match, user_id: int, now: float) -> bool:
        """Make at most one trading decision after the match advances to a new bar."""
        if match.status != "active" or match.revealed_count == self._last_revealed_count:
            return False
        self._last_revealed_count = match.revealed_count

        player = match.players[user_id]
        position = player.position
        if position is not None:
            return self._consider_close(match, user_id, player, position, now)

        rest = 5.0 - 4.0 * self._skill
        if player.cash <= 0 or match.duration - self._last_close_at < rest:
            return False

        direction, confidence = self._read_prices(match)
        if direction is None:
            action = self._rng.choice(("buy", "short"))
        elif self._rng.random() < 0.5 + self._skill * (0.2 + 0.25 * confidence):
            action = direction
        else:
            action = "short" if direction == "buy" else "buy"

        exposure = 25 + 75 * self._skill * (0.35 + 0.65 * confidence)
        percent = min(match.mode.buy_percentages, key=lambda value: abs(value - exposure))
        match.act(user_id, action, {"percent": percent}, now)
        return True

    def _consider_close(
        self, match: Match, user_id: int, player: PlayerState, position: Position, now: float
    ) -> bool:
        hold_seconds = match.duration - position.bought_at
        if hold_seconds < 2.5 - 2.0 * self._skill:
            return False

        profit = position.pnl(match.price)
        if profit < 0 and min(match.mode.loss_damage_cap, int(-profit)) >= player.hp:
            return False

        in_storm = match.duration >= match.mode.market_storm_at
        profit_target = round(16 - 9 * self._skill)
        loss_limit = max(2, round(player.hp * (0.18 - 0.12 * self._skill)))
        max_hold = 22.0 - 10.0 * self._skill
        if not (
            profit >= profit_target
            or profit <= -loss_limit
            or hold_seconds >= max_hold
            or (in_storm and profit > 0)
        ):
            return False

        quote = match.act(user_id, "sell", {}, now)
        if quote.get("requiresChoice"):
            # Build a bonus early when the profit would not yet cap an attack.
            mode = match.mode
            can_grow = (
                not in_storm
                and player.grow_bonus < mode.grow_bonus_cap * self._skill
                and profit * mode.grow_multiplier >= 2
                and profit * mode.attack_multiplier < mode.base_attack_cap
            )
            match.act(user_id, "confirm_sell", {
                "positionId": quote["positionId"],
                "choice": "grow" if can_grow else "attack",
            }, now)
        self._last_close_at = match.duration
        return True

    @staticmethod
    def _read_prices(match: Match) -> tuple[str | None, float]:
        count = match.revealed_count
        bars = match.scenario.bars[max(0, count - 7):count]
        moves = [second.close - first.close for first, second in zip(bars, bars[1:])]

        # Recent swings that repeatedly reverse favor a reversal over trend following.
        swings = moves[-4:]
        if len(swings) == 4 and all(a < 0 < b or b < 0 < a for a, b in zip(swings, swings[1:])):
            return ("short" if swings[-1] > 0 else "buy"), 1.0

        net_move = sum(moves)
        if not net_move:
            return None, 0.0
        confidence = float(abs(net_move) / sum(abs(move) for move in moves))
        return ("buy" if net_move > 0 else "short"), confidence
