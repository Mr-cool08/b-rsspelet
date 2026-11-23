"""Fictional market quotes and unlocks for the trading firm."""

STARTING_CASH = 500

LIVE_ASSETS = {
    "F": {"name": {"sv": "Ford Motor", "en": "Ford Motor"}, "unlockLevel": 1},
    "SOSI": {"name": {"sv": "Sotkamo Silver", "en": "Sotkamo Silver"}, "unlockLevel": 1, "market": "SE", "currency": "SEK"},
    "PLTR": {"name": {"sv": "Palantir Technologies", "en": "Palantir Technologies"}, "unlockLevel": 1},
    "SOFI": {"name": {"sv": "SoFi Technologies", "en": "SoFi Technologies"}, "unlockLevel": 2},
    "BRIX": {"name": {"sv": "Briox", "en": "Briox"}, "unlockLevel": 2, "market": "SE", "currency": "SEK"},
    "INTC": {"name": {"sv": "Intel", "en": "Intel"}, "unlockLevel": 3},
    "SPLTN": {"name": {"sv": "Spiltan Invest", "en": "Spiltan Invest"}, "unlockLevel": 3, "market": "SE", "currency": "SEK"},
    "AMD": {"name": {"sv": "AMD", "en": "AMD"}, "unlockLevel": 4},
    "AAPL": {"name": {"sv": "Apple", "en": "Apple"}, "unlockLevel": 5},
}

ASSETS = {
    "AUR": {"name": {"sv": "Aurora Kraft", "en": "Aurora Power"}, "unlockLevel": 1},
    "DIM": {"name": {"sv": "Dimma Data", "en": "Dimma Data"}, "unlockLevel": 2},
    "LIN": {"name": {"sv": "Lindhälsa", "en": "Lind Health"}, "unlockLevel": 3},
    "NSK": {"name": {"sv": "Norrsken Infrastruktur", "en": "Northern Infrastructure"}, "unlockLevel": 4},
    "KOB": {"name": {"sv": "Kobolt Teknik", "en": "Cobalt Technology"}, "unlockLevel": 5},
}

LEVELS = (
    {"number": 1, "name": {"sv": "Nystartad", "en": "Starter"}, "target": 0, "capacity": 4, "unlock": "AUR"},
    {"number": 2, "name": {"sv": "Handlare", "en": "Trader"}, "target": 60, "capacity": 6, "unlock": "DIM"},
    {"number": 3, "name": {"sv": "Etablerad", "en": "Established"}, "target": 180, "capacity": 8, "unlock": "LIN"},
    {"number": 4, "name": {"sv": "Storhandlare", "en": "Market Maker"}, "target": 420, "capacity": 10, "unlock": "NSK"},
    {"number": 5, "name": {"sv": "Börsledare", "en": "Market Leader"}, "target": 800, "capacity": 12, "unlock": "KOB"},
)

UPGRADES = (
    {"price": 85, "bonus": 2},
    {"price": 170, "bonus": 3},
    {"price": 300, "bonus": 5},
)

# Buy quote, committed resale quote, and number of shares available. All firms
# see the same price cycle, with liquidity and margins shifting independently.
_QUOTES = {
    "AUR": (
        (36, 44, 8), (39, 46, 7), (34, 44, 9), (42, 49, 5),
        (38, 47, 11), (37, 44, 13), (41, 52, 7), (43, 52, 10),
        (40, 47, 15), (37, 48, 9), (44, 52, 14), (38, 46, 12),
    ),
    "DIM": (
        (58, 72, 6), (64, 75, 8), (53, 64, 5), (49, 65, 9),
        (55, 67, 10), (61, 69, 14), (65, 80, 6), (56, 69, 13),
        (62, 73, 14), (49, 66, 7), (68, 81, 9), (54, 63, 13),
    ),
    "LIN": (
        (31, 38, 18), (29, 37, 16), (35, 44, 13), (34, 43, 18),
        (30, 46, 9), (32, 45, 13), (37, 47, 14), (36, 44, 20),
        (33, 45, 18), (31, 41, 20), (39, 47, 15), (30, 44, 12),
    ),
    "NSK": (
        (48, 59, 17), (45, 60, 13), (52, 61, 22), (53, 65, 15),
        (56, 66, 20), (46, 59, 20), (51, 62, 18), (55, 68, 15),
        (43, 56, 24), (50, 59, 19), (47, 63, 16), (48, 60, 21),
    ),
    "KOB": (
        (90, 112, 10), (96, 113, 12), (84, 111, 9), (103, 125, 7),
        (87, 103, 17), (91, 108, 11), (106, 133, 8), (85, 102, 18),
        (90, 109, 14), (99, 126, 6), (86, 101, 19), (83, 108, 10),
    ),
}

TRADE_RESERVE = max(buy_price for buy_price, _, _ in _QUOTES["AUR"])


def market_on_day(day: int) -> dict[str, dict[str, int]]:
    """Give each stock's public offer for the current 1-based trading day."""
    market = {}
    for symbol, quotes in _QUOTES.items():
        buy_price, sell_price, supply = quotes[(day - 1) % len(quotes)]
        market[symbol] = {"buyPrice": buy_price, "sellPrice": sell_price, "supply": supply}
    return market
