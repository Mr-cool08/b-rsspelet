from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

import pytest

from stockfight import company, create_app, socketio
from stockfight import campaign_http
from stockfight.campaign_http import COMPANY_NAMESPACE
from stockfight.company import CompanyError
from stockfight.data import CompanySave, User, db
from test_multiplayer import Clock, PASSWORD, post


STATE = "/api/company"
COMMANDS = "/api/company/commands"
STANDINGS = "/api/company/standings"
MARKET = "/api/company/market"


class TestCompanyQuotes:
    __test__ = False
    name = "Company test quotes"

    def __init__(self):
        self.market_open = True
        self.prices = {"F": 4_000, "SOFI": 2_000, "INTC": 3_000, "AMD": 15_000, "AAPL": 25_000}

    def snapshot(self, now):
        return self.market_open, {symbol: (price, now) for symbol, price in self.prices.items()}


@pytest.fixture
def company_app(tmp_path):
    config = {
        "TESTING": True,
        "SQLALCHEMY_DATABASE_URI": f"sqlite:///{(tmp_path / 'company.db').as_posix()}",
        "SECRET_KEY": "company-integration-test-key",
        "INVITE_CODE": "",
        "AUTO_SEED_DEMO": False,
        "MATCH_BACKGROUND": False,
        "COMPANY_LEGACY_TRADES": True,
    }
    return create_app(config), config


@pytest.fixture
def live_company_app(tmp_path):
    clock = Clock(now=500.0)
    quotes = TestCompanyQuotes()
    config = {
        "TESTING": True,
        "SQLALCHEMY_DATABASE_URI": f"sqlite:///{(tmp_path / 'live-company.db').as_posix()}",
        "SECRET_KEY": "live-company-integration-test-key",
        "INVITE_CODE": "",
        "AUTO_SEED_DEMO": False,
        "MATCH_BACKGROUND": False,
        "COMPANY_MARKET_BACKGROUND": False,
        "COMPANY_MARKET_CLOCK": clock,
        "COMPANY_MARKET_PROVIDER": quotes,
    }
    return create_app(config), config, clock, quotes


def register(app, username):
    http = app.test_client()
    assert post(http, "/api/register", {"username": username, "password": PASSWORD}).status_code == 201
    return http


def test_company_progress_saves_per_account(company_app):
    app, config = company_app
    visitor = app.test_client()
    assert visitor.get("/campaign").location == "/"
    assert visitor.get(STATE).status_code == 401

    player = register(app, "CompanyPlayer")
    other = register(app, "OtherCompany")
    assert "Börsföretag" in player.get("/").get_data(as_text=True)
    page = player.get("/campaign")
    assert page.status_code == 200 and b"/static/js/company.js" in page.data
    trade = {"action": "trade", "symbol": "AUR", "revision": 0}
    assert player.post(COMMANDS, json=trade).status_code == 403
    initial = player.get(STATE).json
    assert (initial["revision"], initial["day"], initial["level"]["number"]) == (0, 1, 1)
    unavailable = player.get(MARKET).json
    assert unavailable["status"] == "unavailable" and unavailable["source"] is None
    assert all(asset["price"] is None and not asset["tradable"] for asset in unavailable["assets"])

    portfolio = post(player, "/api/campaign/commands", {
        "action": "start", "revision": 0, "missionId": "rank1-fixed-1",
    }).json
    assert portfolio["attempt"] is not None
    assert player.get("/campaign/portfolio").status_code == 200

    response = post(player, COMMANDS, trade)
    assert response.status_code == 200, response.json
    advanced = response.json
    assert (advanced["revision"], advanced["day"], advanced["trades"]) == (1, 2, 1)
    aurora = next(asset for asset in initial["assets"] if asset["symbol"] == "AUR")
    assert advanced["cash"] == initial["cash"] + aurora["profit"]
    assert advanced["lastTrade"]["quantity"] == aurora["quantity"]
    assert player.get("/api/campaign").json["attempt"]["id"] == portfolio["attempt"]["id"]
    assert other.get(STATE).json == initial

    restarted = create_app(config).test_client()
    assert post(restarted, "/api/login", {"username": "CompanyPlayer", "password": PASSWORD}).status_code == 200
    assert restarted.get(STATE).json == advanced


