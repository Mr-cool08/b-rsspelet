from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from stockfight.engine import Bar, RuleError, Scenario
from stockfight.prediction import MAX_MOVE_BPS, MAX_ROUNDS, PREDICT_SECONDS, REVEAL_SECONDS, PredictionMatch


def make_match(*future_prices, countdown=3):
    last_price = future_prices[-1] if future_prices else "100"
    prices = ("98", "100", *future_prices, *([last_price] * (MAX_ROUNDS - len(future_prices))))
    first_bar_time = datetime(2020, 1, 1, tzinfo=UTC)
    bars = tuple(
        Bar(first_bar_time + timedelta(minutes=index), price, price, price, price, 100)
        for index, price in enumerate(map(Decimal, prices))
    )
    scenario = Scenario("TEST", "SE", "1m", "test fixture", True, bars, 2)
    return PredictionMatch("match-id", {1: "First", 2: "Second"}, scenario, 0, countdown=countdown)


def test_countdown_private_predictions_reveal_and_next_round():
    match = make_match("103", "105.06")
    preview = match.public(1, 0)
    assert preview["countdown"] == 3
    assert preview["roundLimit"] == MAX_ROUNDS
    assert preview["bars"] == [{"time": -1, "close": "98"}, {"time": 0, "close": "100"}]
    with pytest.raises(RuleError):
        match.submit(1, 1, 200, 2.99)

    match.submit(1, 1, 200, 3)
    assert match.public(1, 3)["round"]["selfMoveBps"] == 200
    private = match.public(2, 3)
    assert private["remaining"] == PREDICT_SECONDS
    assert private["round"] == {
        "number": 1, "phase": "predict", "selfLocked": False, "opponentLocked": True,
        "selfMoveBps": None, "outcome": None,
    }
    assert private["bars"] == preview["bars"]
    assert "rounds" not in private
    assert private["opponent"]["hp"] == 100
    with pytest.raises(RuleError):
        match.submit(1, 1, 300, 4)

    match.submit(2, 1, 0, 5)
    reveal = match.public(1, 5)
    assert reveal["remaining"] == REVEAL_SECONDS
    assert reveal["bars"][-1] == {"time": 1, "close": "103"}
    assert reveal["opponent"]["hp"] == 75
    assert reveal["round"]["phase"] == "reveal"
    assert reveal["round"]["outcome"] == {
        "actualMoveBps": 300, "selfMoveBps": 200, "opponentMoveBps": 0,
        "selfErrorBps": 100, "opponentErrorBps": 300, "winnerId": 1, "damage": 25,
    }
    assert reveal["event"] == {"id": 1, "type": "attack", "actorId": 1, "targetId": 2, "damage": 25}
    assert match.public(2, 5)["round"]["outcome"]["opponentErrorBps"] == 100
    assert match.summary(1)["lastRound"] == reveal["round"]["outcome"]

    match.advance(9)
    next_round = match.public(1, 9)
    assert next_round["round"] == {
        "number": 2, "phase": "predict", "selfLocked": False, "opponentLocked": False,
        "selfMoveBps": None, "outcome": None,
    }
    assert next_round["bars"] == reveal["bars"]
    with pytest.raises(RuleError):
        match.submit(1, 1, 200, 9)
    match.submit(1, 2, 200, 9)
    match.submit(2, 2, 500, 9)
    assert match.public(1, 9)["round"]["outcome"]["actualMoveBps"] == 200


@pytest.mark.parametrize(("future_price", "actual_bps"), [("100.005", 1), ("99.995", -1)])
def test_half_basis_point_is_rounded_away_from_zero(future_price, actual_bps):
    match = make_match(future_price, countdown=0)
    match.submit(1, 1, 0, 0)
    match.submit(2, 1, actual_bps * 2, 0)
    state = match.public(1, 0)
    assert state["round"]["outcome"] == {
        "actualMoveBps": actual_bps, "selfMoveBps": 0, "opponentMoveBps": actual_bps * 2,
        "selfErrorBps": 1, "opponentErrorBps": 1, "winnerId": None, "damage": 0,
    }
    assert state["self"]["hp"] == state["opponent"]["hp"] == 100
    assert state["event"] is None


@pytest.mark.parametrize("move_bps", [True, -10_001, MAX_MOVE_BPS + 1, 1.0, "1", None])
def test_invalid_predictions_do_not_lock(move_bps):
    match = make_match(countdown=0)
    with pytest.raises(RuleError):
        match.submit(1, 1, move_bps, 0)
    assert not match.public(1, 0)["round"]["selfLocked"]


