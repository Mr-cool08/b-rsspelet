import json
import unittest
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from stockfight.engine import Bar, Match, RANKED, RuleError, Scenario


START = 1000.0
PLAYERS = {1: "Ines", 2: "Sam"}


def make_scenario(prices, preview_count=1):
    first_bar = datetime(2025, 1, 1, tzinfo=timezone.utc)
    bars = tuple(
        Bar(first_bar + timedelta(minutes=index), price, price, price, price, 100)
        for index, price in enumerate(map(Decimal, prices))
    )
    return Scenario("TEST", "Test Market", "1m", "test", True, bars, preview_count, "Test Co")


def make_match(*prices, tick_seconds=1.0, preview_count=1):
    match = Match(
        "test-match",
        PLAYERS,
        make_scenario(prices, preview_count),
        START,
        tick_seconds=tick_seconds,
        countdown=0,
    )
    match.advance(START)
    return match


def act(match, action, elapsed, data=None, user_id=1):
    now = START + elapsed
    match.advance(now)
    return match.act(user_id, action, data or {}, now)


def request_sale(match, elapsed, user_id=1):
    return act(match, "sell", elapsed, user_id=user_id)


def confirm_sale(match, elapsed, choice, position_id, user_id=1):
    return act(
        match,
        "confirm_sell",
        elapsed,
        {"choice": choice, "positionId": position_id},
        user_id=user_id,
    )


