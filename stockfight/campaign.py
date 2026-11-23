"""Portfolio rules, progression and crisis timing for a single campaign save."""

from copy import deepcopy
from decimal import Decimal, InvalidOperation, ROUND_DOWN
from secrets import randbits
from uuid import uuid4

from .campaign_catalog import ASSET_NAMES, MISSIONS, PHASE_COUNT, PHASE_STEPS, PREVIEW, RANKS, TOOLS, generate_prices


TICK_SECONDS = 5
DAILY_REBALANCES = 3
FEE_RATE = Decimal("0.001")
TRADE_PRECISION = Decimal("0.000000000001")
PERCENT_TOLERANCE = Decimal("0.00000001")
HUNDRED = Decimal(100)
ZERO = Decimal(0)
TOOL_UNLOCKS = {"analysis": 1, "stop": 2, "extra": 3}
MISSION_FIELDS = ("id", "rank", "kind", "title", "brief", "titleEn", "briefEn", "assets",
                  "steps", "capital", "goals", "mastery")


class CampaignError(ValueError):
    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


def default_state() -> dict:
    return {"rank": 0, "achievements": {}, "comeback": None, "attempt": None}


def _mission_summary(mission: dict) -> dict:
    return deepcopy({field: mission[field] for field in MISSION_FIELDS})


def _tool_slots(rank: int) -> int:
    return 0 if rank == 0 else 1 if rank < 4 else 2


def _rank_missions(rank: int, kind: str) -> list[dict]:
    return [mission for mission in MISSIONS.values() if mission["rank"] == rank and mission["kind"] == kind]


def _passed(state: dict, mission: dict) -> bool:
    return state["achievements"].get(mission["id"], {}).get("passed", False)


def _mission_available(state: dict, mission: dict) -> bool:
    rank, kind = mission["rank"], mission["kind"]
    if kind == "comeback":
        return state["comeback"] == mission["id"]
    if rank > state["rank"]:
        return False
    if rank == 0:
        first = _rank_missions(0, "fixed")[0]
        if mission["id"] != first["id"] and not _passed(state, first):
            return False
    if kind == "exam":
        blocked = state["comeback"] and MISSIONS[state["comeback"]]["rank"] == rank
        return (not blocked and all(_passed(state, item) for item in _rank_missions(rank, "fixed"))
                and sum(_passed(state, item) for item in _rank_missions(rank, "elective")) >= 5)
    return True


def _is_exam(attempt: dict) -> bool:
    return attempt["mission"]["kind"] == "exam"


def _prices(attempt: dict, step: int) -> list[Decimal]:
    return [Decimal(price) for price in attempt["prices"][attempt["preview"] + step]]


def _percent(numerator: Decimal, denominator: Decimal) -> Decimal:
    return numerator / denominator * HUNDRED


def _metrics(attempt: dict) -> dict[str, Decimal]:
    prices = _prices(attempt, attempt["step"])
    base = _prices(attempt, 0)
    initial = Decimal(attempt["mission"]["capital"])
    invested = sum((Decimal(shares) * price for shares, price in zip(attempt["shares"], prices)), ZERO)
    cash = Decimal(attempt["cash"])
    value = invested + cash
    index_value = initial * sum(price / start for price, start in zip(prices, base)) / len(prices)
    return {
        "value": value,
        "cashPercent": _percent(cash, value),
        "equityPercent": _percent(invested, value),
        "returnPercent": _percent(value - initial, initial),
        "indexValue": index_value,
        "indexReturn": _percent(index_value - initial, initial),
    }


def _record(attempt: dict, *, checkpoint: bool = False, exposure: bool = True) -> None:
    metrics = _metrics(attempt)
    value, step = metrics["value"], attempt["step"]
    peak = max(Decimal(attempt["peak"]), value)
    attempt["peak"] = str(peak)
    drawdown = _percent(peak - value, peak)
    if drawdown > Decimal(attempt["drawdown"]):
        attempt["drawdown"], attempt["worstStep"] = str(drawdown), step
    if exposure:
        previous = attempt["minExposure"]
        minimum = metrics["equityPercent"] if previous is None else min(Decimal(previous), metrics["equityPercent"])
        attempt["minExposure"] = str(minimum)
    if checkpoint:
        # The checkpoint is tested when the new bar arrives, before the player can react to its price.
        attempt["cashPoints"][str(step)] = str(metrics["cashPercent"])
    row = {"step": step, "value": str(value), "indexValue": str(metrics["indexValue"])}
    if attempt["history"] and attempt["history"][-1]["step"] == step:
        attempt["history"][-1] = row
    else:
        attempt["history"].append(row)