def test_legacy_company_save_converts_on_first_successful_action(company_app):
    app, _ = company_app
    player = register(app, "ReturningFirm")
    player_id = player.get("/api/me").json["user"]["id"]
    legacy = {
        "status": "planning", "chapter": 0, "week": 3, "cash": 2050, "lots": {"AUR": [[3, 34]]},
        "history": [{"week": 1}, {"week": 2}, {"week": 3}],
        "standing": {"status": "planning", "chapter": 1, "week": 3, "equity": 2152, "cash": 2050},
    }
    with app.app_context():
        db.session.add(CompanySave(user_id=player_id, revision=7, state=legacy))
        db.session.commit()

    migrated = player.get(STATE).json
    assert (migrated["revision"], migrated["day"], migrated["level"]["number"], migrated["profit"]) == (7, 4, 2, 120)
    assert "previousCampaign" not in migrated
    listed = player.get(STANDINGS).json["companies"][0]
    assert (listed["id"], listed["isYou"], listed["level"], listed["profit"]) == (player_id, True, 2, 120)
    assert post(player, COMMANDS, {"action": "trade", "symbol": "KOB", "revision": 7}).json == {"error": "locked_asset"}
    with app.app_context():
        assert db.session.get(CompanySave, player_id).state == legacy

    response = post(player, COMMANDS, {"action": "trade", "symbol": "AUR", "revision": 7})
    assert response.status_code == 200, response.json
    assert response.json["revision"] == 8 and "previousCampaign" not in response.json
    with app.app_context():
        assert db.session.get(CompanySave, player_id).state["previousCampaign"] == legacy


def test_firm_administration_preserves_progress_and_settles_operating_decisions(company_app):
    app, config = company_app
    player = register(app, "FirmOperator")
    player_id = player.get("/api/me").json["user"]["id"]
    older_save = {
        "version": 2, "day": 4, "cash": 250, "profit": 60, "peakProfit": 60,
        "trades": 3, "upgrades": 0, "peerShares": {}, "lastTrade": None,
        "lastEmployeeTrades": [],
        "employees": [{"id": 1, "active": True, "trades": 10, "profit": -8, "strategy": "balanced"}],
    }
    with app.app_context():
        db.session.add(CompanySave(user_id=player_id, revision=3, state=older_save))
        db.session.commit()

    state = player.get(STATE).json
    assert state["revision"] == 3 and state["level"]["number"] == 2
    assert state["administration"]["desk"] == "lean"
    assert state["administration"]["reservePolicy"] == "standard"
    assert state["employees"][0]["focus"] == "all"
    assert state["upgrade"]["available"]
    initial_capacity = state["capacity"]

    def play(action, **payload):
        nonlocal state
        response = post(player, COMMANDS, {"action": action, "revision": state["revision"], **payload})
        assert response.status_code == 200, response.json
        state = response.json
        return state

    play("set_reserve_policy", policy="defensive")
    assert state["administration"]["reserve"] == 180
    assert state["cash"] == 250 and not state["upgrade"]["available"]
    rejected = post(player, COMMANDS, {"action": "upgrade", "revision": state["revision"]})
    assert rejected.status_code == 400 and rejected.json["error"] == "upgrade_unavailable"

    play("set_desk", desk="execution")
    desk = next(offer for offer in state["administration"]["desks"] if offer["id"] == "execution")
    assert state["capacity"] == initial_capacity + desk["capacityBonus"]
    assert state["administration"]["availableCash"] == 250 - 180 - desk["cost"]
    assert state["cash"] == 250 and state["day"] == 4

    rejected = post(player, COMMANDS, {
        "action": "set_employee_focus", "revision": state["revision"], "employeeId": 1, "symbol": "AAPL",
    })
    assert rejected.status_code == 400
    assert player.get(STATE).json == state

    play("set_employee_focus", employeeId=1, symbol="SOFI")
    assert state["employees"][0]["focus"] == "SOFI"
    play("close_day")
    report = state["administration"]["dayReport"]
    assert state["day"] == 5 and report["day"] == 4
    assert report["employeeTrades"] == []
    assert state["employees"][0]["trades"] == 10 and state["trades"] == 3
    assert report["operatingCost"] == desk["cost"] and report["tradingProfit"] == 0
    assert report["net"] == -report["operatingCost"] and report["employeeProfit"] == 0
    assert state["cash"] == report["cash"] == 250 + report["net"]
    assert state["profit"] == 60 + report["net"]
    assert state["administration"]["reports"] == [report]

    restarted = create_app(config).test_client()
    assert post(restarted, "/api/login", {"username": "FirmOperator", "password": PASSWORD}).status_code == 200
    assert restarted.get(STATE).json == state


