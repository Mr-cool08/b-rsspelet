"""Run each employee's configured strategy against the shared live market."""

from . import company, company_market


_MAX_CATCH_UP_TICKS = 120


def signal(config: dict, history: list[int]) -> str | None:
    """Return a buy or sell signal using only the lookback and current quote."""
    lookback = config["lookback"]
    if len(history) <= lookback:
        return None
    previous = history[-lookback - 1:-1]
    current = history[-1]
    threshold = round(config["threshold"] * 100)
    if config["strategy"] == "mean_reversion":
        total = sum(previous)
        scaled_quote = current * lookback * 10_000
        if scaled_quote <= total * (10_000 - threshold):
            return "buy"
        if scaled_quote >= total * (10_000 + threshold):
            return "sell"
        return None

    lower = upper = previous[0]
    if config["strategy"] == "breakout":
        lower, upper = min(previous), max(previous)
    if current * 10_000 >= upper * (10_000 + threshold):
        return "buy"
    if current * 10_000 <= lower * (10_000 - threshold):
        return "sell"
    return None


def _live_config(state: dict, employee: dict) -> dict:
    config = company.bot_configuration(employee)
    return {**config, "lookback": config["lookback"] + company.desk_terms(state)["lookbackBonus"]}


def _history(symbol: str, tick: int, lookback: int, cache: dict) -> list[int]:
    current_key = (symbol, tick)
    if current_key not in cache:
        cache[current_key] = company_market.price_on_tick(symbol, tick)
    current = cache[current_key]
    if current is None:
        return []

    history = []
    for step in range(max(0, tick - lookback), tick):
        key = (symbol, step)
        if key not in cache:
            cache[key] = company_market.price_on_tick(symbol, step)
        if cache[key] is not None:
            history.append(cache[key])
    return [*history, current]


def _exit_reason(position: dict, config: dict, history: list[int]) -> str | None:
    is_long = position["side"] == "long"
    entry = position["entryValue"]
    move = history[-1] * position["quantity"] - entry
    gain = move if is_long else -move
    if gain * 100 <= -entry * config["stopLoss"]:
        return "stop_loss"
    if gain * 100 >= entry * config["takeProfit"]:
        return "take_profit"

    if config["strategy"] == "mean_reversion" and len(history) > config["lookback"]:
        # The average is the target for either side of a mean-reversion trade.
        difference = history[-1] * config["lookback"] - sum(history[:-1])
        if (is_long and difference >= 0) or (not is_long and difference <= 0):
            return "signal"
    if signal(config, history) == ("sell" if is_long else "buy"):
        return "signal"
    return None


def _run_employee(state: dict, employee: dict, config: dict, tick: int, quotes: dict) -> bool:
    book = employee.get("botBook") or company_market.new_book()
    if not employee["active"] and not book["positions"]:
        return False

    lookback = config["lookback"]
    if book["positions"]:
        symbol, position = next(iter(book["positions"].items()))
        history = _history(symbol, tick, lookback, quotes)
        if not history:
            return False
        reason = _exit_reason(position, config, history)
        if reason is None:
            return False
        side = "sell" if position["side"] == "long" else "cover"
        trade = company_market.execute_order(state, book, symbol, side, position["quantity"], tick, employee=True)
        trade["reason"] = reason
        company.record_employee_trade(state, employee, trade)
        return True

    budget = company.bot_budget(state, employee)
    if budget <= 0:
        return False
    focus = employee.get("focus", "all")
    level = company.level_for_profit(state["peakProfit"])
    for symbol, asset in company_market.LIVE_ASSETS.items():
        if (focus in company_market.LIVE_ASSETS and focus != symbol) or asset["unlockLevel"] > level:
            continue
        history = _history(symbol, tick, lookback, quotes)
        decision = signal(config, history)
        if decision is None:
            continue
        side = "buy" if decision == "buy" else "short"
        quantity = company_market.order_limits(state, book, symbol, history[-1], budget=budget)[side]
        if quantity:
            trade = company_market.execute_order(state, book, symbol, side, quantity, tick, employee=True)
            trade["reason"] = "signal"
            employee["botBook"] = book
            return True
    return False


def anchor(state: dict, tick: int) -> None:
    if state["employees"]:
        state["botTick"] = max(tick, state.get("botTick", tick))


def apply_ticks(state: dict, tick: int) -> bool:
    """Settle expired ticks in order, persisting the cursor with the next change."""
    employees = state["employees"]
    if not employees:
        return False
    if "botTick" not in state:
        anchor(state, tick)
        return True
    workers = [(employee, _live_config(state, employee)) for employee in employees
               if employee["active"] or employee.get("botBook", {}).get("positions")]
    if not workers:
        return False

    first_tick = max(state["botTick"] + 1, tick - _MAX_CATCH_UP_TICKS + 1)
    changed = False
    quotes = {}
    for step in range(first_tick, tick + 1):
        for employee, config in workers:
            if _run_employee(state, employee, config, step, quotes):
                changed = True
    if changed:
        anchor(state, tick)
    return changed


def public_state(state: dict, tick: int) -> list[dict]:
    bots = []
    for employee in state["employees"]:
        book = employee.get("botBook") or company_market.new_book()
        symbol = next(iter(book["positions"]), None)
        position = None
        if symbol is not None:
            price = company_market.latest_price(symbol, tick)
            position = {"symbol": symbol, **company_market.position_snapshot(book, symbol, price)}
        bots.append({
            "employeeId": employee["id"], "name": company.employee_name(employee), "active": employee["active"],
            "configuration": company.bot_configuration(employee), "position": position, "lastTrade": book["lastTrade"],
        })
    return bots


def totals(state: dict, tick: int) -> dict:
    result = {"liquidationValue": 0, "unrealizedProfit": 0, "fees": 0}
    for employee in state["employees"]:
        if book := employee.get("botBook"):
            values = company_market.book_totals(book, tick)
            for key in result:
                result[key] += values[key]
    return {key: round(value, 2) for key, value in result.items()}
