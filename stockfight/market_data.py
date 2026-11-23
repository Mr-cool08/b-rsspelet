"""Import and select historical market data from the database."""

from __future__ import annotations

import csv
import re
from collections import deque
from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from itertools import groupby, islice
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


class DatabaseMarketProvider:
    _recent: WeakKeyDictionary[Engine, deque[int]] = WeakKeyDictionary()
    _lock = Lock()

    def __init__(self, allow_synthetic: bool = True) -> None:
        self.allow_synthetic = allow_synthetic

    def choose(self, *, required_bars: int, preview_count: int) -> Scenario:
        """Choose a window with the preview and no interruption beyond the interval policy."""
        from .data import db
        from .engine import Bar, Scenario

        if not 1 <= preview_count < required_bars:
            raise ValueError("Välj minst en kurspunkt för förhandsvisning och en för handel.")
        with self._lock:
            recent = self._recent.setdefault(db.engine, deque(maxlen=16))
            data_types = (False, True) if self.allow_synthetic else (False,)
            for synthetic in data_types:
                chosen = self._choose_window(required_bars, synthetic, set(recent))
                if chosen is not None:
                    first = chosen[0]
                    recent.append(first.id)
                    return Scenario(
                        symbol=first.symbol,
                        market=first.market,
                        interval=first.interval,
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

    @staticmethod
    def _choose_window(
        required_bars: int, synthetic: bool, recent: set[int]
    ) -> tuple[MarketData, ...] | None:
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
        eligible_count = 0
        has_fresh = False
        try:
            for (_, _, interval, _), series in groupby(rows, key=attrgetter(*_SERIES_COLUMNS)):
                step = _interval_delta(interval)
                calendar_interval = interval.endswith(("d", "w"))
                window: deque[MarketData] = deque(maxlen=required_bars)
                for row in series:
                    if window and not _consecutive(window[-1].timestamp, row.timestamp, step, calendar_interval):
                        window.clear()
                    window.append(row)
                    if len(window) != required_bars:
                        continue
                    fresh = window[0].id not in recent
                    if fresh and not has_fresh:
                        has_fresh = True
                        eligible_count = 0
                    if has_fresh and not fresh:
                        continue
                    # Reservoir sampling gives each eligible start the same chance.
                    eligible_count += 1
                    if randrange(eligible_count) == 0:
                        selected = tuple(window)
        finally:
            rows.close()
        return selected