def _start_attempt(state: dict, command: dict) -> None:
    current = state["attempt"]
    if current is not None and current["status"] != "complete":
        raise CampaignError("attempt_active")
    mission_id = command.get("missionId")
    mission = MISSIONS.get(mission_id) if isinstance(mission_id, str) else None
    if mission is None:
        raise CampaignError("invalid_mission")
    if not _mission_available(state, mission):
        raise CampaignError("locked_mission")

    tools = command.get("tools", [])
    rank = state["rank"]
    if (not isinstance(tools, list) or len(tools) > _tool_slots(rank)
            or any(not isinstance(tool, str) or TOOL_UNLOCKS.get(tool, len(RANKS)) > rank for tool in tools)
            or len(set(tools)) != len(tools)):
        raise CampaignError("invalid_tools")

    capital = str(mission["capital"])
    attempt = {
        "id": uuid4().hex,
        "mission": _mission_summary(mission),
        "preview": PREVIEW,
        "prices": generate_prices(mission, randbits(64)),
        "status": "setup",
        "tools": list(tools),
        "step": 0,
        "phase": 1 if mission["kind"] == "exam" else None,
        "phaseStartedAt": None,
        "rebalances": 1 if mission["kind"] == "exam" else DAILY_REBALANCES,
        "extraUsed": False,
        "stopUsed": False,
        "stopOrder": None,
        "cash": capital,
        "shares": ["0" for _ in mission["assets"]],
        "fees": "0",
        "peak": capital,
        "drawdown": "0",
        "worstStep": 0,
        "maxTarget": 0,
        "minExposure": None,
        "cashPoints": {},
        "history": [],
        "report": None,
    }
    _record(attempt, exposure=False)
    state["attempt"] = attempt


def _require_current_step(command: dict, attempt: dict) -> None:
    if "step" in command and (type(command["step"]) is not int or command["step"] != attempt["step"]):
        raise CampaignError("stale_quote")


def _extra_available(attempt: dict) -> bool:
    return "extra" in attempt["tools"] and not attempt["extraUsed"] and attempt["status"] != "complete"


def _charge_trade(attempt: dict, target: list[int]) -> None:
    prices = _prices(attempt, attempt["step"])
    holdings = [Decimal(shares) * price for shares, price in zip(attempt["shares"], prices)]
    value = sum(holdings, Decimal(attempt["cash"]))
    fractions = [Decimal(weight) / HUNDRED for weight in target]

    def allocations(net: Decimal) -> list[Decimal]:
        return [net * fraction for fraction in fractions]

    def fee(amounts: list[Decimal]) -> Decimal:
        return sum(abs(new - old) for new, old in zip(amounts, holdings)) * FEE_RATE

    # Target weights apply to the value after fees. This iteration converges with a slope of at most 0.001.
    net = value
    for _ in range(10):
        net = value - fee(allocations(net))
    amounts = [amount.quantize(TRADE_PRECISION, rounding=ROUND_DOWN) for amount in allocations(net)]
    trade_fee = fee(amounts)
    attempt["cash"] = str(value - trade_fee - sum(amounts))
    attempt["shares"] = [str(amount / price) for amount, price in zip(amounts, prices)]
    attempt["fees"] = str(Decimal(attempt["fees"]) + trade_fee)


def _allocate(attempt: dict, command: dict) -> None:
    setup = attempt["status"] == "setup"
    if attempt["status"] not in ("setup", "trading", "phaseActive"):
        raise CampaignError("invalid_phase")
    _require_current_step(command, attempt)
    if not setup and not attempt["rebalances"] and not _extra_available(attempt):
        raise CampaignError("no_rebalances")

    weights = command.get("weights")
    assets = attempt["mission"]["assets"]
    if (not isinstance(weights, dict) or any(asset not in assets for asset in weights)
            or any(type(weight) is not int or weight < 0 or weight > 100 or weight % 10 for weight in weights.values())
            or sum(weights.values()) > 100):
        raise CampaignError("invalid_weights")
    target = [weights.get(asset, 0) for asset in assets]
    limit = min((goal["value"] for goal in attempt["mission"]["goals"] if goal["type"] == "concentration"), default=100)
    if max(target) > limit:
        raise CampaignError("concentration_limit")

    _charge_trade(attempt, target)
    attempt["maxTarget"] = max(attempt["maxTarget"], max(target))
    if attempt["stopOrder"] and not Decimal(attempt["shares"][assets.index(attempt["stopOrder"]["asset"])]):
        attempt["stopOrder"] = None
    if setup:
        attempt["status"] = "phaseReady" if _is_exam(attempt) else "trading"
    elif attempt["rebalances"]:
        attempt["rebalances"] -= 1
    else:
        attempt["extraUsed"] = True
    _record(attempt, checkpoint=setup)


