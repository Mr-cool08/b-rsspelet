"""Five-second snapshots of a configured real equity market feed."""

import json
import os
from datetime import UTC, date, datetime, time, timedelta
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path
from urllib.error import URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from flask import current_app, g
from sqlalchemy.exc import IntegrityError

from .company_catalog import LIVE_ASSETS
from .company_replay import EXCHANGE_ZONES, ReplayQuotes, ReplaySnapshot, Session
from .data import CompanyMarketTick, db
from .ngm_history import NgmHistory


TICK_SECONDS = 5
_RECENT_FRAMES = 180
_MAX_QUOTE_AGE = 60
REPLAY_METADATA = "_replay"


class AlpacaHistory:
    def __init__(self, key, secret, feed):
        if feed not in ("iex", "sip"):
            raise ValueError("COMPANY_ALPACA_FEED must be iex or sip")
        self.name = f"Alpaca · {feed.upper()}"
        self._feed = feed
        self._headers = {"APCA-API-KEY-ID": key, "APCA-API-SECRET-KEY": secret, "Accept": "application/json"}
        self._cached_day = None
        self._session = None

    def _get(self, url):
        request = Request(url)
        for name, value in self._headers.items():
            request.add_unredirected_header(name, value)
        with urlopen(request, timeout=4) as response:
            return json.load(response, parse_float=Decimal)

    def session_before(self, day):
        if day != self._cached_day:
            params = urlencode({"start": day - timedelta(days=14), "end": day - timedelta(days=1)})
            calendar = self._get(f"https://paper-api.alpaca.markets/v2/calendar?{params}")
            prior_days = [entry for entry in calendar if date.fromisoformat(entry["date"]) < day]
            self._session = self._read_session(max(prior_days, key=lambda entry: entry["date"])) if prior_days else None
            self._cached_day = day
        return self._session

    def _read_session(self, entry):
        day = date.fromisoformat(entry["date"])
        opens = time.fromisoformat(entry["open"])
        closes = time.fromisoformat(entry["close"])
        start = datetime.combine(day, opens, EXCHANGE_ZONES["US"]).astimezone(UTC)
        end = datetime.combine(day, closes, EXCHANGE_ZONES["US"]).astimezone(UTC)
        symbols = [symbol for symbol, asset in LIVE_ASSETS.items() if asset.get("market", "US") == "US"]
        params = {"symbols": ",".join(symbols), "feed": self._feed, "timeframe": "1Min", "limit": 10000,
                  "start": start.isoformat(), "end": end.isoformat()}
        quotes = {symbol: [] for symbol in symbols}
        while True:
            result = self._get(f"https://data.alpaca.markets/v2/stocks/bars?{urlencode(params)}")
            for symbol, bars in (result["bars"] or {}).items():
                if symbol not in quotes:
                    continue
                for bar in bars:
                    minute = datetime.fromisoformat(bar["t"].replace("Z", "+00:00"))
                    ready = minute + timedelta(minutes=1)
                    price = int((Decimal(bar["c"]) * 100).to_integral_value(rounding=ROUND_HALF_UP))
                    if start <= minute < ready <= end and price > 0:
                        quotes[symbol].append((ready.timestamp(), price))
            token = result.get("next_page_token")
            if not token or token == params.get("page_token"):
                break
            params["page_token"] = token
        return Session(day, opens, closes, {symbol: sorted(series) for symbol, series in quotes.items()})


def configured_provider(instance_path):
    sources = {"SE": NgmHistory(Path(instance_path) / "ngm-history")}
    key = os.getenv("COMPANY_ALPACA_KEY_ID")
    secret = os.getenv("COMPANY_ALPACA_SECRET_KEY")
    if key and secret:
        sources["US"] = AlpacaHistory(key, secret, os.getenv("COMPANY_ALPACA_FEED", "sip"))
    return ReplayQuotes(sources)


def market_tick(now):
    return int(now // TICK_SECONDS)


def publish_tick(provider, tick, now=None):
    if provider is None or db.session.get(CompanyMarketTick, tick) is not None:
        return
    try:
        sample = provider.snapshot(tick * TICK_SECONDS if now is None else now)
        if isinstance(sample, ReplaySnapshot):
            market_open, prices = sample.market_open, {**sample.prices, REPLAY_METADATA: sample.markets}
        else:
            market_open, prices = sample
    except (URLError, TimeoutError, OSError, KeyError, ValueError, ArithmeticError) as exc:
        current_app.logger.warning("Aktiekurserna kunde inte hämtas (%s).", type(exc).__name__)
        market_open, prices = None, {}
        if getattr(provider, "mode", None) == ReplayQuotes.mode:
            prices[REPLAY_METADATA] = {}

    try:
        db.session.add(CompanyMarketTick(tick=tick, market_open=market_open, prices=prices))
        if tick % 12 == 0:
            minimum = tick - 24 * 60 * 60 // TICK_SECONDS
            db.session.execute(db.delete(CompanyMarketTick).where(CompanyMarketTick.tick < minimum))
        db.session.commit()
    except IntegrityError:
        # Another process may have published the same shared tick.
        db.session.rollback()


def load_frames(tick):
    if g.get("company_frames_through") != tick:
        query = db.select(CompanyMarketTick.tick, CompanyMarketTick.market_open, CompanyMarketTick.prices)
        frames = db.session.execute(query.where(CompanyMarketTick.tick <= tick).order_by(
            CompanyMarketTick.tick.desc()).limit(_RECENT_FRAMES))
        provider = current_app.config.get("COMPANY_MARKET_PROVIDER")
        replay = getattr(provider, "mode", None) == ReplayQuotes.mode
        g.company_quote_frames = {row.tick: row for row in frames if (REPLAY_METADATA in row.prices) == replay}
        g.company_frames_through = tick
    return g.company_quote_frames


def frames_through(tick):
    first_loaded = g.get("company_frames_through")
    if first_loaded is None or tick > first_loaded:
        load_frames(tick)
    return g.company_quote_frames


def latest_frame(tick):
    return next((frame for step, frame in frames_through(tick).items() if step <= tick), None)


def quote_on_tick(symbol, tick):
    frame = frames_through(tick).get(tick)
    quote = frame.prices.get(symbol) if frame and frame.market_open else None
    if quote:
        _, quoted_at = quote
        replay = frame.prices.get(REPLAY_METADATA)
        if replay is None:
            if -TICK_SECONDS <= tick * TICK_SECONDS - quoted_at <= _MAX_QUOTE_AGE:
                return quote
        else:
            market = replay.get(LIVE_ASSETS[symbol].get("market", "US"), {})
            if market.get("status") == "open" and quoted_at <= market["replayAt"]:
                return quote
    return None


def settlement_cents(symbol, native_cents):
    if LIVE_ASSETS[symbol].get("currency") == "SEK":
        return max(1, (native_cents + 5) // 10)
    return native_cents


def price_on_tick(symbol, tick):
    quote = quote_on_tick(symbol, tick)
    return settlement_cents(symbol, quote[0]) if quote else None


def latest_quote(symbol, tick):
    frame = latest_frame(tick)
    exchange = LIVE_ASSETS[symbol].get("market", "US")
    market = frame.prices.get(REPLAY_METADATA, {}).get(exchange, {}) if frame else {}
    cursor = market.get("replayAt")
    for step, frame in frames_through(tick).items():
        quote = frame.prices.get(symbol)
        if step <= tick and quote and (cursor is None or quote[1] <= cursor):
            return quote
    return None


def latest_price(symbol, tick):
    quote = latest_quote(symbol, tick)
    return settlement_cents(symbol, quote[0]) if quote else None
