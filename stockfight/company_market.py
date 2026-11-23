"""Cash-settled long and short game orders priced from real equity quotes."""

from flask import current_app

from . import company
from .company_catalog import LIVE_ASSETS
from .company_quotes import TICK_SECONDS, frames_through, latest_frame, latest_price, latest_quote, market_tick, price_on_tick


_HISTORY_LENGTH = 48
_SIDES = ("buy", "sell", "short", "cover")


def trading_tick(now):
    wall_tick = market_tick(now)
    frame = latest_frame(wall_tick)
    return frame.tick if frame and frame.tick >= wall_tick - 1 else wall_tick


def _fee(value):
    return (value + 999) // 1000


def cash_cents(state):
    return state["cash"] * 100 + state.get("cashRemainder", 0)


def _available_cash_cents(state):
    return max(0, cash_cents(state) - company.required_cash(state) * 100)


def _change_cash(state, amount):
    state["cash"], state["cashRemainder"] = divmod(cash_cents(state) + amount, 100)


def new_book():
    return {"positions": {}, "fees": 0, "lastTrade": None}


def _max_affordable(cash, order_limit, price, unit_cost):
    quantity = min(order_limit, max(0, cash) // unit_cost)
    while quantity > 0 and quantity * unit_cost + _fee(quantity * price) > cash:
        quantity -= 1
    return quantity


def order_limits(state, book, symbol, price, *, budget=None):
    limits = dict.fromkeys(_SIDES, 0)
    if price is None or not _is_unlocked(state, symbol):
        return limits

    position = book["positions"].get(symbol)
    held = position["quantity"] if position else 0
    remaining = max(0, company.trading_capacity(state) - held)
    available = _available_cash_cents(state)
    if budget is not None:
        available = min(available, int(budget * 100))
    if not position or position["side"] == "long":
        limits["buy"] = _max_affordable(available, remaining, price, price)
        limits["sell"] = held
    if not position or position["side"] == "short":
        limits["short"] = _max_affordable(available, remaining, price, price)
        limits["cover"] = held
    return limits


def _is_unlocked(state, symbol):
    return LIVE_ASSETS[symbol]["unlockLevel"] <= company.level_for_profit(state["peakProfit"])


def _liquidation_value(position, price):
    quantity = position["quantity"]
    value = price * quantity
    if position["side"] == "long":
        return value - _fee(value)
    return max(0, position["collateral"] + position["entryValue"] - value - _fee(value))


def position_snapshot(book, symbol, price):
    position = book["positions"].get(symbol)
    if position is None:
        return None
    is_short = position["side"] == "short"
    quantity = position["quantity"]
    if price is None:
        price = round(position["entryValue"] / quantity)
    collateral = position.get("collateral", 0)
    entry_cost = collateral if is_short else position["entryValue"]
    return {
        "side": position["side"], "quantity": quantity,
        "averagePrice": round(position["entryValue"] / quantity / 100, 2),
        "unrealizedProfit": (_liquidation_value(position, price) - entry_cost - position["entryFees"]) / 100,
        "collateral": collateral / 100,
    }


def book_totals(book, tick):
    liquidation = 0
    unrealized = 0
    for symbol, position in book["positions"].items():
        price = latest_price(symbol, tick)
        if price is None:
            price = round(position["entryValue"] / position["quantity"])
        liquidation += _liquidation_value(position, price)
        unrealized += position_snapshot(book, symbol, price)["unrealizedProfit"]
    return {"liquidationValue": liquidation / 100, "unrealizedProfit": round(unrealized, 2), "fees": book["fees"] / 100}


def execute_order(state, book, symbol, side, quantity, tick, *, employee=False):
    if not isinstance(symbol, str) or symbol not in LIVE_ASSETS:
        raise company.CompanyError("invalid_asset")
    if not _is_unlocked(state, symbol):
        raise company.CompanyError("locked_asset")
    if side not in _SIDES:
        raise company.CompanyError("invalid_command")
    if type(quantity) is not int or quantity <= 0:
        raise company.CompanyError("invalid_quantity")

    price = price_on_tick(symbol, tick)
    if price is None:
        raise company.CompanyError("market_unavailable")
    limits = order_limits(state, book, symbol, price)
    positions = book["positions"]
    position = positions.get(symbol)
    opening = side in ("buy", "short")
    position_side = "long" if side in ("buy", "sell") else "short"
    if quantity > limits[side]:
        if not opening:
            raise company.CompanyError("insufficient_shares")
        if position and position["side"] != position_side:
            raise company.CompanyError("position_conflict")
        held = position["quantity"] if position else 0
        if held + quantity > company.trading_capacity(state):
            raise company.CompanyError("position_limit")
        raise company.CompanyError("insufficient_cash")

    value = price * quantity
    fee = _fee(value)
    profit = None
    company.record_desk_use(state)
    if opening:
        if position is None:
            position = positions[symbol] = {
                "side": position_side, "quantity": 0, "entryValue": 0, "entryFees": 0, "collateral": 0,
            }
        position["quantity"] += quantity
        position["entryValue"] += value
        position["entryFees"] += fee
        if side == "short":
            position["collateral"] += value
        _change_cash(state, -value - fee)
    else:
        entry_value = position["entryValue"] * quantity // position["quantity"]
        entry_fees = position["entryFees"] * quantity // position["quantity"]
        if side == "sell":
            _change_cash(state, value - fee)
            profit = (value - entry_value - fee - entry_fees) / 100
        else:
            collateral = position["collateral"] * quantity // position["quantity"]
            remaining_collateral = max(0, collateral + entry_value - value)
            fee = min(fee, remaining_collateral)
            released = remaining_collateral - fee
            _change_cash(state, released)
            position["collateral"] -= collateral
            profit = (released - collateral - entry_fees) / 100
        position["quantity"] -= quantity
        position["entryValue"] -= entry_value
        position["entryFees"] -= entry_fees
        if not position["quantity"]:
            del positions[symbol]
        company.record_trading_profit(state, profit, employee=employee)

    state["trades"] += 1
    book["fees"] += fee
    trade = {"symbol": symbol, "side": side, "quantity": quantity, "price": price / 100, "fee": fee / 100, "profit": profit}
    book["lastTrade"] = trade
    return trade


def apply_command(state, command, tick):
    quoted_tick = command.get("tick")
    if type(quoted_tick) is not int:
        raise company.CompanyError("invalid_command")
    if quoted_tick != tick:
        raise company.CompanyError("stale_quote")
    if current_app.config["COMPANY_MARKET_PROVIDER"] is None:
        raise company.CompanyError("market_unavailable")
    frame = latest_frame(tick)
    if frame and frame.tick == tick and frame.market_open is False:
        raise company.CompanyError("market_closed")
    book = state.get("liveTrading", new_book())
    execute_order(state, book, command.get("symbol"), command.get("side"), command.get("quantity"), tick)
    state["liveTrading"] = book


def public_state(state, revision, now):
    tick = trading_tick(now)
    frame = latest_frame(tick)
    provider = current_app.config.get("COMPANY_MARKET_PROVIDER")
    status = "unavailable"
    if provider and frame and frame.tick == tick and frame.market_open is not None:
        status = "open" if frame.market_open else "closed"
    book = state.get("liveTrading", new_book())
    assets = []
    for symbol, asset in LIVE_ASSETS.items():
        quote = latest_quote(symbol, tick)
        price, quoted_at = quote if quote else (None, None)
        history = []
        for step in sorted(frames_through(tick)):
            if step <= tick and (sample := price_on_tick(symbol, step)) is not None:
                history.append({"time": step * TICK_SECONDS, "price": sample / 100})
        history = history[-_HISTORY_LENGTH:]
        if quote and not history:
            history.append({"time": int(quoted_at), "price": price / 100})
        previous_price = history[-2]["price"] if len(history) > 1 else None
        tradable_price = price_on_tick(symbol, tick) if status == "open" else None
        assets.append({
            "symbol": symbol, "name": asset["name"], "unlocked": _is_unlocked(state, symbol),
            "price": price / 100 if price is not None else None, "quotedAt": quoted_at,
            "tradable": tradable_price is not None,
            "changePercent": round((price / 100 / previous_price - 1) * 100, 2) if previous_price else 0,
            "history": history, "position": position_snapshot(book, symbol, price),
            "maxOrder": order_limits(state, book, symbol, tradable_price),
        })

    totals = book_totals(book, tick)
    cash = cash_cents(state) / 100
    return {
        "revision": revision, "tick": tick, "tickSeconds": TICK_SECONDS, "serverTime": now,
        "nextTickAt": (market_tick(now) + 1) * TICK_SECONDS, "cash": cash, "reserve": company.cash_reserve(state),
        "availableCash": _available_cash_cents(state) / 100,
        "awaitingTick": bool(provider and (not frame or frame.tick < market_tick(now))),
        "status": status, "source": provider.name if provider else None,
        "unrealizedProfit": totals["unrealizedProfit"], "equity": round(cash + totals["liquidationValue"], 2),
        "fees": totals["fees"], "lastTrade": book["lastTrade"], "assets": assets,
    }
