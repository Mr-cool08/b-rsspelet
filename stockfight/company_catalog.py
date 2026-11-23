"""Fictional quotes, market depth, and milestones for the trading firm campaign."""

STARTING_CASH = 1_800
CAPACITY = 46
OVERHEAD = 120

PRODUCTS = ("AUR", "DIM", "LIN")
TIER_IDS = ("low", "regular", "premium")
_NAMES = {
    "AUR": {"sv": "Aurora Kraft", "en": "Aurora Power"},
    "DIM": {"sv": "Dimma Data", "en": "Dimma Data"},
    "LIN": {"sv": "Lindhälsa", "en": "Lind Health"},
}
_SALE_PRICES = {
    "AUR": (53, 66, 84),
    "DIM": (40, 52, 69),
    "LIN": (46, 61, 79),
}


def _week(
    sv: str,
    en: str,
    offers: tuple[tuple[int, int, tuple[int, int, int]], ...],
    contract: tuple[str, int, int, str, str] | None = None,
    *,
    sale_offsets: tuple[int, int, int] = (0, 0, 0),
) -> dict:
    products = [
        {
            "id": product,
            "name": _NAMES[product],
            "buyPrice": cost,
            "supply": supply,
            "tiers": [
                {"id": tier, "price": price + offset, "demand": demand}
                for tier, price, demand in zip(TIER_IDS, _SALE_PRICES[product], demands, strict=True)
            ],
        }
        for product, (cost, supply, demands), offset in zip(PRODUCTS, offers, sale_offsets, strict=True)
    ]
    order = None
    if contract is not None:
        product, units, price, customer_sv, customer_en = contract
        order = {"productId": product, "units": units, "price": price,
                 "customer": {"sv": customer_sv, "en": customer_en}}
    return {"note": {"sv": sv, "en": en}, "products": products, "contract": order}


