import csv
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta, timezone
from decimal import Decimal
from itertools import pairwise
from statistics import median
from threading import Barrier
from types import SimpleNamespace

import pytest
from flask import Flask
from sqlalchemy import func, select
from sqlalchemy.exc import StatementError
from sqlalchemy.orm import object_session

from stockfight.data import (
    DatabaseMarketProvider,
    MarketData,
    MarketDataUnavailable,
    Match,
    MatchResult,
    PlayerRating,
    TradeHistory,
    User,
    db,
    get_rating,
    import_csv,
    initialize_database,
    leaderboard,
    profile,
    save_match,
    seed_demo,
)
from stockfight.prediction import MAX_ROUNDS, price_move_bps


FIRST_BAR = datetime(2020, 6, 1, 13, 30, tzinfo=UTC)
STARTED = datetime(2026, 11, 23, 16, 17, 0, tzinfo=timezone(timedelta(hours=1)))
ENDED = STARTED + timedelta(seconds=0.75)
PRECISE_CAPITAL = Decimal("1010.1234567890123456789")
CSV_HEADERS = ("symbol", "market", "timestamp", "open", "high", "low", "close", "volume", "name", "synthetic")


@pytest.fixture
def database(tmp_path):
    app = Flask(__name__, instance_path=str(tmp_path))
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///test.db"
    db.init_app(app)
    with app.app_context():
        db.create_all()
        yield app


@pytest.fixture
def players(database):
    db.session.add_all([
        User(username="Agnes", username_key="agnes", password_hash="fixture"),
        User(username="Bob", username_key="bob", password_hash="fixture"),
    ])
    db.session.commit()
    return tuple(db.session.scalars(select(User.id).order_by(User.id)))


def _count(model):
    return db.session.scalar(select(func.count()).select_from(model))


def _completed_match(match_id, players, *, draw=False, mode="ranked"):
    scenario = SimpleNamespace(
        symbol="DEMO-FIXTURE",
        market="US",
        interval="1m",
        source="synthetic fixture",
        synthetic=True,
        bars=tuple(SimpleNamespace(timestamp=FIRST_BAR + timedelta(minutes=i)) for i in range(10)),
        preview_count=3,
    )
    winner = None if draw else players[0]
    trades = [] if draw else [
        {
            "user_id": players[0],
            "bought_at": 0.125,
            "sold_at": 0.75,
            "buy_price": Decimal("51.1234567890123456789"),
            "sell_price": Decimal("52.7654321987654321987"),
            "invested": Decimal("250.000000001"),
            "profit": Decimal("8.0303912345674912345"),
            "choice": "attack",
            "damage": 16,
        }
    ]

    def summary(user_id):
        won = winner == user_id
        return {
            "hp": 45 if won else 0,
            "capital": PRECISE_CAPITAL if won else Decimal("1000"),
            "attackDamage": 16 if won else 0,
            "growCount": 0,
            "trades": int(won),
            "winningTrades": int(won),
            "losingTrades": 0,
            "peakCapital": PRECISE_CAPITAL if won else Decimal("1000"),
        }

    return SimpleNamespace(
        id=match_id, mode=SimpleNamespace(key=mode, rating_k=32), scenario=scenario,
        players=dict.fromkeys(players), winner_id=winner, duration=0.75, summary=summary,
        trades=trades, revealed_count=scenario.preview_count + 1, status="finished",
    )


def test_empty_rankings_return_transient_defaults(players):
    rating = get_rating(players[0])
    assert rating.elo == 1000
    assert rating.matches == rating.wins == rating.losses == rating.draws == 0
    assert object_session(rating) is None
    assert _count(PlayerRating) == 0
    assert profile(players[0]) == {
        "elo": 1000, "league": "Silver", "nextLeague": "Gold", "nextElo": 1100, "progress": 50,
        "matches": 0, "wins": 0, "losses": 0, "draws": 0, "winRate": 0, "history": [],
    }
    assert leaderboard(limit=1) == [
        {"username": "Agnes", "elo": 1000, "league": "Silver", "wins": 0, "matches": 0},
    ]


