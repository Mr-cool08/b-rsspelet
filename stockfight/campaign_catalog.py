"""Authored Börskarriär assignments and their simulated markets."""

from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal
from random import Random


RANKS = (
    "Lärling", "Analytiker", "Juniorförvaltare", "Portföljförvaltare", "Seniorförvaltare", "Fondchef",
)
TOOLS = {"analysis": "Samvariation", "stop": "Automatisk säljorder", "extra": "Extra ombalansering"}
ASSET_NAMES = {
    "AUR": "Aurora Kraft", "BRO": "Brohamn Logistik", "DIM": "Dimma Data",
    "EKO": "Ekomark", "FEN": "Fenvik Industri", "GLT": "Gläntan Telekom",
    "KOB": "Kobolt Teknik", "LIN": "Lindhälsa", "MSA": "Mosaik Handel",
    "NSK": "Norrsken Infrastruktur", "ORB": "Orbital Komponenter", "VIK": "Viklivs",
}
PREVIEW = 6
PHASE_STEPS = 12
PHASE_COUNT = 3

_EXAM_STEPS = PHASE_STEPS * PHASE_COUNT
_ASSETS = tuple(ASSET_NAMES)
_CAPITAL = (5_000, 12_500, 25_000, 50_000, 125_000)
_ASSET_COUNTS = (3, 3, 4, 4, 5)
_CENT = Decimal("0.01")

# Approximate percentage change per asset in each third of a scenario.
# Asset roles vary across scenarios. Temporary moves within a third can differ from its overall direction.
_MARKETS = {
    "climb": ((5, 2, -2, 2, 0), (4, 1, 1, 3, -2), (5, 2, 0, 2, 1)),
    "rotation": ((9, -3, 2, 1, 4), (-5, 9, 1, -2, 2), (-2, 7, 4, 2, 0)),
    "reversal": ((-6, 3, -1, -2, 2), (-2, 2, 1, 0, -4), (18, -3, 5, 4, 6)),
    "divergence": ((4, 8, 0, -3, 2), (7, -4, 1, -2, 1), (4, -4, 2, -3, 0)),
    "flat": ((1, 2, -3, 1, 0), (-1, 3, 3, 3, -2), (1, -1, 3, 1, 2)),
    "selloff": ((3, 3, 3, 1, 2), (-13, -8, -18, -4, -5), (1, 6, 9, 3, -1)),
    "defensive": ((-6, -3, 1, 2, -3), (-9, -1, 2, 3, -5), (6, -3, 3, 2, 0)),
    "whipsaw": ((9, 1, -6, 2, 1), (-13, 4, 5, 1, -3), (6, 1, -5, 5, 6)),
    "funding": ((5, 3, 2, 1, -3), (-8, -5, -2, 0, -8), (11, 2, 8, 6, 1)),
    "rally": ((7, -2, 3, 1, 3), (1, 10, 2, 2, 0), (3, 9, 4, 2, 2)),
    "exam-1": ((5, -2, 1, 0, 0), (-6, 6, 3, 0, 0), (1, 8, 4, 0, 0)),
    "exam-2": ((8, 3, -4, 0, 1), (-8, 5, 7, 1, 4), (2, 4, 8, 0, -2)),
    "exam-3": ((-9, -6, -12, -4, -2), (-8, -2, -4, 2, 5), (4, 7, 9, 6, 3)),
    "exam-4": ((8, -2, 5, 1, 4), (-10, -5, 3, 1, 1), (3, 11, 10, 3, 2)),
    "exam-5": ((-17, -10, -23, -6, -12), (5, -2, 10, 2, 2), (18, 9, 28, 6, 14)),
}


def _goal(kind: str, value: int | float, step: int | None = None) -> dict:
    goal = {"type": kind, "value": value}
    if step is not None:
        goal["step"] = step
    return goal


@dataclass(frozen=True)
class _Case:
    title: str
    title_en: str
    brief: str
    brief_en: str
    market: str
    steps: int
    goals: tuple[dict, ...]
    mastery: dict


