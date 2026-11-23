"""Previous Swedish trading sessions from NGM's public post-trade files."""

import csv
import json
from datetime import date, datetime, time, timedelta
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from html.parser import HTMLParser
from io import StringIO
from pathlib import Path
from tempfile import NamedTemporaryFile
from time import monotonic
from urllib.error import HTTPError
from urllib.request import urlopen

from .company_replay import EXCHANGE_ZONES, Session


_REPORTS = "https://mdapi.ngm.se/delayed/post-trade"
_CALENDAR = "https://www.ngm.se/borsen/oppettider"
_STOCKHOLM = EXCHANGE_ZONES["SE"]
_OPEN = time(9)
_FULL_CLOSE = time(17, 30)
_HALF_CLOSE = time(13)
_REFRESH_AFTER = 15 * 60
_INSTRUMENTS = {
    "SE0001057910": ("SOSI", "XNGM"),
    "SE0008588131": ("BRIX", "NSME"),
    "SE0013382546": ("SPLTN", "XNGM"),
}


class _CalendarRows(HTMLParser):
    def __init__(self):
        super().__init__()
        self.half_days = set()
        self._row = None
        self._cell = None

    def handle_starttag(self, tag, attrs):
        if tag == "tr":
            self._row = []
        elif tag == "td" and self._row is not None:
            self._cell = []

    def handle_data(self, data):
        if self._cell is not None:
            self._cell.append(data)

    def handle_endtag(self, tag):
        if tag == "td" and self._cell is not None:
            self._row.append("".join(self._cell).strip())
            self._cell = None
        elif tag == "tr" and self._row is not None:
            if len(self._row) >= 3 and self._row[2] == "Halvdag":
                self.half_days.add(date.fromisoformat(self._row[0]))
            self._row = None
            self._cell = None


def _parse_reports(lines, day, closes):
    prices = {}
    for row in csv.DictReader(lines):
        instrument = _INSTRUMENTS.get(row.get("Instrument identification code"))
        if instrument is None or row.get("Price currency") != "SEK":
            continue
        symbol, venue = instrument
        if row.get("Venue of execution") != venue or row.get("Type") not in (None, ""):
            continue
        try:
            traded = datetime.fromisoformat(row["Trading date and Time"])
            published = datetime.fromisoformat(row["Publication date and time"])
            if traded.tzinfo is None or published.tzinfo is None:
                continue
            available = max(traded, published).astimezone(_STOCKHOLM)
            cents = int((Decimal(row["Price"]) * 100).to_integral_value(rounding=ROUND_HALF_UP))
        except (InvalidOperation, KeyError, TypeError, ValueError, OverflowError):
            continue
        if cents > 0 and available.date() == day and _OPEN <= available.time() <= closes:
            prices.setdefault(symbol, []).append((available.timestamp(), cents))
    for series in prices.values():
        series.sort(key=lambda quote: quote[0])
    return prices


class NgmHistory:
    name = "Nordic Growth Market (NGM)"

    def __init__(self, cache_dir: Path):
        self._cache_dir = cache_dir
        self._current_day = None
        self._session = None
        self._retry_at = 0
        self._half_days = None
        self._calendar_year = None

    @staticmethod
    def _get(url):
        with urlopen(url, timeout=4) as response:
            return response.read().decode("utf-8-sig")

    def _closing_time(self, day):
        if self._calendar_year != day.year:
            calendar = _CalendarRows()
            calendar.feed(self._get(_CALENDAR))
            self._half_days = calendar.half_days
            self._calendar_year = day.year
        return _HALF_CLOSE if day in self._half_days else _FULL_CLOSE

    def _store(self, session):
        self._cache_dir.mkdir(parents=True, exist_ok=True)
        with NamedTemporaryFile(mode="w", encoding="utf-8", dir=self._cache_dir, delete=False) as pending:
            path = Path(pending.name)
            try:
                json.dump({"closes": session.closes.isoformat(), "quotes": session.quotes}, pending, separators=(",", ":"))
                pending.close()
                path.replace(self._cache_dir / f"{session.day.isoformat()}.json")
            finally:
                pending.close()
                path.unlink(missing_ok=True)

    def _cached_session(self, day):
        for path in sorted(self._cache_dir.glob("????-??-??.json"), reverse=True):
            try:
                session_day = date.fromisoformat(path.stem)
                if session_day >= day:
                    continue
                data = json.loads(path.read_text(encoding="utf-8"))
                closes = time.fromisoformat(data["closes"])
                if not isinstance(data["quotes"], dict):
                    continue
                prices = {symbol: [(stamp, price) for stamp, price in quotes]
                          for symbol, quotes in data["quotes"].items()}
            except (OSError, KeyError, TypeError, ValueError):
                continue
            if prices:
                return Session(session_day, _OPEN, closes, prices)
        return None

    def _download_session(self, day, cached):
        dates = (date.fromisoformat(value) for value in json.loads(self._get(_REPORTS)))
        for previous in sorted((value for value in dates if value < day and value.weekday() < 5), reverse=True):
            if cached and previous <= cached.day:
                break
            try:
                data = self._get(f"{_REPORTS}/{previous.isoformat()}")
            except HTTPError as exc:
                if exc.code != 404:
                    raise
                continue
            closes = self._closing_time(previous)
            prices = _parse_reports(StringIO(data), previous, closes)
            if prices:
                session = Session(previous, _OPEN, closes, prices)
                self._store(session)
                return session
        return cached

    def session_before(self, day: date) -> Session | None:
        now = monotonic()
        if day != self._current_day:
            self._current_day = day
            self._session = self._cached_session(day)
            self._retry_at = 0
        if now < self._retry_at:
            return self._session
        latest_weekday = day - timedelta(days=1)
        while latest_weekday.weekday() >= 5:
            latest_weekday -= timedelta(days=1)
        self._retry_at = now + _REFRESH_AFTER
        if self._session is None or self._session.day < latest_weekday:
            try:
                self._session = self._download_session(day, self._session)
            except (OSError, ValueError):
                if self._session is None:
                    raise
        if self._session and self._session.day == latest_weekday:
            self._retry_at = float("inf")
        return self._session
