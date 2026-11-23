"""Firm progression, automatic traders, and one-click trades."""

from copy import deepcopy

from .company_catalog import ASSETS, LEVELS, STARTING_CASH, TRADE_RESERVE, UPGRADES, market_on_day


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


class CompanyError(ValueError):
    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


def default_state() -> dict:
    return {
        "version": _SAVE_VERSION, "day": 1, "cash": STARTING_CASH, "profit": 0, "peakProfit": 0,
        "trades": 0, "upgrades": 0, "employees": [], "peerShares": {},
        "lastTrade": None, "lastEmployeeTrades": [],
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


def _level(profit: int) -> dict:
    return next(level for level in reversed(LEVELS) if profit >= level["target"])


def level_for_profit(profit: int) -> int:
    return _level(profit)["number"]


def _capacity(state: dict, level: dict) -> int:
    return level["capacity"] + sum(upgrade["bonus"] for upgrade in UPGRADES[:state["upgrades"]])


def _can_spend(cash: int, price: int) -> bool:
    return cash - price >= TRADE_RESERVE


def _upgrade_offer(state: dict) -> dict | None:
    index = state["upgrades"]
    if index >= len(UPGRADES):
        return None
    next_upgrade = UPGRADES[index]
    return {"number": index + 1, **next_upgrade, "available": _can_spend(state["cash"], next_upgrade["price"])}


def _hire_offer(state: dict, level: dict) -> dict | None:
    index = len(state["employees"])
    if index >= len(_HIRES):
        return None
    name, unlock_level, price = _HIRES[index]
    return {
        "name": name, "price": price, "unlockLevel": unlock_level,
        "available": level["number"] >= unlock_level and _can_spend(state["cash"], price),
    }


def _trade_offer(quote: dict, cash: int, capacity: int) -> dict:
    quantity = min(quote["supply"], cash // quote["buyPrice"], capacity)
    cost = quantity * quote["buyPrice"]
    revenue = quantity * quote["sellPrice"]
    return {"quantity": quantity, "cost": cost, "revenue": revenue, "profit": revenue - cost}


def _worker_budget(cash: int, stake_percent: int) -> int:
    return min(cash * stake_percent // 100, cash - TRADE_RESERVE)


def _worker_symbols(market: dict, level: dict, budget: int) -> list[str]:
    return [
        symbol for symbol, asset in ASSETS.items()
        if (asset["unlockLevel"] <= level["number"] and market[symbol]["buyPrice"] <= budget
            and market[symbol]["supply"] > 0)
    ]


def _worker_return(employee: dict, day: int) -> int:
    trades = employee["trades"]
    if trades < len(_TRAINING_RETURNS):
        return _TRAINING_RETURNS[trades]

    variation = (day + 2 * employee["id"] + trades) % 12
    return -4 if variation in (0, 9) else 8 + variation


def _worker_name(employee: dict) -> str:
    return _HIRES[employee["id"] - 1][0]


def _worker_trades(state: dict, cash: int, level: dict, market: dict) -> list[dict]:
    results = []
    day = state["day"]
    capacity = _capacity(state, level)
    for employee in state["employees"]:
        if not employee["active"]:
            continue

        strategy = employee.get("strategy", _DEFAULT_STRATEGY)
        stake_percent, return_multiplier = _STRATEGIES[strategy]
        budget = _worker_budget(cash, stake_percent)
        symbols = _worker_symbols(market, level, budget)
        if not symbols:
            continue

        choice = (day + employee["id"] + employee["trades"] - 2) % len(symbols)
        symbol = symbols[choice]
        quote = market[symbol]
        quantity = min(capacity, quote["supply"], budget // quote["buyPrice"])
        stake = quantity * quote["buyPrice"]
        profit = stake * _worker_return(employee, day) * return_multiplier // 10_000
        cash += profit
        employee["trades"] += 1
        employee["profit"] += profit
        results.append({
            "employeeId": employee["id"], "name": _worker_name(employee), "symbol": symbol,
            "quantity": quantity, "profit": profit,
        })
    return results


def _play_day(state: dict, command: dict, level: dict) -> None:
    market = market_on_day(state["day"])
    cash = state["cash"]
    player_trade = None
    if command["action"] == "trade":
        symbol = command.get("symbol")
        if not isinstance(symbol, str) or symbol not in ASSETS:
            raise CompanyError("invalid_asset")
        if ASSETS[symbol]["unlockLevel"] > level["number"]:
            raise CompanyError("locked_asset")

        player_trade = {"symbol": symbol, **_trade_offer(market[symbol], cash, _capacity(state, level))}
        if not player_trade["quantity"]:
            raise CompanyError("insufficient_cash")
        cash += player_trade["profit"]
    elif not any(employee["active"] for employee in state["employees"]):
        raise CompanyError("no_active_employee")

    workers = _worker_trades(state, cash, level, market)
    if player_trade is None and not workers:
        raise CompanyError("insufficient_cash")

    profit = (player_trade["profit"] if player_trade else 0) + sum(result["profit"] for result in workers)
    state["cash"] += profit
    state["profit"] += profit
    state["peakProfit"] = max(state["peakProfit"], state["profit"])
    state["trades"] += int(player_trade is not None)
    state["day"] += 1
    state["lastTrade"] = player_trade
    state["lastEmployeeTrades"] = workers


def apply_command(state: dict, command: object) -> None:
    """Apply one validated command and convert an older save on its first successful write."""
    if not isinstance(command, dict):
        raise CompanyError("invalid_command")

    action = command.get("action")
    current = normalize_state(state)
    level = _level(current["peakProfit"])
    if action in ("trade", "advance"):
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
        })
    elif action in ("toggle_employee", "set_employee_strategy"):
        employee_id = command.get("employeeId")
        if type(employee_id) is not int or not 1 <= employee_id <= len(current["employees"]):
            raise CompanyError("invalid_employee")
        employee = current["employees"][employee_id - 1]
        if action == "toggle_employee":
            employee["active"] = not employee["active"]
        else:
            strategy = command.get("strategy")
            if not isinstance(strategy, str) or strategy not in _STRATEGIES:
                raise CompanyError("invalid_strategy")
            employee["strategy"] = strategy
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
        next_level = {
            "number": following["number"], "name": following["name"], "target": following["target"],
            "unlock": {"symbol": symbol, "name": ASSETS[symbol]["name"]} if symbol else None,
        }

    assets = []
    for symbol, asset in ASSETS.items():
        unlocked = asset["unlockLevel"] <= level["number"]
        quote = market[symbol]
        offer = _trade_offer(quote, cash, capacity if unlocked else 0)
        assets.append({
            "symbol": symbol, **asset, **quote, "quantity": offer["quantity"], "cost": offer["cost"],
            "profit": offer["profit"], "unlocked": unlocked,
        })

    workers = [
        {**employee, "name": _worker_name(employee),
         "strategy": employee.get("strategy", _DEFAULT_STRATEGY),
         "skill": min(100, employee["trades"] * 100 // len(_TRAINING_RETURNS))}
        for employee in state["employees"]
    ]
    can_advance = any(
        employee["active"] and _worker_symbols(market, level, _worker_budget(cash, _STRATEGIES[employee["strategy"]][0]))
        for employee in workers
    )
    return deepcopy({
        "day": state["day"], "cash": cash, "profit": state["profit"], "peakProfit": state["peakProfit"],
        "trades": state["trades"], "level": {"number": level["number"], "name": level["name"]},
        "nextLevel": next_level, "capacity": capacity, "upgrade": _upgrade_offer(state), "assets": assets,
        "lastTrade": state["lastTrade"], "employees": workers, "hire": _hire_offer(state, level),
        "lastEmployeeTrades": state["lastEmployeeTrades"],
        "canAdvance": can_advance,
    })


def public_standing(state: dict) -> dict:
    """Summarize firm progress for the multiplayer standings."""
    state = normalize_state(state)
    return {
        "level": level_for_profit(state["peakProfit"]), "profit": state["profit"], "day": state["day"],
        "cash": state["cash"], "trades": state["trades"],
    }