_REGULAR_CASES = (
    (
        _Case("Första portföljen", "Your first portfolio",
              "Jämför hur aktierna rört sig i förhandsvisningen och fördela sedan kapitalet. Pengar du lämnar ofördelade ligger kvar i kassan.",
              "Compare the stocks in the preview before allocating your credits. Everything you leave unallocated stays in cash.",
              "climb", 18, (_goal("index", 0),), _goal("index", 2.5)),
        _Case("Låt kassan vänta", "Keep cash in reserve",
              "Kunden vill ha en del pengar på börsen hela perioden. Du väljer hur mycket du vill hålla i reserv när ledarskapet skiftar.",
              "The client wants to stay partly invested throughout the period. You choose how much to keep in reserve as market leadership changes.",
              "rotation", 19, (_goal("index", 0), _goal("exposure", 25)), _goal("index", 3)),
        _Case("Välj ditt ögonblick", "Pick your moment",
              "En stark öppning har lockat in köpare. Avgör vilka uppgångar som har stöd och när en ombalansering är värd avgiften.",
              "A strong opening has drawn in buyers. Decide which gains have support and when a rebalance is worth the fee.",
              "divergence", 20, (_goal("index", 0.5),), _goal("index", 3)),
        _Case("Medvind", "Tailwind", "Börsen är stark. Avgör om du vill följa uppgången brett eller koncentrera dig på ett ledande innehav.",
              "The market is strong. Decide whether to participate broadly or concentrate on a leading stock.",
              "rally", 20, (_goal("index", 0.5), _goal("exposure", 35)), _goal("index", 3)),
        _Case("När börsen står still", "When the market stands still", "Små kursrörelser sätter affärskostnaderna i centrum.",
              "Small price moves put trading costs in focus.", "flat", 22, (_goal("index", 0),), _goal("index", 1)),
        _Case("Utmanaren", "The challenger", "En eftersläntrare kan komma igen. Jämför hur mycket du tjänar på att byta med vad affären kostar.",
              "A laggard may come back. Compare what you stand to gain by switching with the cost of the trade.",
              "reversal", 21, (_goal("index", 0),), _goal("index", 3)),
        _Case("Behåll vinnaraktierna", "Hold the winners", "Kunden vill se tre procents avkastning. Följ vilka uppgångar som håller i sig.",
              "The client is looking for a three percent return. Track which gains hold up.",
              "climb", 21, (_goal("return", 3), _goal("exposure", 30)), _goal("return", 8)),
        _Case("Lugnt vatten", "Calm waters", "Kunderna följer slutresultatet. Du avgör om några av de små rörelserna är värda att handla på.",
              "The clients care about the end result. You decide whether any of the small moves are worth trading.",
              "flat", 18, (_goal("index", 0.2),), _goal("return", 4)),
        _Case("Skiftande vindar", "Changing winds", "Tidiga vinnare kan byta plats med förlorarna. Ta ställning när du ser hur rörelsen utvecklas.",
              "Early winners and losers can trade places. Decide what to do as the move develops.",
              "rotation", 23, (_goal("index", 0.5), _goal("exposure", 30)), _goal("index", 3)),
        _Case("Köpstyrka", "Buying strength", "Kunden jämför med hela aktiekorgen. Fundera på hur mycket kassa du har råd att behålla i en uppgång.",
              "The client compares against the whole basket. Consider how much cash you can afford to hold during a rally.",
              "rally", 24, (_goal("index", 0.3),), _goal("index", 2.5)),
    ),
    (
        _Case("Viktgränsen", "The weight limit", "En kund sätter ett tak per innehav. Hitta två aktier som kan bära avkastningen tillsammans.",
              "A client caps the weight of each holding. Find two stocks that can deliver returns together.",
              "climb", 19, (_goal("concentration", 60), _goal("index", 0)), _goal("index", 2.5)),
        _Case("Ledarskifte", "New leadership", "De starkaste aktierna byter plats. Använd analysvyn för att jämföra rörelserna du har sett.",
              "The strongest stocks change places. Use the analysis view to compare the moves you have seen.",
              "rotation", 21, (_goal("concentration", 60), _goal("index", 0.5), _goal("exposure", 30)), _goal("index", 3)),
        _Case("Gemensam rörelse", "Moving together", "Två innehav kan bete sig nästan likadant. Bestäm när du hellre vill sprida risken.",
              "Two holdings may behave almost alike. Decide when spreading the risk matters more to you.",
              "divergence", 22, (_goal("concentration", 50), _goal("index", 0)), _goal("index", 2.5)),
        _Case("En ny favorit", "A new favorite", "Kundens viktgräns håller tillbaka den första vinnaren. Se vilka alternativ som växer fram under perioden.",
              "The client’s weight limit holds back the early winner. Look for alternatives as the period progresses.",
              "reversal", 23, (_goal("concentration", 50), _goal("index", 0)), _goal("index", 2)),
        _Case("Kassan och indexet", "Cash and the index", "En uppgång kan göra reservkapital dyrt. Kunden har satt en lägsta aktieandel för hela perioden.",
              "A rally can make cash reserves costly. The client sets a minimum equity allocation for the whole period.",
              "rally", 24, (_goal("concentration", 60), _goal("index", 0), _goal("exposure", 40)), _goal("index", 2)),
        _Case("Grannaktien", "The stock next door", "Sprid portföljen inom ramarna när två till synes likartade aktier börjar gå åt olika håll.",
              "Diversify within the limits as two seemingly similar stocks begin to move in opposite directions.",
              "divergence", 18, (_goal("concentration", 40), _goal("index", 0)), _goal("index", 2)),
        _Case("Tålamodets pris", "The price of patience", "Två korta vändningar prövar värdet av att byta innehav i en marknad med små rörelser.",
              "Two short reversals test whether switching holdings pays off when price moves are small.",
              "flat", 20, (_goal("concentration", 50), _goal("index", 0), _goal("exposure", 40)), _goal("return", 3.5)),
        _Case("Andra försöket", "Second chance", "Marknaden ifrågasätter sin första bedömning. Kunden vill ha positiv avkastning med spridda innehav.",
              "The market reconsiders its first impression. The client wants a positive return with diversified holdings.",
              "reversal", 22, (_goal("concentration", 50), _goal("return", 2)), _goal("index", 2)),
        _Case("Tre vägar upp", "Three ways up", "Flera aktier kan bidra till avkastningen. Leta efter en mix som håller när tempot ändras.",
              "Several stocks can contribute to returns. Look for a mix that holds up when the pace changes.",
              "climb", 23, (_goal("concentration", 40), _goal("return", 4), _goal("exposure", 50)), _goal("index", 1.5)),
        _Case("Utan skygglappar", "A wider view", "Kundens låga viktgräns gör det svårt att leva på en enda träff. Följ hela aktiekorgen.",
              "The client’s low weight limit makes it hard to rely on one pick. Follow the whole basket.",
              "rotation", 24, (_goal("concentration", 40), _goal("index", 0.5)), _goal("index", 2)),
    ),
    (
        _Case("Från toppen", "From the peak", "Kunden mäter varje fall från portföljens högsta värde hittills. Använd kassa, spridning eller en stopporder för att hålla dig inom gränsen.",
              "The client measures every fall from the portfolio’s previous peak. Use cash, diversification or a stop order to stay within the limit.",
              "selloff", 20, (_goal("concentration", 60), _goal("drawdown", 6), _goal("exposure", 25), _goal("index", 0)), _goal("drawdown", 3)),
        _Case("Skydd i nedgång", "Downside protection", "Aktierna faller i olika takt. Du behöver behålla en del på börsen medan du skyddar kundens kapital.",
              "Stocks fall at different rates. Stay partly invested while protecting the client’s capital.",
              "defensive", 21, (_goal("concentration", 60), _goal("drawdown", 5), _goal("exposure", 30), _goal("index", 0)), _goal("return", 3)),
        _Case("Falsk trygghet", "False comfort", "En stark uppgång höjer också värdet som framtida nedgångar mäts från.",
              "A strong rally also raises the value against which later drawdowns are measured.",
              "whipsaw", 22, (_goal("concentration", 60), _goal("drawdown", 5), _goal("index", 0), _goal("exposure", 25)), _goal("index", 2)),
        _Case("Behåll lugnet", "Hold your nerve", "Skydda kapitalet i en nervös marknad där de tidigare ledarna faller först.",
              "Protect capital in a nervous market where the former leaders are first to fall.",
              "selloff", 18, (_goal("concentration", 60), _goal("drawdown", 5), _goal("exposure", 30)), _goal("index", 3)),
        _Case("Risk före fart", "Risk before speed", "Kunden vill delta i återhämtningen men sätter en stram gräns för nedgången på vägen dit.",
              "The client wants to participate in the recovery but sets a tight drawdown limit on the way there.",
              "reversal", 23, (_goal("concentration", 50), _goal("drawdown", 4), _goal("exposure", 30), _goal("index", 0)), _goal("index", 2)),
        _Case("Stabilitetsmandatet", "The stability mandate", "Så länge aktieandelen hålls uppe får du skydda portföljen med en kassa av valfri storlek.",
              "As long as the equity allocation holds up, you can protect the portfolio with a cash reserve of your choosing.",
              "defensive", 24, (_goal("concentration", 50), _goal("drawdown", 4), _goal("exposure", 40), _goal("return", 1)), _goal("drawdown", 2)),
        _Case("Kort stubin", "Short fuse", "Det skakar i flera aktier på samma gång. En stopporder kan begränsa ett fall men också sälja före en vändning.",
              "Several stocks are shaking at once. A stop order may limit a drop, or sell just before a rebound.",
              "whipsaw", 22, (_goal("concentration", 50), _goal("drawdown", 6), _goal("exposure", 35), _goal("index", 0)), _goal("drawdown", 3)),
        _Case("Över hela svängen", "Through the full cycle", "Fonden vill hålla igen när marknaden faller och ändå komma tillbaka i nästa uppgång.",
              "The fund wants to limit losses as the market falls and still take part in the next rally.",
              "funding", 23, (_goal("concentration", 60), _goal("drawdown", 5), _goal("exposure", 30), _goal("index", 0)), _goal("index", 2)),
        _Case("Uppgång med säkerhetsbälte", "A rally with a seat belt", "Håll nedgången liten även när det känns lockande att jaga den senaste vinnaraktien.",
              "Keep drawdown low even when it is tempting to chase the latest winner.",
              "divergence", 21, (_goal("concentration", 50), _goal("drawdown", 3), _goal("exposure", 35), _goal("index", 0.5)), _goal("index", 2)),
        _Case("Säker hamn", "Safe harbor", "Flera aktier är under press. Kunden behöver en portfölj som kan tåla fler bakslag.",
              "Several stocks are under pressure. The client needs a portfolio that can withstand further setbacks.",
              "defensive", 24, (_goal("concentration", 50), _goal("drawdown", 4), _goal("exposure", 35), _goal("index", 0.5)), _goal("return", 2.5)),
    ),
    (
        _Case("Reservera en utbetalning", "Reserve for a payout", "En utbetalning närmar sig. Håll den kassa kunden behöver på rätt dag och fortsätt förvalta resten.",
              "A payout is approaching. Hold the cash the client needs on the scheduled day and keep managing the rest.",
              "funding", 20, (_goal("concentration", 60), _goal("cash", 35, 10), _goal("drawdown", 6), _goal("index", 0)), _goal("index", 2)),
        _Case("Två datum", "Two dates", "Kundens kassakrav ändras två gånger. Planera hur många ombalanseringar du vill reservera.",
              "The client’s cash requirement changes twice. Plan how many rebalances you want to keep in reserve.",
              "rotation", 22, (_goal("concentration", 60), _goal("cash", 25, 7), _goal("cash", 40, 15), _goal("index", -0.5)), _goal("index", 2)),
        _Case("Kassabrist i uppgång", "Cash in a rally", "En kund som snart behöver pengar vill ändå delta i uppgången fram till utbetalningen.",
              "A client who needs cash soon still wants to participate in the rally until the payout.",
              "rally", 24, (_goal("concentration", 60), _goal("cash", 30, 8), _goal("index", 0)), _goal("index", 2)),
        _Case("Reserven", "The reserve", "Kunden kräver gott om kassa halvvägs. Hur mycket av den vill du använda efter kontrollen?",
              "The client requires plenty of cash halfway through. How much will you put to work after the checkpoint?",
              "reversal", 22, (_goal("concentration", 60), _goal("cash", 45, 11), _goal("drawdown", 7), _goal("index", 0)), _goal("index", 2)),
        _Case("En vecka till betalning", "One week to payment", "Likviditet måste finnas tidigt, medan börsen rör sig åt olika håll.",
              "Cash must be available early while stocks are moving in different directions.",
              "divergence", 21, (_goal("concentration", 50), _goal("cash", 35, 5), _goal("return", 2.5)), _goal("index", 1.5)),
        _Case("Likviditetsbron", "The liquidity bridge", "Utbetalningen ligger nära ett oroligt skede. Det finns utrymme att investera igen efter kontrollen.",
              "The payout falls close to a turbulent stretch. There is room to reinvest after the checkpoint.",
              "selloff", 23, (_goal("concentration", 60), _goal("cash", 45, 13), _goal("drawdown", 5), _goal("index", 0)), _goal("drawdown", 2.5)),
        _Case("Täck åtagandena", "Cover the commitments", "Kunden har två förfallodatum. Håll reda på hur aktiernas rörelser förändrar andelen kassa.",
              "The client has two due dates. Watch how price moves change cash as a share of the portfolio.",
              "flat", 19, (_goal("concentration", 50), _goal("cash", 25, 6), _goal("cash", 35, 16), _goal("return", 1)), _goal("return", 3)),
        _Case("Lånad tid", "Borrowed time", "Det är ett bra börsläge, men kunden behöver sin reserv innan den sista delen av perioden.",
              "The market is favorable, but the client needs a reserve before the final part of the period.",
              "climb", 24, (_goal("concentration", 50), _goal("cash", 35, 14), _goal("return", 3.5)), _goal("index", 2)),
        _Case("Utrymme för vändning", "Room for a reversal", "En kund håller fast vid sitt kassakrav trots att flera aktier kan studsa tillbaka.",
              "A client sticks to the cash requirement even though several stocks could rebound.",
              "whipsaw", 23, (_goal("concentration", 60), _goal("cash", 40, 16), _goal("drawdown", 6), _goal("index", 0)), _goal("index", 2)),
        _Case("Fasta förfallodagar", "Fixed due dates", "Två utbetalningsdatum konkurrerar om samma reserv. Fördela risk och kassa så att båda går att möta.",
              "Two payout dates compete for the same reserve. Allocate risk and cash to meet both.",
              "funding", 24, (_goal("concentration", 50), _goal("cash", 30, 8), _goal("cash", 40, 18), _goal("index", 0)), _goal("index", 1.5)),
    ),
    (
        _Case("Håll hela mandatet", "Meet the full mandate", "Förvalta en större fond med kassakrav, viktgräns och en gräns för nedgångar. Du har plats för två verktyg.",
              "Manage a larger fund with cash, weight and drawdown limits. You have room for two tools.",
              "funding", 22, (_goal("concentration", 50), _goal("cash", 35, 13), _goal("drawdown", 5), _goal("exposure", 30), _goal("index", 0)), _goal("index", 2)),
        _Case("Återhämtning med ansvar", "A measured recovery", "Du behöver både bromsa en djupare nedgång och vara investerad när marknaden vänder.",
              "Limit a deeper drawdown and stay invested for the turn.",
              "selloff", 24, (_goal("concentration", 50), _goal("cash", 30, 11), _goal("drawdown", 4.5), _goal("exposure", 30), _goal("index", 0)), _goal("drawdown", 3)),
        _Case("Många viljor", "Competing priorities", "Kunden kräver utdelningsberedskap vid två tillfällen och vill följa index över hela perioden.",
              "The client needs cash ready on two dates and wants to keep up with the index over the whole period.",
              "rotation", 24, (_goal("concentration", 50), _goal("cash", 30, 7), _goal("cash", 30, 16), _goal("drawdown", 6), _goal("exposure", 35), _goal("index", 0)), _goal("index", 2)),
        _Case("Skiftet efter rapporten", "The post-earnings shift", "Det kan löna sig att vänta in ett skifte, men portföljen måste kunna möta uttaget längs vägen.",
              "Waiting for a shift may pay off, but the portfolio must be ready for a withdrawal along the way.",
              "divergence", 20, (_goal("concentration", 50), _goal("cash", 30, 9), _goal("drawdown", 4), _goal("exposure", 35), _goal("index", 0)), _goal("index", 2)),
        _Case("Stram riskbudget", "A tight risk budget", "Kunden tål liten nedgång och kräver samtidigt att en betydande andel ligger investerad.",
              "The client tolerates little drawdown and also requires a substantial proportion to stay invested.",
              "defensive", 24, (_goal("concentration", 50), _goal("cash", 30, 11), _goal("drawdown", 4), _goal("exposure", 40), _goal("index", 0.6)), _goal("return", 2)),
        _Case("En andra chans i marknaden", "A second chance in the market", "Välj hur mycket kapital du skyddar när kurserna sjunker och hur mycket du investerar när de vänder.",
              "Decide how much capital to protect as prices fall and how much to invest when they turn.",
              "reversal", 23, (_goal("concentration", 50), _goal("cash", 30, 12), _goal("drawdown", 5), _goal("exposure", 30), _goal("index", 0)), _goal("index", 2)),
        _Case("Pensionsstiftelsen", "The pension foundation", "Stiftelsen vill kunna göra två utbetalningar och hålla sin riskgräns när marknaden kastar.",
              "The foundation needs to make two payouts and stay within its risk limit as the market swings.",
              "whipsaw", 24, (_goal("concentration", 50), _goal("cash", 30, 8), _goal("cash", 35, 17), _goal("drawdown", 6), _goal("exposure", 30), _goal("index", 0)), _goal("index", 2)),
        _Case("Fem aktier, en plan", "Five stocks, one plan", "Flera till synes trygga innehav kan sacka efter när köptrycket ökar. Få kassan att räcka utan att tappa index.",
              "Several seemingly safe holdings can lag when buying picks up. Keep enough cash without falling behind the index.",
              "rally", 22, (_goal("concentration", 50), _goal("cash", 25, 12), _goal("drawdown", 5), _goal("exposure", 40), _goal("index", 0)), _goal("index", 1.5)),
        _Case("Kapitalförsäkringen", "The capital reserve", "Ett trygghetsmandat i en liten marknadsrörelse där affärsavgifter kan avgöra marginalen.",
              "A preservation mandate in a quiet market where trading fees can decide the margin.",
              "flat", 19, (_goal("concentration", 50), _goal("cash", 30, 10), _goal("drawdown", 3.5), _goal("exposure", 40), _goal("index", 0)), _goal("index", 1.2)),
        _Case("Före kommittén", "Before the committee", "Förvalta portföljen till sista dagen med kapital redo för kommitténs planerade utbetalning.",
              "Manage the portfolio through the last day with cash ready for the committee’s planned payout.",
              "climb", 24, (_goal("concentration", 50), _goal("cash", 25, 24), _goal("drawdown", 4), _goal("exposure", 40), _goal("index", 0)), _goal("index", 1.5)),
    ),
)