@pytest.mark.parametrize("open_side,close_side,position_side,sign", [
    ("buy", "sell", "long", 1),
    ("short", "cover", "short", -1),
])
def test_live_company_orders_settle_revealed_prices_and_survive_restart(live_company_app, open_side, close_side, position_side, sign):
    from stockfight.company_live import run_live_tick

    app, config, clock, quotes = live_company_app
    assert app.test_client().get(MARKET).status_code == 401
    player = register(app, "LiveCompanyTrader")
    other = register(app, "LiveCompanyObserver")
    starting_cash = player.get(STATE).json["cash"]

    def quote(market, symbol="F"):
        return next(asset for asset in market["assets"] if asset["symbol"] == symbol)

    def market_tick(price):
        quotes.prices["F"] = price
        run_live_tick(app, int(clock.now) // 5)
        return player.get(MARKET).json

    quantity = 2
    market_tick(4_000)
    clock.now += 5
    opening = market_tick(4_100)
    assert opening["revision"] == 0 and opening["tickSeconds"] == 5
    assert opening["serverTime"] <= opening["nextTickAt"] <= opening["serverTime"] + 5
    assert quote(opening)["price"] == quote(other.get(MARKET).json)["price"]
    assert quote(opening)["position"] is None and quote(opening)["maxOrder"][open_side] >= quantity
    history = quote(opening)["history"]
    assert history[-1]["price"] == quote(opening)["price"]
    assert history[-1]["time"] <= opening["serverTime"]
    assert history[-1]["time"] - history[-2]["time"] == opening["tickSeconds"]

    def trade(tick, revision, side, **overrides):
        return post(player, COMMANDS, {
            "action": "market_trade", "symbol": "F", "quantity": quantity, "side": side,
            "tick": tick, "revision": revision, **overrides,
        })

    assert trade(opening["tick"], 0, open_side, symbol="AAPL").status_code == 400
    assert trade(opening["tick"], 0, open_side, quantity=True).status_code == 400
    entry_cents = 4_025
    clock.now += 5
    entry_market = market_tick(entry_cents)
    stale = trade(opening["tick"], 0, open_side)
    assert stale.status_code == 409 and stale.json["error"] == "stale_quote"
    assert stale.json["market"]["tick"] == opening["tick"] + 1
    assert stale.json["market"]["revision"] == 0 and quote(stale.json["market"])["position"] is None

    def fee_cents(price_cents):
        return (quantity * price_cents + 999) // 1_000

    entered = trade(entry_market["tick"], 0, open_side)
    assert entered.status_code == 200, entered.json
    after_entry = entered.json["market"]
    assert after_entry["revision"] == 1 and after_entry["fees"] == fee_cents(entry_cents) / 100
    position = quote(after_entry)["position"]
    assert (position["side"], position["quantity"], position["averagePrice"]) == (position_side, quantity, entry_cents / 100)
    assert after_entry["cash"] >= after_entry["reserve"] and after_entry["cash"] < starting_cash
    assert quote(other.get(MARKET).json)["position"] is None

    app = create_app(config)
    player = app.test_client()
    assert post(player, "/api/login", {"username": "LiveCompanyTrader", "password": PASSWORD}).status_code == 200
    assert quote(player.get(MARKET).json)["position"] == position

    exit_cents = entry_cents + sign * 250
    clock.now += 5
    moving = market_tick(exit_cents)
    assert moving["revision"] == 1 and quote(moving)["price"] == exit_cents / 100
    assert moving["unrealizedProfit"] > 0 and quote(moving)["maxOrder"][close_side] == quantity
    exited = trade(moving["tick"], 1, close_side)
    assert exited.status_code == 200, exited.json
    fees = fee_cents(entry_cents) + fee_cents(exit_cents)
    net = (sign * (exit_cents - entry_cents) * quantity - fees) / 100
    market = exited.json["market"]
    assert market["revision"] == 2 and quote(market)["position"] is None
    assert market["lastTrade"]["profit"] == net and market["lastTrade"]["price"] == exit_cents / 100
    assert market["fees"] == fees / 100
    assert market["cash"] == market["equity"] == starting_cash + net
    assert exited.json["profit"] == net
    assert trade(moving["tick"], 1, close_side).status_code == 409

    closed_day = post(player, COMMANDS, {"revision": 2, "action": "close_day"})
    assert closed_day.status_code == 200, closed_day.json
    assert closed_day.json["administration"]["dayReport"]["tradingProfit"] == net


def test_bot_strategies_evaluate_the_same_market_move_differently():
    from stockfight.company_bots import signal

    config = {"lookback": 3, "threshold": 2, "stopLoss": 3, "takeProfit": 3}
    rising = [4_000, 4_000, 4_000, 4_400]
    recovering = [4_000, 4_500, 3_900, 4_200]
    falling = [4_100, 4_200, 4_300, 3_850]
    assert signal({**config, "strategy": "momentum"}, rising) == "buy"
    assert signal({**config, "strategy": "mean_reversion"}, rising) == "sell"
    assert signal({**config, "strategy": "breakout"}, rising) == "buy"
    assert signal({**config, "strategy": "momentum"}, recovering) == "buy"
    assert signal({**config, "strategy": "breakout"}, recovering) is None
    assert signal({**config, "strategy": "momentum"}, falling) == "sell"
    assert signal({**config, "strategy": "mean_reversion"}, falling) == "buy"


def test_offline_bots_trade_both_firms_once_per_published_tick(live_company_app):
    from stockfight.company_live import run_live_tick

    app, _, clock, quotes = live_company_app
    players = [register(app, username) for username in ("OfflineOperator", "OfflineManager")]
    player_ids = [player.get("/api/me").json["user"]["id"] for player in players]

    def publish(price):
        quotes.prices["F"] = price
        run_live_tick(app, int(clock.now) // 5)

    publish(4_000)
    for _ in range(3):
        clock.now += 5
        publish(4_000)

    for player in players:
        hired = post(player, COMMANDS, {"action": "hire", "revision": 0})
        assert hired.status_code == 200, hired.json
        configured = post(player, COMMANDS, {
            "action": "set_employee_bot", "revision": hired.json["revision"], "employeeId": 1,
            "strategy": "momentum", "lookback": 3, "threshold": 2, "stopLoss": 3, "takeProfit": 3,
        })
        assert configured.status_code == 200, configured.json
        chosen = post(player, COMMANDS, {
            "action": "set_employee_focus", "revision": configured.json["revision"], "employeeId": 1, "symbol": "F",
        })
        assert chosen.status_code == 200, chosen.json

    live_state = players[0].get(STATE).json
    for action in ("trade", "advance"):
        rejected = post(players[0], COMMANDS, {"action": action, "symbol": "AUR", "revision": live_state["revision"]})
        assert rejected.status_code == 400 and rejected.json == {"error": "invalid_command"}
    assert players[0].get(STATE).json == live_state

    def saved_firms():
        with app.app_context():
            rows = [db.session.get(CompanySave, player_id) for player_id in player_ids]
            return [(row.revision, row.state) for row in rows]

    before = saved_firms()
    clock.now += 5
    publish(4_400)
    opened = saved_firms()
    assert all(current[0] > old[0] for old, current in zip(before, opened))
    publish(4_400)
    assert saved_firms() == opened

    clock.now += 5
    publish(4_800)
    settled = saved_firms()
    assert all(current[0] > old[0] for old, current in zip(opened, settled))
    publish(4_800)
    assert saved_firms() == settled

    for player in players:
        snapshot = player.get(STATE).json
        assert snapshot["cash"] > 400 and snapshot["profit"] > 0
        assert snapshot["employees"][0]["profit"] > 0 and snapshot["employees"][0]["focus"] == "F"
        employee = player.get(MARKET).json["bots"][0]
        assert employee["position"] is None and employee["lastTrade"]["reason"] == "take_profit"
        assert employee["lastTrade"]["symbol"] == "F" and employee["lastTrade"]["profit"] > 0
        closed = post(player, COMMANDS, {"action": "close_day", "revision": snapshot["revision"]})
        assert closed.status_code == 200, closed.json
        report = closed.json["administration"]["dayReport"]
        assert report["employeeProfit"] == snapshot["employees"][0]["profit"]
        assert report["tradingProfit"] == 0 and report["net"] == snapshot["profit"]


def test_company_closed_market_exposes_quotes_but_rejects_orders(live_company_app):
    from stockfight.company_live import run_live_tick

    app, _, clock, quotes = live_company_app
    player = register(app, "ClosedMarketTrader")
    run_live_tick(app, int(clock.now) // 5)
    opened = player.get(MARKET).json
    assert opened["status"] == "open" and opened["source"] == quotes.name
    stock = next(asset for asset in opened["assets"] if asset["symbol"] == "F")
    assert stock["tradable"] and stock["price"] == 40 and stock["quotedAt"] == clock.now

    clock.now += 5
    quotes.market_open = False
    run_live_tick(app, int(clock.now) // 5)
    closed = player.get(MARKET).json
    assert closed["status"] == "closed" and closed["revision"] == 0
    assert all(not asset["tradable"] for asset in closed["assets"])
    rejected = post(player, COMMANDS, {
        "action": "market_trade", "revision": 0, "tick": closed["tick"], "side": "buy", "symbol": "F", "quantity": 1,
    })
    assert rejected.status_code == 400 and rejected.json["error"] == "market_closed"
    assert player.get(STATE).json["revision"] == 0


def test_company_trade_can_settle_only_once_per_revision(company_app, monkeypatch):
    app, _ = company_app
    player = register(app, "ParallelCompany")
    cookie = player.get_cookie(app.config["SESSION_COOKIE_NAME"])
    token = player.get("/api/me").json["csrfToken"]
    barrier = Barrier(2, timeout=10)
    apply = company.apply_command

    def synchronized_apply(state, command):
        apply(state, command)
        barrier.wait()

    def trade():
        http = app.test_client()
        http.set_cookie(cookie.key, cookie.value)
        return http.post(COMMANDS, json={"action": "trade", "symbol": "AUR", "revision": 0},
                         headers={"X-CSRF-Token": token})

    monkeypatch.setattr(company, "apply_command", synchronized_apply)
    with ThreadPoolExecutor(max_workers=2) as executor:
        first, second = executor.submit(trade), executor.submit(trade)
        winner, conflict = sorted((first.result(), second.result()), key=lambda response: response.status_code)
    assert (winner.status_code, conflict.status_code) == (200, 409)
    assert conflict.json == {"error": "stale_revision", "state": winner.json}
    assert (winner.json["revision"], winner.json["day"], winner.json["trades"]) == (1, 2, 1)
    assert player.get(STATE).json == winner.json


def test_trading_unlocks_new_stocks_and_reinvestment_increases_capacity():
    state = company.default_state()
    start = company.public_state(state)
    assert [offer["symbol"] for offer in start["assets"] if offer["unlocked"]] == ["AUR"]

    with pytest.raises(CompanyError, match="locked_asset"):
        company.apply_command(state, {"action": "trade", "symbol": start["nextLevel"]["unlock"]["symbol"]})
    assert company.public_state(state) == start

    company.apply_command(state, {"action": "upgrade"})
    upgraded = company.public_state(state)
    assert upgraded["cash"] == start["cash"] - start["upgrade"]["price"]
    assert upgraded["capacity"] == start["capacity"] + start["upgrade"]["bonus"]
    assert upgraded["day"] == start["day"]

    for _ in range(12):
        before = company.public_state(state)
        offer = max((item for item in before["assets"] if item["unlocked"]), key=lambda item: item["profit"])
        company.apply_command(state, {"action": "trade", "symbol": offer["symbol"]})
        after = company.public_state(state)
        assert after["cash"] == before["cash"] + offer["profit"]
        assert after["lastTrade"]["quantity"] == offer["quantity"]
        assert after["capacity"] >= before["capacity"]
    assert after["nextLevel"] is None
    assert all(asset["unlocked"] for asset in after["assets"])


def test_employee_risk_styles_and_experience_affect_real_results():
    first_losses = {}
    for strategy in ("careful", "aggressive"):
        state = company.default_state()
        start = company.public_state(state)
        company.apply_command(state, {"action": "hire"})
        hired = company.public_state(state)
        employee = hired["employees"][0]
        assert hired["cash"] == start["cash"] - start["hire"]["price"]
        assert employee["trades"] == 0 and employee["skill"] == 0
        company.apply_command(state, {"action": "set_employee_strategy", "employeeId": employee["id"], "strategy": strategy})
        company.apply_command(state, {"action": "advance"})
        first = company.public_state(state)
        first_losses[strategy] = first["lastEmployeeTrades"][0]["profit"]
        assert first["cash"] == hired["cash"] + first_losses[strategy]
        assert first["employees"][0]["skill"] > 0
        assert first["lastTrade"] is None and first["employees"][0]["trades"] == 1

        company.apply_command(state, {"action": "toggle_employee", "employeeId": employee["id"]})
        with pytest.raises(CompanyError, match="no_active_employee"):
            company.apply_command(state, {"action": "advance"})
        company.apply_command(state, {"action": "trade", "symbol": "AUR"})
        paused = company.public_state(state)
        assert paused["lastEmployeeTrades"] == [] and paused["employees"][0]["trades"] == 1
        company.apply_command(state, {"action": "toggle_employee", "employeeId": employee["id"]})
        for _ in range(25):
            before = company.public_state(state)
            offer = max((asset for asset in before["assets"] if asset["unlocked"]), key=lambda asset: asset["profit"])
            company.apply_command(state, {"action": "trade", "symbol": offer["symbol"]})
        trained = company.public_state(state)["employees"][0]
        assert trained["trades"] == 26 and trained["skill"] == 100
        assert trained["profit"] > 0
    assert first_losses["aggressive"] < first_losses["careful"] < 0


def test_listed_firms_trade_with_live_quotes_and_private_positions(company_app):
    app, _ = company_app
    visitor = app.test_client()
    assert visitor.get(STANDINGS).status_code == 401
    anonymous = socketio.test_client(app, flask_test_client=visitor, namespace=COMPANY_NAMESPACE,
                                     auth={"csrfToken": visitor.get("/api/me").json["csrfToken"]})
    assert not anonymous.is_connected(COMPANY_NAMESPACE)

    issuer = register(app, "ListedFirm")
    buyer = register(app, "BuyingFirm")
    rejected = socketio.test_client(app, flask_test_client=buyer, namespace=COMPANY_NAMESPACE,
                                    auth={"csrfToken": "invalid"})
    assert not rejected.is_connected(COMPANY_NAMESPACE)
    watcher = socketio.test_client(app, flask_test_client=buyer, namespace=COMPANY_NAMESPACE,
                                   auth={"csrfToken": buyer.get("/api/me").json["csrfToken"]})
    assert watcher.is_connected(COMPANY_NAMESPACE)

    try:
        listed_at_registration = buyer.get(STANDINGS).json["companies"]
        assert {firm["name"] for firm in listed_at_registration} == {"BuyingFirm Capital", "ListedFirm Capital"}
        assert all(firm["price"] == 25 and firm["held"] == 0 for firm in listed_at_registration)
        company_trade = {"action": "trade", "symbol": "AUR", "revision": 0}
        assert post(issuer, COMMANDS, company_trade).status_code == 200
        assert [event["name"] for event in watcher.get_received(COMPANY_NAMESPACE)] == ["company_market_changed"]

        listed = buyer.get(STANDINGS).json["companies"][0]
        assert set(listed) == {"id", "name", "isYou", "level", "profit", "price", "held"}
        assert listed["name"] == "ListedFirm Capital" and not listed["isYou"] and listed["held"] == 0
        buy = {"action": "buy_peer", "firmId": listed["id"], "quote": listed["price"], "revision": 0}
        self_trade = post(issuer, COMMANDS, {**buy, "revision": 1})
        assert self_trade.status_code == 400 and self_trade.json == {"error": "self_trade"}

        wallet = buyer.get(STATE).json["cash"]
        bought = post(buyer, COMMANDS, buy)
        assert bought.status_code == 200, bought.json
        assert bought.json["cash"] == wallet - listed["price"]
        assert buyer.get(STANDINGS).json["companies"][0]["held"] == 1
        visible_to_issuer = issuer.get(STANDINGS).json["companies"]
        assert visible_to_issuer[0]["isYou"] and all(firm["held"] == 0 for firm in visible_to_issuer)
        assert "peerShares" not in bought.json
        assert [event["name"] for event in watcher.get_received(COMPANY_NAMESPACE)] == ["company_market_changed"]

        assert post(issuer, COMMANDS, {**company_trade, "revision": 1}).status_code == 200
        assert [event["name"] for event in watcher.get_received(COMPANY_NAMESPACE)] == ["company_market_changed"]
        current = buyer.get(STANDINGS).json["companies"][0]
        assert current["price"] > listed["price"] and current["held"] == 1

        sale = {**buy, "action": "sell_peer", "revision": 1}
        stale = post(buyer, COMMANDS, sale)
        assert stale.status_code == 409 and stale.json["error"] == "stale_quote"
        assert stale.json["state"] == bought.json and not watcher.get_received(COMPANY_NAMESPACE)
        sold = post(buyer, COMMANDS, {**sale, "quote": current["price"]})
        assert sold.status_code == 200, sold.json
        assert sold.json["cash"] == wallet - listed["price"] + current["price"]
        assert buyer.get(STANDINGS).json["companies"][0]["held"] == 0
        oversold = post(buyer, COMMANDS, {**sale, "quote": current["price"], "revision": 2})
        assert oversold.status_code == 400 and oversold.json == {"error": "insufficient_shares"}
    finally:
        watcher.disconnect(namespace=COMPANY_NAMESPACE)


def test_new_company_shares_can_trade_before_the_issuer_plays(company_app):
    app, _ = company_app
    issuer = register(app, "UnplayedIssuer")
    buyer = register(app, "EarlyInvestor")
    issuer_id = issuer.get("/api/me").json["user"]["id"]
    company_row = next(row for row in buyer.get(STANDINGS).json["companies"] if row["id"] == issuer_id)
    assert company_row["price"] == 25 and company_row["held"] == 0
    funds = buyer.get(STATE).json["cash"]
    order = {"firmId": issuer_id, "quote": company_row["price"]}

    bought = post(buyer, COMMANDS, {**order, "action": "buy_peer", "revision": 0})
    assert bought.status_code == 200, bought.json
    assert bought.json["cash"] == funds - company_row["price"]
    held = next(row for row in buyer.get(STANDINGS).json["companies"] if row["id"] == issuer_id)
    assert held["held"] == 1

    sold = post(buyer, COMMANDS, {**order, "action": "sell_peer", "revision": 1})
    assert sold.status_code == 200, sold.json
    assert sold.json["cash"] == funds and issuer.get(STATE).json["revision"] == 0


def test_company_search_can_find_and_trade_firms_outside_the_leading_rows(company_app):
    app, _ = company_app
    target = register(app, "ZebraCapital")
    buyer = register(app, "BuyerSearcher")
    target_id = target.get("/api/me").json["user"]["id"]
    with app.app_context():
        for index in range(50):
            username = f"EarlierFirm{index:02}"
            db.session.add(User(username=username, username_key=username.casefold(), password_hash="test-only"))
        db.session.commit()

    first_page = buyer.get(STANDINGS).json
    assert first_page["hasMore"] and all(row["id"] != target_id for row in first_page["companies"])
    second_page = buyer.get(STANDINGS, query_string={"page": 2}).json
    assert second_page["page"] == 2 and not second_page["hasMore"]
    assert any(row["id"] == target_id for row in second_page["companies"])
    search = buyer.get(STANDINGS, query_string={"search": "BRACAP"}).json
    firm = next(row for row in search["companies"] if row["id"] == target_id)
    assert not search["hasMore"] and firm["price"] == 25 and firm["held"] == 0
    bought = post(buyer, COMMANDS, {"action": "buy_peer", "revision": 0, "firmId": target_id, "quote": firm["price"]})
    assert bought.status_code == 200, bought.json
    filtered = buyer.get(STANDINGS, query_string={"search": "earlierfirm00"}).json
    assert filtered["holdingsValue"] == firm["price"]


@pytest.mark.parametrize("buyer_revision,issuer_revision", [(0, 0), (0, 1), (1, 1)])
def test_company_quote_is_checked_during_the_buyers_write(company_app, monkeypatch, buyer_revision, issuer_revision):
    app, _ = company_app
    issuer = register(app, "MovingFirm")
    buyer = register(app, "PendingBuyer")
    trade = {"action": "trade", "symbol": "AUR", "revision": 0}
    if issuer_revision:
        assert post(issuer, COMMANDS, trade).status_code == 200
    if buyer_revision:
        assert post(buyer, COMMANDS, trade).status_code == 200
    original = buyer.get(STATE).json
    firm = next(row for row in buyer.get(STANDINGS).json["companies"] if not row["isYou"])
    save = campaign_http.save_campaign

    def settle_after_repricing(*args, **kwargs):
        if kwargs.get("condition") is not None:
            with ThreadPoolExecutor(max_workers=1) as executor:
                response = executor.submit(post, issuer, COMMANDS, {**trade, "revision": issuer_revision}).result()
            assert response.status_code == 200
        return save(*args, **kwargs)

    monkeypatch.setattr(campaign_http, "save_campaign", settle_after_repricing)
    response = post(buyer, COMMANDS, {
        "action": "buy_peer", "firmId": firm["id"], "quote": firm["price"], "revision": buyer_revision,
    })
    assert response.status_code == 409
    assert response.json == {"error": "stale_quote", "state": original}
    assert buyer.get(STATE).json == original
    updated = next(row for row in buyer.get(STANDINGS).json["companies"] if row["id"] == firm["id"])
    assert updated["price"] > firm["price"] and updated["held"] == 0
