# Stock Fight

Stock Fight är ett mobilanpassat spel med två rankade lägen. I Handelsduell handlar båda samma aktie med 500 virtuella krediter och börjar med 100 HP. En vinstaffär kan användas till **Attack** för att skada motståndaren eller **Grow** för att öka kapitalet och ladda nästa attack. I Ritduell tävlar spelarna om att komma närmast nästa kursrörelse. Handelsduell går även att spela privat med en vän eller mot en bot. Ritduell har en övning för en spelare. Elo och avslutade rankade matcher sparas i SQLite lokalt eller i PostgreSQL på Render.

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

Öppna [Stock Fight på localhost](http://127.0.0.1:8080) och registrera ett konto. Välj **Spela mot bot** för en träningsmatch. För en rankad handelsduell, öppna spelet i två separata webbläsarprofiler eller på två enheter, logga in med varsitt konto och tryck **Spela rankad duell** på båda. Spelet skapar SQLite-filen i `instance/` och importerar medföljande historiska kurser automatiskt vid start. Handelsduell och rankad Ritduell lottar en aktie och en startpunkt i dess kurshistorik. Datumen visas när matchen är slut.

- Före den första botduellen kan du prova Attack och Grow på en exempelaffär. Öppna **Så spelar du** för att starta guiden igen.
- **Spela med en vän** skapar en länk till en orankad Handelsduell. Länken fungerar en gång inom 15 minuter. Värden behöver vara ansluten när gästen bekräftar. Efter matchen kan båda tacka ja till revansch inom 15 minuter. Spela från samma lokalnätsadress eller publika adress om ni använder olika enheter.
- **Spela ritduell** öppnar en separat rankad kö med egen Elo. Dra uppåt eller nedåt i det skuggade prognosfältet eller skriv din gissning i procent. Lås prognosen för att tävla om vem som kommer närmast facit.
- **Öva ritduell** går igenom tre rundor på en kurva med syntetiska priser. Lås prognosen för att se facit och din avvikelse. Gå vidare när du är redo.
- **Börsföretag** går ut på att driva en handelsfirma. Köp poster i fiktiva börsbolag, välj säljkurser och ta emot blockorder från institutioner. Planera med nästa veckas marknadsbesked och se andra spelares firmor på börslistan. Kampanjen spelas i egen takt och sparas på kontot. Äldre portföljsparningar går att öppna på `/campaign/portfolio`.

För att spela från två mobiler på samma nätverk, sätt `STOCK_FIGHT_DEV_HOST=0.0.0.0` i `.env` före start. Öppna datorns lokala IP-adress med port 8080 från båda mobilerna.

## Kör spelet med Docker Compose

1. Kopiera `.env.example` till `.env` om filen saknas.
2. Skapa vid behov ett värde med `python -c "import secrets; print(secrets.token_hex(32))"` och lägg det i `SECRET_KEY`. Sätt `INVITE_CODE` om registrering ska kräva en kod.
3. Stoppa en eventuell manuell spelserver som använder samma port och starta tjänsten från projektmappen.

```bash
docker compose up --build -d
docker compose ps
```

Öppna [Stock Fight på localhost](http://127.0.0.1:8080). På andra enheter i samma nätverk använder du datorns lokala IP-adress och porten som anges i `STOCK_FIGHT_PORT` (standard 8080).

Compose-projektet heter `stock-fight-app`. Med standardinställningen ligger konton, Elo, marknadsdata och historik i projektets namngivna SQLite-volym. `docker compose down` stoppar tjänsten och behåller volymen. Vill du ansluta Compose på din dator till Render Postgres, sätt `DATABASE_URL` i `.env` till databasens externa anslutningssträng. [Externa anslutningar till Render Postgres](https://render.com/docs/postgresql-creating-connecting#external-connections)

Gunicorn kör exakt en trådad serverprocess med WebSocket-stöd via Flask-SocketIO och simple-websocket. Aktiva matcher och kön ligger i den processen och försvinner vid omstart.

### Konfiguration

| Variabel | Funktion |
| --- | --- |
| `SECRET_KEY` | Signerar sessionskakor. Compose kräver ett värde. Lokalt skapas en tillfällig nyckel per start om värdet saknas. |
| `INVITE_CODE` | Gemensam inbjudningskod. Tomt värde öppnar registrering. |
| `STOCK_FIGHT_PORT` | Extern port. Standard 8080. |
| `STOCK_FIGHT_BIND` | Bindningsadress för Compose. Standard `0.0.0.0`. |
| `STOCK_FIGHT_DEV_HOST` | Bindningsadress för lokal utvecklingsserver. Standard `127.0.0.1`. |
| `SESSION_COOKIE_SECURE` | Standard `0` för HTTP. Använd `1` när spelarna ansluter via HTTPS. |
| `AUTO_SEED_HISTORICAL` | `1` importerar de medföljande historiska dagskurserna automatiskt. |
| `AUTO_SEED_DEMO` | `1` importerar medföljande syntetiska data automatiskt. |
| `ALLOW_SYNTHETIC` | `0` kräver en spelbar verklig serie för matcher. |
| `MARKET_TICK_SECONDS` | Sekunder per historisk stapel. Standard `3`. |
| `MATCH_PREVIEW_BARS` | Antal staplar i förhandsvisningen. Standard `12`. |
| `DATABASE_URL` | Direkt PostgreSQL-anslutning för tabellinitiering, eller SQLite-adress. Utan databasadress använder appen `sqlite:///stockfight.sqlite3` i `instance/`. |
| `DATABASE_URL_POOLED` | Valfri poolad PostgreSQL-anslutning för spelets löpande databasfrågor. |

Om du anger bara en av anslutningssträngarna används den både vid tabellinitiering och medan spelet körs.

## Publicera på Render med Render Postgres

1. Öppna din PostgreSQL-databas i Render. Välj **Connect → Internal** och kopiera hela **Internal Database URL**. [Anslut till Render Postgres](https://render.com/docs/postgresql-creating-connecting#internal-connections)
2. Öppna spelets **Web Service** eller skapa den i samma region och arbetsyta som databasen. För en ny tjänst väljer du projektets Git-repo, **Docker** och **Free**. Låt Render bygga projektets `Dockerfile` och använda dess startkommando. Ange `/healthz` som hälsokontrollens sökväg. [Renders privata nätverk](https://render.com/docs/private-network) · [Docker på Render](https://render.com/docs/docker) · [Render Health Checks](https://render.com/docs/health-checks)
3. Lägg till följande miljövariabler i Render.

   | Variabel | Värde |
   | --- | --- |
   | `DATABASE_URL` | Databasens **Internal Database URL**. |
   | `SECRET_KEY` | Ett slumpvärde som du behåller mellan driftsättningar. Skapa ett med `python -c "import secrets; print(secrets.token_hex(32))"`. |
   | `SESSION_COOKIE_SECURE` | `1` |
   | `PORT` | `8000`, samma port som Gunicorn använder i `Dockerfile`. |

   Ta bort `DATABASE_URL_POOLED` från webbtjänsten om den är satt sedan tidigare. Då används `DATABASE_URL` både vid tabellinitiering och när spelet körs.

4. Driftsätt spelet. Vid start skapar spelet tabellerna och importerar som standard de medföljande historiska kurserna och demokurserna. Registrera ett testkonto, välj **Manual Deploy → Restart service** i Render och logga sedan in med samma konto för att kontrollera att det sparats. [Starta om en Render-tjänst](https://render.com/docs/deploys#restarting-a-service)

Render kan pausa spelet vid inaktivitet, så det första besöket efter en paus kan ta längre tid. Konton, Elo, färdigspelade rankade matcher och importerade kurser ligger kvar i PostgreSQL när webbtjänsten startar om. Om databasen använder Renders gratisplan förfaller den 30 dagar efter att den skapats. Vill du ta med befintliga konton och resultat behöver du föra över dem från SQLite separat. [Render Free](https://render.com/docs/free#30-day-limit)

## Importera verkliga kurser

`data/historical_market.csv` innehåller verkliga amerikanska dagskurser från 2015–2017. Filen är ett urval ur Cam Nugents dataset *S&P 500 stock data*, publicerat under CC0. `data/demo_market.csv` innehåller syntetisk minutdata för provspel när verklig data saknas för en match. [S&P 500 stock data på Kaggle](https://www.kaggle.com/datasets/camnugent/sandp500/data)

Fler svenska och amerikanska aktier kan läggas till från en lokal kursfil. Använd data som du har rätt att använda på din server och visa för dina spelare.

Spara filen som kommaavgränsad UTF-8 med följande kolumnrubriker. `name` är valfri.

```csv
symbol,market,timestamp,open,high,low,close,volume,name
```

Använd till exempel `SE` eller `US` för marknad och ISO 8601 för tidsstämpeln. Tider utan tidszon tolkas som UTC. Priser använder punkt som decimaltecken. Ange intervallet per import, exempelvis `1m`, `5m`, `1h`, `1d` eller `1w`. En stapel spelas upp per kurstick oavsett historiskt intervall. Flaggan `--synthetic` ska användas för påhittade kurser.

En handelsduell behöver som standard **51 observationer** i en och samma serie. Det motsvarar förhandsvisningen plus tillräckligt med observationer för 115 sekunders uppspelning. Om du ändrar uppspelningshastigheten behöver varje handelsduell `MATCH_PREVIEW_BARS + ceil(115 / MARKET_TICK_SECONDS)` observationer. En rankad Ritduell behöver minst `MATCH_PREVIEW_BARS + 8` observationer. Intradagsfönster bryts vid luckor. Dagliga och veckovisa serier kan passera stängda handelsdagar, upp till det nominella intervallet plus sex kalenderdagar mellan två observationer.

Ritduellen föredrar perioder med större kursrörelser och lottar bland lämpliga startpunkter. Den kan använda var femte, var tredje eller varje stängningskurs, beroende på vilka fönster som finns. Grafen visar intervallet för de valda kurspunkterna, exempelvis `5d` för var femte dagskurs.

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
- Attackkraften börjar på 100 % och ändras med 1 procentenhet per hela 2,5 krediter som kapitalet ligger över eller under startkapitalet på 500. Den begränsas till 75–125 % och skalar hela attacken, inklusive Grow-bonusen. Kapitalet räknas som kassan plus den ursprungliga insatsen i en eventuell öppen position.
- Förhandsvisningen av Attack och Grow visar effekten vid den senast visade kursen. Servern uppdaterar effekten när en ny stapel visas. Ett väntande val återställs när spelaren ansluter igen med samma konto.
- **Market Storm** drar 2 HP per sekund från sekund 75. **Final Storm** drar 4 HP per sekund från sekund 105. En match där båda behåller full hälsa före stormen når dubbel KO vid cirka 114 sekunder. Vid samtidig KO vinner den med mest kapital, avrundat till två decimaler. Vid lika kapital avgör mest attackskada. Om även den är lika blir matchen oavgjord.
- Matchen fortsätter vid nätavbrott och kan återupptas genom att ansluta med samma konto. Ett kort avbrott ändrar varken HP eller Elo på egen hand. En öppen position vid KO räknas med till sitt investerade belopp i slutkapitalet. Högsta kapital avser det högsta realiserade handelskapitalet.
- Matchningen börjar på ±100 Elo och söker inom ±200 när båda har väntat minst 15 sekunder. Spelaren kan lämna kön när som helst före matchstart. I båda rankade lägena börjar spelaren i Bronze på 100 Elo. Det finns nio ranker från Iron till Stock Legend. Elo räknas med K = 32 och uppdateras i samma databastransaktion som resultatet och affärerna. Tidigare rating och matchhistorik visas på samma skala, 900 poäng lägre än tidigare.
- Botens svårighetsgrad utgår från spelarens aktuella Ranked-Elo vid matchstart. Boten spelar med samma regler och ser samma kursstaplar som spelaren. Botmatcher påverkar varken Elo, topplistan eller Ranked-historiken.
- En rankad Ritduell har upp till åtta rundor. Spelarna har 20 sekunder att förutsäga rörelsen till nästa punkt i grafen. Facit visas när båda låst sin prognos eller tiden gått ut. Den närmaste prognosen gör skada på motståndaren. Lika nära ger noll skada, och en ensam prognos vinner rundan. Matchen avgörs vid knockout eller av vem som har mest HP efter sista rundan.
- Resultatskärmen visar slut-HP, slutorsak och egna affärer i Handelsduell eller båda spelarnas rundresultat i Ritduell. Matchdetaljer, privata inbjudningar och pågående soloövningar ligger i serverns minne och försvinner vid omstart. En soloövning kan återupptas inom 15 minuter efter frånkoppling.

## Kod och tester

| Del | Filer |
| --- | --- |
| Flask, konton och importkommandon | `stockfight/__init__.py`, `run.py` |
| Handel, kurstick och Ranked-regler | `stockfight/engine.py` |
| Botens handelsstrategi | `stockfight/bot.py` |
| Rankad Ritduell och soloövning | `stockfight/prediction.py`, `stockfight/practice.py` |
| Socket.IO, kö och matchrum | `stockfight/multiplayer.py` |
| Databas, marknadsdata och Elo | `stockfight/data.py`, `stockfight/market_data.py`, `stockfight/ranking.py` |
| HTML, CSS, JavaScript och kursgraf | `stockfight/templates/`, `stockfight/static/` |

```bash
python -m pip install -r requirements-test.txt
python -m pytest -q
```

Testerna täcker spelregler, kursimport, konton, Elo, Ranked-matcher mellan två Socket.IO-testklienter och träningsmatcher mot boten. Lokalt paketerade webbläsarbibliotek inkluderar Socket.IO Client (MIT) och TradingView Lightweight Charts (Apache 2.0). Licenserna finns i `stockfight/static/vendor/`.
