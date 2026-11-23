from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

import pytest
from sqlalchemy import func, select

from stockfight import create_app
from stockfight import campaign as career
from stockfight.campaign_catalog import MISSIONS, PHASE_STEPS, PREVIEW, generate_prices, market_outlooks
from stockfight.data import CampaignSave, Match, PlayerRating, db

from test_multiplayer import Clock, PASSWORD, post


@pytest.fixture
def campaign(tmp_path):
    clock = Clock()
    config = {
        "TESTING": True,
        "SQLALCHEMY_DATABASE_URI": f"sqlite:///{(tmp_path / 'campaign.db').as_posix()}",
        "SECRET_KEY": "campaign-integration-tests-key",
        "INVITE_CODE": "",
        "AUTO_SEED_DEMO": False,
        "MATCH_BACKGROUND": False,
        "CAMPAIGN_CLOCK": clock,
    }
    return create_app(config), config, clock


def register(app, username):
    http = app.test_client()
    assert post(http, "/api/register", {"username": username, "password": PASSWORD}).status_code == 201
    return http


def read(http):
    response = http.get("/api/campaign")
    assert response.status_code == 200
    return response.get_json()


def command(http, revision, action, **payload):
    return post(http, "/api/campaign/commands", {"revision": revision, "action": action, **payload})


def test_catalog_has_five_playable_stages_and_seeded_variations():
    direction_ranges = {
        "strongDown": (float("-inf"), -5),
        "down": (-6, -1),
        "steady": (-2, 2),
        "up": (1, 6),
        "strongUp": (5, float("inf")),
    }
    for rank, capital in enumerate((5_000, 12_500, 25_000, 50_000, 125_000)):
        missions = [mission for mission in MISSIONS.values() if mission["rank"] == rank]
        assert sorted(mission["kind"] for mission in missions) == ["comeback"] + ["elective"] * 7 + ["exam"] + ["fixed"] * 3
        for mission in missions:
            assert mission["capital"] == capital
            prices = generate_prices(mission, 21)
            assert prices == generate_prices(mission, 21)
            assert prices != generate_prices(mission, 22)
            assert len(prices) == PREVIEW + 1 + mission["steps"]
            assert all(len(prices_on_day) == len(mission["assets"]) for prices_on_day in prices)
            assert mission["titleEn"] and mission["briefEn"]
            for outlook in market_outlooks(mission, 21):
                assert set(outlook["assets"]) == set(mission["assets"])
                for column, asset in enumerate(mission["assets"]):
                    before = float(prices[PREVIEW + outlook["startStep"]][column])
                    after = float(prices[PREVIEW + outlook["throughStep"]][column])
                    lower, upper = direction_ranges[outlook["assets"][asset]["direction"]]
                    assert lower < (after / before - 1) * 100 < upper
            if mission["kind"] in {"fixed", "elective"}:
                assert 18 <= mission["steps"] <= 24


def test_mission_replays_keep_prices_and_reveal_only_the_current_outlook():
    mission = MISSIONS["rank1-fixed-1"]
    state = career.default_state()

    def play(action, **data):
        career.apply_command(state, {"action": action, **data}, 100)
        return career.public_state(state, 100)["attempt"]

    started = play("start", missionId=mission["id"])
    original = state["attempt"]
    assert len(started["prices"]) == PREVIEW + 1
    assert "outlooks" not in started
    first, second, third = original["outlooks"]
    for index, outlook in enumerate((first, second, third)):
        assert outlook["startStep"] == mission["steps"] * index // 3
        assert outlook["throughStep"] == mission["steps"] * (index + 1) // 3
    assert started["outlook"] == first

    play("allocate", weights={})
    for step in range(1, mission["steps"] + 1):
        current = play("advance")
        assert len(current["prices"]) == PREVIEW + step + 1
        if step < first["throughStep"]:
            assert current["outlook"] == first
        elif step < second["throughStep"]:
            assert current["outlook"] == second
        elif step < third["throughStep"]:
            assert current["outlook"] == third
        else:
            assert current["outlook"] is None and current["status"] == "complete"

    replay = play("start", missionId=mission["id"])
    assert replay["id"] != started["id"]
    assert replay["prices"] == started["prices"]
    assert replay["outlook"] == first
    assert state["attempt"]["prices"] == original["prices"]


