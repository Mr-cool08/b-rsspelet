"""Database models, rating reads, and completed-match persistence."""

from datetime import UTC, datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import and_, create_engine, false, func, inspect, literal, update
from sqlalchemy.dialects.postgresql import insert as postgresql_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.engine import URL
from sqlalchemy.orm import Session, aliased
from sqlalchemy.pool import NullPool
from sqlalchemy.types import Integer, Text, TypeDecorator

from .market_data import (
    DatabaseMarketProvider,
    MarketDataUnavailable,
    MarketProvider,
    import_csv,
    seed_demo,
)
from .prediction import PREDICTION
from .ranking import STARTING_ELO, league_progress, rating_changes

if TYPE_CHECKING:
    from .engine import Match as EngineMatch
    from .prediction import PredictionMatch


__all__ = [
    "db",
    "User",
    "CampaignSave",
    "CompanySave",
    "PlayerRating",
    "Match",
    "MatchResult",
    "TradeHistory",
    "MarketData",
    "initialize_database",
    "get_rating",
    "leaderboard",
    "profile",
    "save_match",
    "save_campaign",
    "import_csv",
    "seed_demo",
    "MarketProvider",
    "DatabaseMarketProvider",
    "MarketDataUnavailable",
]


db = SQLAlchemy()


def _insert_for_dialect(dialect_name: str):
    return {"postgresql": postgresql_insert, "sqlite": sqlite_insert}[dialect_name]


class ExactDecimal(TypeDecorator[Decimal]):
    """Store decimals as text to round-trip their values exactly."""

    impl = Text
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        decimal = Decimal(str(value))
        if not decimal.is_finite():
            raise ValueError("Expected a finite decimal")
        return str(decimal)

    def process_result_value(self, value, dialect):
        return Decimal(value) if value is not None else None


class EloRating(TypeDecorator[int]):
    """Translate Elo while retaining the original 1000-point start in storage."""

    impl = Integer
    cache_ok = True
    _offset = 1000 - STARTING_ELO

    def process_bind_param(self, value, dialect):
        return value + self._offset if value is not None else None

    def process_result_value(self, value, dialect):
        return value - self._offset if value is not None else None


def _utc_naive(timestamp: datetime) -> datetime:
    if timestamp.utcoffset() is not None:
        return timestamp.astimezone(UTC).replace(tzinfo=None)
    return timestamp


class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), nullable=False)
    username_key = db.Column(db.String(160), nullable=False, unique=True)
    password_hash = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=lambda: _utc_naive(datetime.now(UTC)))
    duel_tutorial_pending = db.Column(db.Boolean, nullable=False, server_default=false())


class CampaignSave(db.Model):
    __tablename__ = "campaign_saves"

    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), primary_key=True)
    revision = db.Column(db.Integer, nullable=False)
    state = db.Column(db.JSON, nullable=False)


class CompanySave(db.Model):
    __tablename__ = "company_saves"

    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), primary_key=True)
    revision = db.Column(db.Integer, nullable=False)
    state = db.Column(db.JSON, nullable=False)


class CompanyMarketTick(db.Model):
    __tablename__ = "company_market_ticks"

    tick = db.Column(db.BigInteger, primary_key=True, autoincrement=False)
    market_open = db.Column(db.Boolean, nullable=True)
    prices = db.Column(db.JSON, nullable=False)


class PlayerRating(db.Model):
    __tablename__ = "player_ratings"

    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), primary_key=True)
    mode = db.Column(db.String(32), primary_key=True)
    elo = db.Column(EloRating, nullable=False, default=STARTING_ELO)
    matches = db.Column(db.Integer, nullable=False, default=0)
    wins = db.Column(db.Integer, nullable=False, default=0)
    losses = db.Column(db.Integer, nullable=False, default=0)
    draws = db.Column(db.Integer, nullable=False, default=0)


class Match(db.Model):
    __tablename__ = "matches"

    id = db.Column(db.String(64), primary_key=True)
    mode = db.Column(db.String(32), nullable=False)
    player1_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    player2_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    status = db.Column(db.String(16), nullable=False)
    symbol = db.Column(db.String(32), nullable=False)
    market = db.Column(db.String(32), nullable=False)
    interval = db.Column(db.String(16), nullable=False)
    source = db.Column(db.String(255), nullable=False)
    synthetic = db.Column(db.Boolean, nullable=False)
    period_start = db.Column(db.DateTime, nullable=False)
    period_end = db.Column(db.DateTime, nullable=False)
    started_at = db.Column(db.DateTime, nullable=False)
    ended_at = db.Column(db.DateTime, nullable=False)
    duration = db.Column(db.Float, nullable=False)
    winner_id = db.Column(db.Integer, db.ForeignKey("users.id"))


