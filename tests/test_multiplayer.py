import json
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from threading import Barrier

import pytest
from sqlalchemy import func, select

from stockfight import create_app, socketio
from stockfight.data import Match, MatchResult, PlayerRating, TradeHistory, User, db
from stockfight.engine import Bar, Scenario
from stockfight.market_data import MarketDataUnavailable


PASSWORD = "stockfight-test-passphrase"
INVITE = "stockfight-test-invite"
FIRST_BAR = datetime(2001, 2, 3, 14, 30, tzinfo=timezone.utc)


@dataclass
class Clock:
    now: float = 500.0

    def __call__(self):
        return self.now


class AlternatingMarket:
    """Fixed synthetic prices exercise wins reproducibly in the Socket.IO flow."""

    def choose(self, *, required_bars, preview_count):
        bars = []
        for index in range(required_bars):
            is_rising_tick = index >= preview_count and (index - preview_count) % 2 == 0
            price = Decimal("102") if is_rising_tick else Decimal("100")
            bars.append(Bar(FIRST_BAR + timedelta(minutes=index), price, price, price, price, 100))
        return Scenario(
            "TEST-01", "SE", "1m", "pytest synthetic fixture", True, tuple(bars), preview_count,
        )


@pytest.fixture
def game(tmp_path):
    clock = Clock()
    database = (tmp_path / "stockfight.db").as_posix()
    app = create_app({
        "TESTING": True,
        "SQLALCHEMY_DATABASE_URI": f"sqlite:///{database}",
        "SECRET_KEY": "stockfight-integration-tests-key",
        "INVITE_CODE": INVITE,
        "AUTO_SEED_DEMO": False,
        "MATCH_BACKGROUND": False,
        "MATCH_CLOCK": clock,
        "MATCH_COUNTDOWN": 3,
        "MATCH_PREVIEW_BARS": 12,
        "MARKET_TICK_SECONDS": 1,
        "MATCH_MARKET_PROVIDER": AlternatingMarket(),
    })
    return app, clock


def post(http, endpoint, body):
    token = http.get("/api/me").get_json()["csrfToken"]
    return http.post(endpoint, json=body, headers={"X-CSRF-Token": token})


@dataclass
class Player:
    app: object
    http: object
    id: int
    socket: object = None

    def connect(self):
        token = self.http.get("/api/me").get_json()["csrfToken"]
        self.socket = socketio.test_client(
            self.app, flask_test_client=self.http, auth={"csrfToken": token},
        )
        assert self.socket.is_connected()

    def emit(self, name, payload=None):
        return self.socket.emit(name, payload or {}, callback=True)

    def trade(self, state, action, **payload):
        return self.emit("trade", {
            "matchId": state["id"], "seq": state["nextSeq"], "action": action, **payload,
        })

    def events(self, name):
        return [event["args"][0] for event in self.socket.get_received() if event["name"] == name]

    def state(self):
        return self.events("match_state")[-1]


def register(app, username):
    http = app.test_client()
    response = post(http, "/api/register", {
        "username": username, "password": PASSWORD, "inviteCode": INVITE,
    })
    assert response.status_code in (200, 201), response.get_json()
    player = Player(app, http, response.get_json()["user"]["id"])
    player.connect()
    return player


def advance(game, seconds):
    app, clock = game
    clock.now += seconds
    app.extensions["match_service"].pump()


def join_both(game):
    app, _ = game
    first = register(app, "BullPlayer")
    second = register(app, "BearPlayer")
    assert first.emit("queue_join")["ok"]
    assert second.emit("queue_join")["ok"]
    return first, second


def settle(player, state, choice):
    quote = player.trade(state, "sell")
    assert quote["ok"] and quote["requiresChoice"]
    confirmation_state = {**state, "nextSeq": state["nextSeq"] + 1}
    return player.trade(
        confirmation_state, "confirm_sell", choice=choice, positionId=quote["positionId"],
    )