def _stop_available(attempt: dict) -> bool:
    return ("stop" in attempt["tools"] and not attempt["stopUsed"]
            and attempt["status"] in ("trading", "phaseReady", "phaseActive")
            and any(Decimal(shares) > 0 for shares in attempt["shares"]))


def _set_stop(attempt: dict, command: dict) -> None:
    if not _stop_available(attempt):
        raise CampaignError("stop_unavailable")
    _require_current_step(command, attempt)
    trigger = command.get("trigger", "loss")
    if trigger not in ("loss", "profit"):
        raise CampaignError("invalid_stop")
    error_code = "invalid_profit_target" if trigger == "profit" else "invalid_stop"
    asset, raw_price = command.get("asset"), command.get("price")
    assets = attempt["mission"]["assets"]
    if asset not in assets or type(raw_price) not in (str, float, int) or len(str(raw_price)) > 32:
        raise CampaignError(error_code)
    position = assets.index(asset)
    try:
        price = Decimal(str(raw_price))
    except InvalidOperation as error:
        raise CampaignError(error_code) from error
    if not price.is_finite() or price <= 0 or Decimal(attempt["shares"][position]) <= 0:
        raise CampaignError(error_code)
    quote = _prices(attempt, attempt["step"])[position]
    if not (price > quote if trigger == "profit" else price < quote):
        raise CampaignError(error_code)
    attempt["stopUsed"] = True
    attempt["stopOrder"] = {"asset": asset, "price": str(price)}
    if trigger == "profit":
        attempt["stopOrder"]["trigger"] = trigger


def _reveal(attempt: dict) -> None:
    attempt["step"] += 1
    if order := attempt["stopOrder"]:
        position = attempt["mission"]["assets"].index(order["asset"])
        price = _prices(attempt, attempt["step"])[position]
        target = Decimal(order["price"])
        reached = price >= target if order.get("trigger") == "profit" else price <= target
        if reached:
            value = Decimal(attempt["shares"][position]) * price
            fee = value * FEE_RATE
            attempt["cash"] = str(Decimal(attempt["cash"]) + value - fee)
            attempt["fees"] = str(Decimal(attempt["fees"]) + fee)
            attempt["shares"][position] = "0"
            attempt["stopOrder"] = None
    _record(attempt, checkpoint=True)


def _evaluate(attempt: dict, goal: dict, metrics: dict[str, Decimal]) -> dict:
    kind = goal["type"]
    values = {
        "index": metrics["returnPercent"] - metrics["indexReturn"],
        "return": metrics["returnPercent"],
        "drawdown": attempt["drawdown"],
        "cash": attempt["cashPoints"].get(str(goal.get("step", attempt["mission"]["steps"]))),
        "exposure": attempt["minExposure"],
        "concentration": attempt["maxTarget"],
    }
    if values[kind] is None:
        return {**goal, "actual": None, "met": None}
    actual, target = Decimal(values[kind]), Decimal(str(goal["value"]))
    met = (actual <= target + PERCENT_TOLERANCE if kind in ("drawdown", "concentration")
           else actual >= target - PERCENT_TOLERANCE)
    return {**goal, "actual": float(actual), "met": met}


def _finish(state: dict, attempt: dict, *, abandoned: bool = False) -> None:
    mission = attempt["mission"]
    mission_id, kind = mission["id"], mission["kind"]
    metrics = _metrics(attempt)
    goals = [_evaluate(attempt, goal, metrics) for goal in mission["goals"]]
    mastery = _evaluate(attempt, mission["mastery"], metrics)
    passed = not abandoned and all(goal["met"] for goal in goals)
    mastered = passed and bool(mastery["met"])
    promoted = kind == "exam" and passed and mission["rank"] == state["rank"]
    attempt["status"], attempt["phaseStartedAt"] = "complete", None
    attempt["report"] = {"passed": passed, "mastered": mastered, "abandoned": abandoned,
                         "promoted": promoted, "goals": goals, "mastery": mastery}

    if kind == "comeback":
        if passed:
            state["comeback"] = None
        return
    if not abandoned:
        previous = state["achievements"].get(mission_id)
        score = float(metrics["returnPercent"])
        if previous is None or (passed, score) > (previous["passed"], previous["score"]):
            state["achievements"][mission_id] = {
                "passed": passed, "mastered": mastered or (previous is not None and previous["mastered"]),
                "score": score,
            }
        elif mastered:
            previous["mastered"] = True
    if kind == "exam":
        if passed:
            state["rank"] = max(state["rank"], mission["rank"] + 1)
        elif not _passed(state, mission):
            state["comeback"] = _rank_missions(mission["rank"], "comeback")[0]["id"]


