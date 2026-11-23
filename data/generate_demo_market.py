"""Build the deterministic CSV of entirely fictional Stock Fight market bars."""

import csv
import random
from datetime import UTC, datetime, timedelta
from pathlib import Path

SYMBOLS = (
    ("DEMO-SKAR", "SE", "Syntetisk demo • Skärkrona Kraft", 8, 0, 12_400),
    ("DEMO-NORR", "SE", "Syntetisk demo • Norrsken Optik", 8, 0, 8_500),
    ("DEMO-RIVR", "US", "Syntetisk demo • Rivermist Systems", 13, 30, 6_800),
    ("DEMO-ORBT", "US", "Syntetisk demo • Orbit Canyon", 13, 30, 23_100),
)
FIELDS = ("symbol", "market", "timestamp", "open", "high", "low", "close", "volume", "name", "synthetic")
SESSION_LENGTH = 390


def decimal_price(cents: int) -> str:
    return f"{cents // 100}.{cents % 100:02d}"


def generate() -> None:
    rng = random.Random(36014)
    path = Path(__file__).with_name("demo_market.csv")
    with path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.writer(file, lineterminator="\n")
        writer.writerow(FIELDS)
        for symbol, market, name, hour, start_minute, price in SYMBOLS:
            for day in range(13, 17):
                session = datetime(2025, 10, day, hour, start_minute, tzinfo=UTC)
                price = round(price * (1 + rng.uniform(-0.035, 0.035)))
                for minute in range(SESSION_LENGTH):
                    if minute % 17 == 0:
                        trend = rng.choice((-52, -35, -18, -5, 5, 18, 35, 52))
                    move = trend + rng.gauss(0, 40)
                    close = max(250, round(price * (1 + move / 10_000)))
                    wick = max(1, round(price * rng.uniform(0.0003, 0.0030)))
                    low = max(1, min(close, price) - wick)
                    high = max(close, price) + wick
                    timestamp = session + timedelta(minutes=minute)
                    session_edge = min(minute, SESSION_LENGTH - minute - 1)
                    volume = round(rng.randint(100, 5_000) + abs(move) * 28 + 80_000 / (session_edge + 12))
                    writer.writerow(
                        (
                            symbol,
                            market,
                            timestamp.isoformat(timespec="seconds").replace("+00:00", "Z"),
                            decimal_price(price),
                            decimal_price(high),
                            decimal_price(low),
                            decimal_price(close),
                            volume,
                            name,
                            "true",
                        )
                    )
                    price = close


if __name__ == "__main__":
    generate()