def test_private_registration_and_login(game):
    app, _ = game
    http = app.test_client()
    info = http.get("/api/me").get_json()
    assert info["user"] is None and info["inviteRequired"]
    credentials = {"username": "SwedishBull", "password": PASSWORD, "inviteCode": INVITE}

    assert http.post("/api/register", json=credentials).status_code >= 400
    assert post(http, "/api/register", {**credentials, "inviteCode": "wrong"}).status_code >= 400
    assert post(http, "/api/register", credentials).status_code in (200, 201)

    with app.app_context():
        user = db.session.scalar(select(User).where(User.username == "SwedishBull"))
        assert user.password_hash and user.password_hash != PASSWORD

    profile = http.get("/api/profile").get_json()
    assert profile["elo"] == 100 and profile["league"] == "Bronze"
    assert (profile["wins"], profile["losses"], profile["draws"], profile["winRate"]) == (0, 0, 0, 0)
    assert profile["history"] == []
    leaders = http.get("/api/leaderboard").get_json()["players"]
    assert any(row["username"] == "SwedishBull" and row["elo"] == 100 for row in leaders)
    page = http.get("/").get_data(as_text=True)
    assert '<th scope="row">Iron</th>' in page and "Under 50" in page
    assert '<th scope="row">Grandmaster</th>' in page and "800–949" in page
    assert '<th scope="row">Stock Legend</th>' in page and "950+" in page
    wrong_token = socketio.test_client(app, flask_test_client=http, auth={"csrfToken": "wrong"})
    assert not wrong_token.is_connected()

    token = http.get("/api/me").get_json()["csrfToken"]
    connected = socketio.test_client(app, flask_test_client=http, auth={"csrfToken": token})
    assert connected.is_connected()
    assert post(http, "/api/logout", {}).status_code == 200
    assert not connected.is_connected()
    assert http.get("/api/me").get_json()["user"] is None
    token = http.get("/api/me").get_json()["csrfToken"]
    unauthenticated = socketio.test_client(app, flask_test_client=http, auth={"csrfToken": token})
    assert not unauthenticated.is_connected()
    assert post(http, "/api/login", {"username": credentials["username"], "password": "wrong"}).status_code >= 400
    login = post(http, "/api/login", {"username": credentials["username"], "password": PASSWORD})
    assert login.get_json()["user"]["username"] == "SwedishBull"


def test_new_account_duel_tutorial_persists_until_completed(game):
    app, _ = game
    first_browser = app.test_client()
    complete = "/api/duel-tutorial/complete"
    credentials = {"username": "NewTrader", "password": PASSWORD}

    assert first_browser.get("/api/me").get_json()["duelTutorialPending"] is False
    assert post(first_browser, complete, {}).status_code == 401
    registration = post(first_browser, "/api/register", {**credentials, "inviteCode": INVITE})
    assert registration.status_code == 201
    assert registration.get_json()["duelTutorialPending"] is True
    assert first_browser.get("/api/me").get_json()["duelTutorialPending"] is True
    assert first_browser.post(complete, json={}).status_code == 403

    second_browser = app.test_client()
    assert post(second_browser, "/api/login", credentials).get_json()["duelTutorialPending"] is True
    for _ in range(2):
        response = post(second_browser, complete, {})
        assert response.status_code == 200
        assert response.get_json()["duelTutorialPending"] is False
        assert response.get_json()["user"] == registration.get_json()["user"]

    assert first_browser.get("/api/me").get_json()["duelTutorialPending"] is False
    assert post(app.test_client(), "/api/login", credentials).get_json()["duelTutorialPending"] is False


def test_online_count_tracks_connected_accounts(game):
    app, _ = game
    guest = app.test_client()
    response = guest.get("/api/online")
    assert response.get_json() == {"count": 0}
    assert response.headers["Cache-Control"] == "no-store"

    first = register(app, "FirstOnline")
    other_tab = Player(app, first.http, first.id)
    other_tab.connect()
    assert guest.get("/api/online").get_json() == {"count": 1}
    assert b"1 online</span>" in guest.get("/").data

    second = register(app, "SecondOnline")
    first.socket.disconnect()
    assert guest.get("/api/online").get_json() == {"count": 2}

    other_tab.socket.disconnect()
    assert guest.get("/api/online").get_json() == {"count": 1}
    assert post(second.http, "/api/logout", {}).status_code == 200
    assert guest.get("/api/online").get_json() == {"count": 0}


