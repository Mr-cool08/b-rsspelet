"""Five-second snapshots of a configured real equity market feed."""

import json
import os
from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP
from urllib.error import URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from flask import current_app, g
from sqlalchemy.exc import IntegrityError

from .company_catalog import LIVE_ASSETS
from .data import CompanyMarketTick, db


TICK_SECONDS = 5
_RECENT_FRAMES = 180
_MAX_QUOTE_AGE = 60


class AlpacaQuotes:
    def __init__(self, key, secret, feed):
        if feed not in ("iex", "sip"):
            raise ValueError("COMPANY_ALPACA_FEED must be iex or sip")
        self.name = f"Alpaca · {feed.upper()}"
        self._feed = feed
        self._headers = {"APCA-API-KEY-ID": key, "APCA-API-SECRET-KEY": secret, "Accept": "application/json"}

    def _get(self, url):
        request = Request(url)
        for name, value in self._headers.items():
            request.add_unredirected_header(name, value)
        with urlopen(request, timeout=2) as response:
            return json.load(response, parse_float=Decimal)

    def snapshot(self, now):
        clock = self._get("https://paper-api.alpaca.markets/v2/clock")
        params = urlencode({"symbols": ",".join(LIVE_ASSETS), "feed": self._feed})
        trades = self._get(f"https://data.alpaca.markets/v2/stocks/trades/latest?{params}")["trades"]
        prices = {}
        for symbol, trade in trades.items():
            price = int((Decimal(trade["p"]) * 100).to_integral_value(rounding=ROUND_HALF_UP))
            quoted_at = datetime.fromisoformat(trade["t"].replace("Z", "+00:00")).timestamp()
            if symbol in LIVE_ASSETS and price > 0:
                prices[symbol] = (price, quoted_at)
        return clock["is_open"], prices


def configured_provider():
    key = os.getenv("COMPANY_ALPACA_KEY_ID")
    secret = os.getenv("COMPANY_ALPACA_SECRET_KEY")
    if key and secret:
        return AlpacaQuotes(key, secret, os.getenv("COMPANY_ALPACA_FEED", "iex"))
    return None


def market_tick(now):
    return int(now // TICK_SECONDS)


def publish_tick(provider, tick, now=None):
    if provider is None or db.session.get(CompanyMarketTick, tick) is not None:
        return
    try:
        market_open, prices = provider.snapshot(tick * TICK_SECONDS if now is None else now)
    except (URLError, TimeoutError, OSError, KeyError, ValueError, ArithmeticError) as exc:
        current_app.logger.warning("Aktiekurserna kunde inte hämtas (%s).", type(exc).__name__)
        market_open, prices = None, {}

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
        g.company_quote_frames = {row.tick: row for row in frames}
        g.company_frames_through = tick
    return g.company_quote_frames


def frames_through(tick):
    first_loaded = g.get("company_frames_through")
    if first_loaded is None or tick > first_loaded:
        load_frames(tick)
    return g.company_quote_frames


def latest_frame(tick):
    return next((frame for step, frame in frames_through(tick).items() if step <= tick), None)


def price_on_tick(symbol, tick):
    frame = frames_through(tick).get(tick)
    quote = frame.prices.get(symbol) if frame and frame.market_open else None
    if quote:
        price, quoted_at = quote
        if -TICK_SECONDS <= tick * TICK_SECONDS - quoted_at <= _MAX_QUOTE_AGE:
            return price
    return None


def latest_quote(symbol, tick):
    for step, frame in frames_through(tick).items():
        if step <= tick and symbol in frame.prices:
            return frame.prices[symbol]
    return None


def latest_price(symbol, tick):
    quote = latest_quote(symbol, tick)
    return quote[0] if quote else None
