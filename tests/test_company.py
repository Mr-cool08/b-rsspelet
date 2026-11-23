from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

import pytest

from stockfight import company, create_app, socketio
from stockfight import campaign_http
from stockfight.campaign_http import COMPANY_NAMESPACE
from stockfight.company import CompanyError
from stockfight.data import CompanySave, db
from test_multiplayer import PASSWORD, post


STATE = "/api/company"
COMMANDS = "/api/company/commands"
STANDINGS = "/api/company/standings"


@pytest.fixture
def company_app(tmp_path):
    config = {
        "TESTING": True,
        "SQLALCHEMY_DATABASE_URI": f"sqlite:///{(tmp_path / 'company.db').as_posix()}",
        "SECRET_KEY": "company-integration-test-key",
        "INVITE_CODE": "",
        "AUTO_SEED_DEMO": False,
        "MATCH_BACKGROUND": False,
    }
    return create_app(config), config


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
        assert buyer.get(STANDINGS).json["companies"] == []
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


@pytest.mark.parametrize("buyer_revision", [0, 1])
def test_company_quote_is_checked_during_the_buyers_write(company_app, monkeypatch, buyer_revision):
    app, _ = company_app
    issuer = register(app, "MovingFirm")
    buyer = register(app, "PendingBuyer")
    trade = {"action": "trade", "symbol": "AUR", "revision": 0}
    assert post(issuer, COMMANDS, trade).status_code == 200
    if buyer_revision:
        assert post(buyer, COMMANDS, trade).status_code == 200
    original = buyer.get(STATE).json
    firm = next(row for row in buyer.get(STANDINGS).json["companies"] if not row["isYou"])
    save = campaign_http.save_campaign

    def settle_after_repricing(*args, **kwargs):
        if kwargs.get("condition") is not None:
            with ThreadPoolExecutor(max_workers=1) as executor:
                response = executor.submit(post, issuer, COMMANDS, {**trade, "revision": 1}).result()
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