@pytest.mark.parametrize("elo_gap, matches_after_widening", [(150, True), (201, False)])
def test_matchmaking_widens_only_to_200_points(game, elo_gap, matches_after_widening):
    app, _ = game
    first = register(app, "FirstQueue")
    second = register(app, "SecondQueue")
    with app.app_context():
        rating = db.session.get(PlayerRating, (second.id, "ranked"))
        if rating is None:
            rating = PlayerRating(user_id=second.id, mode="ranked")
            db.session.add(rating)
        rating.elo = 100 + elo_gap
        db.session.commit()

    assert first.emit("queue_join")["ok"]
    assert second.emit("queue_join")["ok"]
    advance(game, 14)
    assert not first.events("match_state")
    assert not second.events("match_state")
    advance(game, 1)
    if matches_after_widening:
        assert first.state()["id"] == second.state()["id"]
    else:
        advance(game, 30)
        assert not first.events("match_state")
        assert not second.events("match_state")
        assert second.emit("queue_leave")["ok"]


def test_queue_update_survives_disconnect_during_broadcast(game, monkeypatch):
    app, _ = game
    first = register(app, "FirstQueue")
    second = register(app, "SecondQueue")
    assert first.emit("queue_join")["ok"]
    assert second.emit("queue_join", {"mode": "prediction"})["ok"]
    first.events("queue_state")
    emit = socketio.emit

    def emit_and_disconnect(event, payload, **kwargs):
        emit(event, payload, **kwargs)
        if event == "queue_state" and payload.get("mode") == "ranked" and second.socket.is_connected():
            second.socket.disconnect()

    monkeypatch.setattr(socketio, "emit", emit_and_disconnect)
    advance(game, 1)

    assert not second.socket.is_connected()
    assert first.events("queue_state")[-1]["waited"] == 1
    assert second.id not in app.extensions["match_service"].queue


def test_two_clients_trade_concurrently_finish_and_persist_once(game):
    app, _ = game
    first, second = join_both(game)
    initial_first, initial_second = first.state(), second.state()
    assert initial_first["status"] == "countdown" and initial_first["countdown"] == 3
    assert initial_first["id"] == initial_second["id"]
    assert initial_first["bars"] == initial_second["bars"]
    assert len(initial_first["bars"]) == 12
    assert {Decimal(bar["close"]) for bar in initial_first["bars"]} == {Decimal("100")}
    assert all(isinstance(bar["time"], int) and abs(bar["time"]) < 1000 for bar in initial_first["bars"])
    assert FIRST_BAR.date().isoformat() not in json.dumps((initial_first, initial_second))
    assert initial_first["synthetic"]

    advance(game, 3)
    first_state, second_state = first.state(), second.state()
    assert first_state["status"] == second_state["status"] == "active"
    barrier = Barrier(2, timeout=5)

    def buy(player, state, percent):
        barrier.wait()
        return player.trade(state, "buy", percent=percent)

    with ThreadPoolExecutor(max_workers=2) as pool:
        first_buy = pool.submit(buy, first, first_state, 100)
        second_buy = pool.submit(buy, second, second_state, 50)
        assert first_buy.result(timeout=10)["ok"]
        assert second_buy.result(timeout=10)["ok"]

    first_position, second_position = first.state(), second.state()
    assert Decimal(first_position["self"]["cash"]) == 0
    assert Decimal(second_position["self"]["cash"]) == 250
    assert Decimal(first_position["self"]["position"]["entryPrice"]) == 100
    assert first_position["opponent"]["hasPosition"]
    assert "entryPrice" not in first_position["opponent"]

    advance(game, 1)
    at_profit_first, at_profit_second = first.state(), second.state()
    assert len(at_profit_first["bars"]) == 13
    assert at_profit_first["bars"] == at_profit_second["bars"]
    assert Decimal(at_profit_first["price"]) == 102
    assert settle(first, at_profit_first, "attack")["ok"]
    assert settle(second, at_profit_second, "grow")["ok"]
    after_attack, after_grow = first.state(), second.state()
    assert after_attack["self"]["hp"] == 100 and after_attack["opponent"]["hp"] == 65
    assert Decimal(after_attack["self"]["cash"]) == 500
    assert Decimal(after_grow["self"]["cash"]) == 505 and after_grow["self"]["growBonus"] == 25
    assert not first.trade(first_state, "buy", percent=100)["ok"]

    for percent in (100, 75):
        advance(game, 1)
        assert first.trade(first.state(), "buy", percent=percent)["ok"]
        advance(game, 1)
        assert settle(first, first.state(), "attack")["ok"]

    first_events = first.socket.get_received()
    second_events = second.socket.get_received()
    first_results = [event["args"][0] for event in first_events if event["name"] == "match_result"]
    second_results = [event["args"][0] for event in second_events if event["name"] == "match_result"]
    assert len(first_results) == len(second_results) == 1
    winner, loser = first_results[0], second_results[0]
    assert (winner["outcome"], loser["outcome"]) == ("win", "lose")
    assert (winner["eloBefore"], winner["eloAfter"], loser["eloBefore"], loser["eloAfter"]) == (100, 116, 100, 84)
    assert (winner["trades"], winner["winningTrades"], winner["losingTrades"]) == (3, 3, 0)
    assert winner["attackDamage"] == 100 and loser["growCount"] == 1
    assert winner["duration"] == 5
    assert winner["periodStart"].startswith(FIRST_BAR.date().isoformat())
    assert winner["periodEnd"] > winner["periodStart"]

    assert not first.trade(after_attack, "buy", percent=25)["ok"]
    advance(game, 180)
    assert first.events("match_result") == second.events("match_result") == []
    winner_profile = first.http.get("/api/profile").get_json()
    assert (winner_profile["elo"], winner_profile["matches"], winner_profile["wins"], winner_profile["winRate"]) == (116, 1, 1, 100)
    assert [match["id"] for match in winner_profile["history"]] == [winner["id"]]
    with app.app_context():
        assert db.session.scalar(select(func.count()).select_from(Match)) == 1
        assert db.session.scalar(select(func.count()).select_from(MatchResult)) == 2
        assert db.session.scalar(select(func.count()).select_from(TradeHistory)) == 4


