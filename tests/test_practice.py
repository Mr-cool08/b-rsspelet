from sqlalchemy import func, select

from stockfight.data import Match, PlayerRating, db
from stockfight.market_data import MarketDataUnavailable

from test_multiplayer import advance, game, register


def test_practice_reveals_only_submitted_rounds_and_never_rates(game, monkeypatch):
    app, _ = game
    player = register(app, "SoloPlayer")
    other = register(app, "OtherPlayer")
    rating_query = select(PlayerRating.user_id, PlayerRating.mode, PlayerRating.elo).order_by(
        PlayerRating.user_id, PlayerRating.mode,
    )
    with app.app_context():
        ratings_before = db.session.execute(rating_query).all()

    def unavailable(**kwargs):
        raise MarketDataUnavailable("Kursdata saknas.")

    monkeypatch.setattr(app.extensions["match_service"].provider, "choose", unavailable)
    assert player.emit("prediction_practice_start")["ok"]
    state = player.state()
    match_id = state["id"]
    assert state["mode"] == "prediction_practice"
    assert state["roundLimit"] == 3
    assert state["remaining"] is None and state["opponent"] is None
    assert len(state["bars"]) == 12
    assert state["round"]["outcome"] is None

    assert player.emit("prediction_practice_start")["ok"]
    assert player.state()["id"] == match_id
    payload = {"matchId": match_id, "round": 1}
    assert not other.emit("prediction_submit", {**payload, "moveBps": 0})["ok"]
    assert not player.emit("prediction_practice_next", payload)["ok"]
    assert not player.emit("prediction_submit", {**payload, "moveBps": True})["ok"]
    assert len(player.state()["bars"]) == 12

    for number, (guess, actual) in enumerate([(40, 39), (-50, -55), (25, 25)], start=1):
        command = {"matchId": match_id, "round": number}
        assert player.emit("prediction_submit", {**command, "moveBps": guess})["ok"]
        reveal = player.state()
        assert len(reveal["bars"]) == 12 + number
        assert reveal["round"]["phase"] == "reveal"
        assert reveal["round"]["outcome"] == {
            "number": number, "actualMoveBps": actual, "selfMoveBps": guess,
            "selfErrorBps": abs(actual - guess),
        }
        assert player.emit("prediction_submit", {**command, "moveBps": guess})["ok"]
        assert player.state()["round"] == reveal["round"]
        assert player.emit("prediction_practice_next", command)["ok"]
        if number < 3:
            following = player.state()
            assert following["round"]["number"] == number + 1
            assert following["round"]["outcome"] is None
            assert len(following["bars"]) == 12 + number
            assert player.emit("prediction_practice_next", command)["ok"]
            assert player.state()["round"]["number"] == number + 1

    result = player.events("match_result")[-1]
    assert result["outcome"] == "completed" and result["roundsPlayed"] == 3
    assert [round_result["selfErrorBps"] for round_result in result["rounds"]] == [1, 5, 0]
    assert "eloAfter" not in result
    assert not other.events("match_result")
    with app.app_context():
        assert db.session.scalar(select(func.count()).select_from(Match)) == 0
        assert db.session.execute(rating_query).all() == ratings_before

    player.socket.disconnect()
    player.connect()
    assert player.events("match_result") == [result]
    assert player.emit("prediction_practice_start")["ok"]
    assert player.state()["id"] != match_id


def test_practice_can_resume_leave_and_switch_modes(game):
    app, _ = game
    player = register(app, "PracticePlayer")
    assert player.emit("queue_join", {"mode": "prediction"})["ok"]
    assert player.events("queue_state")[-1]["queued"]
    assert player.emit("prediction_practice_start")["ok"]
    practice = player.state()
    assert player.id not in app.extensions["match_service"].queue

    assert player.emit("prediction_submit", {"matchId": practice["id"], "round": 1, "moveBps": -20})["ok"]
    player.socket.disconnect()
    advance(game, 60)
    player.connect()
    resumed = player.state()
    assert resumed["id"] == practice["id"]
    assert resumed["round"]["selfMoveBps"] == -20
    assert len(resumed["bars"]) == 13

    assert player.emit("prediction_practice_leave", {"matchId": resumed["id"]})["ok"]
    assert player.events("prediction_practice_ended") == [{"id": resumed["id"]}]
    assert player.emit("prediction_practice_start")["ok"]
    restarted = player.state()
    assert restarted["id"] != resumed["id"] and len(restarted["bars"]) == 12
    assert player.emit("bot_start")["ok"]
    assert player.state()["mode"] == "bot"
    assert not player.emit("prediction_practice_start")["ok"]


def test_disconnected_practice_expires(game):
    app, _ = game
    player = register(app, "PracticeReconnect")
    assert player.emit("prediction_practice_start")["ok"]
    old_id = player.state()["id"]
    player.socket.disconnect()
    advance(game, 900)
    player.connect()
    assert player.events("prediction_practice_ended") == [{"id": None}]
    assert player.emit("prediction_practice_start")["ok"]
    assert player.state()["id"] != old_id
