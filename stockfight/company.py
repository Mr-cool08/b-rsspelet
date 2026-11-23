"""Firm progression, desk management, and trading-day settlement."""

from copy import deepcopy

from .company_catalog import ASSETS, LEVELS, LIVE_ASSETS, STARTING_CASH, TRADE_RESERVE, UPGRADES, market_on_day


_SAVE_VERSION = 2
LEGACY_PROFIT_PER_WEEK = 40
_HIRES = (
    ("Alex", 1, 100),
    ("Kim", 3, 230),
    ("Sam", 5, 400),
)
_TRAINING_RETURNS = (-42, -28, 7, -20, 11, -10, 13, 7, 16, -4)
_STRATEGIES = {
    "careful": (15, 75),
    "balanced": (25, 100),
    "aggressive": (35, 130),
}
_DEFAULT_STRATEGY = "balanced"
_RESERVE_POLICIES = {"standard": TRADE_RESERVE, "buffered": 100, "defensive": 180}
_DESKS = {
    "lean": {"cost": 0, "returnBonus": 0, "capacityBonus": 0, "stakeBonus": 0, "lookbackBonus": 0},
    "research": {"cost": 8, "returnBonus": 10, "capacityBonus": 0, "stakeBonus": 0, "lookbackBonus": 2},
    "execution": {"cost": 12, "returnBonus": 0, "capacityBonus": 2, "stakeBonus": 8, "lookbackBonus": 0},
}
_BOT_STRATEGIES = ("momentum", "mean_reversion", "breakout")
_BOT_SETTING_RANGES = {"lookback": (3, 12), "stopLoss": (1, 20), "takeProfit": (1, 25)}
_REPORT_LIMIT = 7
_REPORT_TRADES_LIMIT = 20


class CompanyError(ValueError):
    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


def default_state() -> dict:
    return {
        "version": _SAVE_VERSION, "day": 1, "cash": STARTING_CASH, "profit": 0, "peakProfit": 0,
        "trades": 0, "upgrades": 0, "employees": [], "peerShares": {},
        "lastTrade": None, "lastEmployeeTrades": [],
        "reservePolicy": "standard", "desk": "lean", "dayTradingProfit": 0, "dayReports": [],
        "dayEmployeeProfit": 0, "dayEmployeeTrades": [],
    }


def normalize_state(state: dict) -> dict:
    """Convert an old chapter save while preserving the original privately."""
    if state.get("version") == _SAVE_VERSION:
        return state

    weeks = len(state["history"])
    profit = weeks * LEGACY_PROFIT_PER_WEEK
    return {
        **default_state(), "day": weeks + 1, "cash": STARTING_CASH + profit,
        "profit": profit, "peakProfit": profit, "previousCampaign": state.copy(),
    }


def _level(profit: int | float) -> dict:
    return next(level for level in reversed(LEVELS) if profit >= level["target"])


def level_for_profit(profit: int | float) -> int:
    return _level(profit)["number"]


def _capacity(state: dict, level: dict) -> int:
    return level["capacity"] + sum(upgrade["bonus"] for upgrade in UPGRADES[:state["upgrades"]])


def trading_capacity(state: dict) -> int:
    return _capacity(state, _level(state["peakProfit"])) + desk_terms(state)["capacityBonus"]


def cash_reserve(state: dict) -> int:
    return _RESERVE_POLICIES[state.get("reservePolicy", "standard")]


def desk_terms(state: dict) -> dict:
    return _DESKS[state.get("desk", "lean")]


def _closing_cost(state: dict) -> int:
    return max(desk_terms(state)["cost"], state.get("dayOperatingCost", 0))


def record_desk_use(state: dict) -> None:
    state["dayOperatingCost"] = _closing_cost(state)


def required_cash(state: dict) -> int:
    return cash_reserve(state) + _closing_cost(state)


def available_cash(state: dict) -> int:
    return max(0, state["cash"] - required_cash(state))


def cash_balance(state: dict) -> int | float:
    remainder = state.get("cashRemainder", 0)
    return round(state["cash"] + remainder / 100, 2) if remainder else state["cash"]


def _add_profit(state: dict, profit: int | float) -> None:
    state["profit"] = round(state["profit"] + profit, 2)
    state["peakProfit"] = max(state["peakProfit"], state["profit"])


def record_trading_profit(state: dict, profit: int | float, *, employee: bool = False) -> None:
    _add_profit(state, profit)
    key = "dayEmployeeProfit" if employee else "dayTradingProfit"
    state[key] = round(state.get(key, 0) + profit, 2)


