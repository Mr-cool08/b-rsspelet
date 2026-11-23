import os
import secrets
from pathlib import Path

import click
from dotenv import load_dotenv
from flask import Flask, jsonify, render_template, request, session
from flask_socketio import SocketIO
from sqlalchemy import select
from sqlalchemy.engine import URL, make_url
from sqlalchemy.exc import IntegrityError
from werkzeug.security import check_password_hash, generate_password_hash

from .campaign_http import install_company_socket, register_campaign
from .data import User, db, get_rating, initialize_database, leaderboard, profile
from .engine import RANKED
from .market_data import DatabaseMarketProvider, import_csv, seed_demo, seed_historical
from .multiplayer import MatchService, install_handlers, token_matches
from .prediction import PREDICTION
from .ranking import LEAGUES

socketio = SocketIO(async_mode="threading", max_http_buffer_size=16_384)
install_handlers(socketio)
install_company_socket(socketio)


def env_flag(name, default=False):
    return os.getenv(name, "1" if default else "0").lower() in {"1", "true", "yes", "on"}


def _database_url(value: str | URL) -> URL:
    url = make_url(value)
    if url.drivername in {"postgres", "postgresql"}:
        return url.set(drivername="postgresql+psycopg")
    return url


def create_app(config=None):
    load_dotenv(Path(__file__).resolve().parent.parent / ".env")
    direct_url = os.getenv("DATABASE_URL")
    pooled_url = os.getenv("DATABASE_URL_POOLED")
    app = Flask(__name__)
    app.config.from_mapping(
        SECRET_KEY=os.getenv("SECRET_KEY") or secrets.token_hex(32),
        SQLALCHEMY_DATABASE_URI=pooled_url or direct_url or "sqlite:///stockfight.sqlite3",
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
        SESSION_COOKIE_SECURE=env_flag("SESSION_COOKIE_SECURE"),
        MAX_CONTENT_LENGTH=16_384,
        INVITE_CODE=os.getenv("INVITE_CODE", ""),
        AUTO_SEED_DEMO=env_flag("AUTO_SEED_DEMO", True),
        ALLOW_SYNTHETIC=env_flag("ALLOW_SYNTHETIC", True),
        MARKET_TICK_SECONDS=float(os.getenv("MARKET_TICK_SECONDS", "3")),
        MATCH_PREVIEW_BARS=int(os.getenv("MATCH_PREVIEW_BARS", "12")),
        MATCH_COUNTDOWN=3,
        MATCH_BACKGROUND=True,
    )
    if config is not None:
        app.config.update(config)
    app.config.setdefault("AUTO_SEED_HISTORICAL", not app.testing and env_flag("AUTO_SEED_HISTORICAL", True))
    if not 0.25 <= app.config["MARKET_TICK_SECONDS"] <= 60:
        raise ValueError("MARKET_TICK_SECONDS måste vara mellan 0,25 och 60.")
    if not 2 <= app.config["MATCH_PREVIEW_BARS"] <= 100:
        raise ValueError("MATCH_PREVIEW_BARS måste vara mellan 2 och 100.")

    database_url = _database_url(app.config["SQLALCHEMY_DATABASE_URI"])
    app.config["SQLALCHEMY_DATABASE_URI"] = database_url
    if database_url.get_backend_name() == "postgresql":
        app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
            "pool_pre_ping": True,
            **app.config.get("SQLALCHEMY_ENGINE_OPTIONS", {}),
        }
    schema_url = None
    if direct_url and pooled_url and (config is None or "SQLALCHEMY_DATABASE_URI" not in config):
        schema_url = _database_url(direct_url)

    db.init_app(app)
    socketio.init_app(app)
    provider = app.config.get("MATCH_MARKET_PROVIDER")
    if provider is None:
        provider = DatabaseMarketProvider(allow_synthetic=app.config["ALLOW_SYNTHETIC"])
    service = MatchService(app, socketio, provider)
    app.extensions["match_service"] = service
    register_http(app, service)
    register_campaign(app, socketio)
    register_cli(app, schema_url)
    with app.app_context():
        initialize_database(schema_url)
        if app.config["AUTO_SEED_HISTORICAL"]:
            seed_historical()
        if app.config["AUTO_SEED_DEMO"] and app.config["ALLOW_SYNTHETIC"]:
            seed_demo()
    return app


