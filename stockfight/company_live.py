"""Publish the shared quote and settle all firms with live employees."""

from time import time

from sqlalchemy.exc import SQLAlchemyError

from . import company, company_bots
from .company_quotes import TICK_SECONDS, load_frames, market_tick, publish_tick
from .data import CompanySave, db, save_campaign


def load_firm(user_id):
    saved = db.session.get(CompanySave, user_id)
    if saved is None:
        return 0, company.default_state()
    return saved.revision, company.normalize_state(saved.state)


def settle_firm(user_id, tick):
    revision, state = load_firm(user_id)
    for _ in range(3):
        if not company_bots.apply_ticks(state, tick):
            break
        state["standing"] = company.public_standing(state)
        if save_campaign(user_id, revision, state, model=CompanySave):
            return revision + 1, state, True
        revision, state = load_firm(user_id)
    return revision, state, False


def run_live_tick(app, tick, now=None):
    provider = app.config.get("COMPANY_MARKET_PROVIDER")
    if provider is None:
        return False
    changed = False
    with app.app_context():
        publish_tick(provider, tick, now)
        load_frames(tick)
        after = 0
        employees = CompanySave.state["employees"][0]["id"].as_integer()
        while True:
            firms = db.session.scalars(db.select(CompanySave.user_id).where(
                CompanySave.user_id > after, employees.is_not(None),
            ).order_by(CompanySave.user_id).limit(100)).all()
            if not firms:
                break
            for user_id in firms:
                _, _, settled = settle_firm(user_id, tick)
                changed |= settled
            after = firms[-1]
    return changed


def start_live_market(app, socketio, namespace):
    if not app.config["COMPANY_MARKET_BACKGROUND"] or app.config["COMPANY_MARKET_PROVIDER"] is None:
        return
    clock = app.config.get("COMPANY_MARKET_CLOCK", time)

    def run():
        while True:
            now = clock()
            tick = market_tick(now)
            try:
                if run_live_tick(app, tick, now):
                    socketio.emit("company_market_changed", namespace=namespace)
            except SQLAlchemyError:
                app.logger.exception("Databasfel vid uppdatering av börsföretag.")
            socketio.sleep(max(0.05, (tick + 1) * TICK_SECONDS - clock()))

    socketio.start_background_task(run)