_EXAMS = (
    _Case("Första börsoron", "First market jitters", "Börsen svänger snabbare än i de tidigare uppdragen. Välj när du ska ombalansera i varje fas.",
          "The market swings faster than in previous assignments. Decide when to use each phase’s rebalance.",
          "exam-1", _EXAM_STEPS, (_goal("index", 0), _goal("exposure", 25)), _goal("index", 2)),
    _Case("När ledarna faller", "When leaders fall", "Kunden prövar din förmåga att slå index när gårdagens vinnare vänder. Viktgränsen gäller varje gång du fördelar kapitalet.",
          "The client tests whether you can beat the index when yesterday’s winners turn. The weight limit applies every time you allocate capital.",
          "exam-2", _EXAM_STEPS, (_goal("concentration", 50), _goal("index", 0), _goal("exposure", 30)), _goal("index", 2.5)),
    _Case("En marknad utan stöd", "A market without support", "Försäljningarna tar fart och liknande aktier kan falla samtidigt. Håll koll på tappet från portföljens topp.",
          "Selling picks up and similar stocks can fall together. Watch the drop from the portfolio’s peak.",
          "exam-3", _EXAM_STEPS, (_goal("concentration", 60), _goal("drawdown", 6), _goal("exposure", 30), _goal("index", 0)), _goal("drawdown", 3.5)),
    _Case("Utbetalning under press", "A payout under pressure", "Kassan ska täcka utbetalningen när andra fasen stänger. Fonden ska också kunna ta del av en återhämtning.",
          "Cash must cover the payout when the second phase ends. The fund must also be positioned to join a recovery.",
          "exam-4", _EXAM_STEPS, (_goal("concentration", 50), _goal("cash", 35, 2 * PHASE_STEPS), _goal("drawdown", 6), _goal("exposure", 30), _goal("index", 0)), _goal("index", 2)),
    _Case("Pensionsfondens slutprov", "The pension fund final", "Pensionskunden kräver kassa vid slutet av andra fasen, en stram riskgräns och samma slutavkastning som index eller bättre.",
          "The pension client requires cash at the end of phase two, a tight risk limit and a final return at least as good as the index.",
          "exam-5", _EXAM_STEPS, (_goal("concentration", 60), _goal("cash", 25, 2 * PHASE_STEPS), _goal("drawdown", 6), _goal("exposure", 30), _goal("index", 0)), _goal("drawdown", 2.5)),
)

