"""Account-scoped routes for the campaign and its revisioned save."""

from time import time

from flask import current_app, jsonify, redirect, render_template, request, session, url_for
from sqlalchemy import func

from . import company, company_bots, company_market
from .campaign import CampaignError, apply_command, default_state, public_state
from .chat import chat_error
from .company_live import load_firm, settle_firm
from .data import CampaignSave, CompanySave, User, db, save_campaign
from .multiplayer import token_matches


COMPANY_NAMESPACE = "/company"


def _player_id():
    user_id = session.get("user_id")
    if user_id is not None and db.session.get(User, user_id) is not None:
        return user_id
    return None


def install_company_socket(socketio):
    def chat():
        return current_app.extensions["public_chat"]

    @socketio.on("connect", namespace=COMPANY_NAMESPACE)
    def connect_company(auth=None):
        token = session.get("csrf")
        user_id = session.get("user_id")
        if not isinstance(auth, dict) or not token_matches(token, auth.get("csrfToken")) or user_id is None:
            return False
        user = db.session.get(User, user_id)
        if user is None:
            return False
        chat().connect(request.sid, user, token)

    @socketio.on("disconnect", namespace=COMPANY_NAMESPACE)
    def disconnect_company(reason=None):
        chat().disconnect(request.sid)

    @socketio.on("company_chat_history", namespace=COMPANY_NAMESPACE)
    def company_chat_history(payload=None, *extra):
        if extra:
            return chat_error("chat_invalid")
        return chat().subscribe(request.sid, payload)

    @socketio.on("company_chat_send", namespace=COMPANY_NAMESPACE)
    def company_chat_send(payload=None, *extra):
        if extra:
            return chat_error("chat_invalid")
        return chat().send(request.sid, payload)