class MatchResult(db.Model):
    __tablename__ = "match_results"

    match_id = db.Column(db.String(64), db.ForeignKey("matches.id"), primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), primary_key=True, index=True)
    outcome = db.Column(db.String(8), nullable=False)
    hp = db.Column(db.Integer, nullable=False)
    capital = db.Column(ExactDecimal, nullable=False)
    attack_damage = db.Column(db.Integer, nullable=False)
    grow_count = db.Column(db.Integer, nullable=False)
    trades = db.Column(db.Integer, nullable=False)
    winning_trades = db.Column(db.Integer, nullable=False)
    losing_trades = db.Column(db.Integer, nullable=False)
    peak_capital = db.Column(ExactDecimal, nullable=False)
    elo_before = db.Column(EloRating, nullable=False)
    elo_after = db.Column(EloRating, nullable=False)


class TradeHistory(db.Model):
    __tablename__ = "trade_history"

    id = db.Column(db.Integer, primary_key=True)
    match_id = db.Column(db.String(64), nullable=False)
    user_id = db.Column(db.Integer, nullable=False)
    side = db.Column(db.String(8), nullable=False, server_default="long")
    # These legacy field names record the opening and closing fills for either side.
    bought_at = db.Column(db.Float, nullable=False)
    sold_at = db.Column(db.Float, nullable=False)
    buy_price = db.Column(ExactDecimal, nullable=False)
    sell_price = db.Column(ExactDecimal, nullable=False)
    invested = db.Column(ExactDecimal, nullable=False)
    profit = db.Column(ExactDecimal, nullable=False)
    choice = db.Column(db.String(16), nullable=False)
    damage = db.Column(db.Integer, nullable=False)

    __table_args__ = (
        db.ForeignKeyConstraint(["match_id", "user_id"], ["match_results.match_id", "match_results.user_id"]),
        db.Index("ix_trade_history_match_user", "match_id", "user_id"),
    )


class MarketData(db.Model):
    __tablename__ = "market_data"

    id = db.Column(db.Integer, primary_key=True)
    symbol = db.Column(db.String(32), nullable=False)
    market = db.Column(db.String(32), nullable=False)
    timestamp = db.Column(db.DateTime, nullable=False)
    open = db.Column(ExactDecimal, nullable=False)
    high = db.Column(ExactDecimal, nullable=False)
    low = db.Column(ExactDecimal, nullable=False)
    close = db.Column(ExactDecimal, nullable=False)
    volume = db.Column(db.BigInteger, nullable=False)
    name = db.Column(db.String(160), nullable=False, default="")
    interval = db.Column(db.String(16), nullable=False)
    source = db.Column(db.String(255), nullable=False)
    synthetic = db.Column(db.Boolean, nullable=False, default=False)

    __table_args__ = (
        db.UniqueConstraint(
            "symbol", "market", "interval", "source", "synthetic", "timestamp",
            name="uq_market_data_series_timestamp",
        ),
    )


def initialize_database(schema_url: URL | None = None) -> None:
    engine = db.engine
    if schema_url is not None and schema_url != engine.url:
        engine = create_engine(schema_url, poolclass=NullPool)
    with engine.begin() as connection:
        # Serialize schema inspection and creation across overlapping starts.
        if connection.dialect.name == "postgresql":
            connection.exec_driver_sql("SELECT pg_advisory_xact_lock(hashtext('stockfight_schema'))")
        else:
            connection.exec_driver_sql("BEGIN IMMEDIATE")
        db.metadata.create_all(connection)
        inspector = inspect(connection)
        trade_columns = inspector.get_columns(TradeHistory.__tablename__)
        if not any(column["name"] == "side" for column in trade_columns):
            connection.exec_driver_sql(
                "ALTER TABLE trade_history ADD COLUMN side VARCHAR(8) NOT NULL DEFAULT 'long'"
            )
        user_columns = inspector.get_columns(User.__tablename__)
        if not any(column["name"] == "duel_tutorial_pending" for column in user_columns):
            connection.exec_driver_sql(
                "ALTER TABLE users ADD COLUMN duel_tutorial_pending BOOLEAN NOT NULL DEFAULT FALSE"
            )


