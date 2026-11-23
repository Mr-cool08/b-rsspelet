"""Import and select historical market data from the database."""

from __future__ import annotations

import csv
import re
from collections import deque
from collections.abc import Callable, Iterator
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from functools import lru_cache
from itertools import groupby, islice, pairwise
from operator import attrgetter
from pathlib import Path
from random import randrange
from threading import Lock
from typing import TYPE_CHECKING, Protocol
from weakref import WeakKeyDictionary

from sqlalchemy import select
from sqlalchemy.engine import Engine

if TYPE_CHECKING:
    from .data import MarketData
    from .engine import Scenario


_REQUIRED_COLUMNS = {"symbol", "market", "timestamp", "open", "high", "low", "close", "volume"}
_SERIES_COLUMNS = ("symbol", "market", "interval", "source")
_DEMO_PATH = Path(__file__).resolve().parent.parent / "data" / "demo_market.csv"
_DEMO_SOURCE = "stockfight-synthetic-demo"
_HISTORICAL_PATH = _DEMO_PATH.with_name("historical_market.csv")
_HISTORICAL_SOURCE = "Kaggle - S&P 500 stock data"
_TIMESTAMP_UNITS = {
    "s": "seconds",
    "m": "minutes",
    "h": "hours",
    "d": "days",
    "w": "weeks",
}
_CALENDAR_GAP_ALLOWANCE_DAYS = 6


class MarketDataUnavailable(ValueError):
    """No eligible series contains the requested number of consecutive bars."""


class MarketProvider(Protocol):
    def choose(self, *, required_bars: int, preview_count: int) -> Scenario: ...


def _interval_delta(interval: str) -> timedelta:
    match = re.fullmatch(r"([1-9][0-9]*)([smhdw])", interval)
    if match is None:
        raise ValueError("Intervall måste anges med ett positivt heltal och en enhet, exempelvis 1m.")
    count, unit = match.groups()
    try:
        return timedelta(**{_TIMESTAMP_UNITS[unit]: int(count)})
    except (ValueError, OverflowError) as exc:
        raise ValueError("Intervall är för långt.") from exc


def _consecutive(previous: datetime, current: datetime, step: timedelta, calendar_interval: bool) -> bool:
    if not calendar_interval:
        return current - previous == step
    # Daily and weekly feeds skip exchange closures and can shift by an hour at DST.
    # Use UTC dates and cut the series at gaps beyond the nominal step plus six days.
    days = (current.date() - previous.date()).days
    return 1 <= days <= step.days + _CALENDAR_GAP_ALLOWANCE_DAYS


def _parse_timestamp(value: str) -> datetime:
    try:
        timestamp = datetime.fromisoformat(value)
        if timestamp.tzinfo is not None:
            timestamp = timestamp.astimezone(UTC).replace(tzinfo=None)
        return timestamp
    except (ValueError, OverflowError) as exc:
        raise ValueError("Tidsstämpeln måste vara ett giltigt ISO 8601-värde.") from exc


def _parse_price(value: str, column: str) -> Decimal:
    try:
        price = Decimal(value)
    except ArithmeticError as exc:
        raise ValueError(f"{column} måste vara ett decimaltal.") from exc
    if not price.is_finite() or price <= 0:
        raise ValueError(f"{column} måste vara ett ändligt positivt pris.")
    return price


def _market_rows(
    rows: csv.DictReader, *, interval: str, source: str, synthetic: bool
) -> Iterator[dict[str, object]]:
    for raw_row in rows:
        try:
            if None in raw_row:
                raise ValueError("Raden har fler värden än rubriken.")
            row = {key: (value or "").strip() for key, value in raw_row.items()}
            missing = _REQUIRED_COLUMNS.difference(key for key, value in row.items() if value)
            if missing:
                raise ValueError(f"Värde saknas för {', '.join(sorted(missing))}.")
            if "synthetic" in row:
                marker = row["synthetic"].lower()
                if marker not in ("true", "false", "0", "1"):
                    raise ValueError("synthetic måste vara true, false, 1 eller 0.")
                if (marker in ("true", "1")) != synthetic:
                    raise ValueError("synthetic måste stämma med importens inställning.")

            open_price = _parse_price(row["open"], "open")
            high_price = _parse_price(row["high"], "high")
            low_price = _parse_price(row["low"], "low")
            close_price = _parse_price(row["close"], "close")
            if low_price > min(open_price, close_price) or high_price < max(open_price, close_price):
                raise ValueError("Öppnings- och stängningspriser måste ligga inom low och high.")
            if not row["volume"].isdecimal():
                raise ValueError("volume måste vara ett icke-negativt heltal.")
            volume = int(row["volume"])
            if volume > 2**63 - 1:
                raise ValueError("volume måste vara ett icke-negativt 64-bitars heltal.")

            yield {
                "symbol": row["symbol"].upper(),
                "market": row["market"].upper(),
                "timestamp": _parse_timestamp(row["timestamp"]),
                "open": open_price,
                "high": high_price,
                "low": low_price,
                "close": close_price,
                "volume": volume,
                "name": row.get("name") or "",
                "interval": interval,
                "source": source,
                "synthetic": synthetic,
            }
        except ValueError as exc:
            raise ValueError(f"CSV-rad {rows.line_num}: {exc}") from exc