_COMEBACKS = (
    _Case("Tillbaka till portföljen", "Back to the portfolio", "Bygg en ny portfölj och försök matcha index i en kortare period.",
          "Build a fresh portfolio and try to match the index over a shorter period.", "climb", 6, (_goal("index", 0),), _goal("index", 2)),
    _Case("Fördela risken igen", "Spread the risk again", "Få två innehav att bidra utan att passera kundens viktgräns.",
          "Have two holdings contribute without exceeding the client’s weight limit.", "climb", 6, (_goal("concentration", 60), _goal("index", 0)), _goal("index", 2)),
    _Case("Bygg ett skydd", "Build a buffer", "Skydda kapitalet med kassa och tåligare innehav medan börsen faller.",
          "Protect capital with cash and sturdier holdings as the market falls.", "defensive", 6, (_goal("drawdown", 5), _goal("exposure", 25)), _goal("drawdown", 2.5)),
    _Case("Säkra kassan igen", "Secure the reserve again", "Lägg undan kundens kassareserv i tid och behåll en del investerad.",
          "Set the client’s cash reserve aside on time and stay partly invested.",
          "funding", 6, (_goal("cash", 35, 4), _goal("exposure", 25)), _goal("index", 1)),
    _Case("Ta tillbaka pensionsmandatet", "Win back the pension mandate", "Säkra kassan före kontrollen och håll kursfallet inom portföljens riskgräns.",
          "Build the cash reserve before the checkpoint and stay within the portfolio’s drawdown limit.",
          "selloff", 6, (_goal("cash", 25, 4), _goal("drawdown", 6), _goal("exposure", 25)), _goal("index", 2)),
)