def test_save_match_records_exact_period_stats_and_trade_once(players):
    # The queue can seat players in an order different from their account IDs.
    first, second = reversed(players)
    engine_match = _completed_match("knockout", (first, second))
    expected = {
        first: {"eloBefore": 1000, "eloAfter": 1016}, second: {"eloBefore": 1000, "eloAfter": 984},
    }
    assert save_match(engine_match, STARTED, ENDED) == expected
    match = db.session.get(Match, engine_match.id)
    assert (match.player1_id, match.player2_id, match.status) == (first, second, "finished")
    assert match.period_start == FIRST_BAR.replace(tzinfo=None)
    assert match.period_end == (FIRST_BAR + timedelta(minutes=3)).replace(tzinfo=None)
    assert match.started_at == STARTED.astimezone(UTC).replace(tzinfo=None)
    assert match.ended_at == ENDED.astimezone(UTC).replace(tzinfo=None)
    assert (match.winner_id, match.duration, match.synthetic) == (first, 0.75, True)

    winner = db.session.get(MatchResult, (engine_match.id, first))
    assert (winner.outcome, winner.hp, winner.attack_damage) == ("win", 45, 16)
    assert winner.capital == winner.peak_capital == PRECISE_CAPITAL
    trade = db.session.scalars(select(TradeHistory)).one()
    assert trade.match_id == match.id
    assert all(getattr(trade, key) == value for key, value in engine_match.trades[0].items())

    assert save_match(engine_match, STARTED, ENDED) == expected
    assert (_count(Match), _count(MatchResult), _count(TradeHistory)) == (1, 2, 1)
    assert profile(first)["history"] == [
        {
            "id": match.id, "opponent": "Agnes", "outcome": "win", "symbol": match.symbol,
            "eloBefore": 1000, "eloAfter": 1016, "endedAt": ENDED.astimezone(UTC).isoformat(),
        },
    ]
    assert profile(second)["history"][0]["outcome"] == "lose"
    assert (profile(first)["wins"], profile(second)["losses"]) == (1, 1)
    assert profile(first)["winRate"] == 100
    assert [entry["elo"] for entry in leaderboard()] == [1016, 984]


def test_database_upgrade_preserves_old_trades_and_stores_short_side(database, players):
    legacy_match = _completed_match("legacy", players)
    save_match(legacy_match, STARTED, ENDED)
    with db.engine.begin() as connection:
        connection.exec_driver_sql("ALTER TABLE trade_history DROP COLUMN side")

    ready = Barrier(2, timeout=5)

    def initialize():
        with database.app_context():
            ready.wait()
            initialize_database()

    with ThreadPoolExecutor(max_workers=2) as executor:
        initializers = [executor.submit(initialize) for _ in range(2)]
        for initializer in initializers:
            initializer.result()

    legacy_trade = db.session.scalars(select(TradeHistory)).one()
    assert legacy_trade.side == "long"
    assert all(getattr(legacy_trade, key) == value for key, value in legacy_match.trades[0].items())

    short_match = _completed_match("short", players)
    short_match.trades[0].update(side="short", buy_price=Decimal("52"), sell_price=Decimal("51"))
    save_match(short_match, STARTED, ENDED)
    short_trade = db.session.scalars(select(TradeHistory).filter_by(match_id="short")).one()
    assert short_trade.side == "short"


def test_active_match_cannot_create_saved_results(players):
    match = _completed_match("active", players)
    match.status = "active"
    with pytest.raises(ValueError, match="Only finished matches"):
        save_match(match, STARTED, ENDED)
    assert all(_count(model) == 0 for model in (Match, MatchResult, TradeHistory, PlayerRating))


