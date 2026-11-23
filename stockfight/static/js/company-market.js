(() => {
    "use strict";

    const section = document.getElementById("company-market");
    const copy = {
        title: ["Aktiemarknad", "Stock market"],
        simulation: ["Riktiga aktiekurser · virtuellt kapital", "Real stock quotes · virtual capital"],
        previousSession: ["Riktiga kurser från föregående handelsdag · virtuellt kapital", "Real quotes from the previous trading session · virtual capital"],
        replayTime: ["Spelar upp {time}", "Replaying {time}"],
        loading: ["Hämtar kurser …", "Loading quotes …"],
        live: ["Öppen", "Open"],
        replay: ["Uppspelning", "Replay"],
        quoteDetails: ["Kurskälla", "Quote source"],
        frequency: ["Uppdateras var {seconds}:e sekund", "Refreshes every {seconds} seconds"],
        source: ["Källa {source}", "Source {source}"],
        sweden: ["Sverige", "Sweden"],
        unitedStates: ["USA", "United States"],
        lastQuote: ["Kurs från {time}", "Quote from {time}"],
        marketClosed: ["Börsen stängd", "Exchange closed"],
        marketUnavailable: ["Kursdata saknas", "Quotes unavailable"],
        noHistory: ["Ingen kurshistorik än", "No price history yet"],
        quoteWait: ["Inväntar nya kurser", "Waiting for quotes"],
        unavailable: ["Anslutningen försvann. Väntar på kurser.", "Connection lost. Waiting for quotes."],
        chartMissing: ["Kursgrafen går inte att visa.", "The price chart is unavailable."],
        chartDescription: ["Senaste kursrörelserna för {symbol}", "Recent price movements for {symbol}"],
        replayChartDescription: ["Historiska kursrörelser för {symbol} under uppspelningen", "Historical price movements for {symbol} during replay"],
        trend: ["Senaste rörelse", "Latest move"],
        chart: ["Kursgraf", "Price chart"],
        stockList: ["Välj aktie", "Select stock"],
        locked: ["Låst", "Locked"],
        locked_asset: ["Låses upp på en högre nivå", "Unlocks at a higher level"],
        ticket: ["Lägg order", "Order ticket"],
        orderJump: ["Order", "Order"],
        orderJumpLabel: ["Gå till orderformuläret", "Go to order form"],
        action: ["Ordertyp", "Order type"],
        buy: ["Köp", "Buy"],
        sell: ["Sälj", "Sell"],
        short: ["Blanka", "Short"],
        cover: ["Täck blankning", "Cover short"],
        shortGuide: ["Ordervärdet binds som säkerhet och kan förloras med avgiften.", "The order value is held as collateral and can be lost with the fee."],
        buyDone: ["Köpte {quantity} {symbol} à {price}", "Bought {quantity} {symbol} at {price} each"],
        sellDone: ["Sålde {quantity} {symbol} à {price}", "Sold {quantity} {symbol} at {price} each"],
        shortDone: ["Blankade {quantity} {symbol} à {price}", "Shorted {quantity} {symbol} at {price} each"],
        coverDone: ["Täckte {quantity} {symbol} à {price}", "Covered {quantity} {symbol} at {price} each"],
        quantity: ["Antal", "Shares"],
        fewer: ["Minska antal", "Fewer shares"],
        more: ["Öka antal", "More shares"],
        max: ["Max {count}", "Max {count}"],
        orderValue: ["Ordervärde", "Order value"],
        available: ["Handelskassa", "Trading cash"],
        equity: ["Totalt värde", "Total equity"],
        paperProfit: ["Orealiserat resultat", "Unrealised P/L"],
        fees: ["Avgifter", "Fees"],
        positions: ["Mina positioner", "My positions"],
        noPositions: ["Inga öppna positioner", "No open positions"],
        symbol: ["Aktie", "Stock"],
        direction: ["Riktning", "Direction"],
        long: ["Uppgång", "Long"],
        shortDirection: ["Nedgång", "Short"],
        average: ["Snittkurs", "Average price"],
        return: ["Resultat", "P/L"],
        botPositions: ["Botarnas affärer", "Bot trades"],
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
        market_closed: ["Börsen är stängd.", "The exchange is closed."],
        market_unavailable: ["Väntar på en aktuell handelskurs.", "Waiting for a current quote."],
        commandError: ["Ordern kunde inte genomföras.", "The order could not be placed."],
    };
    const sideIcons = { buy: "↗", sell: "✓", short: "↘", cover: "✓" };
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
    const price = (value, currency = "USD") => value == null ? "–" : format(value, { style: "currency", currency, maximumFractionDigits: 2 });
    const percent = (value) => value == null ? "–" : format(value / 100, { style: "percent", maximumFractionDigits: 2, signDisplay: "exceptZero" });
    const formatTime = (value) => new Intl.DateTimeFormat(locale(), {
        year: "numeric", month: "short", day: "numeric", hour: "2-digit", minute: "2-digit", second: "2-digit", timeZoneName: "short",
    }).format(new Date(value * 1000));
    const tone = (value) => value < 0 ? "company-negative" : value > 0 ? "company-positive" : "";
    const stockName = (asset) => asset.name[english() ? "en" : "sv"];
    const selectedAsset = () => market?.assets.find(({ symbol }) => symbol === selected);
    const marketName = (asset) => asset?.market === "SE" ? text("sweden") : asset?.market === "US" ? text("unitedStates") : "";
    const tradingStatus = (asset) => asset?.marketStatus ?? market?.status;
    const byId = (id) => document.getElementById(`company-market-${id}`);

    let market;
    let revision;
    let selected;
    let manuallySelected = false;
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
        const showSource = byId("quote-details")?.open;
        const showBots = byId("bots")?.open;
        chart?.remove();
        chart = series = chartKey = undefined;
        section.innerHTML = `<div class="company-market-heading">
            <h2 id="company-market-title">${tx("title")}</h2>
            <span id="company-market-status" class="company-market-status"></span>
            <button id="company-market-order-jump" class="company-order-jump" type="button" aria-label="${tx("orderJumpLabel")}" aria-controls="company-market-order" hidden>
                ${tx("orderJump")} <span aria-hidden="true">↓</span>
            </button>
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
                    <h3 id="company-market-order-title" tabindex="-1">${tx("ticket")}</h3>
                    <fieldset id="company-market-sides" class="company-order-sides">
                        <legend class="sr-only">${tx("action")}</legend>
                        ${Object.entries(sideIcons).map(([value, icon]) => `<label class="company-order-option company-side-${value}" hidden>
                            <input type="radio" class="sr-only" id="company-market-side-${value}" name="side" value="${value}">
                            <span><b aria-hidden="true">${icon}</b>${tx(value)}</span>
                        </label>`).join("")}
                    </fieldset>
                    <div class="company-order-label"><label for="company-market-quantity">${tx("quantity")}</label><span id="company-market-limit"></span></div>
                    <div class="company-order-stepper">
                        <button id="company-market-fewer" type="button" data-step="-1" aria-label="${tx("fewer")}">−</button>
                        <input id="company-market-quantity" class="company-field" name="quantity" type="number" min="1" step="1" inputmode="numeric" aria-describedby="company-market-limit company-market-order-total" required>
                        <button id="company-market-more" type="button" data-step="1" aria-label="${tx("more")}">+</button>
                    </div>
                    <dl class="company-order-total"><dt>${tx("orderValue")}</dt><dd id="company-market-order-total"></dd></dl>
                    <p id="company-market-order-help" class="company-muted company-order-help" hidden>${tx("shortGuide")}</p>
                    <button type="submit" id="company-market-submit" class="button button-primary"></button>
                    <p id="company-market-order-blocked" class="company-muted company-order-help" hidden></p>
                </form>
            </div>
            <p id="company-market-fill" class="company-market-fill" role="status" hidden></p>
            <div id="company-market-balances"></div>
            <div id="company-market-positions" class="company-market-positions"></div>
            <details id="company-market-bots" class="company-details"${showBots ? " open" : ""} hidden>
                <summary id="company-market-bots-title">${tx("botPositions")}</summary>
                <div id="company-market-bot-rows"></div>
            </details>
        </div>
        <details id="company-market-quote-details" class="company-details"${showSource ? " open" : ""}>
            <summary>${tx("quoteDetails")}</summary>
            <p class="company-muted" id="company-market-source">${tx("simulation")}</p>
        </details>`;
        byId("quantity").value = quantity;
    }

    function paintAssets() {
        byId("assets").innerHTML = market.assets.map((asset) => {
            const movement = asset.unlocked ? percent(asset.price == null ? null : asset.changePercent) : text("locked");
            const details = [asset.market === "US" ? "USA" : asset.market, movement].filter(Boolean).join(" · ");
            const label = [`${asset.symbol} ${stockName(asset)}`, marketName(asset), movement].filter(Boolean).join(", ");
            return `<button type="button" class="company-market-asset" id="company-market-asset-${escape(asset.symbol)}"
                data-stock="${escape(asset.symbol)}" aria-pressed="${asset.symbol === selected}" aria-label="${escape(label)}">
                <strong>${escape(asset.symbol)}</strong><span class="${asset.unlocked ? tone(asset.changePercent) : ""}">${escape(details)}</span>
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
        const description = market.mode === "previous_session" ? "replayChartDescription" : "chartDescription";
        container.setAttribute("aria-label", text(description, { symbol: asset.symbol }));
        if (!chart) {
            chart = library.createChart(container, {
                autoSize: true,
                layout: { background: { color: "#101b23" }, textColor: "#b3c2c9", attributionLogo: false },
                grid: { vertLines: { color: "#23343f" }, horzLines: { color: "#23343f" } },
                rightPriceScale: { borderColor: "#344851" },
                localization: { locale: locale(), priceFormatter: (value) => price(value, selectedAsset()?.currency) },
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
        const position = asset.position?.side;
        const allowed = position === "long" ? ["buy", "sell"] : position === "short" ? ["short", "cover"] : ["buy", "short"];
        if (!allowed.includes(side)) side = position === "short" ? "cover" : "buy";
        const max = asset.maxOrder[side];
        const orderQuantity = byId("quantity").valueAsNumber;
        const status = tradingStatus(asset);
        let blocked;
        if (!asset.unlocked) blocked = "locked_asset";
        else if (status === "closed") blocked = "market_closed";
        else if (failed || !asset.tradable || status !== "open") blocked = "market_unavailable";
        const cannotEdit = pending || Boolean(blocked);
        for (const input of byId("sides").querySelectorAll("input")) {
            input.closest("label").hidden = !allowed.includes(input.value);
            input.disabled = cannotEdit || !allowed.includes(input.value);
            input.checked = input.value === side;
        }
        byId("quantity").disabled = cannotEdit;
        byId("quantity").max = Math.max(1, max);
        byId("fewer").disabled = cannotEdit || max === 0 || !(orderQuantity > 1);
        byId("more").disabled = cannotEdit || max === 0 || orderQuantity >= max;
        byId("limit").textContent = blocked ? "" : text("max", { count: format(max) });
        const validQuantity = Number.isInteger(orderQuantity) && orderQuantity > 0;
        const estimated = validQuantity && !blocked;
        byId("order-total").textContent = estimated
            ? (Number.isFinite(asset.orderPrice) ? money(asset.orderPrice * orderQuantity) : price(asset.price * orderQuantity, asset.currency))
            : "–";
        byId("order-help").hidden = side !== "short" || Boolean(blocked);
        const submit = byId("submit");
        submit.textContent = `${text(side)} ${asset.symbol}`;
        submit.disabled = cannotEdit || market.revision !== revision || !validQuantity || orderQuantity > max;
        const reason = byId("order-blocked");
        reason.hidden = !blocked;
        reason.textContent = blocked ? text(blocked) : "";
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
                    <td>${format(position.quantity)}</td><td>${money(position.averagePrice)}</td>
                    <td class="${tone(position.unrealizedProfit)}"><strong>${money(position.unrealizedProfit, true)}</strong></td>
                </tr>`).join("")}</tbody></table></div>` : `<p class="company-muted">${tx("noPositions")}</p>`}`;
    }

    function fillText(trade) {
        const outcome = trade.profit == null ? "" : ` · ${money(trade.profit, true)}`;
        const fillPrice = trade.quotedPrice == null ? money(trade.price) : price(trade.quotedPrice, trade.currency);
        return text(`${trade.side}Done`, {
            quantity: format(trade.quantity), symbol: trade.symbol, price: fillPrice,
        }) + outcome;
    }

    function paintBots() {
        const bots = market.bots ?? [];
        byId("bots").hidden = !bots.length;
        if (!bots.length) return;
        const headings = ["botName", "botPosition", "botFill"];
        byId("bot-rows").innerHTML = `<div class="company-table-scroll"><table class="company-data-table" aria-labelledby="company-market-bots-title">
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
        if (market && !manuallySelected && !selectedAsset()?.source && selectedAsset()?.price == null) {
            const preferred = market.assets.find(({ unlocked, tradable }) => unlocked && tradable);
            const sourced = market.assets.find(({ unlocked, source }) => unlocked && source);
            selected = preferred?.symbol ?? sourced?.symbol ?? selected ?? market.assets.find(({ unlocked }) => unlocked)?.symbol;
        }
        const asset = selectedAsset();
        const status = byId("status");
        const replay = market?.mode === "previous_session";
        const marketStatus = { closed: "marketClosed", open: replay ? "replay" : "live", unavailable: "marketUnavailable" };
        const selectedStatus = tradingStatus(asset);
        status.classList.toggle("company-market-connected", selectedStatus === "open" && !failed);
        status.textContent = failed ? text("quoteWait") : market ? text(marketStatus[selectedStatus] ?? "marketUnavailable") : text("loading");
        const replayAt = asset?.market ? asset.replayAt : market?.replayAt;
        const source = asset?.market ? asset.source : market?.source;
        const sourceDetails = [text(replay ? "previousSession" : "simulation")];
        if (replay && Number.isFinite(replayAt)) sourceDetails.push(text("replayTime", { time: formatTime(replayAt) }));
        if (source) sourceDetails.push(text("source", { source }));
        if (selectedStatus === "open") sourceDetails.push(text("frequency", { seconds: market.tickSeconds }));
        byId("source").textContent = sourceDetails.join(" · ");
        byId("data").hidden = !asset;
        byId("order-jump").hidden = !asset;
        paintFeedback();
        if (!asset) return;
        const time = Number.isFinite(asset.quotedAt) ? formatTime(asset.quotedAt) : null;
        byId("quote").innerHTML = `<div><h3>${escape(stockName(asset))}</h3><strong>${price(asset.price, asset.currency)}</strong>
            ${time ? `<span class="company-muted">${tx("lastQuote", { time })}</span>` : ""}</div>
            <strong class="company-market-move ${tone(asset.changePercent)}"><span class="sr-only">${tx("trend")} </span>${percent(asset.price == null ? null : asset.changePercent)}</strong>`;
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
        if (event.target.closest("#company-market-order-jump")) {
            byId("order").scrollIntoView({ block: "start" });
            byId("order-title").focus({ preventScroll: true });
            return;
        }
        const stepper = event.target.closest("button[data-step]");
        if (stepper && !stepper.disabled) {
            const asset = selectedAsset();
            const current = Math.trunc(byId("quantity").valueAsNumber || 0);
            quantity = String(Math.max(1, Math.min(asset.maxOrder[side], current + Number(stepper.dataset.step))));
            byId("quantity").value = quantity;
            paintTicket(asset);
            return;
        }
        const button = event.target.closest("button[data-stock]");
        if (!button) return;
        manuallySelected = true;
        if (selected === button.dataset.stock) return;
        selected = button.dataset.stock;
        side = selectedAsset().position?.side === "short" ? "cover" : "buy";
        quantity = "1";
        byId("quantity").value = quantity;
        error = undefined;
        render();
    });
    section.addEventListener("change", (event) => {
        if (event.target.name === "side") {
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
        manuallySelected = true;
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
        const asset = selectedAsset();
        if (asset) paintTicket(asset);
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
