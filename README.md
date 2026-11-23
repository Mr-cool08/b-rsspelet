# Stock Fight

Stock Fight är ett mobilanpassat spel med två rankade lägen. I Handelsduell handlar båda samma aktie med 1 000 virtuella krediter och börjar med 100 HP. En vinstaffär kan användas till **Attack** för att skada motståndaren eller **Grow** för att öka kapitalet och ladda nästa attack. I Ritduell tävlar spelarna om att komma närmast nästa kursrörelse. Handelsduell går även att spela privat med en vän eller mot en bot. Ritduell har en övning för en spelare. Elo och avslutade rankade matcher sparas i SQLite.

## Spela lokalt

Installera Python 3.12 eller senare och kör kommandona från projektmappen.

**Windows PowerShell**

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe run.py
```

**Ubuntu och macOS**

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python run.py
```

Öppna [Stock Fight på localhost](http://127.0.0.1:8080) och registrera ett konto. Välj **Spela mot bot** för en träningsmatch. För Ranked, öppna spelet i två separata webbläsarprofiler eller på två enheter, logga in med varsitt konto och tryck **PLAY** på båda. Spelet skapar SQLite-filen i `instance/` och importerar medföljande, tydligt markerad syntetisk minutdata under första starten.

- **Spela med en vän** skapar en länk till en orankad Handelsduell. Länken fungerar en gång inom 15 minuter. Värden behöver vara ansluten när gästen bekräftar. Efter matchen kan båda tacka ja till revansch inom 15 minuter. Spela från samma lokalnätsadress eller publika adress om ni använder olika enheter.
- **Spela ritduell** öppnar en separat rankad kö med egen Elo. Dra till höger i grafen eller ange en procentuell kursrörelse i fältet och lås prognosen.
- **Öva ritduell** går igenom tre rundor på en kurva med syntetiska priser. Lås prognosen för att se facit och din avvikelse. Gå vidare när du är redo.

För att spela från två mobiler på samma nätverk, sätt `STOCK_FIGHT_DEV_HOST=0.0.0.0` i `.env` före start. Öppna datorns lokala IP-adress med port 8080 från båda mobilerna.

## Spela via ngrok utan Docker

Installera [ngrok för Windows](https://ngrok.com/download/windows) om klienten saknas. Kopiera din [authtoken från ngroks kontrollpanel](https://dashboard.ngrok.com/get-started/your-authtoken) till raden `NGROK_AUTHTOKEN=` i projektets `.env`.

Starta spelet från projektmappen i PowerShell med sessionskakor för HTTPS.

```powershell
$env:SESSION_COOKIE_SECURE = '1'
$env:STOCK_FIGHT_DEV_HOST = '127.0.0.1'
.\.venv\Scripts\python.exe run.py
```

Starta tunneln från projektmappen i ett andra PowerShell-fönster. Skriptet läser token och port från `.env`.

```powershell
.\.venv\Scripts\python.exe run_ngrok.py
```

Dela HTTPS-adressen som ngrok visar under **Forwarding**. Båda spelarna öppnar samma länk, loggar in med varsitt konto och trycker på **PLAY**. Om `INVITE_CODE` är satt behöver nya spelare koden för att registrera sig. Låt båda terminalfönstren vara igång medan ni spelar.

## Kör spelet och ngrok med Docker Compose

1. Kopiera `.env.example` till `.env` om filen saknas.
2. Skapa vid behov ett värde med `python -c "import secrets; print(secrets.token_hex(32))"` och lägg det i `SECRET_KEY`. Sätt `INVITE_CODE` om registrering ska kräva en kod.
3. Fyll i `NGROK_AUTHTOKEN` från [ngroks kontrollpanel](https://dashboard.ngrok.com/get-started/your-authtoken) och sätt `SESSION_COOKIE_SECURE=1` för HTTPS.
4. Stoppa en eventuell manuell spelserver och ngrok-tunnel och starta båda tjänsterna från projektmappen.

```bash
docker compose up --build -d
docker compose ps
docker compose logs --tail=20 ngrok
```

Dela HTTPS-adressen som ngrok visar i loggen för `started tunnel`. Compose startar tunneln när spelets hälsokontroll lyckas. Båda containrarna startar igen när Docker startar, om de lämnades igång.

Compose-projektet heter `stock-fight-app`. Konton, Elo, marknadsdata och historik ligger i den namngivna volymen för projektet. `docker compose down` stoppar tjänsterna och behåller volymen.

Gunicorn kör exakt en trådad serverprocess med WebSocket-stöd via Flask-SocketIO och simple-websocket. Aktiva matcher och kön ligger i den processen och försvinner vid omstart. Färdigspelade Ranked-matcher och Elo ligger i SQLite.

### Konfiguration

| Variabel | Funktion |
| --- | --- |
| `SECRET_KEY` | Signerar sessionskakor. Compose kräver ett värde. Lokalt skapas en tillfällig nyckel per start om värdet saknas. |
| `INVITE_CODE` | Gemensam inbjudningskod. Tomt värde öppnar registrering. |
| `STOCK_FIGHT_PORT` | Extern port. Standard 8080. |
| `STOCK_FIGHT_BIND` | Bindningsadress för Compose. Standard `0.0.0.0`. |
| `STOCK_FIGHT_DEV_HOST` | Bindningsadress för lokal utvecklingsserver. Standard `127.0.0.1`. |
| `SESSION_COOKIE_SECURE` | Använd `1` när spelarna ansluter via HTTPS. |
| `NGROK_AUTHTOKEN` | Token som ngrok använder för att öppna tunneln. |
| `AUTO_SEED_DEMO` | `1` importerar medföljande syntetiska data automatiskt. |
| `ALLOW_SYNTHETIC` | `0` kräver en spelbar importerad verklig serie. |
| `MARKET_TICK_SECONDS` | Sekunder per historisk stapel. Standard `3`. |
| `MATCH_PREVIEW_BARS` | Antal staplar i förhandsvisningen. Standard `12`. |
| `DATABASE_URL` | Lokal SQLite-anslutning. Standard `sqlite:///stockfight.sqlite3` i `instance/`. Compose anger sin egen väg. |

## Importera verkliga kurser

Kursfiler med verkliga svenska och amerikanska aktier importeras lokalt. Använd data som du har rätt att använda på din server och visa för dina spelare. Den medföljande CSV-filen innehåller påhittade instrument och kurser för utveckling och provspel. Matchningen väljer i första hand bland spelbara verkliga serier när sådana har importerats.

Spara filen som kommaavgränsad UTF-8 med följande kolumnrubriker. `name` är valfri.

```csv
symbol,market,timestamp,open,high,low,close,volume,name
```

Använd till exempel `SE` eller `US` för marknad och ISO 8601 för tidsstämpeln. Tider utan tidszon tolkas som UTC. Priser använder punkt som decimaltecken. Ange intervallet per import, exempelvis `1m`, `5m`, `1h`, `1d` eller `1w`. En stapel spelas upp per kurstick oavsett historiskt intervall. Flaggan `--synthetic` ska användas för påhittade kurser.

Ett spelbart fönster behöver som standard **51 observationer** i en och samma serie. Det motsvarar förhandsvisningen plus tillräckligt med observationer för 115 sekunders uppspelning. Om du ändrar uppspelningshastigheten behöver varje fönster `MATCH_PREVIEW_BARS + ceil(115 / MARKET_TICK_SECONDS)` observationer. Intradagsfönster bryts vid luckor. Dagliga och veckovisa serier kan passera stängda handelsdagar, upp till det nominella intervallet plus sex kalenderdagar mellan två observationer.

Importera med projektets virtuella miljö aktiv.

```bash
python -m flask --app stockfight:create_app init-db
python -m flask --app stockfight:create_app import-market data/imports/kurser.csv --source "Min datakälla" --interval 1m
```

Med Docker placerar du filen under `data/imports/` och kör importen i samma Compose-projekt.

```bash
docker compose run --rm --no-deps game flask --app stockfight:create_app import-market /app/imports/kurser.csv --source "Min datakälla" --interval 1m
```

Om en rad är ogiltig avbryts hela importen och kommandot anger felet. En andra import av samma symbol, marknad, tidsstämpel, intervall och källa behåller redan lagrade staplar av samma typ. Kör `seed-demo` som Flask-kommando för att manuellt återställa saknade syntetiska staplar.

## Spelregler och serverbeteende

- Båda spelarna får samma förhandsvisning och tre sekunders nedräkning. Spelservern skickar bara redan visade staplar och använder relativa tider tills resultatet har fastställts.
- En spelare kan öppna en position med 25, 50, 75 eller 100 procent av sitt tillgängliga kapital. **Upp** ger vinst när kursen stiger och **Ner** ger vinst när den faller. Spelaren kan ha en öppen position åt gången och förlora högst insatsen per affär. Handel och priser räknas med decimaler på servern. Servern behandlar varje kommando under ett lås och uppdaterar först alla kurstick som har förfallit vid behandlingstidpunkten. Varje spelare har ett eget stigande kommandonummer per match.
- När spelaren stänger en position som ligger på vinst gäller kursen vid bekräftelse av **Attack** eller **Grow**. Om utfallet då har blivit en förlust eller noll används de vanliga reglerna för det utfallet. Attack förbrukar vinsten och Grow-bonusen. Grow behåller vinsten och sparar upp till 25 bonus-HP. En förlust dras från kapitalet, skadar spelaren med högst 20 HP och nollställer bonusen.
- Förhandsvisningen av Attack och Grow visar effekten vid den senast visade kursen. Servern uppdaterar effekten när en ny stapel visas. Ett väntande val återställs när spelaren ansluter igen med samma konto.
- **Market Storm** drar 2 HP per sekund från sekund 75. **Final Storm** drar 4 HP per sekund från sekund 105. En match där båda behåller full hälsa före stormen når dubbel KO vid cirka 114 sekunder. Vid samtidig KO vinner den som har tagit bort flest HP med attacker. Vid lika attackskada blir matchen oavgjord.
- Matchen fortsätter vid nätavbrott och kan återupptas genom att ansluta med samma konto. Ett kort avbrott ändrar varken HP eller Elo på egen hand. En öppen position vid KO räknas med till sitt investerade belopp i slutkapitalet. Högsta kapital avser det högsta realiserade handelskapitalet.
- Matchningen börjar på ±100 Elo och söker inom ±200 när båda har väntat minst 15 sekunder. Spelaren kan lämna kön när som helst före matchstart. Elo börjar på 1 000, räknas med K = 32 och uppdateras i samma databastransaktion som resultatet och affärerna.
- Botens svårighetsgrad utgår från spelarens aktuella Ranked-Elo vid matchstart. Boten spelar med samma regler och ser samma kursstaplar som spelaren. Botmatcher påverkar varken Elo, topplistan eller Ranked-historiken.
- En rankad Ritduell har upp till åtta rundor. Spelarna har 20 sekunder att förutsäga nästa stängningskurs. Facit visas när båda låst sin prognos eller tiden gått ut. Den närmaste prognosen gör skada på motståndaren. Lika nära ger noll skada, och en ensam prognos vinner rundan. Matchen avgörs vid knockout eller av vem som har mest HP efter sista rundan.
- Resultatskärmen visar slut-HP, slutorsak och egna affärer i Handelsduell eller båda spelarnas rundresultat i Ritduell. Matchdetaljer, privata inbjudningar och pågående soloövningar ligger i serverns minne och försvinner vid omstart. En soloövning kan återupptas inom 15 minuter efter frånkoppling.

## Kod och tester

| Del | Filer |
| --- | --- |
| Flask, konton och importkommandon | `stockfight/__init__.py`, `run.py` |
| Handel, kurstick och Ranked-regler | `stockfight/engine.py` |
| Botens handelsstrategi | `stockfight/bot.py` |
| Rankad Ritduell och soloövning | `stockfight/prediction.py`, `stockfight/practice.py` |
| Socket.IO, kö och matchrum | `stockfight/multiplayer.py` |
| SQLite, marknadsdata och Elo | `stockfight/data.py`, `stockfight/market_data.py`, `stockfight/ranking.py` |
| HTML, CSS, JavaScript och kursgraf | `stockfight/templates/`, `stockfight/static/` |

```bash
python -m pip install -r requirements-test.txt
python -m pytest -q
```

Testerna täcker spelregler, kursimport, konton, Elo, Ranked-matcher mellan två Socket.IO-testklienter och träningsmatcher mot boten. Lokalt paketerade webbläsarbibliotek inkluderar Socket.IO Client (MIT) och TradingView Lightweight Charts (Apache 2.0). Licenserna finns i `stockfight/static/vendor/`.