def test_exam_can_spend_its_rebalance_during_a_pause():
    exam = MISSIONS["rank1-exam"]
    state = career.default_state()
    state["achievements"] = {
        mission["id"]: {"passed": True, "mastered": False, "score": 0}
        for mission in MISSIONS.values()
        if mission["rank"] == exam["rank"] and mission["kind"] in ("fixed", "elective")
    }
    now = 100

    def play(action, **data):
        career.apply_command(state, {"action": action, **data}, now)
        return career.public_state(state, now)["attempt"]

    play("start", missionId=exam["id"])
    first_asset, second_asset, _ = exam["assets"]
    ready = play("allocate", weights={first_asset: 80}, step=0)
    assert ready["rebalances"] == 1
    play("phase")
    now += PHASE_STEPS * career.TICK_SECONDS
    paused = career.public_state(state, now)["attempt"]
    assert paused["status"] == "phaseReady"
    assert paused["rebalances"] == 1
    assert paused["outlook"]["startStep"] == PHASE_STEPS

    with pytest.raises(career.CampaignError, match="stale_quote"):
        play("allocate", weights={second_asset: 80}, step=PHASE_STEPS - 1)
    adjusted = play("allocate", weights={second_asset: 80}, step=PHASE_STEPS)
    assert adjusted["status"] == "phaseReady" and adjusted["phaseEndsAt"] is None
    assert adjusted["step"] == PHASE_STEPS
    assert adjusted["fees"] > paused["fees"]
    assert adjusted["weights"][first_asset] == 0
    assert adjusted["weights"][second_asset] == pytest.approx(80)
    assert adjusted["rebalances"] == 0
    with pytest.raises(career.CampaignError, match="no_rebalances"):
        play("allocate", weights={first_asset: 80}, step=PHASE_STEPS)

    assert play("phase")["rebalances"] == 0
    now += PHASE_STEPS * career.TICK_SECONDS
    next_pause = career.public_state(state, now)["attempt"]
    assert next_pause["phase"] == 3 and next_pause["rebalances"] == 1


def test_http_account_revisions_visible_prices_and_restart(campaign):
    app, config, _ = campaign
    visitor = app.test_client()
    assert visitor.get("/campaign").location == "/"
    assert visitor.get("/api/campaign").status_code == 401
    assert command(visitor, 0, "advance").status_code == 401
    player = register(app, "CampaignPlayer")
    other = register(app, "OtherFund")
    assert b'href="/campaign"' in player.get("/").data
    page = player.get("/campaign")
    assert page.status_code == 200 and page.headers["Cache-Control"] == "no-store"

    initial = read(player)
    assert initial["revision"] == 0 and initial["attempt"] is None
    assert player.post("/api/campaign/commands", json={"revision": 0, "action": "advance"}).status_code == 403
    assert command(player, True, "advance").status_code == 400
    assert command(player, 0, "start", missionId="rank5-exam", tools=[]).status_code == 400
    assert read(player) == initial

    mission = MISSIONS["rank1-fixed-1"]
    response = command(player, 0, "start", missionId=mission["id"], tools=[])
    assert response.status_code == 200, response.get_json()
    started = response.get_json()
    assert started["revision"] == 1
    assert started["attempt"]["cash"] == 5_000
    assert len(started["attempt"]["prices"]) == PREVIEW + 1
    conflict = command(player, 0, "start", missionId=mission["id"], tools=[])
    assert conflict.status_code == 409 and conflict.get_json()["state"] == started
    assert read(other)["attempt"] is None

    weights = {asset: 30 for asset in mission["assets"]}
    response = command(player, 1, "allocate", weights=weights)
    assert response.status_code == 200, response.get_json()
    response = command(player, 2, "advance")
    assert response.status_code == 200, response.get_json()
    advanced = response.get_json()
    assert len(advanced["attempt"]["prices"]) == PREVIEW + 2
    assert advanced["attempt"]["fees"] > 0

    restarted = create_app(config)
    resumed = restarted.test_client()
    assert post(resumed, "/api/login", {"username": "CampaignPlayer", "password": PASSWORD}).status_code == 200
    assert read(resumed) == advanced
    with restarted.app_context():
        assert db.session.scalar(select(func.count()).select_from(Match)) == 0
        assert db.session.scalar(select(func.count()).select_from(CampaignSave)) == 1
        assert all(rating.matches == 0 for rating in db.session.scalars(select(PlayerRating)))