def test_capital_breaks_simultaneous_knockout_and_counts_for_ranked_elo(game):
    first, second = join_both(game)
    first.state()
    second.state()
    advance(game, 3)
    assert first.trade(first.state(), "buy", percent=100)["ok"]
    advance(game, 1)
    assert settle(first, first.state(), "grow")["ok"]

    grown = first.state()
    assert Decimal(grown["self"]["capital"]) == 510
    assert grown["self"]["attackPower"] == 104
    assert first.trade(grown, "buy", percent=100)["ok"]
    open_position = first.state()
    assert Decimal(open_position["self"]["cash"]) == 0
    assert open_position["self"]["attackPower"] == 104
    assert Decimal(second.state()["opponent"]["capital"]) == 510

    advance(game, 115)
    winner, = first.events("match_result")
    loser, = second.events("match_result")
    assert winner["hp"] == loser["hp"] == 0
    assert winner["tiebreak"] == loser["tiebreak"] == "capital"
    assert Decimal(winner["opponentCapital"]) == 500
    assert Decimal(loser["opponentCapital"]) == 510
    assert winner["outcome"] == "win" and winner["eloAfter"] == 116
    assert loser["outcome"] == "lose" and loser["eloAfter"] == 84


def test_short_trade_on_falling_price_can_attack_via_socket(game):
    app, _ = game
    first, second = join_both(game)
    advance(game, 4)
    entry = first.state()
    assert Decimal(entry["price"]) == 102
    assert first.trade(entry, "short", percent=50)["ok"]
    opened = first.state()
    assert opened["self"]["position"]["side"] == "short"
    assert Decimal(opened["self"]["cash"]) == 250
    assert second.state()["opponent"]["hasPosition"]

    advance(game, 1)
    exit_state = first.state()
    assert Decimal(exit_state["price"]) == 100
    assert Decimal(exit_state["self"]["position"]["pnl"]) > 0
    assert settle(first, exit_state, "attack")["ok"]

    closed = first.state()
    assert closed["self"]["position"] is None
    assert Decimal(closed["self"]["cash"]) == 500
    assert closed["self"]["attackDamage"] == 19
    assert second.state()["self"]["hp"] == 81

    advance(game, 120)
    assert first.events("match_result")[0]["outcome"] == "win"
    assert second.events("match_result")[0]["outcome"] == "lose"
    with app.app_context():
        trade = db.session.scalars(select(TradeHistory)).one()
        assert trade.user_id == first.id
        assert trade.side == "short"