def test_retry_returns_original_elo_and_profiles_are_mode_specific(players):
    first, second = players
    initial = _completed_match("initial", players)
    original = save_match(initial, STARTED, ENDED)
    draw = _completed_match("draw", players, draw=True)
    save_match(draw, ENDED, ENDED + timedelta(seconds=1))
    independent = _completed_match("separate", players, mode="future-mode")
    assert save_match(independent, STARTED, ENDED) == original
    assert save_match(initial, STARTED, ENDED) == original
    assert get_rating(first).elo == 1015
    assert get_rating(second).elo == 985
    assert get_rating(first, "future-mode").elo == 1016
    ranked = profile(first)
    assert [entry["id"] for entry in ranked["history"]] == ["draw", "initial"]
    assert (ranked["matches"], ranked["wins"], ranked["draws"], ranked["winRate"]) == (2, 1, 1, 50)
    assert [entry["id"] for entry in profile(first, "future-mode")["history"]] == ["separate"]


def test_failed_trade_rolls_back_match_results_and_elo(players):
    match = _completed_match("retryable", players)
    match.trades.append({**match.trades[0], "profit": Decimal("NaN")})
    with pytest.raises(StatementError, match="finite decimal"):
        save_match(match, STARTED, ENDED)
    assert all(_count(model) == 0 for model in (Match, MatchResult, TradeHistory, PlayerRating))
    match.trades.pop()
    assert save_match(match, STARTED, ENDED)[players[0]]["eloAfter"] == 1016


def test_concurrent_saves_are_idempotent_and_preserve_rating_updates(database, players):
    previous = _completed_match("shared", players)
    subsequent = _completed_match("distinct", players)
    ready = Barrier(3, timeout=5)

    def save_in_context(match):
        with database.app_context():
            ready.wait()
            return save_match(match, STARTED, ENDED)

    with ThreadPoolExecutor(max_workers=3) as executor:
        first, retry, other = executor.map(save_in_context, (previous, previous, subsequent))

    assert first == retry
    assert {first[players[0]]["eloBefore"], other[players[0]]["eloBefore"]} == {1000, 1016}
    assert get_rating(players[0]).elo == 1031
    assert get_rating(players[0]).wins == get_rating(players[1]).losses == 2
    assert (_count(Match), _count(MatchResult), _count(TradeHistory)) == (2, 4, 2)


def _csv_row(offset, *, symbol="FIXTURE", market="SE", synthetic=False):
    return (
        symbol, market, (FIRST_BAR + timedelta(minutes=offset)).isoformat(),
        "25.1234567890123456789", "26", "25", "25.5", "0", "Testinstrument", str(synthetic).lower(),
    )


def _write_csv(path, rows):
    with path.open("w", encoding="utf-8-sig", newline="") as file:
        writer = csv.writer(file)
        writer.writerow(CSV_HEADERS)
        writer.writerows(rows)
    return path


def test_csv_handles_timezone_and_deduplicates_bars(database, tmp_path):
    first = _csv_row(0)
    same_in_other_timezone = (" fixture ", " se ", "2020-06-01T15:30:00+02:00", *first[3:])
    path = _write_csv(tmp_path / "prices.csv", [first, same_in_other_timezone, _csv_row(5)])
    assert import_csv(path, interval="5M", source="authorised local fixture") == 2
    assert import_csv(path, interval="5m", source="authorised local fixture") == 0
    bars = db.session.scalars(select(MarketData).order_by(MarketData.timestamp)).all()
    assert [bar.timestamp for bar in bars] == [
        FIRST_BAR.replace(tzinfo=None), (FIRST_BAR + timedelta(minutes=5)).replace(tzinfo=None),
    ]
    assert bars[0].open == Decimal(first[3])
    assert bars[0].name == "Testinstrument"
    assert (bars[0].market, bars[0].interval, bars[0].symbol, bars[0].synthetic) == ("SE", "5m", "FIXTURE", False)


def test_csv_accepts_optional_columns_and_keeps_sources_distinct(database, tmp_path):
    path = tmp_path / "required-columns.csv"
    with path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.writer(file)
        writer.writerow(CSV_HEADERS[:8])
        writer.writerow(_csv_row(0)[:8])
    assert import_csv(path, source="local fixture A") == 1
    assert import_csv(path, source="local fixture B") == 1
    assert import_csv(path, source="local fixture A", synthetic=True) == 1
    bars = db.session.scalars(select(MarketData)).all()
    assert {(bar.source, bar.synthetic, bar.name, bar.interval) for bar in bars} == {
        ("local fixture A", False, "", "1m"),
        ("local fixture B", False, "", "1m"),
        ("local fixture A", True, "", "1m"),
    }


