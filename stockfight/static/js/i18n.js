(() => {
    "use strict";

    const preferenceKey = "stockfight-language";
    const locales = { sv: "sv-SE", en: "en-GB" };
    const english = {
        "Språk": "Language",
        "Historik": "History",
        "Rita prognos": "Draw forecast",
        "Nästa punkt": "Next point",

        "Exempelgraf": "Example chart",
        "Senaste": "Latest",
        "Logga ut": "Log out",
        "Börsduell": "Stock duels",
        "i realtid": "in real time",
        "Handla med virtuella krediter på historiska börskurser. Tävla mot andra spelare eller öva mot en bot.": "Trade historical stock prices with virtual credits. Compete against other players or practise against a bot.",
        "Logga in eller skapa ett konto för att öppna din vänduell.": "Log in or create an account to open your friend duel.",
        "Spelarkonto": "Player account",
        "Välj kontoåtgärd": "Choose an account action",
        "Logga in": "Log in",
        "Registrera": "Register",
        "Spelarnamn": "Username",
        "Lösenord": "Password",
        "Inbjudningskod": "Invitation code",
        "Din första 1 mot 1-duell": "Your first 1 vs 1 duel",
        "Steg {step} av {total}": "Step {step} of {total}",
        "Sänk motståndaren till 0 HP": "Bring your opponent to 0 HP",
        "500 krediter": "500 credits",
        "Välj riktning": "Choose a direction",
        "25 % · 125 krediter": "25% · 125 credits",
        "100 ↗ 104 · +5 krediter": "100 ↗ 104 · +5 credits",
        "100 ↘ 96 · +5 krediter": "100 ↘ 96 · +5 credits",
        "Använd vinsten": "Use your profit",
        "+5 krediter": "+5 credits",
        "En förlust kostar krediter och kan kosta HP.": "A losing trade costs credits and can cost HP.",
        "Motståndare −20 HP · 500 krediter kvar": "Opponent −20 HP · 500 credits left",
        "505 krediter · 102 % attackkraft · +25 bonus-HP": "505 credits · 102% attack power · +25 bonus HP",
        "När duellen avgörs": "How the duel is decided",
        "Efter 75 sekunder drar stormen HP från båda.": "After 75 seconds, the storm drains HP from both players.",
        "Vid dubbel KO avgör kapital, sedan attackskada.": "On a double KO, capital decides, then attack damage.",
        "Öva i Botduell. Tävla om Elo i rankat läge.": "Practise in Bot Duel. Play ranked to compete for Elo.",
        "Tillbaka": "Back",
        "Nästa": "Next",
        "Slutför introduktionen": "Finish tutorial",
        "Spela introduktionen igen": "Replay the tutorial",
        "Logga in för att slutföra duellguiden.": "Log in to finish the duel tutorial.",
        "Wall Street-marknaden": "Wall Street Market",
        "Strategi · Flerspelare": "Strategy · Multiplayer",
        "Börsföretag": "Trading Firms",
        "Bygg din firma, träna handlare och köp aktier i andra spelares företag på livemarknaden.": "Build your firm, train traders, and buy shares in other players' companies on the live market.",
        "Öppna handelsfirman": "Open your trading firm",
        "Inloggad som": "Logged in as",
        "Rankad · 1 mot 1": "Ranked · 1 vs 1",
        "Handelsduell": "Trading Duel",
        "Handla på samma aktiekurs som motståndaren och tävla om Elo.": "Trade the same stock as your opponent and compete for Elo.",
        "Spela rankad duell": "Play ranked duel",
        "Fler spellägen": "More game modes",
        "Ritduell": "Forecast Duel",
        "Rita nästa kursrörelse. Den som kommer närmast gör skada.": "Draw the next price move. The closest forecast deals damage.",
        "Spela ritduell": "Play Forecast Duel",
        "Öva ritduell": "Practise Forecast Duel",
        "Botduell": "Bot Duel",
        "Orankad duell med svårighetsgrad anpassad till ditt Elo.": "An unranked duel with difficulty based on your Elo.",
        "Spela mot bot": "Play against a bot",
        "Spela handelsduell mot bot": "Play a Trading Duel against a bot",
        "Så spelar du": "How to play",
        "Vänduell": "Friend Duel",
        "Skicka en länk till en vän och spela en orankad handelsduell.": "Send a friend a link to play an unranked trading duel.",
        "Spela med en vän": "Play with a friend",
        "Pågående matcher": "Live matches",
        "Följ andra spelares dueller i realtid.": "Watch other players’ duels in real time.",
        "Titta live": "Watch live",
        "Din ranking": "Your rank",
        "Liga": "League",
        "Visa alla ranker": "Show all ranks",
        "Nästa nivå": "Next rank",
        "Mot nästa nivå": "Progress to the next rank",
        "Spelarmeny": "Player menu",
        "Ranking": "Leaderboard",
        "Profil": "Profile",
        "Inställningar": "Settings",
        "Till huvudmenyn": "Back to main menu",
        "Laddar pågående matcher …": "Loading live matches …",
        "Matcher att följa live": "Matches to watch live",
        "Försök igen": "Try again",
        "Åskådarläge": "Spectator mode",
        "Till matchlistan": "Back to match list",
        "Första spelarens hälsa": "First player’s health",
        "Kapital": "Capital",
        "Startar": "Starting",
        "Andra spelarens hälsa": "Second player’s health",
        "Marknad och kursgraf": "Market and price chart",
        "Syntetisk": "Synthetic",
        "Kurs": "Price",
        "Graf över aktiekursen": "Stock price chart",
        "Kurshistorik och avslöjade prognoser": "Price history and revealed forecasts",
        "Zoom för kursgrafen": "Price chart zoom",
        "Zooma ut": "Zoom out",
        "Zooma in": "Zoom in",
        "Facit": "Actual",
        "Första spelaren": "First player",
        "Andra spelaren": "Second player",
        "Söker motståndare": "Looking for an opponent",
        "Väntetid": "Wait time",
        "Elo-intervall": "Elo range",
        "Lämna kön": "Leave queue",
        "Inbjudningslänk": "Invitation link",
        "Kopiera länk": "Copy link",
        "Gå med i duellen": "Join the duel",
        "Avbryt": "Cancel",
        "Du": "You",
        "Din hälsa": "Your health",
        "Attackkraft": "Attack power",
        "Motståndare": "Opponent",
        "Motståndarens hälsa": "Opponent’s health",
        "Öppen position": "Open position",
        "Avsluta övning": "End practice",
        "Hoppa över guiden": "Skip tutorial",
        "Linjegraf över aktiekursen": "Stock price line chart",
        "Kurshistorik och nästa kurspunkt. Ange en prognos med procentfältet eller genom att dra i prognosfältet i grafen.": "Price history and the next price point. Enter a forecast in the percentage field or drag in the forecast area of the chart.",
        "Matchstart": "Match starts",
        "Position och handel": "Position and trading",
        "Handelns steg": "Trading steps",
        "Öppna": "Open",
        "Följ kursen": "Watch price",
        "Avsluta": "Exit",
        "Välj insats i krediter": "Choose a stake in credits",
        "Andel av tillgängliga krediter att satsa": "Share of available credits to stake",
        "Vald insats": "Selected stake",
        "krediter": "credits",
        "Välj riktning för din position": "Choose the direction of your position",
        "UPP": "UP",
        "NER": "DOWN",
        "Vinst vid uppgång": "Profit if the price rises",
        "Vinst vid nedgång": "Profit if the price falls",
        "STÄNG POSITION": "CLOSE POSITION",
        "Stäng affären": "Close trade",
        "Affären just nu": "Trade so far",
        "Avsluta affären": "Exit the trade",
        "Vid aktuell kurs": "At the current price",
        "Fortsätt hålla": "Keep holding",
        "Gör skada": "Deal damage",
        "Bygg kapital och bonus": "Build capital and bonus",
        "Tillgängligt": "Available",
        "Investerat": "Invested",
        "Grow-bonus": "Grow bonus",
        "Ingångskurs": "Entry price",
        "Orealiserat resultat": "Unrealised P/L",
        "Ritduellens prognos": "Forecast Duel prediction",
        "Dra uppåt eller nedåt i prognosfältet, eller skriv din gissning i procent.": "Drag up or down in the forecast area, or enter your percentage guess.",
        "Din prognos (%)": "Your forecast (%)",
        "t.ex. −1,25": "e.g. −1.25",
        "Negativt tecken": "Negative sign",
        "Rensa": "Clear",
        "Lås prognos": "Lock in forecast",
        "Motståndaren": "Opponent",
        "Nästa runda": "Next round",
        "Matchresultat": "Match result",
        "Elo före": "Elo before",
        "Elo efter": "Elo after",
        "Dina slut-HP": "Your final HP",
        "Motståndarens slut-HP": "Opponent’s final HP",
        "Affärer": "Trades",
        "Vinstaffärer": "Winning trades",
        "Förlustaffärer": "Losing trades",
        "Attackskada": "Attack damage",
        "Grow-val": "Grow choices",
        "Högsta kapital": "Peak capital",
        "Ditt slutkapital": "Your final capital",
        "Motståndarens slutkapital": "Opponent’s final capital",
        "Hälsa vid slut": "Final health",
        "Matchlängd": "Match duration",
        "Rundor": "Rounds",
        "Dina affärer": "Your trades",
        "Tid": "Time",
        "Avslut": "Close action",
        "Kursvinst/förlust": "Price gain/loss",
        "Skada": "Damage",
        "Prognos och facit per runda": "Forecasts and actual moves by round",
        "Runda": "Round",
        "Utfall": "Result",
        "Ditt fel": "Your error",
        "Motståndarens fel": "Opponent’s error",
        "Spela igen": "Play again",
        "Huvudmeny": "Main menu",
        "Stäng spelguiden": "Close game guide",
        "Välj insats → UPP eller NER → Stäng affären.": "Choose a stake → UP or DOWN → Close trade.",
        "Attack gör skada. Grow sparar vinsten.": "Attack deals damage. Grow keeps the profit.",
        "Fler duellregler": "More duel rules",
        "Grow laddar nästa attack. En förlust kostar krediter och kan kosta HP.": "Grow powers up the next attack. A losing trade costs credits and can cost HP.",
        "Attackkraften ändras med 1 procentenhet per 2,5 krediter över eller under 500, inom 75–125 %. Kapitalet är kassan plus insatsen i en öppen affär.": "Attack power changes by 1 percentage point for every 2.5 credits above or below 500, within 75–125%. Capital is your cash plus the stake in an open trade.",
        "Vid dubbel KO avgör kapital, sedan attackskada. Vid lika blir det oavgjort.": "On a double KO, capital decides, then attack damage. If both are equal, the duel is a draw.",
        "Starta guidad botduell": "Start guided Bot Duel",
        "Dra i prognosfältet i grafen eller skriv hur många procent kursen ändras till nästa punkt. Den som låst den närmaste prognosen gör skada. Flest HP kvar efter sista rundan vinner, om ingen slagits ut tidigare.": "Drag in the forecast area of the chart or enter how much you think the price will change as a percentage. The player with the closest locked forecast deals damage. If both players reach the final round, the one with the most HP left wins.",
        "Prova Attack och Grow": "Try Attack and Grow",
        "Stäng introduktionen": "Close introduction",
        "Vinst i exemplet": "Example profit",
        "Prova vad vinsten kan användas till": "Try the ways to use a profit",
        "Prova Attack": "Try Attack",
        "Prova Grow": "Try Grow",
        "Ranker": "Ranks",
        "Stäng ranklistan": "Close rank list",
        "Stäng ranking": "Close leaderboard",
        "Spelläge": "Game mode",
        "Rankingtavla": "Leaderboard table",
        "Spelare": "Player",
        "Vinster": "Wins",
        "Matcher": "Matches",
        "Stäng profil": "Close profile",
        "Förluster": "Losses",
        "Oavgjorda": "Draws",
        "Vinstprocent": "Win rate",
        "Matchhistorik": "Match history",
        "Aktie": "Stock",
        "Datum": "Date",
        "Stäng inställningar": "Close settings",
        "Graftyp": "Chart type",
        "Linjegraf": "Line chart",
        "Ljusstaplar": "Candlesticks",
        "Ljud": "Sound",
        "Ljudeffekter vid attacker, Grow och matchslut.": "Sound effects for attacks, Grow and match endings.",
        "Kraftiga animationer": "Intense animations",
        "Skärmeffekter vid bland annat skada och KO.": "Screen effects for damage, knockouts and other events.",

        "Ner": "Down",
        "Upp": "Up",
        "Handel": "Trading",
        "Duell": "Duel",
        "Prognos": "Forecast",
        "Marknadsstorm": "Market storm",
        "Slutstorm": "Final storm",
        "VANN": "WON",
        "FÖRLORADE": "LOST",
        "OAVGJORT": "DRAW",
        "Nytt spelarkonto": "New player account",
        "Skapa konto": "Create account",
        "Hämtar profil …": "Loading profile …",
        "Högsta ligan": "Top league",
        "Inga avslutade matcher ännu.": "No completed matches yet.",
        "Hämtar ranking …": "Loading leaderboard …",
        "Rankingen är tom.": "The leaderboard is empty.",
        "Spelanslutningen kunde inte startas": "Could not connect to the game",
        "Anslutningen bröts under handeln. Kontrollera din position när du är tillbaka.": "The connection dropped during the trade. Check your position when you reconnect.",
        "Spelanslutningen avslutades. Uppdatera sidan för att försöka igen.": "The game connection closed. Reload the page to try again.",
        "Spelanslutningen nekades": "The game connection was refused",
        "Hämtar pågående matcher …": "Loading live matches …",
        "Matchlistan kunde inte hämtas.": "Could not load the match list.",
        "Inga matcher pågår just nu.": "No matches are live right now.",
        " mot ": " vs ",
        "Startar snart": "Starting soon",
        "Titta live på {players}": "Watch {players} live",
        "Inte live": "Offline",
        "Runda {round} av {limit}": "Round {round} of {limit}",
        "{storm} om {time}": "{storm} in {time}",
        "{winner} vann matchen.": "{winner} won the match.",
        "Matchen slutade oavgjort.": "The match ended in a draw.",
        "Avslutad": "Finished",
        "Prognos låst": "Forecast locked in",
        "{actor} · Förlustaffär{damage}": "{actor} · Losing trade{damage}",
        "{winner} vann rundan · {damage} HP i skada": "{winner} won the round · {damage} HP damage",
        "Spelanslutningen är offline. Uppdatera sidan för att försöka igen.": "The game is offline. Reload the page to try again.",
        "Söker en ritduell": "Looking for a Forecast Duel",
        "Startar …": "Starting …",
        "Vänta tills spelet är anslutet och försök igen.": "Wait for the game to connect, then try again.",
        "Inbjudningslänken är kopierad.": "Invitation link copied.",
        "Länken är markerad. Kopiera den för att dela den.": "The link is selected. Copy it to share it.",
        "Kön svarade inte. Försök igen.": "The queue did not respond. Try again.",
        "Väntar på kursgraf …": "Waiting for the price chart …",
        "Kursgrafen kunde inte visas.": "Could not display the price chart.",
        "ÖVNING": "PRACTICE",
        "Kunde inte nå servern. Kontrollera din anslutning.": "Could not reach the server. Check your connection.",
        "Servern kunde inte slutföra begäran.": "The server could not complete the request.",
        "Ansluter …": "Connecting …",
        "Återansluter …": "Reconnecting …",
        "Ansluten": "Connected",
        "Spelanslutningen är offline.": "The game is offline.",
        "Ansluter till matchen …": "Connecting to the match …",
        "Liveuppdateringarna kunde inte startas.": "Could not start live updates.",
        "Matchen startar snart": "The match is starting soon",
        "Oavgjord runda": "Round drawn",
        "Servern svarade inte. Försök igen.": "The server did not respond. Try again.",
        "Inbjudan är inte längre aktiv.": "The invitation has expired.",
        "Skapar inbjudan …": "Creating invitation …",
        "Dela länken och vänta på att din vän går med.": "Share the link and wait for your friend to join.",
        "Du har fått en inbjudan till en orankad handelsduell.": "You have been invited to an unranked Trading Duel.",
        "Välj insats och tryck UPP eller NER.": "Choose a stake and press UP or DOWN.",
        "Följ affären och stäng när du vill.": "Watch the trade and close it when you're ready.",
        "Stäng till aktuell kurs eller fortsätt hålla.": "Close at the current price or keep holding.",
        "Kurspunkt {time}": "Price point {time}",
        "Kursgraf med ljusstaplar": "Candlestick price chart",
        "Inget svar": "No response",
        "Inga prognoser": "No forecasts",
        "Tiden gick ut för båda spelarna. Ingen tog skada.": "Both players ran out of time. Neither took damage.",
        "Ni kom lika nära facit. Ingen tog skada.": "Both forecasts were equally close. Neither player took damage.",
        "{winner} vann rundan": "{winner} won the round",
        "{winner} var ensam om att låsa en prognos.": "{winner} locked in the only forecast.",
        "{winner} kom {margin} procentenheter närmare facit.": "{winner} came {margin} percentage points closer.",
        "Se sammanfattning": "View summary",
        "{error} procentenheter fel": "{error} percentage points off",
        "Facit för rundan": "Actual move this round",
        "{player} förlorade {damage} HP.": "{player} lost {damage} HP.",
        "Gör dig redo att gissa nästa kursrörelse.": "Get ready to guess the next price move.",
        "Prognosen är låst. Väntar på facit.": "Forecast locked in. Waiting for the actual move.",
        "Låser prognosen …": "Locking in forecast …",
        "Väntar på anslutning …": "Waiting for a connection …",
        "Motståndaren har låst sin prognos.": "Your opponent has locked in their forecast.",
        "Hur rör sig kursen härnäst?": "How will the price move next?",
        "Ange minst −100 % med högst två decimaler.": "Enter a value of at least −100% with up to two decimal places.",
        "Prognosen kunde inte bekräftas. Försök igen.": "Could not confirm the forecast. Try again.",
        "{damage} HP skada": "{damage} HP damage",
        "{credits} krediter · {bonus} bonus-HP": "{credits} credits · {bonus} bonus HP",
        "{credits} krediter · {damage} HP": "{credits} credits · {damage} HP",
        "±0 krediter": "±0 credits",
        "Handeln kunde inte bekräftas. Kontrollera din position.": "Could not confirm the trade. Check your position.",
        "Revansch mot samma spelare": "Rematch with the same player",
        "Revansch är inte tillgänglig.": "A rematch is unavailable.",
        "Skickar ditt svar …": "Sending your response …",
        "Väntar på att motståndaren accepterar.": "Waiting for your opponent to accept.",
        "Motståndaren vill ha revansch.": "Your opponent wants a rematch.",
        "Revanschen startar när båda accepterar.": "The rematch starts when both players accept.",
        "Din attack avgjorde matchen.": "Your attack decided the match.",
        "Motståndarens attack avgjorde matchen.": "Your opponent’s attack decided the match.",
        "Matchen avgjordes av en attack.": "An attack decided the match.",
        "Din förlustaffär avslutade matchen.": "Your losing trade ended the match.",
        "Motståndarens förlustaffär avslutade matchen.": "Your opponent’s losing trade ended the match.",
        "Högst slutkapital avgjorde.": "The player with more final capital won.",
        "Kapitalet var lika, så mest attackskada avgjorde.": "Capital was tied, so the player who dealt more attack damage won.",
        "Ni hade lika mycket kapital och gjorde lika mycket attackskada.": "You both had the same capital and dealt the same attack damage.",
        "Båda slogs ut i {storm}. {tiebreak}": "Both players were knocked out in the {storm}. {tiebreak}",
        "Matchen avgjordes i {storm}.": "The match was decided in the {storm}.",
        "Matchen avgjordes genom knockout.": "A knockout decided the match.",
        "Matchen avgjordes av slut-HP efter sista rundan.": "The remaining HP after the final round decided the match.",
        "Du sänkte {opponent} till 0 HP.": "You reduced {opponent} to 0 HP.",
        "{opponent} sänkte dig till 0 HP.": "{opponent} reduced you to 0 HP.",
        "Ni hade lika mycket HP kvar efter sista rundan.": "You both had the same HP left after the final round.",
        "{winner} hade mest HP kvar efter sista rundan.": "{winner} had the most HP left after the final round.",
        "{opponent} · slut-HP": "{opponent} · final HP",
        "Förlust": "Loss",
        "Ingen vinst eller förlust": "Break-even",
        "{credits} krediter": "{credits} credits",
        "Ingen prognos": "No forecast",
        "{error} procentenheter": "{error} percentage points",
        "{damage} HP i skada": "{damage} HP damage",
        "Ritduell · Övning": "Forecast Duel · Practice",
        "Botduell · Orankad": "Bot Duel · Unranked",
        "Vänduell · Orankad": "Friend Duel · Unranked",
        "Du vann": "You won",
        "Du förlorade": "You lost",
        "Oavgjort": "Draw",
        "Övning klar": "Practice complete",
        "MATCH SLUT": "MATCH OVER",

        "Sessionen behöver uppdateras. Ladda om sidan.": "Your session needs to be refreshed. Reload the page.",
        "Välj ett användarnamn på 3–24 tecken. Använd bokstäver, siffror, _ eller -.": "Choose a username of 3–24 characters. Use letters, numbers, _ or -.",
        "Lösenordet behöver vara 8–128 tecken.": "Your password must be 8–128 characters long.",
        "Inbjudningskoden är fel.": "The invitation code is incorrect.",
        "Användarnamnet är redan taget.": "That username is already taken.",
        "Fel användarnamn eller lösenord.": "Incorrect username or password.",
        "Logga in för att öppna profilen.": "Log in to open your profile.",
        "Logga in för att öppna topplistan.": "Log in to open the leaderboard.",
        "Logga in igen.": "Log in again.",
        "Ogiltig förfrågan.": "Invalid request.",
        "Ogiltig matchförfrågan.": "Invalid match request.",
        "Matchen är inte längre live.": "The match is no longer live.",
        "Ogiltig köförfrågan.": "Invalid queue request.",
        "Okänt spelläge.": "Unknown game mode.",
        "Kontot finns inte längre.": "The account no longer exists.",
        "En match har redan startat.": "A match has already started.",
        "Ogiltig inbjudningsförfrågan.": "Invalid invitation request.",
        "Du har redan en aktiv match.": "You already have an active match.",
        "Ange en giltig matchkod.": "Enter a valid match code.",
        "Matchkoden finns inte eller har gått ut.": "The match code is invalid or has expired.",
        "Du kan inte gå med i din egen kompismatch.": "You cannot join your own friend duel.",
        "En av spelarna har redan en aktiv match.": "One of the players already has an active match.",
        "Värden är inte ansluten. Försök igen när värden är tillbaka.": "The host is disconnected. Try again when the host returns.",
        "En av spelarnas konton finns inte längre.": "One of the players’ accounts no longer exists.",
        "Ogiltig revanschförfrågan.": "Invalid rematch request.",
        "Revanschen är inte längre tillgänglig.": "The rematch is no longer available.",
        "Motståndaren är inte ansluten.": "Your opponent is disconnected.",
        "Ogiltig handelsförfrågan.": "Invalid trade request.",
        "Okänd handelsåtgärd.": "Unknown trading action.",
        "Ogiltiga fält i handelsförfrågan.": "Invalid fields in the trade request.",
        "Matchen är inte aktiv.": "The match is inactive.",
        "Handel är inte tillgänglig i Ritduell.": "Trading is unavailable in Forecast Duel.",
        "Handelsförfrågan är redan behandlad eller ur ordning.": "The trade request was already processed or arrived out of order.",
        "Ogiltig prognosförfrågan.": "Invalid forecast request.",
        "Du har ingen aktiv ritduell.": "You have no active Forecast Duel.",
        "Ogiltig övningsförfrågan.": "Invalid practice request.",
        "Avsluta din pågående match först.": "Finish your current match first.",
        "Du har ingen aktiv övning.": "You have no active practice session.",
        "Förfrågan gäller en annan övning.": "The request refers to a different practice session.",
        "Din prognos är redan låst.": "Your forecast is already locked in.",
        "Lås en prognos innan du går vidare.": "Lock in a forecast before continuing.",
        "Prognosen gäller inte den aktuella rundan.": "This forecast is for a different round.",
        "Ogiltig kursförändring.": "Invalid price change.",
        "Rundan är stängd för prognoser.": "Forecasts are closed for this round.",
        "Du deltar inte i den här matchen.": "You are not in this match.",
        "Åtgärden är inte tillgänglig i spelläget.": "This action is unavailable in this game mode.",
        "Du har ingen position att stänga.": "You have no position to close.",
        "Bekräftelsen gäller inte den aktuella positionen.": "The confirmation is for a different position.",
        "Affären visar vinst igen. Välj Attack eller Grow.": "The trade is profitable again. Choose Attack or Grow.",
        "Välj Attack eller Grow för att stänga positionen.": "Choose Attack or Grow to close the position.",
        "Välj 25, 50, 75 eller 100 procent.": "Choose 25, 50, 75 or 100 percent.",
        "Du har redan en öppen position.": "You already have an open position.",
        "Du har inte tillräckligt med kapital.": "You do not have enough capital.",
    };

    function browserLanguage() {
        const preferred = [...(navigator.languages || []), navigator.language];
        for (const locale of preferred) {
            const code = locale?.toLowerCase().split(/[-_]/)[0];
            if (Object.hasOwn(locales, code)) return code;
        }
        return "en";
    }

    function savedLanguage() {
        try {
            const saved = localStorage.getItem(preferenceKey);
            if (Object.hasOwn(locales, saved)) return saved;
        } catch {
            // The language control still works when the browser disables storage.
        }
        return null;
    }

    let manualLanguage = savedLanguage();
    let language = manualLanguage || browserLanguage();

    function getLocale() {
        return locales[language];
    }

    function t(source, values) {
        if (typeof source !== "string") return source;
        let translated = source;
        if (language === "en") {
            if (Object.hasOwn(english, source)) {
                translated = english[source];
            } else {
                // The market service sends the requested number within this message.
                const marketError = /^Marknadsdatan saknar en sammanhängande serie med (\d+) kurspunkter\.$/.exec(source);
                if (marketError) return `Market data does not contain a continuous series of ${marketError[1]} price points.`;
            }
        }
        if (!values) return translated;
        return translated.replace(/\{(\w+)\}/g, (placeholder, name) =>
            Object.hasOwn(values, name) ? values[name] : placeholder);
    }

    const selector = document.getElementById("language-select");

    function renderLanguage() {
        document.documentElement.lang = language;
        if (selector) selector.value = language;

        for (const element of document.querySelectorAll("[data-i18n]")) {
            element.textContent = t(element.dataset.i18n);
        }
        for (const attribute of ["aria-label", "title", "placeholder"]) {
            const key = `data-i18n-${attribute}`;
            for (const element of document.querySelectorAll(`[${key}]`)) {
                element.setAttribute(attribute, t(element.getAttribute(key)));
            }
        }

        const decimal = new Intl.NumberFormat(getLocale(), {
            minimumFractionDigits: 2,
            maximumFractionDigits: 2,
        });
        const change = new Intl.NumberFormat(getLocale(), {
            style: "percent",
            signDisplay: "exceptZero",
            minimumFractionDigits: 2,
            maximumFractionDigits: 2,
        });
        for (const element of document.querySelectorAll("[data-i18n-number]")) {
            element.textContent = decimal.format(Number(element.dataset.i18nNumber));
        }
        for (const element of document.querySelectorAll("[data-i18n-signed-percent]")) {
            element.textContent = change.format(Number(element.dataset.i18nSignedPercent));
        }
    }

    function setLanguage(nextLanguage) {
        if (nextLanguage === language) return;
        language = nextLanguage;
        renderLanguage();
        window.dispatchEvent(new Event("stockfight:languagechange"));
    }

    selector?.addEventListener("change", () => {
        if (!Object.hasOwn(locales, selector.value)) return;
        manualLanguage = selector.value;
        try {
            localStorage.setItem(preferenceKey, manualLanguage);
        } catch {
            // Keep the current choice for this page even without storage.
        }
        setLanguage(manualLanguage);
    });
    window.addEventListener("languagechange", () => {
        if (!manualLanguage) setLanguage(browserLanguage());
    });

    window.StockFightI18n = { getLocale, t };
    renderLanguage();
})();