def import_csv(path: str | Path, *, interval: str = "1m", source: str, synthetic: bool = False) -> int:
    """Import a UTF-8 CSV atomically and return the count of newly inserted bars.

    Timestamps use ISO 8601 and values without a timezone are interpreted as UTC.
    Reimporting a bar from the same series keeps the value already stored.
    Real CSV data must come from a source the operator is permitted to use.
    """
    from .data import MarketData, _insert_for_dialect, db

    interval = interval.strip().lower()
    _interval_delta(interval)
    source = source.strip()
    if not source:
        raise ValueError("Ange en källa för marknadsdatan.")
    if not isinstance(synthetic, bool):
        raise ValueError("synthetic måste anges som bool.")

    engine = db.engine
    dialect = engine.dialect.name
    insert = _insert_for_dialect(dialect)
    statement = insert(MarketData.__table__).on_conflict_do_nothing(
        index_elements=(*_SERIES_COLUMNS, "synthetic", "timestamp")
    )
    if dialect == "postgresql":
        # PostgreSQL bulk inserts need RETURNING to count the non-conflicting rows.
        statement = statement.returning(MarketData.id)
    inserted = 0
    with engine.begin() as connection, Path(path).open(encoding="utf-8-sig", newline="") as file:
        reader = csv.DictReader(file, strict=True)
        try:
            columns = [column.strip().lower() for column in reader.fieldnames or ()]
            if len(columns) != len(set(columns)):
                raise ValueError("CSV-rubriken innehåller upprepade kolumnnamn.")
            missing = _REQUIRED_COLUMNS.difference(columns)
            if missing:
                raise ValueError(f"Obligatoriska CSV-kolumner saknas: {', '.join(sorted(missing))}.")
            reader.fieldnames = columns
            rows = _market_rows(reader, interval=interval, source=source, synthetic=synthetic)
            while batch := list(islice(rows, 500)):
                result = connection.execute(statement, batch)
                inserted += len(result.fetchall()) if dialect == "postgresql" else result.rowcount
        except csv.Error as exc:
            raise ValueError(f"Ogiltig CSV vid rad {reader.line_num}.") from exc
    return inserted


def seed_demo() -> int:
    """Import the explicitly synthetic data shipped with Stock Fight."""
    return import_csv(_DEMO_PATH, source=_DEMO_SOURCE, synthetic=True)


def seed_historical() -> int:
    """Import the bundled daily stock prices without a network request."""
    return import_csv(_HISTORICAL_PATH, interval="1d", source=_HISTORICAL_SOURCE)


