from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

import pytest

from stockfight import company, create_app
from stockfight.company import CompanyError
from test_multiplayer import PASSWORD, post


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


def test_company_campaign_replaces_menu_entry_and_saves_per_account(company_app):
    app, config = company_app
    visitor = app.test_client()
    assert visitor.get("/campaign").location == "/"
    assert visitor.get("/api/company").status_code == 401

    player = register(app, "CompanyPlayer")
    other = register(app, "OtherCompany")
    assert "Börsföretag" in player.get("/").get_data(as_text=True)
    page = player.get("/campaign")
    assert page.status_code == 200 and b"/static/js/company.js" in page.data
    assert player.post("/api/company/commands", json={"action": "settle", "revision": 0}).status_code == 403
    initial = player.get("/api/company").json
    assert initial["revision"] == 0 and initial["week"] == 1 and initial["status"] == "planning"

    legacy = post(player, "/api/campaign/commands", {
        "action": "start", "revision": 0, "missionId": "rank1-fixed-1",
    }).json
    assert legacy["attempt"] is not None
    assert player.get("/campaign/portfolio").status_code == 200

    response = post(player, "/api/company/commands", {"action": "settle", "revision": 0})
    assert response.status_code == 200, response.json
    advanced = response.json
    assert advanced["revision"] == 1 and advanced["week"] == 2
    assert advanced["market"] == initial["nextMarket"]
    assert advanced["cash"] == initial["cash"] - initial["overhead"]
    assert player.get("/api/campaign").json["attempt"]["id"] == legacy["attempt"]["id"]
    assert other.get("/api/company").json == initial

    restarted = create_app(config).test_client()
    assert post(restarted, "/api/login", {"username": "CompanyPlayer", "password": PASSWORD}).status_code == 200
    assert restarted.get("/api/company").json == advanced


def test_concurrent_company_plans_settle_only_once(company_app, monkeypatch):
    app, _ = company_app
    player = register(app, "ParallelCompany")
    cookie = player.get_cookie(app.config["SESSION_COOKIE_NAME"])
    token = player.get("/api/me").json["csrfToken"]
    barrier = Barrier(2, timeout=10)
    apply = company.apply_command

    def synchronized_apply(state, command):
        apply(state, command)
        barrier.wait()

    def settle():
        http = app.test_client()
        http.set_cookie(cookie.key, cookie.value)
        return http.post("/api/company/commands", json={"action": "settle", "revision": 0},
                         headers={"X-CSRF-Token": token})

    monkeypatch.setattr(company, "apply_command", synchronized_apply)
    with ThreadPoolExecutor(max_workers=2) as executor:
        first, second = executor.submit(settle), executor.submit(settle)
        winner, conflict = sorted((first.result(), second.result()), key=lambda response: response.status_code)
    assert (winner.status_code, conflict.status_code) == (200, 409)
    assert conflict.json == {"error": "stale_revision", "state": winner.json}
    assert winner.json["revision"] == 1 and len(winner.json["history"]) == 1


def test_company_standings_show_other_accounts_in_rank_order(company_app):
    app, _ = company_app
    endpoint = "/api/company/standings"
    assert app.test_client().get(endpoint).status_code == 401
    first = register(app, "FirstFirm")
    second = register(app, "SecondFirm")
    assert first.get(endpoint).json == {"companies": []}

    initial = first.get("/api/company").json
    product = initial["market"]["products"][0]["id"]
    command = {"action": "settle", "revision": 0}
    assert post(first, "/api/company/commands", command).status_code == 200
    assert post(second, "/api/company/commands", {**command, "purchases": {product: 10}}).status_code == 200
    best, other = first.get(endpoint).json["companies"]
    assert (best["name"], best["rank"], best["isYou"]) == ("SecondFirm Capital", 1, False)
    assert (other["name"], other["rank"], other["isYou"]) == ("FirstFirm Capital", 2, True)
    assert best["week"] == other["week"] == 1 and best["equity"] > other["equity"]
    assert set(best) == {"status", "chapter", "week", "equity", "cash", "rank", "name", "isYou"}
    assert second.get(endpoint).json["companies"][0]["isYou"] is True

    assert post(first, "/api/company/commands", {**command, "revision": 1}).status_code == 200
    leader = second.get(endpoint).json["companies"][0]
    assert leader["name"] == "FirstFirm Capital" and leader["week"] == 2