def record_employee_trade(state: dict, employee: dict, trade: dict) -> None:
    employee["trades"] += 1
    employee["profit"] = round(employee["profit"] + trade["profit"], 2)
    entry = {"employeeId": employee["id"], "name": employee_name(employee), **trade}
    state["dayEmployeeTrades"] = [entry, *state.get("dayEmployeeTrades", ())][:_REPORT_TRADES_LIMIT]


def _upgrade_offer(state: dict) -> dict | None:
    index = state["upgrades"]
    if index >= len(UPGRADES):
        return None
    next_upgrade = UPGRADES[index]
    return {"number": index + 1, **next_upgrade, "available": available_cash(state) >= next_upgrade["price"]}


def _hire_offer(state: dict, level: dict) -> dict | None:
    index = len(state["employees"])
    if index >= len(_HIRES):
        return None
    name, unlock_level, price = _HIRES[index]
    return {
        "name": name, "price": price, "unlockLevel": unlock_level,
        "available": level["number"] >= unlock_level and available_cash(state) >= price,
    }


def _trade_offer(quote: dict, cash: int, capacity: int) -> dict:
    quantity = min(quote["supply"], cash // quote["buyPrice"], capacity)
    cost = quantity * quote["buyPrice"]
    revenue = quantity * quote["sellPrice"]
    return {"quantity": quantity, "cost": cost, "revenue": revenue, "profit": revenue - cost}


def _worker_budget(state: dict, cash: int, strategy: str) -> int:
    stake_percent, _ = _STRATEGIES[strategy]
    stake_percent += desk_terms(state)["stakeBonus"]
    return min(cash * stake_percent // 100, cash - cash_reserve(state))


def bot_budget(state: dict, employee: dict) -> int:
    cash = state["cash"] - _closing_cost(state)
    return _worker_budget(state, cash, employee.get("strategy", _DEFAULT_STRATEGY))


def _worker_symbols(market: dict, level: dict, budget: int, focus: str) -> list[str]:
    return [
        symbol for symbol, asset in ASSETS.items()
        if (focus in ("all", symbol) and asset["unlockLevel"] <= level["number"] and market[symbol]["buyPrice"] <= budget
            and market[symbol]["supply"] > 0)
    ]


def _worker_return(employee: dict, day: int) -> int:
    trades = employee["trades"]
    if trades < len(_TRAINING_RETURNS):
        return _TRAINING_RETURNS[trades]

    variation = (day + 2 * employee["id"] + trades) % 12
    return -4 if variation in (0, 9) else 8 + variation


def employee_name(employee: dict) -> str:
    return _HIRES[employee["id"] - 1][0]


def bot_configuration(employee: dict) -> dict:
    return employee.get("bot", {
        "strategy": _BOT_STRATEGIES[employee["id"] - 1], "lookback": 5,
        "threshold": (0.2, 0.3, 0.2)[employee["id"] - 1], "stopLoss": 1, "takeProfit": 2,
    })


def _set_bot(employee: dict, command: dict) -> None:
    strategy = command.get("strategy")
    threshold = command.get("threshold")
    settings = {key: command.get(key) for key in _BOT_SETTING_RANGES}
    if strategy not in _BOT_STRATEGIES or type(threshold) not in (int, float) or not 0.1 <= threshold <= 10:
        raise CompanyError("invalid_bot")
    if any(type(settings[key]) is not int or not low <= settings[key] <= high
           for key, (low, high) in _BOT_SETTING_RANGES.items()):
        raise CompanyError("invalid_bot")
    employee["bot"] = {"strategy": strategy, "threshold": round(threshold, 2), **settings}


def _worker_trades(state: dict, cash: int, level: dict, market: dict) -> list[dict]:
    results = []
    day = state["day"]
    desk = desk_terms(state)
    capacity = _capacity(state, level) + desk["capacityBonus"]
    for employee in state["employees"]:
        if not employee["active"]:
            continue

        strategy = employee.get("strategy", _DEFAULT_STRATEGY)
        _, return_multiplier = _STRATEGIES[strategy]
        budget = _worker_budget(state, cash, strategy)
        symbols = _worker_symbols(market, level, budget, employee.get("focus", "all"))
        if not symbols:
            continue

        choice = (day + employee["id"] + employee["trades"] - 2) % len(symbols)
        symbol = symbols[choice]
        quote = market[symbol]
        quantity = min(capacity, quote["supply"], budget // quote["buyPrice"])
        stake = quantity * quote["buyPrice"]
        return_basis_points = _worker_return(employee, day) * return_multiplier + desk["returnBonus"] * 100
        profit = stake * return_basis_points // 10_000
        cash += profit
        employee["trades"] += 1
        employee["profit"] += profit
        results.append({
            "employeeId": employee["id"], "name": employee_name(employee), "symbol": symbol,
            "quantity": quantity, "profit": profit,
        })
    return results


def _play_day(state: dict, command: dict, level: dict) -> None:
    cash = state["cash"]
    operating_cost = _closing_cost(state)
    if cash < operating_cost:
        raise CompanyError("closing_cost_unavailable")
    action = command["action"]
    market = market_on_day(state["day"])
    player_trade = None
    if action == "trade":
        symbol = command.get("symbol")
        if not isinstance(symbol, str) or symbol not in ASSETS:
            raise CompanyError("invalid_asset")
        if ASSETS[symbol]["unlockLevel"] > level["number"]:
            raise CompanyError("locked_asset")

        player_trade = {"symbol": symbol, **_trade_offer(market[symbol], available_cash(state), _capacity(state, level))}
        if not player_trade["quantity"]:
            raise CompanyError("insufficient_cash")
        cash += player_trade["profit"]
    elif action == "advance" and not any(employee["active"] for employee in state["employees"]):
        raise CompanyError("no_active_employee")

    workers = [] if action == "close_day" else _worker_trades(state, cash - operating_cost, level, market)
    if action == "advance" and not workers:
        raise CompanyError("insufficient_cash")

    player_profit = player_trade["profit"] if player_trade else 0
    legacy_employee_profit = sum(result["profit"] for result in workers)
    employee_profit = round(state.get("dayEmployeeProfit", 0) + legacy_employee_profit, 2)
    employee_trades = [*workers, *state.get("dayEmployeeTrades", ())][:_REPORT_TRADES_LIMIT]
    trading_profit = round(state.get("dayTradingProfit", 0) + player_profit, 2)
    _add_profit(state, player_profit + legacy_employee_profit - operating_cost)
    state["cash"] = cash + legacy_employee_profit - operating_cost
    report = {
        "day": state["day"], "employeeProfit": employee_profit, "tradingProfit": trading_profit,
        "operatingCost": operating_cost, "net": round(trading_profit + employee_profit - operating_cost, 2),
        "cash": cash_balance(state), "employeeTrades": employee_trades,
    }
    state["dayReports"] = [report, *state.get("dayReports", ())][:_REPORT_LIMIT]
    state["dayTradingProfit"] = 0
    state["dayEmployeeProfit"], state["dayEmployeeTrades"] = 0, []
    state["dayOperatingCost"] = 0
    state["trades"] += int(player_trade is not None)
    state["day"] += 1
    state["lastTrade"] = player_trade
    state["lastEmployeeTrades"] = employee_trades


def apply_command(state: dict, command: object) -> None:
    """Apply one validated command and convert an older save on its first successful write."""
    if not isinstance(command, dict):
        raise CompanyError("invalid_command")

    action = command.get("action")
    current = normalize_state(state)
    level = _level(current["peakProfit"])
    if action in ("trade", "advance", "close_day"):
        _play_day(current, command, level)
    elif action == "upgrade":
        upgrade = _upgrade_offer(current)
        if upgrade is None or not upgrade["available"]:
            raise CompanyError("upgrade_unavailable")
        current["cash"] -= upgrade["price"]
        current["upgrades"] += 1
    elif action == "hire":
        hire = _hire_offer(current, level)
        if hire is None or not hire["available"]:
            raise CompanyError("hire_unavailable")
        current["cash"] -= hire["price"]
        current["employees"].append({
            "id": len(current["employees"]) + 1, "active": True, "trades": 0, "profit": 0, "strategy": _DEFAULT_STRATEGY,
            "focus": "all",
        })
    elif action == "set_reserve_policy":
        policy = command.get("policy")
        if not isinstance(policy, str) or policy not in _RESERVE_POLICIES:
            raise CompanyError("invalid_reserve_policy")
        current["reservePolicy"] = policy
    elif action == "set_desk":
        desk = command.get("desk")
        if not isinstance(desk, str) or desk not in _DESKS:
            raise CompanyError("invalid_desk")
        if current["cash"] < _DESKS[desk]["cost"]:
            raise CompanyError("closing_cost_unavailable")
        current["desk"] = desk
    elif action in ("toggle_employee", "set_employee_strategy", "set_employee_focus", "set_employee_bot"):
        employee_id = command.get("employeeId")
        if type(employee_id) is not int or not 1 <= employee_id <= len(current["employees"]):
            raise CompanyError("invalid_employee")
        employee = current["employees"][employee_id - 1]
        if action == "toggle_employee":
            employee["active"] = not employee["active"]
        elif action == "set_employee_bot":
            _set_bot(employee, command)
        elif action == "set_employee_strategy":
            strategy = command.get("strategy")
            if not isinstance(strategy, str) or strategy not in _STRATEGIES:
                raise CompanyError("invalid_strategy")
            employee["strategy"] = strategy
        else:
            focus = command.get("symbol")
            if focus != "all":
                if not isinstance(focus, str) or focus not in LIVE_ASSETS:
                    raise CompanyError("invalid_asset")
                if LIVE_ASSETS[focus]["unlockLevel"] > level["number"]:
                    raise CompanyError("locked_asset")
            employee["focus"] = focus
    else:
        raise CompanyError("invalid_command")

    if current is not state:
        state.clear()
        state.update(current)


def public_state(state: dict) -> dict:
    """Expose the current day's trading choices and show what the next rank unlocks."""
    state = normalize_state(state)
    level = _level(state["peakProfit"])
    market = market_on_day(state["day"])
    cash = state["cash"]
    capacity = _capacity(state, level)
    next_level = None
    if level["number"] < len(LEVELS):
        following = LEVELS[level["number"]]
        symbol = following["unlock"]
        live_unlock = next((
            {"symbol": ticker, "name": asset["name"]}
            for ticker, asset in LIVE_ASSETS.items() if asset["unlockLevel"] == following["number"]
        ), None)
        next_level = {
            "number": following["number"], "name": following["name"], "target": following["target"],
            "unlock": {"symbol": symbol, "name": ASSETS[symbol]["name"]} if symbol else None,
            "liveUnlock": live_unlock,
        }

    assets = []
    for symbol, asset in ASSETS.items():
        unlocked = asset["unlockLevel"] <= level["number"]
        quote = market[symbol]
        offer = _trade_offer(quote, available_cash(state), capacity if unlocked else 0)
        assets.append({
            "symbol": symbol, **asset, **quote, "quantity": offer["quantity"], "cost": offer["cost"],
            "profit": offer["profit"], "unlocked": unlocked,
        })

    workers = [
        {"id": employee["id"], "active": employee["active"], "trades": employee["trades"], "profit": employee["profit"],
         "name": employee_name(employee), "bot": bot_configuration(employee),
         "strategy": employee.get("strategy", _DEFAULT_STRATEGY),
         "focus": employee["focus"] if employee.get("focus") in LIVE_ASSETS else "all",
         "skill": min(100, employee["trades"] * 100 // len(_TRAINING_RETURNS))}
        for employee in state["employees"]
    ]
    closing_cost = _closing_cost(state)
    can_advance = any(
        employee["active"] and _worker_symbols(
            market, level, _worker_budget(state, cash - closing_cost, employee["strategy"]), employee["focus"],
        )
        for employee in workers
    )
    reports = state.get("dayReports", [])
    return deepcopy({
        "day": state["day"], "cash": cash_balance(state), "profit": state["profit"], "peakProfit": state["peakProfit"],
        "trades": state["trades"], "level": {"number": level["number"], "name": level["name"]},
        "nextLevel": next_level, "capacity": trading_capacity(state), "upgrade": _upgrade_offer(state), "assets": assets,
        "liveAssets": [{"symbol": symbol, "name": asset["name"], "unlocked": asset["unlockLevel"] <= level["number"]}
                       for symbol, asset in LIVE_ASSETS.items()],
        "lastTrade": state["lastTrade"], "employees": workers, "hire": _hire_offer(state, level),
        "lastEmployeeTrades": state["lastEmployeeTrades"],
        "canAdvance": can_advance,
        "administration": {
            "reservePolicy": state.get("reservePolicy", "standard"), "reserve": cash_reserve(state),
            "reservePolicies": [{"id": policy, "amount": amount} for policy, amount in _RESERVE_POLICIES.items()],
            "desk": state.get("desk", "lean"), "desks": [{"id": desk, **terms} for desk, terms in _DESKS.items()],
            "closingCost": closing_cost, "availableCash": available_cash(state),
            "dayTradingProfit": state.get("dayTradingProfit", 0), "dayEmployeeProfit": state.get("dayEmployeeProfit", 0),
            "dayReport": reports[0] if reports else None,
            "reports": reports,
        },
    })


def public_standing(state: dict) -> dict:
    """Summarize firm progress for the multiplayer standings."""
    state = normalize_state(state)
    return {
        "level": level_for_profit(state["peakProfit"]), "profit": state["profit"], "day": state["day"],
        "cash": cash_balance(state), "trades": state["trades"],
    }