def _settle_clock(state: dict, now: float) -> None:
    attempt = state["attempt"]
    if attempt is None or attempt["status"] != "phaseActive":
        return
    elapsed = max(0, now - attempt["phaseStartedAt"])
    phase_step = min(PHASE_STEPS, int(elapsed / TICK_SECONDS))
    target_step = (attempt["phase"] - 1) * PHASE_STEPS + phase_step
    while attempt["step"] < target_step:
        _reveal(attempt)
    if phase_step == PHASE_STEPS:
        if attempt["phase"] == PHASE_COUNT:
            _finish(state, attempt)
        else:
            attempt["phase"] += 1
            attempt["phaseStartedAt"] = None
            attempt["status"] = "phaseReady"
            attempt["rebalances"] = 1


def apply_command(state: dict, command: object, now: float) -> None:
    """Apply a command to a working save, which the caller commits only on success."""
    if not isinstance(command, dict):
        raise CampaignError("invalid_command")
    action = command.get("action")
    if action not in ("start", "allocate", "advance", "phase", "stop", "leave"):
        raise CampaignError("invalid_command")
    _settle_clock(state, now)
    if action == "start":
        _start_attempt(state, command)
        return

    attempt = state["attempt"]
    if attempt is None:
        raise CampaignError("no_attempt")
    if action == "allocate":
        _allocate(attempt, command)
    elif action == "advance":
        if attempt["status"] != "trading":
            raise CampaignError("invalid_phase")
        _reveal(attempt)
        if attempt["step"] == attempt["mission"]["steps"]:
            _finish(state, attempt)
    elif action == "stop":
        _set_stop(attempt, command)
    elif action == "phase":
        if attempt["status"] != "phaseReady":
            raise CampaignError("invalid_phase")
        attempt["status"], attempt["phaseStartedAt"] = "phaseActive", now
    elif action == "leave":
        if _is_exam(attempt) and (attempt["status"] == "phaseActive"
                                  or (attempt["status"] == "phaseReady" and attempt["step"] > 0)):
            _finish(state, attempt, abandoned=True)
        state["attempt"] = None


def _public_attempt(attempt: dict, now: float) -> dict:
    mission = attempt["mission"]
    step, preview = attempt["step"], attempt["preview"]
    metrics = _metrics(attempt)
    holdings = [Decimal(shares) * price for shares, price in zip(attempt["shares"], _prices(attempt, step))]
    started = attempt["phaseStartedAt"]
    report = attempt["report"]
    return {
        "id": attempt["id"], "missionId": mission["id"], "mission": _mission_summary(mission),
        "status": attempt["status"], "step": step, "phase": attempt["phase"], "serverNow": now,
        "phaseEndsAt": None if started is None else started + PHASE_STEPS * TICK_SECONDS,
        "tools": attempt["tools"], "rebalances": attempt["rebalances"] if not report else 0,
        "extraAvailable": _extra_available(attempt), "stopAvailable": _stop_available(attempt),
        "stopOrder": attempt["stopOrder"],
        "cash": float(Decimal(attempt["cash"])), "cashPercent": float(metrics["cashPercent"]),
        "value": float(metrics["value"]), "returnPercent": float(metrics["returnPercent"]),
        "indexReturn": float(metrics["indexReturn"]), "drawdown": float(Decimal(attempt["drawdown"])),
        "worstStep": attempt["worstStep"], "fees": float(Decimal(attempt["fees"])),
        "weights": {asset: float(_percent(value, metrics["value"])) for asset, value in zip(mission["assets"], holdings)},
        "prices": [{"step": index - preview, "prices": [float(price) for price in prices]}
                   for index, prices in enumerate(attempt["prices"][:preview + step + 1])],
        "history": [{"step": point["step"], "value": float(Decimal(point["value"])),
                     "indexValue": float(Decimal(point["indexValue"]))} for point in attempt["history"]],
        "goals": report["goals"] if report else [_evaluate(attempt, goal, metrics) for goal in mission["goals"]],
        "report": report,
    }


def public_state(state: dict, now: float) -> dict:
    """Project any elapsed crisis ticks without updating the stored save or exposing future bars."""
    state = deepcopy(state)
    _settle_clock(state, now)
    attempt, rank = state["attempt"], state["rank"]
    return {
        "rank": rank, "ranks": list(RANKS), "toolSlots": _tool_slots(rank),
        "missions": [{**_mission_summary(mission), "available": _mission_available(state, mission)}
                     for mission in MISSIONS.values()],
        "tools": [{"id": tool, "label": label, "unlockRank": TOOL_UNLOCKS[tool], "available": TOOL_UNLOCKS[tool] <= rank}
                  for tool, label in TOOLS.items()],
        "assetNames": dict(ASSET_NAMES), "achievements": state["achievements"], "comeback": state["comeback"],
        "attempt": _public_attempt(attempt, now) if attempt else None,
    }
