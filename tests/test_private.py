from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

from sqlalchemy import func, select

from stockfight.data import Match, MatchResult, PlayerRating, TradeHistory, db
from stockfight.market_data import MarketDataUnavailable

from test_multiplayer import advance, game, register, settle


def private_state(player):
    return player.events("private_state")[-1]


def create_invitation(player):
    assert player.emit("private_create")["ok"]
    return private_state(player)["invitation"]["code"]


def test_invitation_can_be_resumed_cancelled_and_expired(game):
    app, _ = game
    host = register(app, "InviteHost")
    guest = register(app, "InviteGuest")
    assert host.emit("queue_join")["ok"]
    assert guest.events("private_state") == [{"invitation": None, "rematch": None}]

    code = create_invitation(host)
    assert host.id not in app.extensions["match_service"].queue
    assert create_invitation(host) == code
    assert guest.events("private_state") == []
    assert not host.emit("private_join", {"code": code})["ok"]

    host.socket.disconnect()
    assert not guest.emit("private_join", {"code": code})["ok"]
    advance(game, 30)
    host.connect()
    assert private_state(host)["invitation"] == {"code": code, "remaining": 870}
    assert host.emit("private_cancel")["ok"]
    assert private_state(host)["invitation"] is None
    assert not guest.emit("private_join", {"code": code})["ok"]

    active_code = create_invitation(host)
    advance(game, 900)
    assert private_state(host)["invitation"] is None
    assert not guest.emit("private_join", {"code": active_code})["ok"]


def test_only_one_guest_can_use_an_invitation_concurrently(game):
    app, _ = game
    host = register(app, "RaceHost")
    first_guest = register(app, "FirstGuest")
    second_guest = register(app, "SecondGuest")
    code = create_invitation(host)
    barrier = Barrier(2, timeout=5)

    def join(player):
        barrier.wait()
        return player.emit("private_join", {"code": f" {code.lower()} "})

    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(join, player) for player in (first_guest, second_guest)]
        joined = [future.result(timeout=10)["ok"] for future in futures]

    assert sorted(joined) == [False, True]
    admitted, rejected = (first_guest, second_guest) if joined[0] else (second_guest, first_guest)
    host_state, guest_state = host.state(), admitted.state()
    assert host_state["id"] == guest_state["id"]
    assert host_state["mode"] == guest_state["mode"] == "private"
    assert host_state["opponent"]["id"] == admitted.id
    assert rejected.events("match_state") == []
    assert not rejected.emit("private_join", {"code": code})["ok"]
    assert admitted.emit("queue_join")["ok"]
    assert admitted.state()["id"] == guest_state["id"]


def test_market_failure_leaves_invitation_and_guest_queue_available(game, monkeypatch):
    app, _ = game
    service = app.extensions["match_service"]
    host = register(app, "MarketHost")
    guest = register(app, "MarketGuest")
    code = create_invitation(host)
    assert guest.emit("queue_join")["ok"]

    def no_market(**settings):
        raise MarketDataUnavailable("Testmarknaden är inte tillgänglig.")

    with monkeypatch.context() as unavailable:
        unavailable.setattr(service.provider, "choose", no_market)
        result = guest.emit("private_join", {"code": code})

    assert not result["ok"]
    assert guest.id in service.queue
    assert create_invitation(host) == code
    assert guest.emit("private_join", {"code": code})["ok"]
    assert guest.id not in service.queue
    assert host.state()["id"] == guest.state()["id"]


def test_private_match_is_unranked_and_rematch_requires_both_players(game):
    app, _ = game
    host = register(app, "RematchHost")
    guest = register(app, "RematchGuest")
    outsider = register(app, "RematchOutsider")

    def database_counts():
        with app.app_context():
            return [
                db.session.scalar(select(func.count()).select_from(model))
                for model in (Match, MatchResult, TradeHistory, PlayerRating)
            ]

    before = database_counts()
    code = create_invitation(host)
    assert guest.emit("private_join", {"code": code})["ok"]
    first_match_id = host.state()["id"]
    advance(game, 3)
    assert host.trade(host.state(), "buy", percent=100)["ok"]
    advance(game, 1)
    assert settle(host, host.state(), "attack")["ok"]

    guest.socket.disconnect()
    advance(game, 1)
    guest.connect()
    assert guest.state()["id"] == first_match_id
    advance(game, 130)
    result, = host.events("match_result")
    assert result["mode"] == "private" and result["outcome"] == "win"
    assert result["trades"] == 1 and result["attackDamage"] > 0
    assert "eloBefore" not in result and "eloAfter" not in result
    assert database_counts() == before

    offer = {"matchId": first_match_id}
    assert not outsider.emit("private_rematch", offer)["ok"]
    assert host.emit("private_rematch", offer)["ok"]
    assert host.emit("private_rematch", offer)["ok"]
    assert private_state(host)["rematch"]["selfAccepted"]
    assert private_state(guest)["rematch"]["opponentAccepted"]

    host.socket.disconnect()
    assert private_state(guest)["rematch"]["available"] is False
    assert not guest.emit("private_rematch", offer)["ok"]
    host.connect()
    events = host.socket.get_received()
    assert next(event["args"][0] for event in events if event["name"] == "match_result") == result
    assert next(event["args"][0] for event in events if event["name"] == "private_state")["rematch"]["selfAccepted"]
    assert private_state(guest)["rematch"]["available"] is True

    assert guest.emit("private_rematch", offer)["ok"]
    second_match_id = guest.state()["id"]
    assert second_match_id == host.state()["id"] != first_match_id
    assert guest.emit("private_rematch", offer)["ok"]
    assert guest.state()["id"] == second_match_id
    assert database_counts() == before


def test_switching_to_ranked_clears_private_rematch_for_both_players(game):
    app, _ = game
    host = register(app, "SwitchHost")
    guest = register(app, "SwitchGuest")
    code = create_invitation(host)
    assert guest.emit("private_join", {"code": code})["ok"]
    match_id = host.state()["id"]
    advance(game, 130)
    assert private_state(guest)["rematch"]["matchId"] == match_id
    assert host.emit("queue_join")["ok"]
    assert private_state(guest)["rematch"] is None
    assert not guest.emit("private_rematch", {"matchId": match_id})["ok"]
