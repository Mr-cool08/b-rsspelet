from datetime import UTC, datetime, timedelta
from decimal import Decimal
from random import Random

from stockfight.bot import TradingBot
from stockfight.engine import BOT, Bar, Match, Scenario


def opening_trade(elo, unrevealed_prices):
    start = datetime(2025, 1, 1, tzinfo=UTC)
    prices = tuple(Decimal(price) for price in (100, 101, 102, *unrevealed_prices))
    bars = tuple(
        Bar(start + timedelta(minutes=index), price, price, price, price, 100)
        for index, price in enumerate(prices)
    )
    scenario = Scenario("TEST", "SE", "1m", "test", True, bars, preview_count=3)
    match = Match("bot", {1: "Player", -1: "Bot"}, scenario, 0.0, countdown=0, mode=BOT)
    bot = TradingBot(elo, Random(5))

    assert bot.act(match, -1, 0.0)
    position = match.players[-1].position
    assert position is not None
    return position.side, position.invested


def test_elo_changes_the_bot_opening_decision():
    low_side, low_stake = opening_trade(600, [103, 104])
    high_side, high_stake = opening_trade(2000, [103, 104])

    assert (low_side, high_side) == ("short", "long")
    assert low_stake < high_stake


def test_unrevealed_prices_do_not_change_the_bot_opening_decision():
    assert opening_trade(2000, [103, 104]) == opening_trade(2000, [99, 98])
