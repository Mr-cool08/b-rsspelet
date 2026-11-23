"""Account-scoped routes for the campaign and its revisioned save."""

from time import time

from flask import jsonify, redirect, render_template, request, session, url_for

from .campaign import CampaignError, apply_command, default_state, public_state
from .data import CampaignSave, User, db, save_campaign


def register_campaign(app):
    clock = app.config.get("CAMPAIGN_CLOCK", time)

    def campaign_user_id():
        user_id = session.get("user_id")
        if user_id is not None and db.session.get(User, user_id) is not None:
            return user_id
        return None

    def load_save(user_id):
        saved = db.session.get(CampaignSave, user_id)
        return (saved.revision, saved.state) if saved is not None else (0, default_state())

    def snapshot(revision, state, now):
        return {**public_state(state, now), "revision": revision}

    @app.get("/campaign")
    def campaign_page():
        if campaign_user_id() is None:
            return redirect(url_for("index"))
        return render_template("campaign.html")

    @app.get("/api/campaign")
    def campaign_state():
        user_id = campaign_user_id()
        if user_id is None:
            return jsonify(error="login_required"), 401
        revision, state = load_save(user_id)
        return snapshot(revision, state, clock())

    @app.post("/api/campaign/commands")
    def campaign_command():
        user_id = campaign_user_id()
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