@pytest.mark.parametrize(("column", "value"), [(2, "not a date"), (3, "NaN"), (4, "24"), (7, "-1"), (9, "true")])
def test_invalid_csv_rolls_back_even_after_first_batch(database, tmp_path, column, value):
    invalid = list(_csv_row(500))
    invalid[column] = value
    path = _write_csv(tmp_path / "invalid.csv", [*(_csv_row(i) for i in range(500)), invalid])
    with pytest.raises(ValueError, match="CSV-rad 502"):
        import_csv(path, source="fixture")
    assert _count(MarketData) == 0


def test_provider_prefers_contiguous_real_bars_and_avoids_a_recent_window(database, tmp_path):
    real = _write_csv(tmp_path / "real.csv", [_csv_row(i) for i in (0, 1, 3, 4)])
    sample = _write_csv(
        tmp_path / "sample.csv", [_csv_row(i, symbol="DEMO-FIXTURE", market="US", synthetic=True) for i in range(4)],
    )
    assert import_csv(real, source="real-data fixture") == 4
    assert import_csv(sample, source="synthetic fixture", synthetic=True) == 4
    provider = DatabaseMarketProvider()
    fallback = provider.choose(required_bars=3, preview_count=1)
    assert fallback.synthetic is True
    assert fallback.name == "Testinstrument"
    with pytest.raises(MarketDataUnavailable):
        DatabaseMarketProvider(allow_synthetic=False).choose(required_bars=3, preview_count=1)

    _write_csv(real, [_csv_row(2)])
    assert import_csv(real, source="real-data fixture") == 1
    used = set()
    for _ in range(3):
        scenario = provider.choose(required_bars=3, preview_count=1)
        assert scenario.synthetic is False
        assert scenario.source == "real-data fixture"
        assert len(scenario.bars) == 3
        assert scenario.preview_count == 1
        first_bar = scenario.bars[0].timestamp
        assert [bar.timestamp for bar in scenario.bars] == [first_bar + timedelta(minutes=i) for i in range(3)]
        used.add(first_bar)
    assert used == {FIRST_BAR + timedelta(minutes=i) for i in range(3)}


@pytest.mark.parametrize("method", ["choose", "choose_prediction"])
def test_provider_varies_stocks_and_start_dates(database, tmp_path, method):
    preview = 12
    required = preview + MAX_ROUNDS
    histories = {
        "LONG": [(index, Decimal(1000 + 50 * (index % 2))) for index in range(140)],
        "SHORT": [(200 + index, Decimal(100) + Decimal(index) / 10) for index in range(62)],
    }
    rows = []
    for symbol, history in histories.items():
        for day, close in history:
            row = _csv_row(day * 1440, symbol=symbol)
            rows.append((*row[:3], close, close, close, close, *row[7:]))
    import_csv(_write_csv(tmp_path / "stocks.csv", rows), interval="1d", source="stock fixture")

    choose = getattr(DatabaseMarketProvider(allow_synthetic=False), method)
    scenarios = [choose(required_bars=required, preview_count=preview) for _ in range(6)]

    assert {scenario.symbol for scenario in scenarios} == set(histories)
    assert all(before.symbol != after.symbol for before, after in pairwise(scenarios))
    assert len({(scenario.symbol, scenario.bars[0].timestamp) for scenario in scenarios}) == len(scenarios)
    for scenario in scenarios:
        history = histories[scenario.symbol]
        bars = [(FIRST_BAR + timedelta(days=day), close) for day, close in history]
        start = next(index for index, (timestamp, _) in enumerate(bars) if timestamp == scenario.bars[0].timestamp)
        stride = int(scenario.interval.removesuffix("d"))
        assert [(bar.timestamp, bar.close) for bar in scenario.bars] == bars[start::stride][:required]