def test_prediction_bounds_and_number_validation():
    match = make_match(countdown=0)
    with pytest.raises(RuleError):
        match.submit(1, True, 0, 0)
    with pytest.raises(RuleError):
        match.submit(3, 1, 0, 0)
    match.submit(1, 1, -10_000, 0)
    match.submit(2, 1, MAX_MOVE_BPS, 0)
    outcome = match.public(1, 0)["round"]["outcome"]
    assert outcome["selfMoveBps"] == -10_000
    assert outcome["opponentMoveBps"] == MAX_MOVE_BPS
    assert outcome["damage"] == 5


def test_exact_deadline_resolves_single_submission_and_both_missing():
    match = make_match(countdown=0)
    deadline = PREDICT_SECONDS
    match.submit(2, 1, 20, deadline - 0.001)
    with pytest.raises(RuleError):
        match.submit(1, 1, 0, deadline)
    outcome = match.public(1, deadline)["round"]["outcome"]
    assert outcome == {
        "actualMoveBps": 0, "selfMoveBps": None, "opponentMoveBps": 20,
        "selfErrorBps": None, "opponentErrorBps": 20, "winnerId": 2, "damage": 29,
    }
    next_deadline = deadline + REVEAL_SECONDS + PREDICT_SECONDS
    assert match.advance(next_deadline)
    missed = match.public(1, next_deadline)
    assert missed["round"]["number"] == 2
    assert missed["round"]["outcome"]["damage"] == 0
    assert missed["round"]["outcome"]["winnerId"] is None
    assert missed["self"]["hp"] == 71
    assert missed["opponent"]["hp"] == 100


def test_knockout_caps_damage_and_finishes_after_reveal():
    match = make_match(countdown=0)
    for round_number in range(1, 5):
        now = (round_number - 1) * REVEAL_SECONDS
        match.submit(1, round_number, 0, now)
        match.submit(2, round_number, 100, now)

    assert match.status == "active"
    assert match.winner_id == 1
    knockout = match.public(1, now)
    assert knockout["event"] == {"id": 4, "type": "ko", "actorId": 1, "targetId": 2, "damage": 10}
    assert knockout["opponent"]["hp"] == 0
    assert knockout["round"]["outcome"]["damage"] == 10
    assert match.summary(1)["attackDamage"] == 100

    match.advance(now + REVEAL_SECONDS - 0.001)
    assert match.status == "active"
    assert match.advance(now + REVEAL_SECONDS)
    assert match.status == "finished"
    assert match.duration == now + REVEAL_SECONDS
    assert match.public(1, now + REVEAL_SECONDS)["round"] == knockout["round"]
    result = match.summary(1)
    assert result["opponentHp"] == 0
    assert result["endReason"] == "knockout"
    assert result["endActor"] == "self"
    assert match.summary(2)["endActor"] == "opponent"
    assert result["rounds"][-1] == {"number": 4, **knockout["round"]["outcome"]}
    assert not match.advance(now + 100)


@pytest.mark.parametrize("first_move", [None, 0])
def test_round_limit_resolves_remaining_hp_and_preserves_last_round(first_move):
    match = make_match(countdown=0)
    if first_move is not None:
        match.submit(1, 1, first_move, 0)
    end_time = MAX_ROUNDS * (PREDICT_SECONDS + REVEAL_SECONDS)
    assert match.advance(end_time - REVEAL_SECONDS)
    assert match.status == "active"
    assert match.public(1, end_time - REVEAL_SECONDS)["round"]["number"] == MAX_ROUNDS
    assert match.advance(end_time)
    assert match.status == "finished"
    assert match.duration == end_time
    assert match.winner_id == (1 if first_move is not None else None)
    assert match.revealed_count == match.scenario.preview_count + MAX_ROUNDS
    result = match.summary(1)
    assert result["roundsPlayed"] == MAX_ROUNDS
    assert result["endReason"] == "round_limit"
    assert result["endActor"] is None
    assert result["lastRound"] == match.public(1, end_time)["round"]["outcome"]
    assert [round_result["number"] for round_result in result["rounds"]] == list(range(1, MAX_ROUNDS + 1))
    assert result["rounds"][0]["selfMoveBps"] == first_move
    assert result["rounds"][0]["opponentMoveBps"] is None
    assert all(round_result["damage"] == 0 for round_result in result["rounds"][1:])