def test_concurrent_starts_and_advances_commit_once(campaign, monkeypatch):
    app, _, _ = campaign
    player = register(app, "ParallelFund")
    session_cookie = player.get_cookie(app.config["SESSION_COOKIE_NAME"])
    token = player.get("/api/me").get_json()["csrfToken"]

    import stockfight.campaign_http as campaign_http

    apply = campaign_http.apply_command
    barrier = Barrier(2, timeout=10)

    def synchronized_apply(state, payload, now):
        apply(state, payload, now)
        barrier.wait()

    def submit(payload):
        http = app.test_client()
        http.set_cookie(session_cookie.key, session_cookie.value)
        return http.post("/api/campaign/commands", json=payload, headers={"X-CSRF-Token": token})

    def compete(payload):
        with monkeypatch.context() as patch, ThreadPoolExecutor(max_workers=2) as executor:
            patch.setattr(campaign_http, "apply_command", synchronized_apply)
            results = list(executor.map(submit, [payload, payload]))
        winner, conflict = sorted(results, key=lambda response: response.status_code)
        assert (winner.status_code, conflict.status_code) == (200, 409)
        assert conflict.get_json()["state"] == winner.get_json()
        return winner.get_json()

    mission = MISSIONS["rank1-fixed-1"]
    compete({"revision": 0, "action": "start", "missionId": mission["id"], "tools": []})
    weights = {asset: 30 for asset in mission["assets"]}
    assert command(player, 1, "allocate", weights=weights).status_code == 200
    state = compete({"revision": 2, "action": "advance"})
    assert state["revision"] == 3 and state["attempt"]["step"] == 1


def test_exams_pause_offline_and_comeback_unlocks_promotion(campaign, monkeypatch):
    app, config, clock = campaign
    player = register(app, "ExamPlayer")
    player_id = player.get("/api/me").get_json()["user"]["id"]
    exam = MISSIONS["rank1-exam"]

    def practice_prices(mission, seed):
        return [[str(100 + 3 * step), *["100"] * (len(mission["assets"]) - 1)]
                for step in range(-PREVIEW, mission["steps"] + 1)]

    monkeypatch.setattr(career, "generate_prices", practice_prices)
    progress = career.default_state()
    exam_prerequisites = [f"rank1-fixed-{number}" for number in range(1, 4)]
    exam_prerequisites += [f"rank1-elective-{number}" for number in range(1, 6)]
    progress["achievements"] = {mission: {"passed": True, "mastered": False, "score": 5.0}
                                for mission in exam_prerequisites}
    with app.app_context():
        db.session.add(CampaignSave(user_id=player_id, revision=1, state=progress))
        db.session.commit()

    state = read(player)

    def play(action, **data):
        nonlocal state
        response = command(player, state["revision"], action, **data)
        assert response.status_code == 200, response.get_json()
        state = response.get_json()
        return state["attempt"]

    play("start", missionId=exam["id"], tools=[])
    assert play("allocate", weights={})["status"] == "phaseReady"
    assert play("phase")["phaseEndsAt"] == clock.now + 60
    clock.now += 5
    stale = command(player, state["revision"], "allocate", weights={}, step=0)
    assert stale.status_code == 409 and stale.get_json()["error"] == "stale_quote"
    assert stale.get_json()["state"]["attempt"]["step"] == 1
    clock.now += 54.99
    assert read(player)["attempt"]["step"] == 11
    clock.now += 0.01
    halfway = read(player)["attempt"]
    assert (halfway["status"], halfway["phase"], halfway["step"]) == ("phaseReady", 2, 12)
    assert halfway["phaseEndsAt"] is None
    clock.now += 3600
    assert read(player)["attempt"]["step"] == 12
    play("phase")
    clock.now += 60
    assert play("phase")["phase"] == 3
    clock.now += 60

    restarted = create_app(config)
    player = restarted.test_client()
    assert post(player, "/api/login", {"username": "ExamPlayer", "password": PASSWORD}).status_code == 200
    state = read(player)
    assert state["attempt"]["report"]["passed"] is False
    assert state["comeback"] == "rank1-comeback"
    assert command(player, state["revision"], "start", missionId=exam["id"]).get_json()["error"] == "locked_mission"

    comeback = MISSIONS[state["comeback"]]
    play("start", missionId=comeback["id"], tools=[])
    play("allocate", weights={comeback["assets"][0]: 80})
    for _ in range(comeback["steps"]):
        report = play("advance")["report"]
    assert report["passed"] and state["comeback"] is None
    assert all(state["achievements"][mission]["passed"] for mission in exam_prerequisites)

    play("start", missionId=exam["id"], tools=[])
    play("allocate", weights={exam["assets"][0]: 80})
    for _ in range(3):
        play("phase")
        clock.now += 60
    state = read(player)
    assert state["attempt"]["report"]["passed"] and state["attempt"]["report"]["promoted"]
    assert state["rank"] == 1 and state["tools"][0]["available"]
    play("leave")
    assert read(player)["rank"] == 1

    best_exam = state["achievements"][exam["id"]]
    play("start", missionId=exam["id"], tools=[])
    play("allocate", weights={})
    for _ in range(3):
        play("phase")
        clock.now += 60
    replayed = read(player)
    assert replayed["attempt"]["report"]["passed"] is False
    assert replayed["attempt"]["report"]["promoted"] is False
    assert replayed["achievements"][exam["id"]] == best_exam and replayed["comeback"] is None