class MatchTests(unittest.TestCase):
    def test_countdown_and_replay_include_preview_but_hide_later_prices(self):
        scenario = make_scenario(("90", "100", "101", "103", "105"), preview_count=2)
        match = Match("replay", PLAYERS, scenario, START, tick_seconds=2.0)
        initial = match.public(1, START)

        self.assertEqual(match.id, "replay")
        self.assertIs(match.mode, RANKED)
        self.assertEqual(match.mode.key, "ranked")
        self.assertEqual(initial["status"], "countdown")
        self.assertEqual(initial["countdown"], 3)
        self.assertEqual(initial["price"], "100")
        self.assertEqual(initial["self"]["id"], 1)
        self.assertEqual(initial["opponent"]["id"], 2)
        self.assertEqual(initial["self"]["hp"], 100)
        self.assertEqual(initial["self"]["cash"], "500")
        self.assertEqual(initial["self"]["capital"], "500")
        self.assertEqual(initial["self"]["attackPower"], 100)
        self.assertEqual(initial["opponent"]["capital"], "500")
        self.assertEqual([bar["close"] for bar in initial["bars"]], ["90", "100"])
        for public_bar, source_bar in zip(initial["bars"], scenario.bars, strict=False):
            self.assertEqual(set(public_bar), {"time", "open", "high", "low", "close"})
            self.assertIsInstance(public_bar["time"], int)
            self.assertNotEqual(public_bar["time"], int(source_bar.timestamp.timestamp()))
        with self.assertRaises(RuleError):
            act(match, "buy", 2.5, {"percent": 25})

        self.assertTrue(match.advance(START + 3))
        active = match.public(2, START + 3)
        self.assertEqual(active["status"], "active")
        self.assertEqual(active["elapsed"], 0)
        self.assertEqual(active["price"], "100")
        self.assertEqual(active["self"]["id"], 2)
        self.assertEqual(active["opponent"]["id"], 1)
        self.assertEqual(match.revealed_count, 2)

        self.assertTrue(match.advance(START + 7))
        replay = match.public(1, START + 7)
        self.assertEqual(replay["elapsed"], 4)
        self.assertEqual(replay["price"], "103")
        self.assertEqual([bar["close"] for bar in replay["bars"]], ["90", "100", "101", "103"])
        self.assertEqual(match.revealed_count, 4)
        json.dumps(replay)

    def test_fractional_tick_reveals_bar_at_intended_time(self):
        scenario = make_scenario(("100", "101", "102", "103"))
        match = Match("fractional", PLAYERS, scenario, 0.0, tick_seconds=0.1, countdown=0)

        match.advance(0.2999)
        self.assertEqual(match.revealed_count, 3)
        match.advance(0.3)
        self.assertEqual(match.revealed_count, 4)
        self.assertEqual(match.public(1, 0.3)["price"], "103")

    def test_purchase_percentages_use_fractional_shares(self):
        for percent in (25, 50, 75, 100):
            with self.subTest(percent=percent):
                match = make_match("128", "160")
                invested = Decimal(5 * percent)
                act(match, "buy", 0, {"percent": percent})
                match.advance(START + 1)
                state = match.public(1, START + 1)["self"]

                self.assertEqual(Decimal(state["cash"]), 500 - invested)
                self.assertEqual(Decimal(state["position"]["entryPrice"]), 128)
                self.assertEqual(Decimal(state["position"]["invested"]), invested)
                self.assertEqual(Decimal(state["position"]["pnl"]), invested / 4)
                self.assertTrue(match.public(2, START + 1)["opponent"]["hasPosition"])

    def test_purchase_rejects_invalid_percentage_and_insufficient_cash(self):
        match = make_match("100")
        with self.assertRaises(RuleError):
            act(match, "buy", 0, {"percent": 26})
        self.assertIsNone(match.public(1, START)["self"]["position"])

        match.players[1].cash = Decimal("0")
        with self.assertRaises(RuleError):
            act(match, "buy", 0, {"percent": 25})
        self.assertIsNone(match.public(1, START)["self"]["position"])

    def test_rejects_empty_sale_and_second_position(self):
        match = make_match("100", "101")
        with self.assertRaises(RuleError):
            request_sale(match, 0)
        act(match, "buy", 0, {"percent": 25})
        with self.assertRaises(RuleError):
            act(match, "buy", 0, {"percent": 25})

        sale = request_sale(match, 1)
        self.assertTrue(sale["requiresChoice"])
        with self.assertRaises(RuleError):
            act(match, "buy", 1, {"percent": 25})
        self.assertEqual(len(match.trades), 0)
        self.assertIsNotNone(match.public(1, START + 1)["self"]["position"])

    def test_short_position_grows_capital_during_a_falling_market(self):
        match = make_match("100", "98", "95")
        act(match, "short", 0, {"percent": 25})
        act(match, "buy", 0, {"percent": 25}, user_id=2)
        with self.assertRaises(RuleError):
            act(match, "buy", 0, {"percent": 25})
        with self.assertRaises(RuleError):
            act(match, "short", 0, {"percent": 25}, user_id=2)

        match.advance(START + 1)
        short = match.public(1, START + 1)["self"]["position"]
        long = match.public(2, START + 1)["self"]["position"]
        self.assertEqual((short["side"], long["side"]), ("short", "long"))
        self.assertEqual(Decimal(short["pnl"]), Decimal("2.5"))
        self.assertEqual(Decimal(long["pnl"]), Decimal("-2.5"))

        sale = request_sale(match, 1)
        self.assertTrue(sale["requiresChoice"])
        confirm_sale(match, 2, "grow", sale["positionId"])

        state = match.public(1, START + 2)["self"]
        self.assertIsNone(state["position"])
        self.assertEqual(Decimal(state["cash"]), Decimal("506.25"))
        self.assertEqual(state["growBonus"], 25)
        self.assertEqual(state["hp"], 100)

    def test_short_confirmation_after_price_spike_cannot_lose_more_than_stake(self):
        for percent in (25, 100):
            with self.subTest(percent=percent):
                match = make_match("100", "98", "250")
                invested = Decimal(5 * percent)
                act(match, "short", 0, {"percent": percent})
                sale = request_sale(match, 1)
                self.assertTrue(sale["requiresChoice"])

                match.advance(START + 2)
                position = match.public(1, START + 2)["self"]["position"]
                self.assertEqual(Decimal(position["pnl"]), -invested)
                confirm_sale(match, 2, "attack", sale["positionId"])

                state = match.public(1, START + 2)
                self.assertIsNone(state["self"]["position"])
                self.assertEqual(Decimal(state["self"]["cash"]), 500 - invested)
                self.assertEqual(state["self"]["hp"], 80)
                self.assertEqual(state["opponent"]["hp"], 100)
                self.assertEqual(state["event"]["type"], "loss")
                self.assertEqual(match.trades[-1]["profit"], -invested)

    def test_attack_spends_profit_and_applies_floored_damage(self):
        match = make_match("100", "101.1")
        act(match, "buy", 0.25, {"percent": 25})
        match.advance(START + 1)
        self.assertEqual(match.public(2, START + 1)["self"]["hp"], 100)
        sale = request_sale(match, 1.25)
        self.assertTrue(sale["requiresChoice"])
        self.assertIsInstance(sale["positionId"], str)
        self.assertTrue(sale["positionId"])

        confirm_sale(match, 1.5, "attack", sale["positionId"])
        state = match.public(1, START + 1.5)
        self.assertEqual(Decimal(state["self"]["cash"]), 500)
        self.assertEqual(state["self"]["attackDamage"], 5)
        self.assertEqual(state["opponent"]["hp"], 95)
        self.assertIsNone(state["self"]["position"])
        self.assertEqual(state["event"]["type"], "attack")
        self.assertEqual(state["event"]["actorId"], 1)
        self.assertEqual(state["event"]["targetId"], 2)
        self.assertEqual(state["event"]["damage"], 5)
        self.assertEqual(match.trades, [
            {
                "user_id": 1,
                "side": "long",
                "bought_at": 0.25,
                "sold_at": 1.5,
                "buy_price": Decimal("100"),
                "sell_price": Decimal("101.1"),
                "invested": Decimal("125"),
                "profit": Decimal("1.375"),
                "choice": "attack",
                "damage": 5,
            }
        ])

    def test_growth_accumulates_bonus_then_capped_attack_spends_it(self):
        match = make_match("100", "100.8", "101.304", "101.81052", "111.991572")
        expected = ((25, "501", 5), (100, "503.505", 17), (100, "506.022525", 25))
        for elapsed, (percent, cash, bonus) in enumerate(expected, start=1):
            act(match, "buy", elapsed - 1, {"percent": percent})
            sale = request_sale(match, elapsed)
            confirm_sale(match, elapsed, "grow", sale["positionId"])
            state = match.public(1, START + elapsed)
            self.assertEqual(Decimal(state["self"]["cash"]), Decimal(cash))
            self.assertEqual(state["self"]["growBonus"], bonus)
            self.assertEqual(state["opponent"]["hp"], 100)

        act(match, "buy", 3, {"percent": 100})
        sale = request_sale(match, 4)
        confirm_sale(match, 4, "attack", sale["positionId"])
        state = match.public(1, START + 4)
        self.assertEqual(state["self"]["growBonus"], 0)
        self.assertEqual(Decimal(state["self"]["cash"]), Decimal("506.022525"))
        self.assertEqual(state["self"]["attackDamage"], 51)
        self.assertEqual(state["opponent"]["hp"], 49)
        stats = match.summary(1)
        self.assertEqual(stats["hp"], 100)
        self.assertEqual(stats["attackDamage"], 51)
        self.assertEqual(stats["growCount"], 3)
        self.assertEqual(stats["trades"], 4)
        self.assertEqual(stats["winningTrades"], 4)
        self.assertEqual(stats["losingTrades"], 0)
        self.assertIsInstance(stats["capital"], str)
        self.assertEqual(Decimal(stats["capital"]), Decimal("506.022525"))
        self.assertGreaterEqual(Decimal(stats["peakCapital"]), Decimal(stats["capital"]))

    def test_realized_capital_scales_attack_preview_and_damage_with_all_cash_invested(self):
        match = make_match("100", "105", "107.1")
        act(match, "buy", 0, {"percent": 100})
        act(match, "short", 0, {"percent": 100}, user_id=2)
        sale = request_sale(match, 1)
        confirm_sale(match, 1, "grow", sale["positionId"])
        request_sale(match, 1, user_id=2)
        act(match, "buy", 1, {"percent": 100})
        act(match, "buy", 1, {"percent": 100}, user_id=2)

        for user_id, capital, attack_power, preview_damage in ((1, 525, 110, 55), (2, 475, 90, 31)):
            with self.subTest(user_id=user_id):
                sale = request_sale(match, 2, user_id=user_id)
                state = match.public(user_id, START + 2)
                self.assertEqual(Decimal(state["self"]["cash"]), 0)
                self.assertEqual(Decimal(state["self"]["capital"]), capital)
                self.assertEqual(state["self"]["attackPower"], attack_power)
                self.assertEqual(state["self"]["position"]["closePreview"]["attackDamage"], preview_damage)
                confirm_sale(match, 2, "attack", sale["positionId"], user_id=user_id)
                self.assertEqual(match.trades[-1]["damage"], preview_damage)
                self.assertEqual(Decimal(match.public(user_id, START + 2)["self"]["cash"]), capital)

    def test_attack_power_changes_at_whole_steps_and_is_bounded(self):
        for price, stronger, weaker in (("100.499", 100, 100), ("100.5", 101, 99), ("130", 125, 75)):
            with self.subTest(price=price):
                match = make_match("100", price)
                act(match, "buy", 0, {"percent": 100})
                act(match, "short", 0, {"percent": 100}, user_id=2)
                sale = request_sale(match, 1)
                confirm_sale(match, 1, "grow", sale["positionId"])
                request_sale(match, 1, user_id=2)
                self.assertEqual(match.public(1, START + 1)["self"]["attackPower"], stronger)
                self.assertEqual(match.public(2, START + 1)["self"]["attackPower"], weaker)

    def test_pending_close_preview_follows_price_and_is_private(self):
        match = make_match("100", "102.4", "106", "100", "101", "95")
        match.players[1].grow_bonus = 21
        match.players[2].hp = 12
        act(match, "buy", 0, {"percent": 25})
        act(match, "buy", 0, {"percent": 25}, user_id=2)
        self.assertIsNone(match.public(1, START)["self"]["position"]["closePreview"])

        sale = request_sale(match, 1)
        state = match.public(1, START + 1)
        preview = state["self"]["position"]["closePreview"]
        self.assertEqual(preview["positionId"], sale["positionId"])
        self.assertEqual(preview["kind"], "profit")
        self.assertEqual(preview["attackDamage"], 12)
        self.assertEqual(Decimal(preview["growCredits"]), 3)
        self.assertEqual(preview["growBonus"], 4)
        opponent_view = match.public(2, START + 1)
        self.assertNotIn("closePreview", opponent_view["opponent"])
        self.assertIsNone(opponent_view["self"]["position"]["closePreview"])

        match.advance(START + 2)
        preview = match.public(1, START + 2)["self"]["position"]["closePreview"]
        self.assertEqual(Decimal(preview["growCredits"]), Decimal("7.5"))
        self.assertEqual(preview["positionId"], sale["positionId"])
        match.advance(START + 3)
        preview = match.public(1, START + 3)["self"]["position"]["closePreview"]
        self.assertEqual(preview["kind"], "flat")
        self.assertEqual(preview["lossDamage"], 0)
        with self.assertRaisesRegex(RuleError, "visar vinst igen"):
            confirm_sale(match, 4, "close", preview["positionId"])
        self.assertEqual(match.public(1, START + 4)["self"]["position"]["closePreview"]["kind"], "profit")
        match.advance(START + 5)
        preview = match.public(1, START + 5)["self"]["position"]["closePreview"]
        self.assertEqual(preview["kind"], "loss")
        self.assertEqual(Decimal(preview["lossCredits"]), Decimal("6.25"))
        self.assertEqual(preview["lossDamage"], 12)
        self.assertEqual(preview["attackDamage"], 0)
        confirm_sale(match, 5, "close", preview["positionId"])
        player = match.public(1, START + 5)["self"]
        self.assertEqual(player["hp"], 88)
        self.assertEqual(Decimal(player["cash"]), Decimal("493.75"))
        self.assertIsNone(player["position"])

    def test_attack_without_bonus_caps_base_damage_and_knocks_out_immediately(self):
        match = make_match("100", "200", "100", "200", "100", "200", "999")
        for sell_at, hp_after_attack in ((1, 65), (3, 30), (5, 0)):
            act(match, "buy", sell_at - 1, {"percent": 100})
            sale = request_sale(match, sell_at)
            confirm_sale(match, sell_at, "attack", sale["positionId"])
            state = match.public(1, START + sell_at)
            self.assertEqual(state["opponent"]["hp"], hp_after_attack)

        self.assertEqual(match.status, "finished")
        self.assertEqual(match.winner_id, 1)
        self.assertEqual(match.duration, 5.0)
        self.assertEqual(state["event"]["type"], "ko")
        self.assertEqual(state["self"]["attackDamage"], 100)
        winner = match.summary(1)
        loser = match.summary(2)
        self.assertEqual(winner["endReason"], "attack")
        self.assertIsNone(winner["tiebreak"])
        self.assertEqual((winner["endActor"], loser["endActor"]), ("self", "opponent"))
        self.assertEqual((winner["opponentHp"], loser["opponentHp"]), (0, 100))
        self.assertEqual([trade["time"] for trade in winner["tradeDetails"]], [1, 3, 5])
        self.assertEqual([trade["damage"] for trade in winner["tradeDetails"]], [35, 35, 30])
        self.assertEqual(loser["tradeDetails"], [])
        with self.assertRaises(RuleError):
            act(match, "buy", 6, {"percent": 25})
        self.assertEqual(match.public(1, START + 6)["price"], "200")

    def test_zero_closes_position_and_preserves_bonus_then_loss_clears_it(self):
        match = make_match("100", "101", "101", "98.98")
        act(match, "buy", 0, {"percent": 100})
        sale = request_sale(match, 1)
        confirm_sale(match, 1, "grow", sale["positionId"])

        act(match, "buy", 1, {"percent": 100})
        self.assertFalse(request_sale(match, 2).get("requiresChoice"))
        breakeven = match.public(1, START + 2)["self"]
        self.assertIsNone(breakeven["position"])
        self.assertEqual(breakeven["growBonus"], 25)
        self.assertEqual(breakeven["hp"], 100)
        self.assertEqual(Decimal(breakeven["cash"]), Decimal("505"))
        self.assertEqual(match.trades[-1]["choice"], "flat")

        act(match, "buy", 2, {"percent": 100})
        self.assertFalse(request_sale(match, 3).get("requiresChoice"))
        state = match.public(1, START + 3)
        self.assertIsNone(state["self"]["position"])
        self.assertEqual(state["self"]["growBonus"], 0)
        self.assertEqual(state["self"]["hp"], 80)
        self.assertEqual(state["event"]["type"], "loss")
        self.assertEqual(Decimal(state["self"]["cash"]), Decimal("494.9"))
        self.assertEqual(match.trades[-1]["profit"], Decimal("-10.1"))
        self.assertEqual(match.trades[-1]["choice"], "loss")
        self.assertEqual(match.trades[-1]["damage"], 20)
        self.assertEqual(match.summary(1)["losingTrades"], 1)

    def test_losing_sale_applies_floored_damage_and_can_knock_out_seller(self):
        match = make_match("100", "98.7")
        act(match, "buy", 0, {"percent": 25})
        request_sale(match, 1)
        self.assertEqual(match.trades[-1]["damage"], 3)
        self.assertEqual(match.public(1, START + 1)["self"]["hp"], 97)

        match = make_match("100", "80", "64", "51.2", "40.96", "32.768")
        for elapsed in range(1, 6):
            act(match, "buy", elapsed - 1, {"percent": 100})
            request_sale(match, elapsed)

        self.assertEqual(match.status, "finished")
        self.assertEqual(match.winner_id, 2)
        self.assertEqual(match.duration, 5.0)
        self.assertEqual(match.public(1, START + 5)["self"]["hp"], 0)
        self.assertEqual(match.summary(1)["endReason"], "trade_loss")
        self.assertEqual(match.summary(1)["endActor"], "self")

    def test_confirmation_uses_current_higher_price_and_rejects_stale_nonce(self):
        match = make_match("100", "104", "108", "112")
        act(match, "buy", 0, {"percent": 100})
        first_sale = request_sale(match, 1)
        with self.assertRaises(RuleError):
            confirm_sale(match, 1, "grow", "wrong-position")
        confirm_sale(match, 2, "grow", first_sale["positionId"])
        self.assertEqual(match.trades[-1]["sell_price"], 108)
        self.assertEqual(match.trades[-1]["profit"], 40)
        self.assertEqual(Decimal(match.public(1, START + 2)["self"]["cash"]), 540)

        act(match, "buy", 2, {"percent": 25})
        second_sale = request_sale(match, 3)
        self.assertNotEqual(first_sale["positionId"], second_sale["positionId"])
        with self.assertRaises(RuleError):
            confirm_sale(match, 3, "attack", first_sale["positionId"])
        self.assertIsNotNone(match.public(1, START + 3)["self"]["position"])
        confirm_sale(match, 3, "attack", second_sale["positionId"])
        self.assertEqual(len(match.trades), 2)

    def test_confirmation_applies_loss_rules_on_price_reversal(self):
        match = make_match("100", "120", "95")
        act(match, "buy", 0, {"percent": 100})
        sale = request_sale(match, 1)
        confirm_sale(match, 2, "attack", sale["positionId"])
        state = match.public(1, START + 2)
        self.assertEqual(match.trades[-1]["sell_price"], 95)
        self.assertEqual(match.trades[-1]["profit"], -25)
        self.assertEqual(match.trades[-1]["choice"], "loss")
        self.assertEqual(Decimal(state["self"]["cash"]), 475)
        self.assertEqual(state["self"]["hp"], 80)
        self.assertEqual(state["self"]["attackDamage"], 0)
        self.assertEqual(state["opponent"]["hp"], 100)
        self.assertEqual(state["event"]["type"], "loss")
        self.assertIsNone(state["self"]["position"])

    def test_confirmation_at_breakeven_keeps_saved_bonus(self):
        match = make_match("100", "101", "102", "101")
        act(match, "buy", 0, {"percent": 100})
        sale = request_sale(match, 1)
        confirm_sale(match, 1, "grow", sale["positionId"])
        act(match, "buy", 1, {"percent": 100})
        sale = request_sale(match, 2)
        confirm_sale(match, 3, "attack", sale["positionId"])
        state = match.public(1, START + 3)

        self.assertEqual(match.trades[-1]["profit"], 0)
        self.assertEqual(match.trades[-1]["choice"], "flat")
        self.assertEqual(state["self"]["growBonus"], 25)
        self.assertEqual(state["self"]["hp"], 100)
        self.assertEqual(state["opponent"]["hp"], 100)
        self.assertEqual(Decimal(state["self"]["cash"]), 505)
        self.assertIsNone(state["self"]["position"])

    def test_storm_uses_whole_seconds_and_hits_both_players(self):
        match = make_match("100", tick_seconds=2.5)
        expected = (
            (74.99, "normal", 100),
            (75.0, "market", 98),
            (75.99, "market", 98),
            (77.0, "market", 94),
            (104.99, "market", 40),
            (105.0, "final", 36),
            (107.0, "final", 28),
        )
        for elapsed, phase, hp in expected:
            with self.subTest(elapsed=elapsed):
                match.advance(START + elapsed)
                state = match.public(1, START + elapsed)
                self.assertEqual(state["storm"], phase)
                self.assertEqual(state["self"]["hp"], hp)
                self.assertEqual(state["opponent"]["hp"], hp)

    def test_skipped_updates_match_stepped_replay_at_simultaneous_draw(self):
        prices = tuple(str(100 + index) for index in range(160))
        fast = make_match(*prices, tick_seconds=2.0)
        stepped = make_match(*prices, tick_seconds=2.0)
        self.assertTrue(fast.advance(START + 150))
        for elapsed in range(1, 151):
            stepped.advance(START + elapsed)

        self.assertEqual(fast.status, "finished")
        self.assertIsNone(fast.winner_id)
        self.assertEqual(fast.duration, 114.0)
        self.assertLess(fast.revealed_count, len(prices))
        summary = fast.summary(1)
        self.assertEqual(summary["endReason"], "final_storm")
        self.assertIsNone(summary["endActor"])
        self.assertIsNone(summary["tiebreak"])
        self.assertEqual((summary["hp"], summary["opponentHp"]), (0, 0))
        state = fast.public(1, START + 150)
        self.assertEqual(state["self"]["hp"], 0)
        self.assertEqual(state["opponent"]["hp"], 0)
        stepped_state = stepped.public(1, START + 150)
        self.assertEqual(state["bars"], stepped_state["bars"])
        self.assertEqual(state["elapsed"], stepped_state["elapsed"])
        self.assertEqual(state["self"], stepped_state["self"])
        self.assertEqual(state["opponent"], stepped_state["opponent"])
        self.assertEqual(fast.status, stepped.status)
        self.assertEqual(fast.winner_id, stepped.winner_id)
        self.assertFalse(fast.advance(START + 200))
        self.assertEqual(state, fast.public(1, START + 200))

    def test_simultaneous_storm_knockout_favors_higher_capital_over_attack_damage(self):
        match = make_match("100", "100.8", "99.1872")
        act(match, "buy", 0, {"percent": 25})
        sale = request_sale(match, 1)
        confirm_sale(match, 1, "attack", sale["positionId"])
        act(match, "buy", 1, {"percent": 25})
        request_sale(match, 2)
        before_storm = match.public(1, START + 2)
        self.assertEqual(before_storm["self"]["hp"], 96)
        self.assertEqual(before_storm["opponent"]["hp"], 96)
        self.assertEqual(before_storm["self"]["attackDamage"], 4)

        match.advance(START + 150)
        state = match.public(1, START + 150)
        self.assertEqual(state["self"]["hp"], 0)
        self.assertEqual(state["opponent"]["hp"], 0)
        self.assertEqual(match.status, "finished")
        self.assertEqual(match.duration, 113.0)
        self.assertEqual(match.winner_id, 2)
        for user_id, capital, opponent_capital in ((1, 498, 500), (2, 500, 498)):
            summary = match.summary(user_id)
            self.assertEqual(Decimal(summary["capital"]), capital)
            self.assertEqual(Decimal(summary["opponentCapital"]), opponent_capital)
            self.assertEqual(summary["tiebreak"], "capital")

    def test_simultaneous_storm_knockout_uses_attack_damage_when_capital_ties(self):
        match = make_match("100", "100.2")
        act(match, "buy", 0, {"percent": 25})
        sale = request_sale(match, 1)
        confirm_sale(match, 1, "attack", sale["positionId"])
        self.assertEqual(match.trades[-1]["damage"], 1)

        match.advance(START + 150)
        summary = match.summary(1)
        self.assertEqual((summary["hp"], summary["opponentHp"]), (0, 0))
        self.assertEqual(match.winner_id, 1)
        self.assertEqual(summary["tiebreak"], "attack_damage")

    def test_simultaneous_storm_knockout_rounds_capital_to_cents_without_open_pnl(self):
        for price, winner, tiebreak in (("100.0008", None, None), ("100.001", 1, "capital")):
            with self.subTest(price=price):
                match = make_match("100", price, "110")
                act(match, "buy", 0, {"percent": 100})
                sale = request_sale(match, 1)
                confirm_sale(match, 1, "grow", sale["positionId"])
                act(match, "buy", 1, {"percent": 100})

                match.advance(START + 150)
                self.assertEqual(match.winner_id, winner)
                self.assertEqual(match.summary(1)["tiebreak"], tiebreak)


if __name__ == "__main__":
    unittest.main()