def register_http(app, service):
    def account_state(user):
        if "csrf" not in session:
            session["csrf"] = secrets.token_urlsafe(32)
        return {
            "user": {"id": user.id, "username": user.username} if user else None,
            "duelTutorialPending": bool(user and user.duel_tutorial_pending),
            "inviteRequired": bool(app.config["INVITE_CODE"]),
            "csrfToken": session["csrf"],
        }

    def login_session(user):
        service.disconnect_session(session.get("csrf"))
        session.clear()
        session["user_id"] = user.id
        return account_state(user)

    def error(message, status):
        return jsonify(error=message), status

    def rating_mode():
        mode = request.args.get("mode", RANKED.key)
        return mode if mode in (RANKED.key, PREDICTION.key) else None

    def credentials():
        body = request.get_json(silent=True)
        if not isinstance(body, dict):
            return None, None, None
        username = body.get("username")
        password = body.get("password")
        invite = body.get("inviteCode")
        return username.strip() if isinstance(username, str) else None, password, invite

    @app.before_request
    def validate_csrf():
        if request.method == "POST" and request.path.startswith("/api/"):
            if not token_matches(session.get("csrf"), request.headers.get("X-CSRF-Token")):
                return error("Sessionen behöver uppdateras. Ladda om sidan.", 403)
        return None

    @app.after_request
    def response_headers(response):
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "same-origin"
        if request.path in {"/", "/campaign", "/campaign/portfolio"} or request.path.startswith("/api/"):
            response.headers["Cache-Control"] = "no-store"
        return response

    @app.get("/")
    def index():
        return render_template("index.html", leagues=LEAGUES, online_count=service.online_count())

    @app.get("/healthz")
    def health():
        return {"status": "ok"}

    @app.get("/api/online")
    def online():
        return {"count": service.online_count()}

    @app.get("/api/me")
    def me():
        user_id = session.get("user_id")
        user = db.session.get(User, user_id) if user_id is not None else None
        return account_state(user)

    @app.post("/api/register")
    def register():
        username, password, invite = credentials()
        if (
            not username
            or not 3 <= len(username) <= 24
            or not username[0].isalnum()
            or not all(char.isalnum() or char in "_-" for char in username)
        ):
            return error("Välj ett användarnamn på 3–24 tecken. Använd bokstäver, siffror, _ eller -.", 400)
        if not isinstance(password, str) or not 8 <= len(password) <= 128:
            return error("Lösenordet behöver vara 8–128 tecken.", 400)
        if app.config["INVITE_CODE"] and not token_matches(app.config["INVITE_CODE"], invite):
            return error("Inbjudningskoden är fel.", 403)
        user = User(
            username=username,
            username_key=username.casefold(),
            password_hash=generate_password_hash(password),
            duel_tutorial_pending=True,
        )
        db.session.add(user)
        try:
            db.session.flush()
            db.session.add(get_rating(user.id))
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            return error("Användarnamnet är redan taget.", 409)
        return login_session(user), 201

    @app.post("/api/login")
    def login():
        username, password, _ = credentials()
        if not username or len(username) > 24 or not isinstance(password, str) or len(password) > 128:
            return error("Fel användarnamn eller lösenord.", 401)
        user = db.session.scalar(select(User).where(User.username_key == username.casefold()))
        if not user or not check_password_hash(user.password_hash, password):
            return error("Fel användarnamn eller lösenord.", 401)
        return login_session(user)

    @app.post("/api/logout")
    def logout():
        service.disconnect_session(session.get("csrf"))
        session.clear()
        return account_state(None)

    @app.post("/api/duel-tutorial/complete")
    def complete_duel_tutorial():
        user_id = session.get("user_id")
        user = db.session.get(User, user_id) if user_id is not None else None
        if user is None:
            return error("Logga in för att slutföra duellguiden.", 401)
        if user.duel_tutorial_pending:
            user.duel_tutorial_pending = False
            db.session.commit()
        return account_state(user)

    @app.get("/api/profile")
    def player_profile():
        user_id = session.get("user_id")
        if user_id is None:
            return error("Logga in för att öppna profilen.", 401)
        mode = rating_mode()
        if mode is None:
            return error("Okänt spelläge.", 400)
        return profile(user_id, mode)

    @app.get("/api/leaderboard")
    def ranking():
        if "user_id" not in session:
            return error("Logga in för att öppna topplistan.", 401)
        mode = rating_mode()
        if mode is None:
            return error("Okänt spelläge.", 400)
        return {"players": leaderboard(mode)}


def register_cli(app, schema_url: URL | None = None):
    @app.cli.command("init-db")
    def init_db():
        initialize_database(schema_url)
        click.echo("Databasen är klar.")

    @app.cli.command("seed-demo")
    def seed():
        click.echo(f"Importerade {seed_demo()} syntetiska kursrader.")

    @app.cli.command("import-market")
    @click.argument("path", type=click.Path(exists=True, dir_okay=False, path_type=Path))
    @click.option("--source", required=True, help="Datakällans namn.")
    @click.option("--interval", default="1m", show_default=True)
    @click.option("--synthetic", is_flag=True, help="Märk påhittade kurser som syntetiska.")
    def import_market(path, source, interval, synthetic):
        try:
            added = import_csv(path, source=source, interval=interval, synthetic=synthetic)
        except (ValueError, OSError) as exc:
            raise click.ClickException(str(exc)) from exc
        click.echo(f"Importerade {added} kursrader.")