def test_ranked_regeneration_purchase_is_authoritative_and_survives_reconnect(game):
    first, second = join_both(game)
    advance(game, 3)
    assert first.trade(first.state(), "buy", percent=50)["ok"]
    advance(game, 1)
    assert settle(first, first.state(), "attack")["ok"]

    damaged = second.state()
    assert damaged["self"]["hp"] == 80
    assert not second.trade(damaged, "buy_regeneration", cost="0", healing=100)["ok"]
    assert second.trade(damaged, "buy_regeneration")["ok"]
    purchased = second.state()
    assert purchased["self"]["hp"] == 80
    assert Decimal(purchased["self"]["cash"]) == 490
    assert purchased["self"]["regenerationRemaining"] == 20
    assert not second.trade(damaged, "buy_regeneration")["ok"]

    second.socket.disconnect()
    advance(game, 11)
    second.connect()
    rejoined = second.state()
    assert rejoined["self"]["hp"] == first.state()["opponent"]["hp"] == 84
    assert Decimal(rejoined["self"]["cash"]) == 490
    assert rejoined["self"]["regenerationRemaining"] == 9

    advance(game, 9)
    expired = second.state()
    assert expired["self"]["hp"] == first.state()["opponent"]["hp"] == 88
    assert expired["self"]["regenerationRemaining"] == 0


@pytest.mark.parametrize("trigger", ["pump", "trade"])
def test_match_broadcast_survives_tab_disconnect(game, monkeypatch, trigger):
    app, clock = game
    first, second = join_both(game)
    other_tab = Player(app, first.http, first.id)
    other_tab.connect()
    other_tab.state()
    second_state = second.state()
    emit = socketio.emit

    def emit_and_disconnect(event, payload, **kwargs):
        emit(event, payload, **kwargs)
        if event == "match_state" and payload["self"]["id"] == first.id and first.socket.is_connected():
            first.socket.disconnect()

    monkeypatch.setattr(socketio, "emit", emit_and_disconnect)
    if trigger == "pump":
        advance(game, 3)
    else:
        clock.now += 3
        assert second.trade(second_state, "buy", percent=50)["ok"]

    assert not first.socket.is_connected()
    assert other_tab.state()["status"] == "active"
    assert second.state()["status"] == "active"


def test_reconnecting_player_cannot_set_authoritative_fields(game):
    first, second = join_both(game)
    advance(game, 3)
    before = first.state()
    assert not first.trade(before, "buy", percent=150)["ok"]
    advance(game, 1)
    state = first.state()
    assert Decimal(state["self"]["cash"]) == 500 and state["self"]["hp"] == 100
    assert state["self"]["position"] is None and Decimal(state["price"]) == 102

    forged = first.trade(state, "buy", percent=25, price="0.01", cash="500000", hp=500, damage=100)
    if not forged["ok"]:
        first.socket.disconnect()
        first.connect()
        state = first.state()
        assert Decimal(state["self"]["cash"]) == 500 and state["self"]["position"] is None
        assert first.trade(state, "buy", percent=25)["ok"]
    opened = first.state()
    assert opened["self"]["hp"] == opened["opponent"]["hp"] == 100
    assert Decimal(opened["self"]["cash"]) == 375
    assert Decimal(opened["self"]["position"]["entryPrice"]) == 102
    first.socket.disconnect()
    advance(game, 105)
    first.connect()
    rejoined = first.state()
    peer = second.state()
    assert rejoined["id"] == opened["id"] == peer["id"]
    assert rejoined["nextSeq"] == opened["nextSeq"]
    assert Decimal(rejoined["self"]["cash"]) == 375
    assert Decimal(rejoined["self"]["position"]["entryPrice"]) == 102
    assert rejoined["elapsed"] == 106 and rejoined["storm"] == "final"
    assert 0 < rejoined["self"]["hp"] < 100
    assert rejoined["self"]["hp"] == peer["opponent"]["hp"] == peer["self"]["hp"]
    assert rejoined["bars"] == peer["bars"]

    advance(game, 20)
    assert first.events("match_result")[0]["outcome"] == "draw"
    assert second.events("match_result")[0]["outcome"] == "draw"


