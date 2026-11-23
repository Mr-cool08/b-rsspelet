(() => {
    "use strict";

    const section = document.getElementById("company-market");
    const copy = {
        title: ["Livebörsen", "Live exchange"],
        simulation: ["Riktiga aktiekurser · virtuellt kapital", "Real stock quotes · virtual capital"],
        loading: ["Hämtar kurser …", "Loading quotes …"],
        frequency: ["Uppdateras var {seconds}:e sekund", "Refreshes every {seconds} seconds"],
        source: ["Källa {source}", "Source {source}"],
        lastQuote: ["Kurs från {time}", "Quote from {time}"],
        marketClosed: ["Börsen stängd", "Exchange closed"],
        marketUnavailable: ["Kursdata saknas", "Quotes unavailable"],
        noQuote: ["Aktuell kurs saknas.", "No current quote."],
        noHistory: ["Kurshistorik visas när data har hämtats.", "Price history appears once quotes are available."],
        quoteWait: ["Inväntar nya kurser", "Waiting for quotes"],
        unavailable: ["Kurserna kunde inte uppdateras. Handeln öppnar när anslutningen är tillbaka.", "Quotes could not be updated. Trading resumes when the connection returns."],
        chartMissing: ["Kursgrafen går inte att visa.", "The price chart is unavailable."],
        chartDescription: ["Senaste kursrörelserna för {symbol}", "Recent price movements for {symbol}"],
        trend: ["Senaste rörelse", "Latest move"],
        chart: ["Kursgraf", "Price chart"],
        stockList: ["Välj aktie", "Select stock"],
        locked: ["Låst", "Locked"],
        locked_asset: ["Aktien låses upp när firman når en högre nivå.", "The stock unlocks when the firm reaches a higher level."],
        ticket: ["Lägg order", "Order ticket"],
        action: ["Ordertyp", "Order type"],
        buy: ["Köp · uppgång", "Buy · price rises"],
        sell: ["Sälj innehav", "Sell holding"],
        short: ["Blanka · nedgång", "Short · price falls"],
        cover: ["Täck blankning", "Cover short"],
        shortGuide: ["Säkerheten motsvarar ordervärdet. Du kan förlora den och handelsavgiften.", "Collateral equals the order value. You can lose it and the trading fee."],
        buyDone: ["Köpte {quantity} {symbol} för {price} per aktie", "Bought {quantity} {symbol} at {price} per share"],
        sellDone: ["Sålde {quantity} {symbol} för {price} per aktie", "Sold {quantity} {symbol} at {price} per share"],
        shortDone: ["Blankade {quantity} {symbol} för {price} per aktie", "Shorted {quantity} {symbol} at {price} per share"],
        coverDone: ["Täckte {quantity} {symbol} för {price} per aktie", "Covered {quantity} {symbol} at {price} per share"],
        quantity: ["Antal aktier", "Number of shares"],
        max: ["Max {count}", "Max {count}"],
        order: ["Genomför order", "Place order"],
        available: ["Kassa över reserv", "Cash above reserve"],
        equity: ["Värde inkl. börspositioner", "Value incl. market positions"],
        paperProfit: ["Orealiserat resultat", "Unrealised P/L"],
        fees: ["Totala avgifter", "Total fees"],
        positions: ["Egna positioner", "Own positions"],
        noPositions: ["Köp inför uppgång eller blanka inför nedgång för att öppna en position.", "Buy if you expect a rise or short if you expect a fall to open a position."],
        symbol: ["Aktie", "Stock"],
        direction: ["Riktning", "Direction"],
        long: ["Uppgång", "Long"],
        shortDirection: ["Nedgång", "Short"],
        average: ["Snittkurs", "Average price"],
        return: ["Resultat", "P/L"],
        botPositions: ["Handelsbotar", "Trading bots"],
        botName: ["Handlare", "Trader"],
        botPosition: ["Position", "Position"],
        botFill: ["Senaste affär", "Latest trade"],
        botPositionInfo: ["{direction} · {quantity} {symbol}", "{direction} · {quantity} {symbol}"],
        botWaiting: ["Söker signal", "Waiting for a signal"],
        botPaused: ["Pausad", "Paused"],
        signal: ["Handelssignal", "Signal"],
        stop_loss: ["Stop-loss", "Stop-loss"],
        take_profit: ["Vinstmål", "Take profit"],
        stale_quote: ["Kursen hann ändras. Kontrollera den nya kursen och lägg ordern igen.", "The quote changed. Check the latest price and place your order again."],
        stale_revision: ["Firman har uppdaterats. Kontrollera saldot och lägg ordern igen.", "Your firm was updated. Check its balance and place your order again."],
        insufficient_cash: ["Kassan räcker inte till ordern och firmans reserv.", "There is not enough cash for this order and the firm’s reserve."],
        insufficient_shares: ["Positionen innehåller för få aktier för ordern.", "The position has too few shares for this order."],
        position_conflict: ["Stäng den befintliga positionen innan du byter riktning.", "Close the existing position before switching direction."],
        position_limit: ["Ordern överskrider firmans gräns för antal aktier.", "The order exceeds the firm’s share limit."],
        invalid_quantity: ["Ange ett giltigt helt antal aktier.", "Enter a valid whole number of shares."],
        market_unavailable: ["En aktuell handelskurs saknas. Lägg ordern när handeln öppnar igen.", "There is no current tradeable quote. Place the order once trading resumes."],
        commandError: ["Ordern kunde inte genomföras.", "The order could not be placed."],
    };
    const sides = ["buy", "sell", "short", "cover"];
    const locale = () => window.StockFightI18n?.getLocale() ?? "sv-SE";
    const english = () => locale().startsWith("en");
    const escape = (value) => String(value).replace(/[&<>"']/g, (character) => ({
        "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
    })[character]);
    const text = (key, values = {}) => copy[key][Number(english())]
        .replace(/\{(\w+)\}/g, (placeholder, name) => values[name] ?? placeholder);
    const tx = (key, values) => escape(text(key, values));
    const format = (value, options) => new Intl.NumberFormat(locale(), options).format(value);
    const money = (value, signed = false) => format(value, {
        maximumFractionDigits: 2, signDisplay: signed ? "exceptZero" : "auto",
    }) + (english() ? " cr" : " kred.");
    const price = (value) => value == null ? "–" : format(value, { style: "currency", currency: "USD", maximumFractionDigits: 2 });
    const percent = (value) => value == null ? "–" : format(value / 100, { style: "percent", maximumFractionDigits: 2, signDisplay: "exceptZero" });
    const tone = (value) => value < 0 ? "company-negative" : value > 0 ? "company-positive" : "";
    const stockName = (asset) => asset.name[english() ? "en" : "sv"];
    const selectedAsset = () => market?.assets.find(({ symbol }) => symbol === selected);
    const byId = (id) => document.getElementById(`company-market-${id}`);

    let market;
    let revision;
    let selected;
    let side = "buy";
    let quantity = "1";
    let pending = false;
    let failed = false;
    let fetching = false;
    let refreshQueued = false;
    let error;
    let timer;
    let mountedLanguage;
    let chart;
    let series;
    let chartKey;

    function mount() {
        if (mountedLanguage === locale()) return;
        mountedLanguage = locale();
        chart?.remove();
        chart = series = chartKey = undefined;
        section.innerHTML = `<div class="company-market-heading">
            <div><h2 id="company-market-title">${tx("title")}</h2><p class="company-muted" id="company-market-source">${tx("simulation")}</p></div>
            <span id="company-market-status" class="company-market-status"></span>
        </div>
        <p class="company-market-warning" id="company-market-error" role="status" hidden></p>
        <div id="company-market-data" hidden>
            <div id="company-market-assets" class="company-market-assets" role="group" aria-label="${tx("stockList")}"></div>
            <div class="company-market-terminal">
                <div class="company-market-chart-panel">
                    <div id="company-market-quote" class="company-market-quote"></div>
                    <div id="company-market-chart" class="company-market-chart" role="img" aria-label="${tx("chart")}"></div>
                    <p id="company-market-chart-empty" class="company-market-chart company-muted" hidden></p>
                </div>
                <form class="company-order" id="company-market-order" aria-labelledby="company-market-order-title">
                    <h3 id="company-market-order-title">${tx("ticket")}</h3>
                    <label for="company-market-side">${tx("action")}</label>
                    <select id="company-market-side" class="company-field" name="side">${sides.map((value) => `<option value="${value}">${tx(value)}</option>`).join("")}</select>
                    <div class="company-order-label"><label for="company-market-quantity">${tx("quantity")}</label><span id="company-market-limit"></span></div>
                    <input id="company-market-quantity" class="company-field" name="quantity" type="number" min="1" step="1" inputmode="numeric" aria-describedby="company-market-limit" required>
                    <div class="company-order-total" id="company-market-order-total"></div>
                    <p id="company-market-order-help" class="company-muted company-order-help" hidden>${tx("shortGuide")}</p>
                    <button type="submit" id="company-market-submit" class="button button-primary">${tx("order")}</button>
                </form>
            </div>
            <p id="company-market-fill" class="company-market-fill" role="status" hidden></p>
            <div id="company-market-balances"></div>
            <div id="company-market-positions" class="company-market-positions"></div>
            <div id="company-market-bots" class="company-market-bots" hidden></div>
        </div>`;
        byId("side").value = side;
        byId("quantity").value = quantity;
    }

    function paintAssets() {
        byId("assets").innerHTML = market.assets.map((asset) => {
            const movement = percent(asset.changePercent);
            return `<button type="button" class="company-market-asset" id="company-market-asset-${escape(asset.symbol)}"
                data-stock="${escape(asset.symbol)}" aria-pressed="${asset.symbol === selected}" aria-label="${escape(`${asset.symbol} ${stockName(asset)}`)}">
                <strong>${escape(asset.symbol)}</strong><span class="${asset.unlocked ? tone(asset.changePercent) : ""}">${asset.unlocked ? movement : tx("locked")}</span>
            </button>`;
        }).join("");
    }

    function paintChart(asset) {
        const container = byId("chart");
        const library = window.LightweightCharts;
        const empty = byId("chart-empty");
        container.hidden = !asset.history.length || !library;
        empty.hidden = !container.hidden;
        if (container.hidden) {
            empty.textContent = text(library ? "noHistory" : "chartMissing");
            return;
        }
        container.setAttribute("aria-label", text("chartDescription", { symbol: asset.symbol }));
        if (!chart) {
            chart = library.createChart(container, {
                autoSize: true,
                layout: { background: { color: "#101b23" }, textColor: "#b3c2c9", attributionLogo: false },
                grid: { vertLines: { color: "#23343f" }, horzLines: { color: "#23343f" } },
                rightPriceScale: { borderColor: "#344851" },
                localization: { locale: locale(), priceFormatter: price },
                timeScale: { borderColor: "#344851", timeVisible: true, secondsVisible: true },
                handleScroll: false,
                handleScale: false,
            });
            series = chart.addSeries(library.AreaSeries, { lineWidth: 2, lastValueVisible: false, priceLineVisible: false });
        }
        const key = `${asset.symbol}:${market.tick}`;
        if (chartKey === key) return;
        chartKey = key;
        const negative = asset.changePercent < 0;
        series.applyOptions({
            lineColor: negative ? "#ffa7a7" : "#9af0c8",
            topColor: negative ? "rgba(255, 167, 167, .28)" : "rgba(154, 240, 200, .32)",
            bottomColor: "rgba(16, 27, 35, .05)",
        });
        series.setData(asset.history.map(({ time, price }) => ({ time, value: price })));
        chart.timeScale().fitContent();
    }

    function paintTicket(asset) {
        const max = asset.maxOrder[side];
        const orderQuantity = byId("quantity").valueAsNumber;
        const cannotEdit = pending || !asset.unlocked;
        const disabled = cannotEdit || failed || !asset.tradable || market.status !== "open" || market.revision !== revision;
        byId("side").disabled = cannotEdit;
        byId("quantity").disabled = cannotEdit;
        byId("quantity").max = Math.max(1, max);
        byId("limit").textContent = text("max", { count: format(max) });
        const orderTotal = `${price(asset.price)} × ${format(Number.isInteger(orderQuantity) && orderQuantity > 0 ? orderQuantity : 0)}`;
        byId("order-total").textContent = !asset.unlocked ? text("locked_asset") : asset.price == null ? text("noQuote") : orderTotal;
        byId("order-help").hidden = side !== "short" || !asset.unlocked;
        byId("submit").disabled = disabled || !Number.isInteger(orderQuantity) || orderQuantity < 1 || orderQuantity > max;
    }

    function paintBalances() {
        const items = [
            ["available", market.availableCash, false],
            ["equity", market.equity, false], ["paperProfit", market.unrealizedProfit, true], ["fees", market.fees, false],
        ];
        byId("balances").innerHTML = `<dl class="company-market-balances">${items.map(([label, value, signed]) =>
            `<div><dt>${tx(label)}</dt><dd class="${signed ? tone(value) : ""}">${money(value, signed)}</dd></div>`).join("")}</dl>`;
    }

    function paintPositions() {
        const positions = market.assets.filter(({ position }) => position);
        const headings = ["symbol", "direction", "quantity", "average", "return"];
        byId("positions").innerHTML = `<h3 id="company-market-positions-title">${tx("positions")}</h3>${positions.length
            ? `<div class="company-table-scroll"><table class="company-data-table" aria-labelledby="company-market-positions-title">
                <thead><tr>${headings.map((heading) => `<th scope="col">${tx(heading)}</th>`).join("")}</tr></thead>
                <tbody>${positions.map(({ symbol, position }) => `<tr><th scope="row">${escape(symbol)}</th>
                    <td>${tx(position.side === "long" ? "long" : "shortDirection")}</td>
                    <td>${format(position.quantity)}</td><td>${price(position.averagePrice)}</td>
                    <td class="${tone(position.unrealizedProfit)}"><strong>${money(position.unrealizedProfit, true)}</strong></td>
                </tr>`).join("")}</tbody></table></div>` : `<p class="company-muted">${tx("noPositions")}</p>`}`;
    }

    function fillText(trade) {
        const outcome = trade.profit == null ? "" : ` · ${money(trade.profit, true)}`;
        return text(`${trade.side}Done`, {
            quantity: format(trade.quantity), symbol: trade.symbol, price: price(trade.price),
        }) + outcome;
    }

    function paintBots() {
        const bots = market.bots ?? [];
        const container = byId("bots");
        container.hidden = !bots.length;
        if (!bots.length) return;
        const headings = ["botName", "botPosition", "botFill"];
        container.innerHTML = `<h3 id="company-market-bots-title">${tx("botPositions")}</h3>
            <div class="company-table-scroll"><table class="company-data-table" aria-labelledby="company-market-bots-title">
                <thead><tr>${headings.map((heading) => `<th scope="col">${tx(heading)}</th>`).join("")}</tr></thead>
                <tbody>${bots.map(({ name, active, position, lastTrade }) => {
                    const positionInfo = position ? tx("botPositionInfo", {
                        symbol: position.symbol, direction: text(position.side === "short" ? "shortDirection" : "long"), quantity: format(position.quantity),
                    }) + (position.unrealizedProfit == null ? "" : ` · ${money(position.unrealizedProfit, true)}`) : tx(active ? "botWaiting" : "botPaused");
                    const lastFill = lastTrade ? `${escape(fillText(lastTrade))}${copy[lastTrade.reason] ? ` <small>${tx(lastTrade.reason)}</small>` : ""}` : "–";
                    return `<tr><th scope="row">${escape(name)}</th><td class="company-text-cell">${positionInfo}</td>
                        <td class="company-text-cell">${lastFill}</td></tr>`;
                }).join("")}</tbody>
            </table></div>`;
    }

    function paintFeedback() {
        const warning = byId("error");
        warning.hidden = !error && !failed;
        const message = error ? (Object.hasOwn(copy, error) ? error : "commandError") : "unavailable";
        const warningText = warning.hidden ? "" : text(message);
        if (warning.textContent !== warningText) warning.textContent = warningText;
        const { lastTrade } = market ?? {};
        const fill = byId("fill");
        fill.hidden = !lastTrade;
        if (!lastTrade) return;
        const feedback = fillText(lastTrade);
        if (fill.textContent !== feedback) fill.textContent = feedback;
    }

    function render() {
        const focusId = section.contains(document.activeElement) ? document.activeElement.id : null;
        mount();
        const status = byId("status");
        const marketStatus = { closed: "marketClosed", open: "frequency", unavailable: "marketUnavailable" };
        status.classList.toggle("company-market-connected", market?.status === "open" && !failed);
        status.textContent = failed ? text("quoteWait") : market ? text(marketStatus[market.status] ?? "marketUnavailable", { seconds: market.tickSeconds }) : text("loading");
        byId("source").textContent = text("simulation") + (market?.source ? ` · ${text("source", { source: market.source })}` : "");
        byId("data").hidden = !market;
        paintFeedback();
        if (!market) return;
        selected ||= market.assets.find(({ unlocked }) => unlocked)?.symbol ?? market.assets[0].symbol;
        const asset = selectedAsset();
        const time = asset.quotedAt == null ? null : new Intl.DateTimeFormat(locale(), {
            day: "numeric", month: "short", hour: "2-digit", minute: "2-digit", second: "2-digit", timeZoneName: "short",
        }).format(new Date(asset.quotedAt * 1000));
        byId("quote").innerHTML = `<div><h3>${escape(stockName(asset))}</h3><strong>${price(asset.price)}</strong>
            ${time ? `<span class="company-muted">${tx("lastQuote", { time })}</span>` : ""}</div>
            <div><span class="company-muted">${tx("trend")}</span><strong class="${tone(asset.changePercent)}">${percent(asset.changePercent)}</strong></div>`;
        paintAssets();
        paintChart(asset);
        paintTicket(asset);
        paintBalances();
        paintPositions();
        paintBots();
        if (focusId && document.activeElement.id !== focusId) document.getElementById(focusId)?.focus({ preventScroll: true });
    }

    function schedule(delay) {
        window.clearTimeout(timer);
        if (document.visibilityState === "visible") timer = window.setTimeout(refresh, delay);
    }

    async function refresh() {
        if (revision === undefined || document.visibilityState !== "visible") return;
        if (fetching) {
            refreshQueued = true;
            return;
        }
        fetching = true;
        let delay = 5000;
        try {
            const response = await fetch("/api/company/market");
            if (!response.ok) throw new Error("market");
            const latest = await response.json();
            if (latest.revision >= revision && (!market || latest.tick >= market.tick)) market = latest;
            failed = false;
            if (market?.revision > revision) window.dispatchEvent(new Event("company:refresh"));
            const untilNextTick = Math.max(250, (latest.nextTickAt - latest.serverTime) * 1000 + 200);
            delay = latest.awaitingTick ? Math.min(1000, untilNextTick) : untilNextTick;
        } catch {
            failed = true;
        } finally {
            fetching = false;
            render();
            schedule(refreshQueued ? 0 : delay);
            refreshQueued = false;
        }
    }

    section.addEventListener("click", (event) => {
        const button = event.target.closest("button[data-stock]");
        if (!button || selected === button.dataset.stock) return;
        selected = button.dataset.stock;
        side = selectedAsset().position?.side === "short" ? "cover" : "buy";
        quantity = "1";
        byId("side").value = side;
        byId("quantity").value = quantity;
        error = undefined;
        render();
    });
    section.addEventListener("change", (event) => {
        if (event.target === byId("side")) {
            side = event.target.value;
            paintTicket(selectedAsset());
        }
    });
    section.addEventListener("input", (event) => {
        if (event.target === byId("quantity")) {
            quantity = event.target.value;
            paintTicket(selectedAsset());
        }
    });
    section.addEventListener("submit", (event) => {
        event.preventDefault();
        if (byId("submit").disabled) return;
        error = undefined;
        window.dispatchEvent(new CustomEvent("company:market-command", {
            detail: { action: "market_trade", symbol: selected, side, quantity: byId("quantity").valueAsNumber, tick: market.tick },
        }));
    });
    window.addEventListener("company:updated", ({ detail }) => {
        revision = detail.revision;
        if (detail.market && (!market || detail.market.tick >= market.tick)) {
            market = detail.market;
            failed = false;
        }
        render();
        if (market?.revision !== revision) refresh();
    });
    window.addEventListener("company:busy", ({ detail }) => {
        pending = detail;
        if (market) paintTicket(selectedAsset());
    });
    window.addEventListener("company:command-error", ({ detail }) => {
        if (detail.action !== "market_trade") return;
        error = detail.error;
        paintFeedback();
        refresh();
    });
    window.addEventListener("stockfight:languagechange", render);
    document.addEventListener("visibilitychange", () => {
        window.clearTimeout(timer);
        refresh();
    });
    render();
})();
