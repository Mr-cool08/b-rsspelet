from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime
from decimal import ROUND_HALF_UP, Decimal
from math import ceil, floor, inf, isfinite
from typing import Literal
from uuid import uuid4

from .ranking import K_FACTOR


REGENERATION_DURATION = 20
REGENERATION_INTERVAL = 5
REGENERATION_HEALING = 2


@dataclass(frozen=True, slots=True)
class Bar:
    timestamp: datetime
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: int


@dataclass(frozen=True, slots=True)
class Scenario:
    symbol: str
    market: str
    interval: str
    source: str
    synthetic: bool
    bars: tuple[Bar, ...]
    preview_count: int
    name: str = ""


@dataclass(frozen=True, slots=True)
class GameMode:
    key: str
    starting_cash: Decimal = Decimal("500")
    starting_hp: int = 100
    allowed_actions: frozenset[str] = frozenset({"buy", "short", "sell", "confirm_sell"})
    buy_percentages: tuple[int, ...] = (25, 50, 75, 100)
    attack_multiplier: Decimal = Decimal("4")
    base_attack_cap: int = 35
    attack_cap: int = 50
    attack_power_credits_per_point: Decimal = Decimal("2.5")
    attack_power_limit: int = 25
    grow_multiplier: Decimal = Decimal("5")
    grow_bonus_cap: int = 25
    loss_damage_cap: int = 20
    market_storm_at: int = 75
    final_storm_at: int = 105
    market_storm_damage: int = 2
    final_storm_damage: int = 4
    rating_k: int = K_FACTOR
    loss_multiplier: Decimal = Decimal("2")
    regeneration_cost: Decimal | None = None

    @property
    def scenario_seconds(self) -> int:
        market_ticks = self.final_storm_at - self.market_storm_at
        remaining_hp = max(0, self.starting_hp - market_ticks * self.market_storm_damage)
        return self.final_storm_at + ceil(remaining_hp / self.final_storm_damage)

    def storm_phase(self, elapsed: int) -> str:
        if elapsed >= self.final_storm_at:
            return "final"
        if elapsed >= self.market_storm_at:
            return "market"
        return "normal"

    def attack_power(self, capital: Decimal) -> int:
        adjustment = (capital - self.starting_cash) / self.attack_power_credits_per_point
        return 100 + int(max(-self.attack_power_limit, min(self.attack_power_limit, adjustment)))

    def resolve_knockout(self, players: dict[int, PlayerState]) -> tuple[bool, int | None, str | None]:
        (first_id, first), (second_id, second) = players.items()
        if first.hp and second.hp:
            return False, None, None
        if first.hp:
            return True, first_id, None
        if second.hp:
            return True, second_id, None
        first_cents = first.capital.scaleb(2).to_integral_value(rounding=ROUND_HALF_UP)
        second_cents = second.capital.scaleb(2).to_integral_value(rounding=ROUND_HALF_UP)
        if first_cents != second_cents:
            return True, first_id if first_cents > second_cents else second_id, "capital"
        if first.attack_damage != second.attack_damage:
            return True, first_id if first.attack_damage > second.attack_damage else second_id, "attack_damage"
        return True, None, None


RANKED = GameMode(key="ranked", regeneration_cost=Decimal("10"))
BOT = replace(RANKED, key="bot", regeneration_cost=None)
PRIVATE = replace(RANKED, key="private")


class RuleError(ValueError):
    pass


PositionSide = Literal["long", "short"]


@dataclass(slots=True)
class Position:
    id: str
    entry_price: Decimal
    invested: Decimal
    shares: Decimal
    bought_at: float
    awaiting_choice: bool = False
    side: PositionSide = "long"

    def pnl(self, price: Decimal) -> Decimal:
        profit = (price - self.entry_price) * self.invested / self.entry_price
        if self.side == "short":
            return max(-self.invested, -profit)
        return profit


@dataclass(slots=True)
class Regeneration:
    started_at: float
    ticks: int = 0

    @property
    def next_tick_at(self) -> float:
        return self.started_at + (self.ticks + 1) * REGENERATION_INTERVAL

    def remaining(self, now: float) -> int:
        return max(0, ceil(REGENERATION_DURATION - (now - self.started_at)))


