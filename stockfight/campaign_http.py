"""Account-scoped routes for the campaign and its revisioned save."""

from time import time

from flask import jsonify, redirect, render_template, request, session, url_for
from sqlalchemy import func

from . import company
from .campaign import CampaignError, apply_command, default_state, public_state
from .company_catalog import TRADE_RESERVE
from .data import CampaignSave, CompanySave, User, db, save_campaign
from .multiplayer import token_matches


COMPANY_NAMESPACE = "/company"


def _player_id():
    user_id = session.get("user_id")
    if user_id is not None and db.session.get(User, user_id) is not None:
        return user_id
    return None


def install_company_socket(socketio):
    @socketio.on("connect", namespace=COMPANY_NAMESPACE)
    def connect_company(auth=None):
        return bool(_player_id() is not None and isinstance(auth, dict)
                    and token_matches(session.get("csrf"), auth.get("csrfToken")))


def _share_price(standing):
    return max(5, 25 + standing["profit"] // 5)


def _trade_share(user_id, state, command):
    firm_id, quote = command.get("firmId"), command.get("quote")
    if type(firm_id) is not int or not 0 < firm_id <= 2_147_483_647 or type(quote) is not int or quote <= 0:
        raise company.CompanyError("invalid_command")
    if firm_id == user_id:
        raise company.CompanyError("self_trade")
    issuer = db.session.get(CompanySave, firm_id)
    if issuer is None:
        raise company.CompanyError("invalid_firm")
    price = _share_price(company.public_standing(issuer.state))
    if quote != price:
        raise company.CompanyError("stale_quote")

    shares = state["peerShares"]
    key = str(firm_id)
    quantity = shares.get(key, 0)
    if command["action"] == "buy_peer":
        if state["cash"] - price < TRADE_RESERVE:
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
    return db.select(listed.c.user_id).where(
        listed.c.user_id == firm_id, listed.c.revision == issuer.revision,
    ).exists()


def register_campaign(app, socketio):
    clock = app.config.get("CAMPAIGN_CLOCK", time)

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

    def load_company(user_id):
        saved = db.session.get(CompanySave, user_id)
        return (saved.revision, company.normalize_state(saved.state)) if saved else (0, company.default_state())

    def company_snapshot(revision, state):
        return {**company.public_state(state), "revision": revision}

    @app.get("/api/company")
    def company_state():
        user_id = _player_id()
        if user_id is None:
            return jsonify(error="login_required"), 401
        return company_snapshot(*load_company(user_id))

    @app.get("/api/company/standings")
    def company_standings():
        user_id = _player_id()
        if user_id is None:
            return jsonify(error="login_required"), 401

        positions = load_company(user_id)[1]["peerShares"]
        standing = CompanySave.state["standing"]
        legacy_profit = standing["week"].as_integer() * company.LEGACY_PROFIT_PER_WEEK
        profit = func.coalesce(standing["profit"].as_integer(), legacy_profit, 0)
        firms = db.select(User.id, User.username, CompanySave.state).join(CompanySave, CompanySave.user_id == User.id)
        rows = db.session.execute(firms.order_by(profit.desc(), User.username_key).limit(50)).all()
        shown = {player_id for player_id, _, _ in rows}
        extra = ({int(key) for key in positions} | {user_id}) - shown
        if extra:
            rows.extend(db.session.execute(firms.where(User.id.in_(extra)).order_by(User.username_key)).all())

        listings = []
        for player_id, username, saved in rows:
            public = company.public_standing(saved)
            listings.append({"id": player_id, "name": f"{username} Capital", "isYou": player_id == user_id,
                             "level": public["level"], "profit": public["profit"], "price": _share_price(public),
                             "held": positions.get(str(player_id), 0)})
        return {"companies": listings, "cashReserve": TRADE_RESERVE}

    @app.post("/api/company/commands")
    def company_command():
        user_id = _player_id()
        if user_id is None:
            return jsonify(error="login_required"), 401
        command = request.get_json(silent=True)
        if not isinstance(command, dict) or type(command.get("revision")) is not int or command["revision"] < 0:
            return jsonify(error="invalid_command"), 400

        revision, state = load_company(user_id)
        if command["revision"] != revision:
            return jsonify(error="stale_revision", state=company_snapshot(revision, state)), 409

        condition = None
        try:
            if command.get("action") in ("buy_peer", "sell_peer"):
                condition = _trade_share(user_id, state, command)
            else:
                company.apply_command(state, command)
        except company.CompanyError as exc:
            if exc.code == "stale_quote":
                return jsonify(error=exc.code, state=company_snapshot(revision, state)), 409
            return jsonify(error=exc.code), 400

        state["standing"] = company.public_standing(state)
        if not save_campaign(user_id, revision, state, model=CompanySave, condition=condition):
            current_revision, latest = load_company(user_id)
            error = "stale_quote" if condition is not None and current_revision == revision else "stale_revision"
            return jsonify(error=error, state=company_snapshot(current_revision, latest)), 409
        socketio.emit("company_market_changed", namespace=COMPANY_NAMESPACE)
        return company_snapshot(revision + 1, state)

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