MISSIONS: dict[str, dict] = {}
_MARKET_BY_MISSION: dict[str, tuple[str, int]] = {}


def _register(rank: int, kind: str, number: int, case: _Case) -> None:
    suffix = f"{kind}-{number}" if kind in {"fixed", "elective"} else kind
    mission_id = f"rank{rank + 1}-{suffix}"
    first_asset = (rank * 4 + number * 3 + (kind == "elective")) % len(_ASSETS)
    symbols = [_ASSETS[(first_asset + offset) % len(_ASSETS)] for offset in range(_ASSET_COUNTS[rank])]
    MISSIONS[mission_id] = {
        "id": mission_id, "rank": rank, "kind": kind, "title": case.title, "brief": case.brief,
        "titleEn": case.title_en, "briefEn": case.brief_en, "assets": symbols, "steps": case.steps,
        "capital": _CAPITAL[rank], "goals": list(case.goals), "mastery": case.mastery,
    }
    _MARKET_BY_MISSION[mission_id] = (case.market, first_asset)


for _rank, _cases in enumerate(_REGULAR_CASES):
    for _number, _case in enumerate(_cases, 1):
        if _number <= 3:
            _register(_rank, "fixed", _number, _case)
        else:
            _register(_rank, "elective", _number - 3, _case)
    _register(_rank, "exam", 1, _EXAMS[_rank])
    _register(_rank, "comeback", 2, _COMEBACKS[_rank])


