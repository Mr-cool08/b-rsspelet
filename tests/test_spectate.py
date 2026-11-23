import json
from collections import defaultdict

from test_multiplayer import FIRST_BAR, Player, advance, game, join_both, register, settle
from test_private import create_invitation


def received(player):
    events = defaultdict(list)
    for message in player.socket.get_received():
        events[message["name"]].append(message["args"][0])
    return events


def watch(player, match_id):
    response = player.emit("spectate_join", {"matchId": match_id})
    assert response["ok"], response
    return response["state"]


def test_spectator_receives_live_market_combat_and_result(game):
    app, _ = game
    spectator = register(app, "Spectator")
    other_tab = Player(app, spectator.http, spectator.id)
    other_tab.connect()
    assert spectator.emit("spectate_list") == {"ok": True, "matches": []}
    received(spectator)
    received(other_tab)

    first, second = join_both(game)
    first_state = first.state()
    match_id = first_state["id"]
    listed, = received(spectator)["spectate_matches"][-1]["matches"]
    assert (listed["id"], listed["mode"], listed["status"]) == (match_id, "ranked", "countdown")
    assert {player["id"]: player["name"] for player in listed["players"]} == {
        first.id: "BullPlayer", second.id: "BearPlayer",
    }
    assert not received(other_tab)

    preview = watch(spectator, match_id)
    assert preview["status"] == "countdown" and preview["countdown"] == 3
    assert preview["bars"] == first_state["bars"]
    advance(game, 3)
    updates = received(spectator)
    assert updates["spectate_matches"][-1]["matches"][0]["status"] == "active"
    assert updates["spectate_state"][-1]["status"] == "active"
    assert not updates["match_state"]

    active = first.state()
    assert not spectator.trade(active, "buy", percent=100)["ok"]
    assert first.trade(active, "buy", percent=100)["ok"]
    opened = received(spectator)["spectate_state"][-1]
    assert {player["id"]: player["hasPosition"] for player in opened["players"]} == {
        first.id: True, second.id: False,
    }
    assert {"self", "opponent", "nextSeq"}.isdisjoint(opened)
    assert all({"position", "closePreview", "cash"}.isdisjoint(player) for player in opened["players"])

    advance(game, 1)
    tick = received(spectator)["spectate_state"][-1]
    trader_tick = first.state()
    assert len(tick["bars"]) == len(preview["bars"]) + 1
    assert tick["bars"] == trader_tick["bars"]
    assert FIRST_BAR.date().isoformat() not in json.dumps(tick)
    assert settle(first, trader_tick, "attack")["ok"]
    attack = received(spectator)["spectate_state"][-1]
    assert attack["event"]["actorId"] == first.id
    assert {player["id"]: player["hp"] for player in attack["players"]} == {
        first.id: 100, second.id: 65,
    }

    advance(game, 130)
    updates = received(spectator)
    finished = updates["spectate_state"][-1]
    assert (finished["id"], finished["status"], finished["winnerId"]) == (match_id, "finished", first.id)
    assert updates["spectate_matches"][-1]["matches"] == []
    assert not updates["match_result"]
    assert not received(other_tab)
    unavailable = spectator.emit("spectate_join", {"matchId": match_id})
    assert not unavailable["ok"] and unavailable["code"] == "match_unavailable"


def test_spectator_can_switch_matches_leave_and_resubscribe(game):
    app, _ = game
    spectator = register(app, "SwitchViewer")
    host = register(app, "SwitchHost")
    guest = register(app, "SwitchGuest")
    bot_player = register(app, "BotPlayer")
    trainee = register(app, "Trainee")
    received(spectator)

    code = create_invitation(host)
    assert trainee.emit("prediction_practice_start")["ok"]
    practice_id = trainee.state()["id"]
    assert spectator.emit("spectate_list")["matches"] == []
    assert not spectator.emit("spectate_join", {"matchId": practice_id})["ok"]
    assert not spectator.emit("spectate_join", {"matchId": code})["ok"]
    assert guest.emit("private_join", {"code": code})["ok"]
    private_id = guest.state()["id"]
    assert bot_player.emit("bot_start")["ok"]
    bot_id = bot_player.state()["id"]

    listing = spectator.emit("spectate_list")["matches"]
    assert {match["id"]: match["mode"] for match in listing} == {private_id: "private", bot_id: "bot"}
    private_view = watch(spectator, private_id)
    assert set(player["id"] for player in private_view["players"]) == {host.id, guest.id}
    messages = received(spectator)
    assert not messages["private_state"] and not messages["match_state"]
    assert code not in json.dumps((listing, private_view, messages))

    assert watch(spectator, bot_id)["mode"] == "bot"
    advance(game, 3)
    updates = received(spectator)["spectate_state"]
    assert updates and {state["id"] for state in updates} == {bot_id}

    assert spectator.emit("spectate_leave")["ok"]
    assert spectator.emit("spectate_list_leave")["ok"]
    advance(game, 130)
    assert not received(spectator)

    first, _ = join_both(game)
    current_id = first.state()["id"]
    assert watch(spectator, current_id)["status"] == "countdown"
    spectator.socket.disconnect()
    spectator.connect()
    advance(game, 3)
    reconnected = received(spectator)
    assert not reconnected["spectate_matches"] and not reconnected["spectate_state"]
    assert watch(spectator, current_id)["status"] == "active"
    advance(game, 1)
    assert received(spectator)["spectate_state"][-1]["id"] == current_id


def test_prediction_spectator_sees_guesses_only_after_round_reveal(game):
    app, _ = game
    spectator = register(app, "PredictionViewer")
    first = register(app, "BullPredictor")
    second = register(app, "BearPredictor")
    for player in (first, second):
        assert player.emit("queue_join", {"mode": "prediction"})["ok"]
    match_id = first.state()["id"]
    assert [match["mode"] for match in spectator.emit("spectate_list")["matches"]] == ["prediction"]
    preview = watch(spectator, match_id)
    advance(game, 3)
    received(spectator)

    prediction = {"matchId": match_id, "round": 1}
    assert not spectator.emit("prediction_submit", {**prediction, "moveBps": 200})["ok"]
    assert first.emit("prediction_submit", {**prediction, "moveBps": 200})["ok"]
    locked = received(spectator)["spectate_state"][-1]
    assert locked["bars"] == preview["bars"]
    assert locked["round"]["phase"] == "predict" and locked["round"]["outcome"] is None
    assert "movebps" not in json.dumps(locked).lower()
    assert {player["id"]: player["locked"] for player in locked["players"]} == {first.id: True, second.id: False}

    assert second.emit("prediction_submit", {**prediction, "moveBps": 100})["ok"]
    reveal = received(spectator)["spectate_state"][-1]
    assert len(reveal["bars"]) == len(preview["bars"]) + 1
    assert reveal["round"]["phase"] == "reveal"
    outcome = reveal["round"]["outcome"]
    assert (outcome["actualMoveBps"], outcome["winnerId"], outcome["damage"]) == (200, first.id, 30)
    assert {entry["id"]: entry["moveBps"] for entry in outcome["players"]} == {first.id: 200, second.id: 100}