@dataclass(slots=True)
class PlayerState:
    name: str
    cash: Decimal
    hp: int
    peak_capital: Decimal
    position: Position | None = None
    grow_bonus: int = 0
    attack_damage: int = 0
    grow_count: int = 0
    trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    regeneration: Regeneration | None = None

    @property
    def capital(self) -> Decimal:
        if self.position is None:
            return self.cash
        return self.cash + self.position.invested


class Match:
    def __init__(
        self,
        match_id: str,
        players: dict[int, str],
        scenario: Scenario,
        now: float,
        *,
        tick_seconds: float = 1.0,
        countdown: float = 3.0,
        mode: GameMode = RANKED,
    ) -> None:
        if len(players) != 2:
            raise ValueError("En match behöver två spelare.")
        if not 1 <= scenario.preview_count <= len(scenario.bars):
            raise ValueError("Scenariot behöver minst en förhandsvisad kursstapel.")
        if any(not bar.close.is_finite() or bar.close <= 0 for bar in scenario.bars):
            raise ValueError("Scenariot behöver positiva, ändliga stängningskurser.")
        if not isfinite(tick_seconds) or tick_seconds <= 0:
            raise ValueError("Tickintervallet måste vara positivt och ändligt.")
        if not isfinite(countdown) or countdown < 0:
            raise ValueError("Nedräkningen måste vara ändlig och minst noll.")
        if not isfinite(now):
            raise ValueError("Matchens starttid måste vara ändlig.")

        self.id = match_id
        self.mode = mode
        self.scenario = scenario
        self.players = {
            user_id: PlayerState(name, mode.starting_cash, mode.starting_hp, mode.starting_cash)
            for user_id, name in players.items()
        }
        self.status = "countdown" if countdown else "active"
        self.winner_id: int | None = None
        self.end_reason: str | None = None
        self.tiebreak: str | None = None
        self.duration = 0.0
        self.trades: list[dict] = []
        self.revealed_count = scenario.preview_count
        self._tick_seconds = Decimal(str(tick_seconds))
        self._now = now
        self._starts_at = now + countdown
        self._next_storm_second = mode.market_storm_at
        self._event: dict | None = None
        self._event_id = 0

    @property
    def price(self) -> Decimal:
        return self.scenario.bars[self.revealed_count - 1].close

    def advance(self, now: float) -> bool:
        """Process due ticks and report whether a client-visible field changed."""
        if self.status == "finished" or now < self._now:
            return False
        if not isfinite(now):
            raise ValueError("Matchtiden måste vara ändlig.")

        previous_now = self._now
        self._now = now
        starting = self.status == "countdown"
        if now < self._starts_at:
            return self._countdown(now) != self._countdown(previous_now)

        self.status = "active"
        previous_second = int(self.duration)
        previous_bars = self.revealed_count
        previous_storm_tick = self._next_storm_second
        regeneration_ticked = False
        while True:
            bar_at = inf
            if self.revealed_count < len(self.scenario.bars):
                bar_number = self.revealed_count - self.scenario.preview_count + 1
                bar_at = self._starts_at + float(bar_number * self._tick_seconds)
            storm_at = self._starts_at + self._next_storm_second
            regeneration_at = min(
                (player.regeneration.next_tick_at for player in self.players.values() if player.regeneration),
                default=inf,
            )
            due = min(bar_at, storm_at, regeneration_at)
            if due > now:
                break

            if bar_at == due:
                self.revealed_count += 1
            if regeneration_at == due:
                self._apply_regeneration(due)
                regeneration_ticked = True
            if storm_at == due:
                self.duration = float(self._next_storm_second)
                self._apply_storm(self._next_storm_second)
                self._next_storm_second += 1
                if self.status == "finished":
                    return True

        self.duration = max(self.duration, now - self._starts_at)
        return (
            starting
            or int(self.duration) != previous_second
            or self.revealed_count != previous_bars
            or self._next_storm_second != previous_storm_tick
            or regeneration_ticked
            or any(
                regeneration.remaining(now) != regeneration.remaining(previous_now)
                for player in self.players.values()
                if (regeneration := player.regeneration) is not None
            )
        )

    def act(self, user_id: int, action: str, data: dict, now: float) -> dict:
        player = self._player(user_id)
        self.advance(now)
        if self.status != "active":
            raise RuleError("Matchen är inte aktiv.")
        if action == "buy_regeneration":
            self._buy_regeneration(player)
            return {}
        if action not in self.mode.allowed_actions:
            raise RuleError("Åtgärden är inte tillgänglig i spelläget.")

        if action in ("buy", "short"):
            self._open_position(player, data.get("percent"), "short" if action == "short" else "long")
            return {}
        if action not in ("sell", "confirm_sell"):
            raise RuleError("Okänd handelsåtgärd.")

        position = player.position
        if position is None:
            raise RuleError("Du har ingen position att stänga.")

        profit = position.pnl(self.price)
        choice = None
        if action == "confirm_sell":
            if not position.awaiting_choice or data.get("positionId") != position.id:
                raise RuleError("Bekräftelsen gäller inte den aktuella positionen.")
            choice = data.get("choice")
            if choice == "close" and profit > 0:
                raise RuleError("Affären visar vinst igen. Välj Attack eller Grow.")
            if choice not in ("attack", "grow", "close"):
                raise RuleError("Välj Attack eller Grow för att stänga positionen.")
        elif profit > 0:
            position.awaiting_choice = True
            return {"requiresChoice": True, "positionId": position.id}

        self._close_position(user_id, player, position, profit, choice if profit > 0 else None)
        return {}

    def _open_position(self, player: PlayerState, percent: object, side: PositionSide) -> None:
        if type(percent) is not int or percent not in self.mode.buy_percentages:
            raise RuleError("Välj 25, 50, 75 eller 100 procent.")
        if player.position is not None:
            raise RuleError("Du har redan en öppen position.")
        if player.cash <= 0:
            raise RuleError("Du har inte tillräckligt med kapital.")

        price = self.price
        invested = player.cash * (Decimal(percent) / 100)
        player.position = Position(uuid4().hex, price, invested, invested / price, self.duration, side=side)
        player.cash -= invested

    def _buy_regeneration(self, player: PlayerState) -> None:
        cost = self.mode.regeneration_cost
        if cost is None:
            raise RuleError("Åtgärden är inte tillgänglig i spelläget.")
        if player.regeneration is not None:
            raise RuleError("Regenerering är redan aktiv.")
        if player.cash < cost:
            raise RuleError("Du har inte tillräckligt med pengar.")

        player.cash -= cost
        player.regeneration = Regeneration(self._now)

    def _apply_regeneration(self, now: float) -> None:
        for player in self.players.values():
            regeneration = player.regeneration
            if regeneration is None or regeneration.next_tick_at != now:
                continue
            player.hp = min(self.mode.starting_hp, player.hp + REGENERATION_HEALING)
            regeneration.ticks += 1
            if regeneration.ticks * REGENERATION_INTERVAL >= REGENERATION_DURATION:
                player.regeneration = None

    def _attack_damage(self, player: PlayerState, target: PlayerState, profit: Decimal) -> int:
        base_damage = min(self.mode.base_attack_cap, profit * self.mode.attack_multiplier)
        damage = min(self.mode.attack_cap, base_damage + player.grow_bonus)
        power = Decimal(self.mode.attack_power(player.capital)) / 100
        return min(target.hp, floor(damage * power))

    def _grow_bonus(self, player: PlayerState, profit: Decimal) -> int:
        return min(self.mode.grow_bonus_cap - player.grow_bonus, floor(profit * self.mode.grow_multiplier))

    def _loss_damage(self, player: PlayerState, profit: Decimal) -> int:
        return min(player.hp, self.mode.loss_damage_cap, floor(-profit * self.mode.loss_multiplier))

    def _close_preview(
        self, position: Position, player: PlayerState, opponent: PlayerState, profit: Decimal
    ) -> dict | None:
        if self.status != "active" or not position.awaiting_choice:
            return None
        profitable = profit > 0
        losing = profit < 0
        return {
            "positionId": position.id,
            "kind": "profit" if profitable else "loss" if losing else "flat",
            "attackDamage": self._attack_damage(player, opponent, profit) if profitable else 0,
            "growCredits": format(profit, "f") if profitable else "0",
            "growBonus": self._grow_bonus(player, profit) if profitable else 0,
            "lossCredits": format(-profit, "f") if losing else "0",
            "lossDamage": self._loss_damage(player, profit) if losing else 0,
        }

    def _close_position(
        self,
        user_id: int,
        player: PlayerState,
        position: Position,
        profit: Decimal,
        choice: str | None,
    ) -> None:
        damage = 0
        target_id = user_id
        event_type = choice
        proceeds = position.invested + profit
        if choice == "attack":
            target_id, target = self._opponent(user_id)
            damage = self._attack_damage(player, target, profit)
            player.grow_bonus = 0
            player.attack_damage += damage
            target.hp -= damage
            proceeds = position.invested
        elif choice == "grow":
            player.grow_bonus += self._grow_bonus(player, profit)
            player.grow_count += 1
        elif profit < 0:
            event_type = "loss"
            damage = self._loss_damage(player, profit)
            player.grow_bonus = 0
            player.hp -= damage

        player.cash += proceeds
        player.position = None
        player.peak_capital = max(player.peak_capital, player.cash)
        player.trades += 1
        player.winning_trades += int(profit > 0)
        player.losing_trades += int(profit < 0)
        self.trades.append(
            {
                "user_id": user_id,
                "side": position.side,
                "bought_at": position.bought_at,
                "sold_at": self.duration,
                "buy_price": position.entry_price,
                "sell_price": self.price,
                "invested": position.invested,
                "profit": profit,
                "choice": event_type or "flat",
                "damage": damage,
            }
        )
        reason = "trade_loss" if event_type == "loss" else event_type
        if self._finish_if_knocked_out(user_id, target_id, damage, reason):
            return
        if event_type is not None:
            self._record_event(event_type, user_id, target_id, damage)

    def _apply_storm(self, elapsed: int) -> None:
        final = elapsed >= self.mode.final_storm_at
        damage = self.mode.final_storm_damage if final else self.mode.market_storm_damage
        for player in self.players.values():
            player.hp = max(0, player.hp - damage)
        self._finish_if_knocked_out(None, None, damage, "final_storm" if final else "market_storm")

    def _finish_if_knocked_out(
        self, actor_id: int | None, target_id: int | None, damage: int, reason: str | None
    ) -> bool:
        finished, winner_id, tiebreak = self.mode.resolve_knockout(self.players)
        if not finished:
            return False
        self.winner_id = winner_id
        self.end_reason = reason
        self.tiebreak = tiebreak
        if winner_id is not None and self.players[winner_id].hp:
            target_id, _ = self._opponent(winner_id)
        self.status = "finished"
        self._record_event("ko", actor_id, target_id, damage)
        return True

    def _record_event(
        self, event_type: str, actor_id: int | None, target_id: int | None, damage: int
    ) -> None:
        self._event_id += 1
        self._event = {
            "id": self._event_id,
            "type": event_type,
            "actorId": actor_id,
            "targetId": target_id,
            "damage": damage,
        }

    def _player(self, user_id: int) -> PlayerState:
        try:
            return self.players[user_id]
        except KeyError:
            raise RuleError("Du deltar inte i den här matchen.") from None

    def _opponent(self, user_id: int) -> tuple[int, PlayerState]:
        return next((other_id, player) for other_id, player in self.players.items() if other_id != user_id)

    def _countdown(self, now: float) -> int:
        return max(0, ceil(self._starts_at - now))

    def _remaining(self, elapsed: int, phase: str) -> int:
        if self.status == "finished":
            return 0
        if phase == "normal":
            return self.mode.market_storm_at - elapsed
        if phase == "market":
            return self.mode.final_storm_at - elapsed
        return ceil(min(player.hp for player in self.players.values()) / self.mode.final_storm_damage)

    def _shared_state(self, now: float) -> dict:
        elapsed = int(self.duration)
        phase = self.mode.storm_phase(elapsed)
        scenario = self.scenario
        return {
            "id": self.id,
            "mode": self.mode.key,
            "status": self.status,
            "elapsed": elapsed,
            "countdown": self._countdown(max(now, self._now)) if self.status == "countdown" else 0,
            "storm": phase,
            "remaining": self._remaining(elapsed, phase),
            "symbol": scenario.symbol,
            "name": scenario.name,
            "market": scenario.market,
            "interval": scenario.interval,
            "synthetic": scenario.synthetic,
            "price": format(self.price, "f"),
            "bars": [
                {
                    "time": index - (scenario.preview_count - 1),
                    "open": format(bar.open, "f"),
                    "high": format(bar.high, "f"),
                    "low": format(bar.low, "f"),
                    "close": format(bar.close, "f"),
                }
                for index, bar in enumerate(scenario.bars[: self.revealed_count])
            ],
            "event": self._event.copy() if self._event is not None else None,
        }

    def public(self, user_id: int, now: float) -> dict:
        player = self._player(user_id)
        opponent_id, opponent = self._opponent(user_id)
        position = player.position
        public_position = None
        if position is not None:
            profit = position.pnl(self.price)
            public_position = {
                "side": position.side,
                "entryPrice": format(position.entry_price, "f"),
                "invested": format(position.invested, "f"),
                "pnl": format(profit, "f"),
                "closePreview": self._close_preview(position, player, opponent, profit),
            }
        state = {
            **self._shared_state(now),
            "self": {
                "id": user_id,
                "name": player.name,
                "hp": player.hp,
                "cash": format(player.cash, "f"),
                "capital": format(player.capital, "f"),
                "attackPower": self.mode.attack_power(player.capital),
                "growBonus": player.grow_bonus,
                "attackDamage": player.attack_damage,
                "position": public_position,
            },
            "opponent": {
                "id": opponent_id,
                "name": opponent.name,
                "hp": opponent.hp,
                "capital": format(opponent.capital, "f"),
                "hasPosition": opponent.position is not None,
                "growBonus": opponent.grow_bonus,
            },
        }
        if self.mode.regeneration_cost is not None:
            state["regeneration"] = {
                "cost": format(self.mode.regeneration_cost, "f"),
                "duration": REGENERATION_DURATION,
                "interval": REGENERATION_INTERVAL,
                "healing": REGENERATION_HEALING,
            }
            state["self"]["regenerationRemaining"] = (
                player.regeneration.remaining(self._now)
                if self.status == "active" and player.regeneration is not None else 0
            )
        return state

    def spectator_state(self, now: float) -> dict:
        state = self._shared_state(now)
        state["players"] = [
            {
                "id": user_id,
                "name": player.name,
                "hp": player.hp,
                "capital": format(player.capital, "f"),
                "hasPosition": player.position is not None,
                "growBonus": player.grow_bonus,
            }
            for user_id, player in self.players.items()
        ]
        if self.status == "finished":
            state.update(winnerId=self.winner_id, endReason=self.end_reason)
        return state

    def summary(self, user_id: int) -> dict:
        player = self._player(user_id)
        opponent_id, opponent = self._opponent(user_id)
        end_actor_id = self._event["actorId"] if self.status == "finished" and self._event else None
        end_actor = "self" if end_actor_id == user_id else "opponent" if end_actor_id == opponent_id else None
        return {
            "hp": player.hp,
            "opponentHp": opponent.hp,
            "endReason": self.end_reason,
            "endActor": end_actor,
            "tiebreak": self.tiebreak,
            "capital": format(player.capital, "f"),
            "opponentCapital": format(opponent.capital, "f"),
            "attackDamage": player.attack_damage,
            "growCount": player.grow_count,
            "trades": player.trades,
            "winningTrades": player.winning_trades,
            "losingTrades": player.losing_trades,
            "peakCapital": format(player.peak_capital, "f"),
            "tradeDetails": [
                {
                    "time": trade["sold_at"],
                    "side": trade["side"],
                    "choice": trade["choice"],
                    "profit": format(trade["profit"], "f"),
                    "damage": trade["damage"],
                }
                for trade in self.trades
                if trade["user_id"] == user_id
            ],
        }