def test_pending_close_and_result_details_survive_reconnect(game):
    first, second = join_both(game)
    advance(game, 3)
    assert first.trade(first.state(), "buy", percent=25)["ok"]
    advance(game, 1)
    sale = first.trade(first.state(), "sell")
    assert sale["ok"] and sale["requiresChoice"]
    pending = first.state()
    quote = pending["self"]["position"]["closePreview"]
    assert quote["positionId"] == sale["positionId"]
    assert quote["attackDamage"] == 10 and Decimal(quote["growCredits"]) == Decimal("2.5")
    assert "closePreview" not in second.state()["opponent"]

    first.socket.disconnect()
    advance(game, 1)
    first.connect()
    resumed = first.state()
    current_quote = resumed["self"]["position"]["closePreview"]
    assert resumed["nextSeq"] == pending["nextSeq"]
    assert current_quote["positionId"] == sale["positionId"] and current_quote["kind"] == "flat"
    assert first.trade(resumed, "confirm_sell", choice="close", positionId=current_quote["positionId"])["ok"]
    assert first.state()["self"]["position"] is None

    advance(game, 115)
    result, = first.events("match_result")
    peer_result, = second.events("match_result")
    assert result["outcome"] == peer_result["outcome"] == "draw"
    assert result["endReason"] == "final_storm" and (result["hp"], result["opponentHp"]) == (0, 0)
    trade, = result["tradeDetails"]
    assert trade["choice"] == "flat" and trade["time"] == 2 and Decimal(trade["profit"]) == 0
    assert peer_result["tradeDetails"] == []

    first.socket.disconnect()
    first.connect()
    assert first.events("match_result") == [result]


def test_bot_match_uses_ranked_elo_and_supports_reconnect_and_rematch(game):
    app, _ = game
    player = register(app, "BotChallenger")
    with app.app_context():
        db.session.get(PlayerRating, (player.id, "ranked")).elo = 525
        db.session.commit()

    ranked_profile = player.http.get("/api/profile").get_json()
    ranked_leaders = player.http.get("/api/leaderboard").get_json()
    assert player.emit("queue_join")["ok"]
    assert player.events("queue_state")[-1]["queued"]
    assert player.emit("bot_start")["ok"]
    assert player.id not in app.extensions["match_service"].queue
    initial = player.state()
    assert initial["mode"] == "bot"
    assert initial["status"] == "countdown" and initial["countdown"] == 3
    assert Decimal(initial["self"]["cash"]) == Decimal(initial["opponent"]["capital"]) == 500
    assert initial["opponent"]["name"] == "Bot" and initial["opponent"]["elo"] == 525
    assert not initial["opponent"]["hasPosition"]
    assert len(initial["bars"]) == 12

    assert player.emit("bot_start")["ok"]
    assert player.state()["id"] == initial["id"]
    advance(game, 3)
    active = player.state()
    assert active["status"] == "active"
    assert player.trade(active, "buy", percent=25)["ok"]

    player.socket.disconnect()
    advance(game, 1)
    player.connect()
    rejoined = player.state()
    assert rejoined["id"] == initial["id"]
    assert rejoined["mode"] == "bot" and rejoined["opponent"]["elo"] == 525
    assert rejoined["nextSeq"] == active["nextSeq"] + 1
    assert Decimal(rejoined["self"]["cash"]) == 375
    assert len(rejoined["bars"]) == 13

    saw_bot_position = active["opponent"]["hasPosition"] or rejoined["opponent"]["hasPosition"]
    saw_bot_close = False
    results = []
    for _ in range(115):
        advance(game, 1)
        for event in player.socket.get_received():
            if event["name"] == "match_state":
                bot_has_position = event["args"][0]["opponent"]["hasPosition"]
                saw_bot_close |= saw_bot_position and not bot_has_position
                saw_bot_position |= bot_has_position
            elif event["name"] == "match_result":
                results.append(event["args"][0])
        if results:
            break

    assert saw_bot_position and saw_bot_close
    assert len(results) == 1
    result = results[0]
    assert result["id"] == initial["id"] and result["mode"] == "bot"
    assert result["eloBefore"] == result["eloAfter"] == 525
    assert result["outcome"] in {"win", "lose", "draw"}
    assert player.http.get("/api/profile").get_json() == ranked_profile
    assert player.http.get("/api/leaderboard").get_json() == ranked_leaders
    with app.app_context():
        assert db.session.scalar(select(func.count()).select_from(User)) == 1
        db.session.get(PlayerRating, (player.id, "ranked")).elo = 75
        db.session.commit()

    player.socket.disconnect()
    player.connect()
    assert player.events("match_result") == [result]
    assert player.emit("bot_start")["ok"]
    rematch = player.state()
    assert rematch["id"] != result["id"] and rematch["mode"] == "bot"
    assert rematch["opponent"]["elo"] == 75