def test_company_carries_inventory_and_accounts_for_historical_cost():
    state = company.default_state()
    initial = company.public_state(state)
    first = initial["market"]["products"][0]
    product = first["id"]
    premium = next(tier for tier in first["tiers"] if tier["id"] == "premium")
    count = premium["demand"] + 5
    plan = {"action": "settle", "purchases": {product: count}, "tiers": {product: "premium"}}

    with pytest.raises(CompanyError, match="invalid_purchase"):
        company.apply_command(state, {"action": "settle", "purchases": {product: True}})
    assert company.public_state(state) == initial
    company.apply_command(state, plan)
    second = company.public_state(state)
    assert second["inventory"][product] == 5
    assert second["inventoryValue"] == first["buyPrice"] * 5
    assert second["lastReport"]["profit"] == premium["demand"] * (premium["price"] - first["buyPrice"]) - initial["overhead"]

    supplier = second["market"]["products"][0]
    company.apply_command(state, {"action": "settle", "purchases": {product: 3}})
    third = company.public_state(state)
    report = third["lastReport"]
    assert report["costOfGoods"] == 5 * first["buyPrice"] + 3 * supplier["buyPrice"]
    assert report["products"][0]["sold"] == 8 and third["inventory"][product] == 0
    assert third["cash"] == second["cash"] - report["purchaseCost"] + report["revenue"] - report["overhead"]


def test_company_failed_chapter_can_be_retried_with_same_market():
    state = company.default_state()
    initial = company.public_state(state)
    for _ in range(initial["weeksInChapter"]):
        company.apply_command(state, {"action": "settle"})
    failed = company.public_state(state)
    assert failed["status"] == "failed" and failed["chapterOutcome"]["reason"] == "goals"
    assert failed["market"] is None and failed["nextMarket"] is None
    company.apply_command(state, {"action": "retry"})
    assert company.public_state(state) == initial


def test_company_can_use_forecast_to_complete_the_campaign():
    state = company.default_state()
    symbols = ("AUR", "DIM", "LIN")
    tiers = {"r": "regular", "l": "low", "p": "premium"}
    # Build up a position before week 10 because its block order exceeds that week's supply.
    plans = (
        ((18, 12, 12), "rrr"), ((7, 5, 34), "ppl"), ((9, 21, 10), "prr"), ((15, 14, 17), "rrp"),
        ((31, 8, 7), "rpp"), ((15, 16, 11), "rpr"), ((9, 8, 29), "ppr"), ((10, 19, 16), "prr"),
        ((28, 7, 11), "rpp"), ((5, 17, 12), "prr"), ((8, 23, 15), "prr"), ((19, 7, 17), "rpp"),
    )
    for week, (purchases, prices) in enumerate(plans, 1):
        before = company.public_state(state)
        assert (before["status"], before["week"]) == ("planning", week)
        if week == 9:
            next_market = before["nextMarket"]
            assert next_market["contract"]["productId"] == "AUR"
            assert next_market["contract"]["units"] > next_market["products"][0]["supply"]
        company.apply_command(state, {
            "action": "settle",
            "purchases": dict(zip(symbols, purchases, strict=True)),
            "tiers": {symbol: tiers[tier] for symbol, tier in zip(symbols, prices, strict=True)},
            "acceptContract": week in (5, 7, 10),
        })
        after = company.public_state(state)
        if week in (5, 7, 10):
            order = before["market"]["contract"]
            line = next(item for item in after["lastReport"]["products"] if item["id"] == order["productId"])
            assert line["contractUnits"] == order["units"]
        if week in (4, 8, 12):
            assert after["chapterOutcome"]["status"] == "passed"

    final = company.public_state(state)
    assert final["status"] == "won" and final["nextMarket"] is None
    assert company.public_standing(state)["week"] == 12
    company.apply_command(state, {"action": "restart"})
    assert company.public_state(state) == company.public_state(company.default_state())