def save_campaign(user_id: int, revision: int, state: dict, *, model=CampaignSave, condition=None) -> bool:
    dialect = db.session.get_bind().dialect.name
    if revision == 0:
        insert = _insert_for_dialect(dialect)
        command = insert(model)
        if condition is None:
            command = command.values(user_id=user_id, revision=1, state=state)
        else:
            values = db.select(literal(user_id), literal(1), literal(state, type_=model.state.type))
            command = command.from_select(["user_id", "revision", "state"], values.where(condition))
        command = command.on_conflict_do_nothing(index_elements=[model.user_id])
    else:
        command = (
            update(model)
            .where(model.user_id == user_id, model.revision == revision)
            .values(revision=revision + 1, state=state)
            .execution_options(synchronize_session=False)
        )
        if condition is not None:
            command = command.where(condition)
    if dialect == "postgresql":
        written = db.session.scalar(command.returning(model.revision)) is not None
    else:
        written = db.session.execute(command).rowcount == 1
    if not written:
        db.session.rollback()
        return False
    db.session.commit()
    return True


def _new_rating(user_id: int, mode: str) -> PlayerRating:
    return PlayerRating(
        user_id=user_id, mode=mode, elo=STARTING_ELO, matches=0, wins=0, losses=0, draws=0,
    )


def get_rating(user_id: int, mode: str = "ranked") -> PlayerRating:
    """A missing rating is returned as a transient starting rating."""
    rating = db.session.get(PlayerRating, (user_id, mode), populate_existing=True)
    return rating if rating is not None else _new_rating(user_id, mode)


def leaderboard(mode: str = "ranked", limit: int = 50) -> list[dict]:
    elo = func.coalesce(PlayerRating.elo, literal(STARTING_ELO, type_=PlayerRating.elo.type))
    wins = func.coalesce(PlayerRating.wins, 0)
    matches = func.coalesce(PlayerRating.matches, 0)
    rows = db.session.execute(
        db.select(User.username, elo, wins, matches)
        .outerjoin(PlayerRating, and_(PlayerRating.user_id == User.id, PlayerRating.mode == mode))
        .order_by(elo.desc(), wins.desc(), User.username_key, User.id)
        .limit(max(0, limit))
    )
    return [
        {"username": username, "elo": points, "league": league_progress(points)["league"],
         "wins": win_count, "matches": match_count}
        for username, points, win_count, match_count in rows
    ]


def profile(user_id: int, mode: str = "ranked") -> dict:
    opponent_result = aliased(MatchResult)
    opponent = aliased(User)
    history = (
        db.select(
            MatchResult.user_id, Match.id.label("match_id"), opponent.username.label("opponent"),
            MatchResult.outcome, Match.symbol,
            MatchResult.elo_before, MatchResult.elo_after, Match.ended_at,
        )
        .join_from(MatchResult, Match, MatchResult.match_id == Match.id)
        .join(opponent_result, and_(opponent_result.match_id == Match.id, opponent_result.user_id != user_id))
        .join(opponent, opponent.id == opponent_result.user_id)
        .where(MatchResult.user_id == user_id, Match.mode == mode)
        .subquery()
    )
    # Read Elo and history in one statement for a consistent snapshot.
    rows = db.session.execute(
        db.select(PlayerRating, history)
        .select_from(User)
        .outerjoin(PlayerRating, and_(PlayerRating.user_id == User.id, PlayerRating.mode == mode))
        .outerjoin(history, history.c.user_id == User.id)
        .where(User.id == user_id)
        .order_by(history.c.ended_at.desc(), history.c.match_id.desc())
        .execution_options(populate_existing=True)
    ).all()
    rating = rows[0][0] if rows else None
    if rating is None:
        rating = _new_rating(user_id, mode)
    return {
        "elo": rating.elo,
        **league_progress(rating.elo),
        "matches": rating.matches,
        "wins": rating.wins,
        "losses": rating.losses,
        "draws": rating.draws,
        "winRate": round(rating.wins * 100 / rating.matches, 1) if rating.matches else 0,
        "history": [
            {
                "id": row.match_id,
                "opponent": row.opponent,
                "outcome": row.outcome,
                "symbol": row.symbol,
                "eloBefore": row.elo_before,
                "eloAfter": row.elo_after,
                "endedAt": row.ended_at.replace(tzinfo=UTC).isoformat(),
            }
            for row in rows
            if row.match_id is not None
        ],
    }