@pytest.mark.parametrize(("interval", "days"), [("1d", (3, 4, 8, 9, 17)), ("1w", (0, 7, 13, 20, 34))])
def test_provider_allows_calendar_closures_without_bridging_long_gaps(database, tmp_path, interval, days):
    path = _write_csv(tmp_path / "calendar.csv", [_csv_row(day * 1440) for day in days])
    assert import_csv(path, interval=interval, source="calendar fixture") == len(days)
    provider = DatabaseMarketProvider(allow_synthetic=False)

    scenario = provider.choose(required_bars=4, preview_count=1)
    assert scenario.interval == interval
    assert [bar.timestamp for bar in scenario.bars] == [FIRST_BAR + timedelta(days=day) for day in days[:4]]
    with pytest.raises(MarketDataUnavailable):
        provider.choose(required_bars=5, preview_count=1)


def test_prediction_provider_prefers_moving_short_window_to_flat_long_window(database, tmp_path):
    preview = 12
    required = preview + MAX_ROUNDS
    active_closes = ("92",) * 8 + ("94", "96", "98", "100", "102", "104", "106", "104", "102", "100", "98", "96")

    def rows(symbol, closes):
        for offset, close in enumerate(closes):
            row = _csv_row(offset, symbol=symbol)
            yield (*row[:3], close, close, close, close, *row[7:])

    path = _write_csv(tmp_path / "prediction.csv", (
        *rows("FLAT", ("100",) * (3 * (required - 1) + 1)), *rows("ACTIVE", active_closes),
    ))
    import_csv(path, source="prediction fixture")

    scenario = DatabaseMarketProvider().choose_prediction(required_bars=required, preview_count=preview)
    assert (scenario.symbol, scenario.interval, scenario.synthetic) == ("ACTIVE", "1m", False)
    assert tuple(bar.close for bar in scenario.bars) == tuple(map(Decimal, active_closes))


def test_demo_is_idempotent_and_all_bars_are_synthetic(database):
    seeded = seed_demo()
    assert seeded == _count(MarketData) > 0
    assert seed_demo() == 0
    assert set(db.session.scalars(select(MarketData.market).distinct())) == {"SE", "US"}
    assert set(db.session.scalars(select(MarketData.synthetic).distinct())) == {True}
    scenario = DatabaseMarketProvider().choose(required_bars=136, preview_count=20)
    assert scenario.synthetic
    assert scenario.symbol.startswith("DEMO-")
    assert len(scenario.bars) == 136
    assert scenario.bars[-1].timestamp - scenario.bars[0].timestamp == timedelta(minutes=135)


def test_demo_prediction_has_meaningful_changes_and_keeps_original_closes(database):
    seed_demo()
    preview = 12
    scenario = DatabaseMarketProvider().choose_prediction(required_bars=preview + MAX_ROUNDS, preview_count=preview)
    assert scenario.interval == "3m"
    assert all(after.timestamp - before.timestamp == timedelta(minutes=3) for before, after in pairwise(scenario.bars))

    original = dict(db.session.execute(select(MarketData.timestamp, MarketData.close).where(
        MarketData.symbol == scenario.symbol, MarketData.source == scenario.source,
        MarketData.timestamp.in_([bar.timestamp.replace(tzinfo=None) for bar in scenario.bars]),
    )).all())
    assert all(bar.close == original[bar.timestamp.replace(tzinfo=None)] for bar in scenario.bars)

    moves = [price_move_bps(before.close, after.close) for before, after in pairwise(scenario.bars)]
    actual_moves = moves[preview - 1:]
    assert min(actual_moves[:4]) <= -75 and max(actual_moves[:4]) >= 75
    assert sum(abs(move) >= 75 for move in actual_moves) >= 6
    assert sum(
        abs(median(moves[index - 3:index]) - moves[index]) < abs(moves[index])
        for index in range(preview - 1, len(moves))
    ) >= 5