def test_failed_bot_start_keeps_ranked_queue_entry(game, monkeypatch):
    app, _ = game
    player = register(app, "StillQueued")
    assert player.emit("queue_join")["ok"]
    assert player.events("queue_state")[-1]["queued"]

    def unavailable(**kwargs):
        raise MarketDataUnavailable("Inga spelbara kurser.")

    monkeypatch.setattr(app.extensions["match_service"].provider, "choose", unavailable)
    assert player.emit("bot_start") == {"ok": False, "error": "Inga spelbara kurser."}
    advance(game, 1)
    assert player.events("queue_state")[-1]["queued"]
    assert player.emit("queue_leave")["ok"]


def test_prediction_queue_pairs_only_with_prediction_and_uses_its_elo(game):
    app, _ = game
    trader = register(app, "TradeQueue")
    first = register(app, "FirstPredictor")
    second = register(app, "SecondPredictor")
    with app.app_context():
        db.session.get(PlayerRating, (second.id, "ranked")).elo = 550
        db.session.commit()

    assert trader.emit("queue_join")["ok"]
    assert first.emit("queue_join", {"mode": "prediction"})["ok"]
    assert first.events("queue_state")[-1]["mode"] == "prediction"
    assert not trader.events("match_state")

    assert second.emit("queue_join", {"mode": "prediction"})["ok"]
    first_state, second_state = first.state(), second.state()
    assert first_state["id"] == second_state["id"]
    assert first_state["mode"] == second_state["mode"] == "prediction"
    assert first_state["opponent"]["id"] == second.id
    assert not trader.events("match_state")
    assert trader.emit("queue_leave")["ok"]