class DatabaseMarketProvider:
    _recent: WeakKeyDictionary[Engine, deque[tuple[tuple[str, str], datetime]]] = WeakKeyDictionary()
    _lock = Lock()

    def __init__(self, allow_synthetic: bool = True) -> None:
        self.allow_synthetic = allow_synthetic

    def choose(self, *, required_bars: int, preview_count: int) -> Scenario:
        """Draw a playable stock and a contiguous window from its history."""
        return self._choose(required_bars, preview_count, strides=(1,))

    def choose_prediction(self, *, required_bars: int, preview_count: int) -> Scenario:
        """Prefer active prediction windows with more time between each close."""
        from .prediction import PREDICTION_STEP, prediction_window_quality, price_move_bps

        preview_moves = min(3, preview_count - 1)
        start = preview_count - 1 - preview_moves

        # Adjacent candidate windows reuse most of the same price changes.
        @lru_cache(maxsize=128)
        def move(before: MarketData, after: MarketData) -> int:
            return price_move_bps(before.close, after.close)

        def score_window(rows: tuple[MarketData, ...]) -> int:
            moves = tuple(move(before, after) for before, after in pairwise(rows[start:]))
            return prediction_window_quality(moves, preview_moves)

        return self._choose(required_bars, preview_count, strides=(PREDICTION_STEP, 1), score_window=score_window)

    def _choose(
        self, required_bars: int, preview_count: int, *, strides: tuple[int, ...],
        score_window: Callable[[tuple[MarketData, ...]], int] | None = None,
    ) -> Scenario:
        from .data import db
        from .engine import Bar, Scenario

        if not 1 <= preview_count < required_bars:
            raise ValueError("Välj minst en kurspunkt för förhandsvisning och en för handel.")
        with self._lock:
            recent = self._recent.setdefault(db.engine, deque(maxlen=16))
            previous_stock = recent[-1][0] if recent else None
            recent_starts = set(recent)
            data_types = (False, True) if self.allow_synthetic else (False,)
            for synthetic in data_types:
                selection = self._choose_window(
                    required_bars, synthetic, recent_starts, previous_stock, strides, score_window,
                )
                if selection is None:
                    continue
                chosen, stride = selection
                first = chosen[0]
                interval = first.interval
                if stride > 1:
                    interval = f"{int(interval[:-1]) * stride}{interval[-1]}"
                recent.append(((first.symbol, first.market), first.timestamp))
                return Scenario(
                    symbol=first.symbol,
                    market=first.market,
                    interval=interval,
                    source=first.source,
                    synthetic=first.synthetic,
                    bars=tuple(
                        Bar(
                            timestamp=row.timestamp.replace(tzinfo=UTC),
                            open=row.open,
                            high=row.high,
                            low=row.low,
                            close=row.close,
                            volume=row.volume,
                        )
                        for row in chosen
                    ),
                    preview_count=preview_count,
                    name=first.name or "",
                )
        raise MarketDataUnavailable(
            f"Marknadsdatan saknar en sammanhängande serie med {required_bars} kurspunkter."
        )

    @classmethod
    def _choose_window(
        cls, required_bars: int, synthetic: bool, recent: set[tuple[tuple[str, str], datetime]],
        previous_stock: tuple[str, str] | None, strides: tuple[int, ...],
        score_window: Callable[[tuple[MarketData, ...]], int] | None,
    ) -> tuple[tuple[MarketData, ...], int] | None:
        from .data import MarketData, db

        order = [getattr(MarketData, column) for column in _SERIES_COLUMNS]
        query = (
            select(MarketData)
            .where(MarketData.synthetic == synthetic)
            .order_by(*order, MarketData.timestamp)
            .execution_options(yield_per=500)
        )
        rows = db.session.scalars(query)
        selected = None
        eligible_stocks = 0
        best_stock_priority = (-1,)
        window_sizes = tuple((stride, (required_bars - 1) * stride + 1) for stride in strides)
        try:
            for stock, stock_rows in groupby(rows, key=attrgetter("symbol", "market")):
                recent_dates = {timestamp for recent_stock, timestamp in recent if recent_stock == stock}
                candidate = cls._choose_stock_window(stock_rows, window_sizes, recent_dates, synthetic, score_window)
                if candidate is None:
                    continue
                stock_window, window_priority = candidate
                stock_priority = (window_priority if synthetic else window_priority[:1]) + (stock != previous_stock,)
                if stock_priority > best_stock_priority:
                    best_stock_priority = stock_priority
                    eligible_stocks = 0
                elif stock_priority < best_stock_priority:
                    continue
                # Draw among eligible stocks independently of how many windows each offers.
                eligible_stocks += 1
                if randrange(eligible_stocks) == 0:
                    selected = stock_window
        finally:
            rows.close()
        return selected

    @staticmethod
    def _choose_stock_window(
        rows: Iterator[MarketData], window_sizes: tuple[tuple[int, int], ...], recent: set[datetime],
        synthetic: bool, score_window: Callable[[tuple[MarketData, ...]], int] | None,
    ) -> tuple[tuple[tuple[MarketData, ...], int], tuple[int, int, int]] | None:
        selected = None
        eligible_windows = 0
        best_priority = (-1, 0, 0)
        max_size = max(size for _, size in window_sizes)
        for (interval, _), series in groupby(rows, key=attrgetter("interval", "source")):
            step = _interval_delta(interval)
            calendar_interval = interval.endswith(("d", "w"))
            window: deque[MarketData] = deque(maxlen=max_size)
            for row in series:
                if window and not _consecutive(window[-1].timestamp, row.timestamp, step, calendar_interval):
                    window.clear()
                window.append(row)
                for stride, size in window_sizes:
                    start = len(window) - size
                    if start < 0:
                        continue
                    sampled = None
                    quality = 0
                    if score_window is not None:
                        sampled = tuple(islice(window, start, None, stride))
                        quality = score_window(sampled)
                    fresh = window[start].timestamp not in recent
                    # Active real windows remain eligible even when another date scores higher.
                    priority = (quality, stride, fresh) if synthetic else (min(1, quality), fresh, stride)
                    if priority > best_priority:
                        best_priority = priority
                        eligible_windows = 0
                    elif priority < best_priority:
                        continue
                    # Sample starts without keeping the whole history in memory.
                    eligible_windows += 1
                    if randrange(eligible_windows) == 0:
                        selected = (sampled if sampled is not None else tuple(window), stride)
        return (selected, best_priority) if selected is not None else None
