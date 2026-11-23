from datetime import UTC, date, datetime, time
from decimal import Decimal
from urllib.parse import parse_qs, urlsplit

import pytest

from stockfight import create_app
from stockfight.company_live import run_live_tick
from stockfight.company_quotes import AlpacaHistory, configured_provider, market_tick
from stockfight.company_replay import ReplayQuotes, Session
from test_company import COMMANDS, MARKET, register
from test_multiplayer import Clock, post


def _timestamp(value):
    return datetime.fromisoformat(value.replace("Z", "+00:00")).timestamp()


def _calendar_day(date, close="16:00"):
    return {"date": date, "open": "09:30", "close": close}


def _quote_provider(monkeypatch, dates, bars):
    source = AlpacaHistory("free-test-key", "free-test-secret", "iex")
    calls = []

    def fetch(url):
        endpoint = urlsplit(url)
        parameters = parse_qs(endpoint.query)
        calls.append((endpoint.path, parameters))
        if endpoint.path == "/v2/calendar":
            start = parameters["start"][0]
            end = parameters["end"][0]
            assert end < dates[-1]["date"]
            return [day for day in dates if start <= day["date"] <= end]
        assert endpoint.path == "/v2/stocks/bars"
        assert parameters["feed"] == ["iex"]
        assert parameters["timeframe"] == ["1Min"]
        assert "F" in parameters["symbols"][0].split(",")
        return {"bars": {
            "F": [{"t": moment, "c": Decimal(price)} for moment, price in bars],
            "AAPL": [{"t": bars[0][0], "c": Decimal("0")}],
            "UNKNOWN": [{"t": bars[0][0], "c": Decimal("50")}],
        }, "next_page_token": None}

    monkeypatch.setattr(source, "_get", fetch)
    return ReplayQuotes({"US": source}), calls


def _app_for_replay(tmp_path, clock, provider):
    return create_app({
        "TESTING": True,
        "SQLALCHEMY_DATABASE_URI": f"sqlite:///{(tmp_path / 'replay.db').as_posix()}",
        "SECRET_KEY": "campaign-replay-test",
        "INVITE_CODE": "",
        "AUTO_SEED_DEMO": False,
        "MATCH_BACKGROUND": False,
        "COMPANY_MARKET_CLOCK": clock,
        "COMPANY_MARKET_PROVIDER": provider,
    })


@pytest.mark.parametrize("today,earlier,now,cursor", [
    ("2026-11-24", "2026-11-23", "2026-11-24T15:15:05Z", "2026-11-23T15:15:05Z"),
    # Clocks moved forward over this weekend, so the same New York hour maps to a different UTC hour.
    ("2026-03-09", "2026-03-06", "2026-03-09T14:15:05Z", "2026-03-06T15:15:05Z"),
    # Labor Day between the current session and the previous session has no calendar entry.
    ("2026-09-08", "2026-09-04", "2026-09-08T14:15:05Z", "2026-09-04T14:15:05Z"),
])
def test_replay_matches_previous_session_in_new_york_time(monkeypatch, today, earlier, now, cursor):
    replay_at = _timestamp(cursor)
    available_at = replay_at - 5
    bar_start = datetime.fromtimestamp(available_at - 60, UTC).isoformat()
    provider, _ = _quote_provider(monkeypatch, [_calendar_day(earlier), _calendar_day(today)], [
        (bar_start, "12.345"),
    ])
    quote = provider.snapshot(_timestamp(now))
    assert quote.market_open is True
    assert quote.markets["US"]["replayAt"] == replay_at
    assert quote.prices == {"F": (1235, available_at)}


def test_replay_keeps_the_final_quote_after_an_early_close(monkeypatch):
    provider, _ = _quote_provider(monkeypatch, [
        _calendar_day("2026-11-27", close="13:00"), _calendar_day("2026-11-30"),
    ], [("2026-11-27T17:59:00Z", "15.00")])

    quote = provider.snapshot(_timestamp("2026-11-30T18:00:05Z"))

    assert quote.market_open is False
    assert quote.markets["US"]["status"] == "closed"
    assert quote.markets["US"]["replayAt"] == _timestamp("2026-11-27T18:00:05Z")
    assert quote.prices["F"] == (1500, _timestamp("2026-11-27T18:00:00Z"))


def test_default_exchange_replays_public_ngm_history_before_a_holiday(monkeypatch, tmp_path):
    monkeypatch.delenv("COMPANY_ALPACA_KEY_ID", raising=False)
    monkeypatch.delenv("COMPANY_ALPACA_SECRET_KEY", raising=False)
    provider = configured_provider(tmp_path)
    assert set(provider.sources) == {"SE"}
    source = provider.sources["SE"]

    reports = "/delayed/post-trade"
    columns = ("Instrument identification code,Price currency,Venue of execution,Type,"
               "Trading date and Time,Publication date and time,Price")
    trade = "SE0001057910,SEK,XNGM,,2026-05-13T10:00:00Z,2026-05-13T10:00:04Z,99.995"
    responses = {
        reports: '["2026-05-15", "2026-05-14", "2026-05-13"]',
        f"{reports}/2026-05-14": columns,
        f"{reports}/2026-05-13": "\n".join((columns, trade)),
        "/borsen/oppettider": "<table><tr><td>2026-05-13</td><td>Kristi himmelsfärdsafton</td><td>Halvdag</td></tr></table>",
    }
    monkeypatch.setattr(source, "_get", lambda url: responses[urlsplit(url).path])

    before_publication = provider.snapshot(_timestamp("2026-05-15T10:00:02Z"))
    assert before_publication.markets["SE"]["replayAt"] == _timestamp("2026-05-13T10:00:02Z")
    assert before_publication.prices == {}
    after_publication = provider.snapshot(_timestamp("2026-05-15T10:00:05Z"))
    assert after_publication.prices == {"SOSI": (10_000, _timestamp("2026-05-13T10:00:04Z"))}