def _share_price(standing):
    return max(5, 25 + int(standing["profit"] // 5))


def _trade_share(user_id, state, command):
    firm_id, quote = command.get("firmId"), command.get("quote")
    if type(firm_id) is not int or not 0 < firm_id <= 2_147_483_647 or type(quote) is not int or quote <= 0:
        raise company.CompanyError("invalid_command")
    if firm_id == user_id:
        raise company.CompanyError("self_trade")
    issuer = db.session.get(CompanySave, firm_id)
    if issuer is None and db.session.get(User, firm_id) is None:
        raise company.CompanyError("invalid_firm")
    price = _share_price(company.public_standing(issuer.state if issuer else company.default_state()))
    if quote != price:
        raise company.CompanyError("stale_quote")

    shares = state["peerShares"]
    key = str(firm_id)
    quantity = shares.get(key, 0)
    if command["action"] == "buy_peer":
        if company.available_cash(state) < price:
            raise company.CompanyError("insufficient_cash")
        state["cash"] -= price
        shares[key] = quantity + 1
    else:
        if quantity == 0:
            raise company.CompanyError("insufficient_shares")
        state["cash"] += price
        if quantity == 1:
            del shares[key]
        else:
            shares[key] = quantity - 1

    # Check the issuer snapshot within the same write that settles the buyer's balance.
    listed = CompanySave.__table__.alias("listed_firm")
    listing = db.select(listed.c.user_id).where(listed.c.user_id == firm_id)
    if issuer is None:
        return ~listing.exists()
    return listing.where(listed.c.revision == issuer.revision).exists()


def register_campaign(app, socketio):
    clock = app.config.get("CAMPAIGN_CLOCK", time)
    market_clock = app.config.get("COMPANY_MARKET_CLOCK", time)

    def load_save(user_id):
        saved = db.session.get(CampaignSave, user_id)
        return (saved.revision, saved.state) if saved is not None else (0, default_state())

    def snapshot(revision, state, now):
        return {**public_state(state, now), "revision": revision}

    @app.get("/campaign")
    def campaign_page():
        if _player_id() is None:
            return redirect(url_for("index"))
        return render_template("company.html")

    @app.get("/campaign/portfolio")
    def portfolio_campaign_page():
        if _player_id() is None:
            return redirect(url_for("index"))
        return render_template("campaign.html")

    def company_snapshot(revision, state):
        return {**company.public_state(state), "revision": revision}

    def market_snapshot(revision, state, now):
        market = company_market.public_state(state, revision, now)
        tick = market["tick"]
        totals = company_bots.totals(state, tick)
        market["bots"] = company_bots.public_state(state, tick)
        market["equity"] = round(market["equity"] + totals["liquidationValue"], 2)
        market["unrealizedProfit"] = round(market["unrealizedProfit"] + totals["unrealizedProfit"], 2)
        market["fees"] = round(market["fees"] + totals["fees"], 2)
        return market

    @app.get("/api/company")
    def company_state():
        user_id = _player_id()
        if user_id is None:
            return jsonify(error="login_required"), 401
        return company_snapshot(*load_firm(user_id))

    @app.get("/api/company/market")
    def live_company_market():
        user_id = _player_id()
        if user_id is None:
            return jsonify(error="login_required"), 401
        now = market_clock()
        return market_snapshot(*load_firm(user_id), now)

    @app.get("/api/company/standings")
    def company_standings():
        user_id = _player_id()
        if user_id is None:
            return jsonify(error="login_required"), 401

        state = load_firm(user_id)[1]
        positions = state["peerShares"]
        standing = CompanySave.state["standing"]
        legacy_profit = standing["week"].as_integer() * company.LEGACY_PROFIT_PER_WEEK
        profit = func.coalesce(standing["profit"].as_float(), legacy_profit, 0)
        firms = db.select(User.id, User.username, CompanySave.state).outerjoin(CompanySave, CompanySave.user_id == User.id)
        search = request.args.get("search", "").strip()[:80].casefold()
        page = min(1_000_000, max(1, request.args.get("page", 1, type=int)))
        matching = firms.where(User.username_key.contains(search, autoescape=True)) if search else firms
        rows = db.session.execute(matching.order_by(profit.desc(), User.username_key, User.id)
                                  .offset((page - 1) * 50).limit(51)).all()
        has_more = len(rows) > 50
        rows = rows[:50]

        relevant = {int(key) for key in positions}
        if not search and page == 1:
            relevant.add(user_id)
        visible = {player_id for player_id, _, _ in rows}
        extra = relevant - visible
        additional = db.session.execute(firms.where(User.id.in_(extra)).order_by(User.username_key)).all() if extra else []
        holdings_value = 0
        for player_id, _, saved in [*rows, *additional]:
            if held := positions.get(str(player_id), 0):
                holdings_value += held * _share_price(company.public_standing(saved if saved else company.default_state()))

        if not search and page == 1:
            rows.extend(additional)

        listings = []
        for player_id, username, saved in rows:
            public = company.public_standing(saved if saved else company.default_state())
            listings.append({"id": player_id, "name": f"{username} Capital", "isYou": player_id == user_id,
                             "level": public["level"], "profit": public["profit"], "price": _share_price(public),
                             "held": positions.get(str(player_id), 0)})
        return {"companies": listings, "cashReserve": company.required_cash(state),
                "page": page, "hasMore": has_more, "holdingsValue": holdings_value}

    @app.post("/api/company/commands")
    def company_command():
        user_id = _player_id()
        if user_id is None:
            return jsonify(error="login_required"), 401
        command = request.get_json(silent=True)
        if not isinstance(command, dict) or type(command.get("revision")) is not int or command["revision"] < 0:
            return jsonify(error="invalid_command"), 400

        action = command.get("action")
        if action in ("trade", "advance") and not app.config.get("COMPANY_LEGACY_TRADES", False):
            return jsonify(error="invalid_command"), 400
        now = market_clock()
        tick = company_market.trading_tick(now)
        if app.config["COMPANY_MARKET_PROVIDER"] is not None:
            revision, state, settled = settle_firm(user_id, tick)
            if settled:
                socketio.emit("company_market_changed", namespace=COMPANY_NAMESPACE)
        else:
            revision, state = load_firm(user_id)

        def conflict(error, revision, state):
            response = {"error": error, "state": company_snapshot(revision, state)}
            if action == "market_trade":
                response["market"] = market_snapshot(revision, state, now)
            return jsonify(response), 409

        if command["revision"] != revision:
            return conflict("stale_revision", revision, state)

        condition = None
        try:
            if action in ("buy_peer", "sell_peer"):
                condition = _trade_share(user_id, state, command)
            elif action == "market_trade":
                company_market.apply_command(state, command, tick)
            else:
                company.apply_command(state, command)
        except company.CompanyError as exc:
            if exc.code == "stale_quote":
                return conflict(exc.code, revision, state)
            return jsonify(error=exc.code), 400

        company_bots.anchor(state, tick)
        state["standing"] = company.public_standing(state)
        if not save_campaign(user_id, revision, state, model=CompanySave, condition=condition):
            current_revision, latest = load_firm(user_id)
            error = "stale_quote" if condition is not None and current_revision == revision else "stale_revision"
            return conflict(error, current_revision, latest)
        socketio.emit("company_market_changed", namespace=COMPANY_NAMESPACE)
        response = company_snapshot(revision + 1, state)
        if action == "market_trade":
            response["market"] = market_snapshot(revision + 1, state, now)
        return response

    @app.get("/api/campaign")
    def campaign_state():
        user_id = _player_id()
        if user_id is None:
            return jsonify(error="login_required"), 401
        revision, state = load_save(user_id)
        return snapshot(revision, state, clock())

    @app.post("/api/campaign/commands")
    def campaign_command():
        user_id = _player_id()
        if user_id is None:
            return jsonify(error="login_required"), 401
        command = request.get_json(silent=True)
        if not isinstance(command, dict) or type(command.get("revision")) is not int or command["revision"] < 0:
            return jsonify(error="invalid_command"), 400

        revision, state = load_save(user_id)
        now = clock()
        if command["revision"] != revision:
            return jsonify(error="stale_revision", state=snapshot(revision, state, now)), 409

        try:
            apply_command(state, command, now)
        except CampaignError as exc:
            if exc.code == "stale_quote":
                return jsonify(error=exc.code, state=snapshot(revision, state, now)), 409
            return jsonify(error=exc.code), 400

        if not save_campaign(user_id, revision, state):
            revision, state = load_save(user_id)
            return jsonify(error="stale_revision", state=snapshot(revision, state, clock())), 409
        return snapshot(revision + 1, state, now)