def generate_prices(mission: dict, seed: str | int) -> list[list[str]]:
    """Six preview closes, the opening close, then one close per trading step."""
    pattern, location = _MARKET_BY_MISSION[mission["id"]]
    market = _MARKETS[pattern]
    rng = Random(str(seed) + ":" + mission["id"])
    steps = mission["steps"]
    assets = mission["assets"]
    opening = [35.0 + 5 * ((location + offset * 4) % 15) for offset in range(len(assets))]
    preview_prices = opening.copy()
    preview = []
    for _ in range(PREVIEW):
        for asset in range(len(assets)):
            anticipation = market[0][asset] * 0.0007
            preview_prices[asset] *= 1 - anticipation + rng.uniform(-0.005, 0.005)
        preview.append(preview_prices.copy())
    closes = [*reversed(preview), opening]
    current = opening.copy()
    for third, changes in enumerate(market):
        length = steps * (third + 1) // 3 - steps * third // 3
        initial = current.copy()
        variation = [rng.uniform(-0.012, 0.012) for _ in assets]
        turn = rng.uniform(0.35, 0.65)
        interim_moves = [rng.uniform(-0.016, 0.016) for _ in assets]
        for step in range(1, length + 1):
            fraction = step / length
            interim_weight = min(fraction / turn, (1 - fraction) / (1 - turn))
            common_move = rng.uniform(-0.005, 0.005)
            for asset in range(len(assets)):
                trend = changes[asset] / 100 + variation[asset]
                noise = common_move + rng.uniform(-0.006, 0.006)
                current[asset] = initial[asset] * (1 + fraction * trend + interim_weight * interim_moves[asset] + noise)
            closes.append(current.copy())
    # A replay keeps the market regime but can give its winning and losing roles to different stocks.
    asset_order = list(range(len(assets)))
    rng.shuffle(asset_order)
    return [
        [str(Decimal(str(row[asset])).quantize(_CENT, rounding=ROUND_HALF_UP)) for asset in asset_order]
        for row in closes
    ]
