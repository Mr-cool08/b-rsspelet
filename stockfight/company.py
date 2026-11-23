"""Rules and account state for the deterministic company campaign."""

from copy import deepcopy

from .company_catalog import CAPACITY, CHAPTERS, OVERHEAD, PRODUCTS, STARTING_CASH, TIER_IDS


class CompanyError(ValueError):
    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


def default_state() -> dict:
    lots = {product: [] for product in PRODUCTS}
    return {
        "status": "planning",
        "chapter": 0,
        "week": 0,
        "cash": STARTING_CASH,
        "lots": lots,
        "checkpoint": {"cash": STARTING_CASH, "lots": deepcopy(lots)},
        "history": [],
        "chapterOutcome": None,
    }


def _inventory(lots: dict) -> dict[str, int]:
    return {product: sum(quantity for quantity, _ in items) for product, items in lots.items()}


def _stock_value(lots: dict) -> int:
    return sum(quantity * price for items in lots.values() for quantity, price in items)


def _goals(chapter_index: int, history: list[dict], cash: int) -> list[dict]:
    reports = [report for report in history if report["chapter"] == chapter_index + 1]
    values = {
        "profit": sum(report["profit"] for report in reports),
        "cash": cash,
        "contracts": sum(report["contractFulfilled"] for report in reports),
        "units": sum(product["sold"] for report in reports for product in report["products"]),
    }
    return [
        {**goal, "actual": values[goal["type"]], "met": values[goal["type"]] >= goal["target"]}
        for goal in CHAPTERS[chapter_index]["goals"]
    ]


def _week_number(chapter_index: int, week_index: int) -> int:
    return sum(len(chapter["weeks"]) for chapter in CHAPTERS[:chapter_index]) + week_index + 1


def _sell(lots: list[list[int]], units: int) -> tuple[list[list[int]], int]:
    """Sell oldest stock first and deduct what the company paid for those units."""
    remaining_lots = []
    cost = 0
    for quantity, price in lots:
        sold = min(units, quantity)
        units -= sold
        cost += sold * price
        if quantity > sold:
            remaining_lots.append([quantity - sold, price])
    return remaining_lots, cost


def _settle(state: dict, command: dict) -> None:
    chapter_index, week_index = state["chapter"], state["week"]
    chapter = CHAPTERS[chapter_index]
    market = chapter["weeks"][week_index]
    products = market["products"]
    inventory = _inventory(state["lots"])
    purchases = command.get("purchases", {})
    if (not isinstance(purchases, dict) or any(product not in inventory for product in purchases)
            or any(type(units) is not int or units < 0 for units in purchases.values())
            or any(purchases.get(product["id"], 0) > product["supply"] for product in products)):
        raise CompanyError("invalid_purchase")

    purchase_cost = sum(purchases.get(product["id"], 0) * product["buyPrice"] for product in products)
    if purchase_cost > state["cash"]:
        raise CompanyError("insufficient_cash")
    if sum(inventory.values()) + sum(purchases.values()) > CAPACITY:
        raise CompanyError("storage_limit")

    tiers = command.get("tiers", {})
    if (not isinstance(tiers, dict) or any(product not in inventory for product in tiers)
            or any(not isinstance(tier, str) or tier not in TIER_IDS for tier in tiers.values())):
        raise CompanyError("invalid_tier")

    accept_contract = command.get("acceptContract", False)
    contract = market["contract"] if accept_contract is True else None
    if type(accept_contract) is not bool or (accept_contract and contract is None):
        raise CompanyError("invalid_contract")
    if contract:
        product = contract["productId"]
        if inventory[product] + purchases.get(product, 0) < contract["units"]:
            raise CompanyError("insufficient_contract_stock")

    lots = {}
    lines = []
    cost_of_goods = 0
    for product in products:
        product_id = product["id"]
        quantity = purchases.get(product_id, 0)
        available = inventory[product_id] + quantity
        price_tier = next(tier for tier in product["tiers"] if tier["id"] == tiers.get(product_id, "regular"))
        contract_units = contract["units"] if contract and contract["productId"] == product_id else 0
        contract_revenue = contract_units * contract["price"] if contract else 0
        retail_units = min(available - contract_units, price_tier["demand"])
        sold = contract_units + retail_units
        existing_lots = state["lots"][product_id]
        if quantity:
            existing_lots = [*existing_lots, [quantity, product["buyPrice"]]]
        lots[product_id], cost = _sell(existing_lots, sold)
        cost_of_goods += cost
        lines.append({
            "id": product_id, "purchased": quantity, "sold": sold, "stock": available - sold,
            "revenue": contract_revenue + retail_units * price_tier["price"],
            "contractUnits": contract_units, "retailSold": retail_units,
        })

    revenue = sum(line["revenue"] for line in lines)
    cash = state["cash"] - purchase_cost + revenue - OVERHEAD
    report = {
        "week": _week_number(chapter_index, week_index), "chapter": chapter_index + 1,
        "weekInChapter": week_index + 1, "revenue": revenue, "purchaseCost": purchase_cost,
        "costOfGoods": cost_of_goods, "overhead": OVERHEAD, "profit": revenue - cost_of_goods - OVERHEAD,
        "cash": cash, "contractFulfilled": accept_contract, "products": lines,
    }
    state.update(cash=cash, lots=lots, history=[*state["history"], report], chapterOutcome=None)

    end_of_chapter = week_index + 1 == len(chapter["weeks"])
    if not end_of_chapter and cash >= 0:
        state["week"] += 1
        return

    goals = _goals(chapter_index, state["history"], cash)
    passed = cash >= 0 and all(goal["met"] for goal in goals)
    reason = None if passed else "cash" if cash < 0 else "goals"
    state["chapterOutcome"] = {
        "chapter": chapter_index + 1, "name": chapter["name"], "status": "passed" if passed else "failed",
        "reason": reason, "goals": goals,
    }
    if not passed:
        state["status"] = "failed"
    elif chapter_index + 1 == len(CHAPTERS):
        state["status"] = "won"
    else:
        state.update(chapter=chapter_index + 1, week=0, checkpoint={"cash": cash, "lots": deepcopy(lots)})