CHAPTERS = (
    {
        "name": {"sv": "Starta handelsfirman", "en": "Open the trading firm"},
        "description": {
            "sv": "Bygg upp firmans handel i tre aktier. Välj en säljkurs som ger marginal och lockar tillräckligt många köpare.",
            "en": "Build the firm's trading business across three stocks. Pick a sell price that earns a margin and attracts enough buyers.",
        },
        "goals": [{"type": "profit", "target": 3_400}, {"type": "units", "target": 145}],
        # Each offer gives the buy quote, available shares, and demand at three sell prices.
        "weeks": [
            _week("Aurora Kraft lockar många köpare inför sin rapport. En större säljorder ger en låg inköpskurs i Dimma Data.",
                  "Aurora Power is attracting buyers ahead of earnings. A large sell order makes Dimma Data cheap to buy.",
                  ((34, 27, (25, 18, 8)), (23, 27, (24, 12, 4)), (30, 23, (18, 12, 6)))),
            _week("En ägarförsäljning pressar inköpskursen i Lindhälsa. Flest köpare finns vid den lägsta säljkursen.",
                  "A major shareholder's sale pushes down the price of Lind Health. Most buyers are at the lowest sell price.",
                  ((31, 35, (26, 16, 7)), (25, 21, (21, 12, 5)), (22, 34, (34, 10, 4))),
                  sale_offsets=(0, 0, -1)),
            _week("Färre vill sälja Aurora Kraft efter rapporten och inköpskursen stiger. En ny stororder till Dimma Data lockar köpare.",
                  "Fewer holders are selling Aurora Power after earnings and the buy quote has risen. A new customer deal draws buyers to Dimma Data.",
                  ((55, 9, (28, 21, 12)), (24, 27, (29, 21, 12)), (34, 18, (16, 10, 4))),
                  sale_offsets=(2, 1, 0)),
            _week("Lovande studieresultat för Lindhälsa lockar köpare även vid den högsta säljkursen.",
                  "Promising trial results for Lind Health draw buyers even at the highest sell price.",
                  ((40, 23, (25, 15, 6)), (27, 24, (21, 14, 6)), (31, 28, (29, 23, 17))),
                  sale_offsets=(0, 0, 2)),
        ],
    },
    {
        "name": {"sv": "Gör blockaffärer", "en": "Trade in blocks"},
        "description": {
            "sv": "Fonder och förvaltare vill köpa större poster. Blockordern fylls före övriga köpares order. Välj vilka affärer som ger bäst utfall.",
            "en": "Funds and asset managers want to buy larger positions. A block order fills before other buyers' orders. Decide which trades are worth taking.",
        },
        "goals": [{"type": "profit", "target": 4_300}, {"type": "contracts", "target": 2}],
        "weeks": [
            _week("En indexfond vill köpa ett block i Aurora Kraft. Utbudet är stort och efterfrågan från övriga köpare är måttlig.",
                  "An index fund wants a block of Aurora Power. Supply is abundant and demand from other buyers is moderate.",
                  ((33, 35, (21, 14, 6)), (25, 24, (26, 15, 8)), (32, 23, (21, 15, 7))),
                  ("AUR", 20, 53, "Indexfonden", "Index fund")),
            _week("Efterfrågan på Dimma Data är hög. Pensionsfondens blockbud ligger under den mellersta säljkursen.",
                  "Demand for Dimma Data is high. The pension fund's block bid is below the middle sell price.",
                  ((39, 22, (24, 15, 7)), (30, 29, (36, 27, 16)), (33, 23, (19, 11, 6))),
                  ("DIM", 22, 41, "Pensionsfonden", "Pension fund"), sale_offsets=(0, 2, 0)),
            _week("En förvaltare vill köpa Lindhälsa. En stor säljpost räcker till både blockaffären och de övriga köparna.",
                  "An asset manager wants a block of Lind Health. A large sell order provides enough shares for both the block trade and other buyers.",
                  ((42, 23, (22, 16, 9)), (26, 25, (25, 18, 8)), (26, 36, (20, 14, 7))),
                  ("LIN", 18, 55, "Hälsovårdsfonden", "Healthcare fund"), sale_offsets=(0, 0, -1)),
            _week("Inköpskursen i Aurora Kraft stiger. En fond vill öka sitt innehav snabbt och lägger ett högre blockbud.",
                  "The buy quote for Aurora Power is rising. A fund wants to increase its position quickly and offers a higher block bid.",
                  ((49, 17, (21, 17, 10)), (25, 27, (28, 19, 9)), (34, 22, (21, 16, 6))),
                  ("AUR", 15, 67, "Infrastrukturfonden", "Infrastructure fund"), sale_offsets=(2, 0, 0)),
        ],
    },
    {
        "name": {"sv": "Bygg upp likviditeten", "en": "Build up liquidity"},
        "description": {
            "sv": "Handelsfirman behöver pengar redo för nästa satsning. Tjäna pengar när inköpskurserna svänger och frigör kassa före periodens slut.",
            "en": "The trading firm needs cash for its next investment. Stay profitable as buy quotes change and free up cash before the period ends.",
        },
        "goals": [{"type": "profit", "target": 5_000}, {"type": "cash", "target": 14_600}],
        "weeks": [
            _week("En fond minskar sitt innehav i Aurora Kraft och säljer en stor post till låg kurs. Lindhälsa har gott om köpare.",
                  "A fund is reducing its stake in Aurora Power and selling a large position at a low price. Lind Health has plenty of buyers.",
                  ((29, 38, (22, 16, 6)), (35, 20, (25, 14, 7)), (29, 28, (26, 21, 11))),
                  sale_offsets=(0, -1, 1)),
            _week("Aurora Kraft blir dyrare och färre aktier finns att köpa. Omställningsfondens blockorder är större än veckans utbud.",
                  "Aurora Power is more expensive and fewer shares are available. The transition fund's block order exceeds this week's supply.",
                  ((52, 10, (32, 25, 15)), (31, 24, (23, 18, 7)), (33, 22, (23, 17, 7))),
                  ("AUR", 17, 62, "Omställningsfonden", "Energy transition fund"), sale_offsets=(3, 0, 0)),
            _week("En större ägare säljer av Dimma Data till låg kurs. Både övriga marknaden och en teknikfond söker aktien.",
                  "A major holder is selling Dimma Data at a low price. Both the wider market and a technology fund want shares.",
                  ((46, 20, (26, 17, 8)), (21, 40, (32, 23, 12)), (37, 21, (25, 15, 7))),
                  ("DIM", 21, 43, "Teknikfonden", "Technology fund"), sale_offsets=(0, -1, 0)),
            _week("Efterfrågan på Lindhälsa stiger inför kvartalets sista handelsvecka. Kassamålet mäts efter veckans försäljning.",
                  "Demand for Lind Health is rising in the quarter's final trading week. The cash target is measured after this week's sales.",
                  ((37, 23, (29, 19, 8)), (26, 26, (27, 18, 7)), (32, 27, (30, 24, 17))),
                  ("LIN", 16, 58, "Småbolagsfonden", "Small-cap fund"), sale_offsets=(0, 0, 2)),
        ],
    },
)