def test_prediction_rounds_reconnect_and_persist_in_separate_ranking(game):
    app, _ = game
    first = register(app, "BullPredictor")
    second = register(app, "BearPredictor")
    ranked_profiles = [player.http.get("/api/profile").get_json() for player in (first, second)]
    ranked_leaders = first.http.get("/api/leaderboard").get_json()

    for player in (first, second):
        assert player.emit("queue_join", {"mode": "prediction"})["ok"]
    initial = first.state()
    assert initial["status"] == "countdown"
    assert len(initial["bars"]) == 12
    assert initial["bars"] == second.state()["bars"]

    def submit(player, number, move_bps):
        return player.emit("prediction_submit", {
            "matchId": initial["id"], "round": number, "moveBps": move_bps,
        })

    assert not submit(first, 1, 200)["ok"]
    advance(game, 3)
    first_active = first.state()
    assert first_active["round"]["phase"] == "predict"
    assert not submit(first, 1, True)["ok"]
    assert submit(first, 1, 200)["ok"]

    # Time and the other player's lock can change without exposing either answer.
    advance(game, 2)
    first_locked, second_waiting = first.state(), second.state()
    assert first_locked["round"]["selfMoveBps"] == 200
    assert second_waiting["round"]["opponentLocked"]
    assert second_waiting["round"]["selfMoveBps"] is None
    assert second_waiting["round"]["outcome"] is None
    assert "opponentMoveBps" not in second_waiting["round"]
    assert "actualMoveBps" not in second_waiting["round"]
    assert first_locked["bars"] == second_waiting["bars"] == initial["bars"]
    assert FIRST_BAR.date().isoformat() not in json.dumps(second_waiting)

    first.socket.disconnect()
    first.connect()
    resumed = first.state()
    assert resumed["id"] == initial["id"]
    assert resumed["round"] == first_locked["round"]
    assert not submit(first, 1, -200)["ok"]
    assert submit(second, 1, 100)["ok"]
    first_reveal, second_reveal = first.state(), second.state()
    assert first_reveal["round"]["phase"] == "reveal"
    first_outcome = first_reveal["round"]["outcome"]
    second_outcome = second_reveal["round"]["outcome"]
    assert first_outcome["actualMoveBps"] == second_outcome["actualMoveBps"] == 200
    assert first_outcome["opponentMoveBps"] == second_outcome["selfMoveBps"] == 100
    assert first_outcome["selfMoveBps"] == second_outcome["opponentMoveBps"] == 200
    assert first_outcome["damage"] == 30 and first_outcome["winnerId"] == first.id
    assert first_reveal["opponent"]["hp"] == second_reveal["self"]["hp"] == 70
    assert len(first_reveal["bars"]) == 13

    # Alternate rising and falling closes from the deterministic provider.
    for number, exact_bps in ((2, -196), (3, 200), (4, -196)):
        advance(game, 4)
        next_round = first.state()["round"]
        assert next_round["number"] == number and next_round["phase"] == "predict"
        assert not submit(first, number - 1, exact_bps)["ok"]
        assert submit(first, number, exact_bps)["ok"]
        assert submit(second, number, 0)["ok"]
    final_reveal = first.state()
    assert final_reveal["round"]["phase"] == "reveal"
    assert final_reveal["opponent"]["hp"] == 0
    assert final_reveal["round"]["outcome"]["damage"] == 10

    advance(game, 4)
    winner, = first.events("match_result")
    loser, = second.events("match_result")
    assert winner["id"] == loser["id"] == initial["id"]
    assert winner["mode"] == loser["mode"] == "prediction"
    assert (winner["outcome"], loser["outcome"]) == ("win", "lose")
    assert (winner["eloBefore"], winner["eloAfter"], loser["eloBefore"], loser["eloAfter"]) == (100, 116, 100, 84)
    assert winner["roundsPlayed"] == loser["roundsPlayed"] == 4
    assert winner["hp"] == winner["attackDamage"] == 100
    assert winner["lastRound"]["actualMoveBps"] == -196
    assert winner["endReason"] == loser["endReason"] == "knockout"
    assert winner["opponentHp"] == 0 and loser["opponentHp"] == 100
    assert [round_result["number"] for round_result in winner["rounds"]] == [1, 2, 3, 4]
    assert winner["rounds"][0] == {"number": 1, **first_outcome}
    assert loser["rounds"][-1]["opponentMoveBps"] == winner["rounds"][-1]["selfMoveBps"]

    assert not submit(first, 4, -196)["ok"]
    advance(game, 10)
    assert not first.events("match_result") and not second.events("match_result")
    first.socket.disconnect()
    first.connect()
    assert first.events("match_result") == [winner]

    for player, ranked_profile, result in zip((first, second), ranked_profiles, (winner, loser), strict=True):
        assert player.http.get("/api/profile").get_json() == ranked_profile
        profile = player.http.get("/api/profile?mode=prediction").get_json()
        assert (profile["elo"], profile["matches"]) == (result["eloAfter"], 1)
        assert [entry["id"] for entry in profile["history"]] == [result["id"]]
    assert first.http.get("/api/leaderboard").get_json() == ranked_leaders
    leaders = first.http.get("/api/leaderboard?mode=prediction").get_json()["players"]
    assert [(row["username"], row["elo"]) for row in leaders] == [
        ("BullPredictor", 116), ("BearPredictor", 84),
    ]
    with app.app_context():
        stored_match = db.session.scalars(select(Match)).one()
        assert stored_match.id == winner["id"] and stored_match.mode == "prediction"
        assert db.session.scalar(select(func.count()).select_from(MatchResult)) == 2
        assert db.session.scalar(select(func.count()).select_from(TradeHistory)) == 0