def apply_command(state: dict, command: object) -> None:
    """Resolve one submitted plan or change campaign status."""
    if not isinstance(command, dict):
        raise CompanyError("invalid_command")
    action = command.get("action")
    allowed = {"settle": ("planning",), "retry": ("failed",), "restart": ("won", "failed")}
    if not isinstance(action, str) or action not in allowed:
        raise CompanyError("invalid_command")
    if state["status"] not in allowed[action]:
        raise CompanyError("invalid_status")

    if action == "settle":
        _settle(state, command)
    elif action == "retry":
        checkpoint = state["checkpoint"]
        history = [report for report in state["history"] if report["chapter"] <= state["chapter"]]
        state.update(status="planning", week=0, cash=checkpoint["cash"], lots=deepcopy(checkpoint["lots"]),
                     history=history, chapterOutcome=None)
    else:
        state.clear()
        state.update(default_state())


def public_state(state: dict) -> dict:
    """Expose the current market and a one-week outlook for planning stock purchases."""
    chapter_index, week_index = state["chapter"], state["week"]
    chapter = CHAPTERS[chapter_index]
    weeks = chapter["weeks"]
    market = next_market = None
    if state["status"] == "planning":
        market = weeks[week_index]
        if week_index + 1 < len(weeks):
            next_market = weeks[week_index + 1]
        elif chapter_index + 1 < len(CHAPTERS):
            next_market = CHAPTERS[chapter_index + 1]["weeks"][0]
    history = state["history"]
    return deepcopy({
        "status": state["status"],
        "chapter": {
            "number": chapter_index + 1, "total": len(CHAPTERS), "name": chapter["name"],
            "description": chapter["description"], "goals": _goals(chapter_index, history, state["cash"]),
        },
        "week": _week_number(chapter_index, week_index), "weekInChapter": week_index + 1,
        "weeksInChapter": len(weeks), "cash": state["cash"], "inventory": _inventory(state["lots"]),
        "inventoryValue": _stock_value(state["lots"]),
        "capacity": CAPACITY, "overhead": OVERHEAD, "market": market, "nextMarket": next_market,
        "history": history, "lastReport": history[-1] if history else None, "chapterOutcome": state["chapterOutcome"],
    })


def public_standing(state: dict) -> dict:
    """Summarize company progress for other players without revealing individual trades."""
    cash = state["cash"]
    return {
        "status": state["status"], "chapter": state["chapter"] + 1, "week": len(state["history"]),
        "equity": cash + _stock_value(state["lots"]), "cash": cash,
    }