def save_match(
    engine_match: "EngineMatch | PredictionMatch", started_at: datetime, ended_at: datetime,
) -> dict[int, dict[str, int]]:
    """Persist a completed match once, returning its original Elo on retries."""
    if engine_match.status != "finished":
        raise ValueError("Only finished matches can be saved")
    scenario = engine_match.scenario
    mode = engine_match.mode.key
    winner_id = engine_match.winner_id
    first_id, second_id = engine_match.players
    if winner_id is not None and winner_id not in (first_id, second_id):
        raise ValueError("Winner must be a match participant")
    if not 1 <= engine_match.revealed_count <= len(scenario.bars):
        raise ValueError("A completed match must have a valid revealed market period")

    engine = db.engine
    dialect_name = engine.dialect.name
    claim = _insert_for_dialect(dialect_name)(Match).values(
        id=engine_match.id,
        mode=mode,
        player1_id=first_id,
        player2_id=second_id,
        status=engine_match.status,
        symbol=scenario.symbol,
        market=scenario.market,
        interval=scenario.interval,
        source=scenario.source,
        synthetic=scenario.synthetic,
        period_start=_utc_naive(scenario.bars[0].timestamp),
        period_end=_utc_naive(scenario.bars[engine_match.revealed_count - 1].timestamp),
        started_at=_utc_naive(started_at),
        ended_at=_utc_naive(ended_at),
        duration=engine_match.duration,
        winner_id=winner_id,
    ).on_conflict_do_nothing(index_elements=[Match.id])

    with Session(engine) as session, session.begin():
        if dialect_name == "postgresql":
            # Lock users in ID order to serialize shared participants, including
            # when a player has no rating row yet. Allow foreign-key checks.
            participant_ids = {first_id, second_id}
            registered_ids = session.scalars(
                db.select(User.id)
                .where(User.id.in_(participant_ids))
                .order_by(User.id)
                .with_for_update(key_share=True)
            )
            if set(registered_ids) != participant_ids:
                raise ValueError("Match participants must be registered users")

            claimed = session.scalar(claim.returning(Match.id)) is not None
        else:
            # In SQLite the insert also locks other writers.
            claimed = session.execute(claim).rowcount != 0
        if not claimed:
            saved = session.scalars(db.select(MatchResult).where(MatchResult.match_id == engine_match.id))
            return {row.user_id: {"eloBefore": row.elo_before, "eloAfter": row.elo_after} for row in saved}

        ratings = []
        for user_id in (first_id, second_id):
            if dialect_name == "sqlite" and session.get(User, user_id) is None:
                raise ValueError("Match participants must be registered users")
            rating = session.get(PlayerRating, (user_id, mode))
            if rating is None:
                rating = _new_rating(user_id, mode)
                session.add(rating)
            ratings.append(rating)

        first, second = ratings
        first_score = 0.5 if winner_id is None else int(winner_id == first_id)
        new_ratings = rating_changes(first.elo, second.elo, first_score, k=engine_match.mode.rating_k)
        changes = {}
        for rating, new_elo in zip(ratings, new_ratings, strict=True):
            user_id = rating.user_id
            changes[user_id] = {"eloBefore": rating.elo, "eloAfter": new_elo}
            summary = engine_match.summary(user_id)
            if mode == PREDICTION.key:
                summary.update(capital=0, peakCapital=0, growCount=0, trades=0, winningTrades=0, losingTrades=0)
            outcome = "draw"
            if winner_id is not None:
                outcome = "win" if winner_id == user_id else "lose"
            session.add(MatchResult(
                match_id=engine_match.id,
                user_id=user_id,
                outcome=outcome,
                hp=summary["hp"],
                capital=summary["capital"],
                attack_damage=summary["attackDamage"],
                grow_count=summary["growCount"],
                trades=summary["trades"],
                winning_trades=summary["winningTrades"],
                losing_trades=summary["losingTrades"],
                peak_capital=summary["peakCapital"],
                elo_before=rating.elo,
                elo_after=new_elo,
            ))
            rating.elo = new_elo
            rating.matches += 1
            rating.wins += outcome == "win"
            rating.losses += outcome == "lose"
            rating.draws += outcome == "draw"

        # Flush the participant results before writing the referencing trades.
        session.flush()
        trades = () if mode == PREDICTION.key else engine_match.trades
        for trade in trades:
            if trade["user_id"] not in changes:
                raise ValueError("Trade must belong to a match participant")
            session.add(TradeHistory(match_id=engine_match.id, **trade))
        return changes