def test_historical_quote_becomes_tradeable_after_bar_closes(monkeypatch, tmp_path):
    provider, calls = _quote_provider(monkeypatch, [_calendar_day("2026-11-23"), _calendar_day("2026-11-24")], [
        ("2026-11-23T15:14:00Z", "12.34"),
        ("2026-11-23T15:15:00Z", "98.76"),
    ])
    clock = Clock(now=_timestamp("2026-11-24T15:15:55Z"))
    app = _app_for_replay(tmp_path, clock, provider)
    first = register(app, "ReplayTrader")
    second = register(app, "ReplayObserver")
    run_live_tick(app, market_tick(clock.now), clock.now)

    def ford(market):
        return next(asset for asset in market["assets"] if asset["symbol"] == "F")

    market = first.get(MARKET).json
    assert market["mode"] == "previous_session"
    assert market["replayAt"] == _timestamp("2026-11-23T15:15:55Z")
    assert ford(market)["price"] == ford(second.get(MARKET).json)["price"] == 12.34
    assert ford(market)["quotedAt"] == _timestamp("2026-11-23T15:15:00Z")
    assert ford(market)["replayAt"] == market["replayAt"]
    assert ford(market)["currency"] == "USD" and ford(market)["market"] == "US"
    assert ford(market)["tradable"]
    assert all(point["price"] != 98.76 for point in ford(market)["history"])

    order = post(first, COMMANDS, {
        "action": "market_trade", "side": "buy", "symbol": "F", "quantity": 1,
        "revision": market["revision"], "tick": market["tick"],
    })
    assert order.status_code == 200, order.json
    assert order.json["market"]["lastTrade"]["price"] == 12.34

    clock.now += 5
    run_live_tick(app, market_tick(clock.now), clock.now)
    next_market = first.get(MARKET).json
    assert next_market["replayAt"] == _timestamp("2026-11-23T15:16:00Z")
    assert ford(next_market)["price"] == 98.76
    assert ford(next_market)["quotedAt"] == next_market["replayAt"]
    assert [path for path, _ in calls].count("/v2/stocks/bars") == 1


def test_orders_follow_each_exchanges_replay_hours(tmp_path):
    class StaticHistory:
        def __init__(self, name, session):
            self.name = name
            self.session = session

        def session_before(self, day):
            assert day == date(2026, 11, 24)
            return self.session

    def quotes(symbol, moment, cents):
        return {symbol: [(_timestamp(moment), cents)]}

    monday = date(2026, 11, 23)
    us = Session(monday, time(9, 30), time(16), quotes("F", "2026-11-23T16:29:50Z", 1234))
    se = Session(monday, time(9), time(17, 30), quotes("SOSI", "2026-11-23T16:29:50Z", 10_000))
    provider = ReplayQuotes({
        "US": StaticHistory("US history", us),
        "SE": StaticHistory("SE history", se),
    })
    clock = Clock(now=_timestamp("2026-11-24T16:29:55Z"))
    app = _app_for_replay(tmp_path, clock, provider)
    player = register(app, "MixedExchangeTrader")
    run_live_tick(app, market_tick(clock.now), clock.now)

    def asset_for(market, symbol):
        return next(asset for asset in market["assets"] if asset["symbol"] == symbol)

    opened = player.get(MARKET).json
    sosi = asset_for(opened, "SOSI")
    assert sosi["currency"] == "SEK" and sosi["market"] == "SE"
    assert sosi["price"] == 100 and sosi["orderPrice"] == 10 and sosi["tradable"]
    bought = post(player, COMMANDS, {
        "action": "market_trade", "side": "buy", "symbol": "SOSI", "quantity": 1,
        "revision": opened["revision"], "tick": opened["tick"],
    })
    assert bought.status_code == 200, bought.json
    assert bought.json["market"]["cash"] == opened["cash"] - 10.01

    clock.now += 15
    run_live_tick(app, market_tick(clock.now), clock.now)
    market = player.get(MARKET).json
    assert market["status"] == "open"
    assert asset_for(market, "F")["tradable"]
    sosi = asset_for(market, "SOSI")
    assert sosi["price"] == 100 and not sosi["tradable"]
    rejected = post(player, COMMANDS, {
        "action": "market_trade", "side": "sell", "symbol": "SOSI", "quantity": 1,
        "revision": market["revision"], "tick": market["tick"],
    })
    assert rejected.status_code == 400, rejected.json
    assert rejected.json["error"] == "market_closed"
    assert player.get(MARKET).json["revision"] == market["revision"]