def test_saved_attempt_keeps_its_original_capital(monkeypatch):
    mission = MISSIONS["rank1-fixed-1"]
    state = career.default_state()
    with monkeypatch.context() as patch:
        patch.setitem(mission, "capital", 10_000)
        career.apply_command(state, {"action": "start", "missionId": mission["id"]}, 100)

    del state["attempt"]["outlooks"]  # Older saves don't have stored outlooks.
    career.apply_command(state, {"action": "allocate", "weights": {}}, 100)
    career.apply_command(state, {"action": "advance"}, 100)
    resumed = career.public_state(state, 100)["attempt"]
    assert resumed["mission"]["capital"] == resumed["value"] == 10_000
    assert resumed["returnPercent"] == 0
    assert resumed["outlook"] is None

    career.apply_command(state, {"action": "leave"}, 100)
    career.apply_command(state, {"action": "start", "missionId": mission["id"]}, 100)
    assert career.public_state(state, 100)["attempt"]["cash"] == 5_000


@pytest.mark.parametrize(
    "trigger, target, market_prices, error_code",
    [({}, "90", [95, 80], "invalid_stop"),
     ({"trigger": "profit"}, "110", [105, 110], "invalid_profit_target")],
)
def test_rebalance_cost_limits_and_stop_fills_at_revealed_quote(monkeypatch, trigger, target, market_prices, error_code):
    mission = MISSIONS["rank3-fixed-1"]

    def prices_for_stop(mission, seed):
        return [["100"] * len(mission["assets"])] * (PREVIEW + 1) + [
            [str(price), *["100"] * (len(mission["assets"]) - 1)]
            for price in market_prices + [market_prices[-1]] * (mission["steps"] - len(market_prices))
        ]

    monkeypatch.setattr(career, "generate_prices", prices_for_stop)
    state = career.default_state() | {"rank": 2}
    asset = mission["assets"][0]
    career.apply_command(state, {"action": "start", "missionId": mission["id"], "tools": ["stop"]}, 100)
    with pytest.raises(career.CampaignError, match="concentration_limit"):
        career.apply_command(state, {"action": "allocate", "weights": {asset: 70}}, 100)

    career.apply_command(state, {"action": "allocate", "weights": {asset: 50}}, 100)
    allocated = career.public_state(state, 100)["attempt"]
    assert allocated["rebalances"] == 3 and allocated["weights"][asset] == pytest.approx(50)
    assert allocated["fees"] == pytest.approx(allocated["value"] * 0.5 * 0.001)
    order = {"asset": asset, "price": target, **trigger}
    with pytest.raises(career.CampaignError, match=error_code):
        career.apply_command(state, {"action": "stop", **order, "price": "100"}, 100)
    career.apply_command(state, {"action": "stop", **order}, 100)
    career.apply_command(state, {"action": "advance"}, 100)
    pending = career.public_state(state, 100)["attempt"]
    assert pending["stopOrder"] == order and not pending["stopAvailable"]
    assert pending["weights"][asset] > 0

    career.apply_command(state, {"action": "advance"}, 100)
    revised = career.public_state(state, 100)["attempt"]
    assert revised["weights"][asset] == 0 and revised["cashPercent"] == 100
    assert not revised["stopAvailable"] and revised["stopOrder"] is None
    assert revised["rebalances"] == allocated["rebalances"]
    assert revised["fees"] == pytest.approx(allocated["fees"] * (1 + market_prices[-1] / 100))
    if not trigger:
        assert revised["drawdown"] > 10 and revised["worstStep"] == 2
