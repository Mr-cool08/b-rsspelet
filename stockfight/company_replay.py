"""Match the game clock to previous trading sessions in each exchange's time zone."""

from bisect import bisect_right
from dataclasses import dataclass
from datetime import date, datetime, time
from urllib.error import URLError
from zoneinfo import ZoneInfo

from flask import current_app, has_app_context


EXCHANGE_ZONES = {"US": ZoneInfo("America/New_York"), "SE": ZoneInfo("Europe/Stockholm")}


@dataclass(frozen=True)
class Session:
    day: date
    opens: time
    closes: time
    quotes: dict[str, list[tuple[float, int]]]


@dataclass(frozen=True)
class ReplaySnapshot:
    market_open: bool | None
    prices: dict[str, tuple[int, float]]
    markets: dict[str, dict]


class ReplayQuotes:
    name = "Historical market data"
    mode = "previous_session"

    def __init__(self, sources):
        self.sources = sources
        self._retry_after = {}

    def snapshot(self, now):
        prices = {}
        markets = {}
        for exchange, zone in EXCHANGE_ZONES.items():
            source = self.sources.get(exchange)
            metadata = {"status": "unavailable", "replayAt": None, "source": source.name if source else None}
            markets[exchange] = metadata
            if source is None or now < self._retry_after.get(exchange, 0):
                continue

            local = datetime.fromtimestamp(now, zone)
            try:
                session = source.session_before(local.date())
            except (URLError, OSError, KeyError, ValueError, ArithmeticError) as exc:
                self._retry_after[exchange] = now + 60
                if has_app_context():
                    current_app.logger.warning("Kunde inte hämta kurshistorik för %s (%s).", exchange, type(exc).__name__)
                continue
            if session is None or session.day >= local.date():
                continue

            replay_at = datetime.combine(session.day, local.time(), zone).timestamp()
            metadata["status"] = "open" if session.opens <= local.time() < session.closes else "closed"
            metadata["replayAt"] = replay_at
            for symbol, series in session.quotes.items():
                index = bisect_right(series, (replay_at, float("inf"))) - 1
                if index >= 0:
                    quoted_at, price = series[index]
                    prices[symbol] = price, quoted_at

        statuses = [market["status"] for market in markets.values()]
        market_open = None if all(status == "unavailable" for status in statuses) else "open" in statuses
        return ReplaySnapshot(market_open, prices, markets)
