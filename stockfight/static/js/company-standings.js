(() => {
    "use strict";

    const section = document.getElementById("company-standings");
    if (!section) return;
    section.setAttribute("aria-labelledby", "company-standings-title");

    const copy = {
        title: ["Spelarbörs", "Player exchange"],
        live: ["Live", "Live"],
        refreshing: ["Uppdateras", "Refreshing"],
        loading: ["Hämtar börskurser …", "Loading share prices …"],
        empty: ["Inga listade firmor", "No listed firms"],
        noMatches: ["Inga träffar", "No matches"],
        searchLabel: ["Spelarnamn", "Player name"],
        search: ["Sök", "Search"],
        clearSearch: ["Rensa sökning", "Clear search"],
        pages: ["Sidor med handelsfirmor", "Trading firm pages"],
        previous: ["Föregående", "Previous"],
        next: ["Nästa", "Next"],
        page: ["Sida {page}", "Page {page}"],
        error: ["Marknaden kunde inte uppdateras just nu.", "The market could not be refreshed."],
        firm: ["Firma", "Firm"],
        price: ["Kurs", "Price"],
        level: ["Nivå", "Level"],
        profit: ["Resultat", "Profit"],
        held: ["Äger", "Owned"],
        trade: ["Handel", "Trade"],
        own: ["Din firma", "Your firm"],
        buy: ["Köp 1", "Buy 1"],
        sell: ["Sälj 1", "Sell 1"],
        tradeFirm: ["{action} aktie i {firm}", "{action} share in {firm}"],
        holdingsValue: ["Innehavsvärde", "Holdings value"],
        reserve: ["Kassareserv", "Cash reserve"],
        stale_quote: ["Kursen hann ändras. Kontrollera den nya kursen innan du försöker igen.",
            "The quote changed. Check the new price before trying again."],
        stale_revision: ["Firmans saldo har uppdaterats. Kontrollera dina innehav och försök igen.",
            "Your firm's balance changed. Check your holdings before trying again."],
        insufficient_cash: ["Kassan räcker inte till köpet och rörelsereserven.", "There is not enough cash for the purchase and operating reserve."],
        insufficient_shares: ["Du har inga aktier att sälja i den firman.", "You have no shares to sell in that firm."],
        invalid_firm: ["Den firman finns inte på börsen längre.", "That firm is no longer on the exchange."],
        self_trade: ["Du kan handla aktier i andra spelares firmor.", "You can trade shares in other players' firms."],
        commandError: ["Affären kunde inte genomföras.", "The trade could not be completed."],
    };
    const locale = () => window.StockFightI18n?.getLocale() ?? "sv-SE";
    const text = (key, values = {}) => copy[key][locale() === "en-GB" ? 1 : 0]
        .replace(/\{(\w+)\}/g, (placeholder, name) => values[name] ?? placeholder);
    const escape = (value) => String(value).replace(/[&<>"']/g, (character) => ({
        "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
    })[character]);

    section.innerHTML = `<header class="company-standings-heading"></header>
        <form class="company-exchange-search" role="search" aria-labelledby="company-standings-title">
            <div><label for="company-exchange-name" class="sr-only"></label><input class="company-field" id="company-exchange-name" type="search" maxlength="24"></div>
            <button type="submit" class="button button-secondary company-exchange-button"></button>
            <button type="button" class="button button-secondary company-exchange-button" data-clear-search hidden><span aria-hidden="true">×</span></button>
        </form>
        <nav class="company-exchange-pages" hidden>
            <button type="button" data-page-change="-1" class="button button-secondary company-exchange-button"></button>
            <span role="status"></span>
            <button type="button" data-page-change="1" class="button button-secondary company-exchange-button"></button>
        </nav>
        <div class="company-exchange-results"></div>`;
    const heading = section.querySelector("header");
    const searchForm = section.querySelector("form");
    const searchInput = searchForm.querySelector("input");
    const clearSearch = searchForm.querySelector("[data-clear-search]");
    const pages = section.querySelector("nav");
    const previousPage = pages.querySelector("[data-page-change='-1']");
    const nextPage = pages.querySelector("[data-page-change='1']");
    const pageStatus = pages.querySelector("[role=status]");
    const results = section.querySelector(".company-exchange-results");

    let market;
    let cash;
    let pending = false;
    let failed = false;
    let fetching = false;
    let refreshQueued = false;
    let commandError;
    let socket;
    let socketToken;
    let search = "";
    let loadedSearch;
    let page = 1;
    let loadedPage;

    const isLoaded = () => loadedSearch === search && loadedPage === page;

    function render() {
        const focusId = results.contains(document.activeElement) ? document.activeElement.id : "";
        const format = new Intl.NumberFormat(locale());
        const signed = new Intl.NumberFormat(locale(), { signDisplay: "exceptZero" });
        const loaded = isLoaded();
        const rows = loaded ? market.companies : [];
        const heldValue = market?.holdingsValue ?? market?.companies.reduce((total, firm) => total + firm.held * firm.price, 0);
        heading.innerHTML = `<div class="company-exchange-title">
            <h2 id="company-standings-title">${text("title")}</h2>
            <span class="company-exchange-status${socket?.connected ? " company-exchange-connected" : ""}">${text(socket?.connected ? "live" : "refreshing")}</span>
        </div>`;
        searchForm.querySelector("label").textContent = text("searchLabel");
        searchInput.placeholder = text("searchLabel");
        searchForm.querySelector("[type=submit]").textContent = text("search");
        clearSearch.setAttribute("aria-label", text("clearSearch"));
        clearSearch.title = text("clearSearch");
        clearSearch.hidden = !search;
        pages.hidden = page <= 1 && !market?.hasMore;
        pages.setAttribute("aria-label", text("pages"));
        const pageText = text("page", { page: format.format(page) });
        if (pageStatus.textContent !== pageText) pageStatus.textContent = pageText;
        previousPage.textContent = text("previous");
        previousPage.setAttribute("aria-disabled", String(page <= 1));
        nextPage.textContent = text("next");
        nextPage.setAttribute("aria-disabled", String(!loaded || !market.hasMore));
        const balances = market ? `<dl class="company-exchange-summary"><div>
            <dt>${text("holdingsValue")}</dt><dd>${format.format(heldValue)}</dd></div><div>
            <dt>${text("reserve")}</dt><dd>${format.format(market.cashReserve)}</dd></div></dl>` : "";
        const error = commandError ? `<p class="company-standings-message company-exchange-warning" role="status">
            ${text(Object.hasOwn(copy, commandError) ? commandError : "commandError")}</p>` : "";
        const table = rows.length ? `<table class="company-standings-table">
            <thead><tr><th scope="col">${text("firm")}</th><th scope="col">${text("price")}</th>
            <th scope="col">${text("held")}</th><th scope="col">${text("trade")}</th></tr></thead>
            <tbody>${rows.map((firm) => {
                const buyDisabled = pending || failed || cash === undefined || cash - firm.price < market.cashReserve;
                const sellDisabled = pending || failed || cash === undefined || !firm.held;
                const button = (action, disabled) => `<button class="button button-secondary company-exchange-button company-peer-${action}" type="button"
                    id="peer-${action}-${firm.id}" data-peer="${action}" data-firm="${firm.id}"
                    aria-label="${escape(text("tradeFirm", { action: text(action), firm: firm.name }))}"${disabled ? " disabled" : ""}>${text(action)}</button>`;
                return `<tr${firm.isYou ? ' class="company-standing-own"' : ""}>
                    <th scope="row"><span>${escape(firm.name)}</span><small>${text("level")} ${format.format(firm.level)} ·
                    ${text("profit")} ${signed.format(firm.profit)}</small></th>
                    <td class="company-exchange-quote">${format.format(firm.price)}</td><td>${format.format(firm.held)}</td>
                    <td>${firm.isYou ? `<small>${text("own")}</small>` : `<div class="company-exchange-controls">
                        ${button("buy", buyDisabled)}${button("sell", sellDisabled)}</div>`}</td>
                </tr>`;
            }).join("")}</tbody>
        </table>` : `<p class="company-standings-message" role="status">${text(loaded ? (search ? "noMatches" : "empty") : "loading")}</p>`;
        const networkError = failed ? `<p class="company-standings-message" role="status">${text("error")}</p>` : "";
        results.innerHTML = balances + error + networkError + (failed && !loaded ? "" : table);
        if (focusId) document.getElementById(focusId)?.focus({ preventScroll: true });
    }

    async function refresh() {
        if (fetching) {
            refreshQueued = true;
            return;
        }
        fetching = true;
        const query = search;
        const requestedPage = page;
        const matches = () => query === search && requestedPage === page;
        try {
            const params = new URLSearchParams();
            if (query) params.set("search", query);
            if (requestedPage > 1) params.set("page", String(requestedPage));
            const queryString = params.toString();
            const path = "/api/company/standings" + (queryString ? `?${queryString}` : "");
            const response = await fetch(path);
            if (!response.ok) throw new Error("market");
            const updated = await response.json();
            if (!matches()) return;
            const changed = failed || !isLoaded() || JSON.stringify(market) !== JSON.stringify(updated);
            market = updated;
            loadedSearch = query;
            page = loadedPage = updated.page ?? requestedPage;
            failed = false;
            if (changed) render();
        } catch {
            if (matches() && !failed) {
                failed = true;
                render();
            }
        } finally {
            fetching = false;
            if (refreshQueued) {
                refreshQueued = false;
                refresh();
            }
        }
    }

    function applySearch() {
        const query = searchInput.value.trim();
        if (query !== search || page !== 1) {
            search = query;
            page = 1;
            failed = false;
            commandError = undefined;
            render();
        }
        refresh();
    }

    searchForm.addEventListener("submit", (event) => {
        event.preventDefault();
        applySearch();
    });
    clearSearch.addEventListener("click", () => {
        searchInput.value = "";
        applySearch();
        searchInput.focus();
    });
    pages.addEventListener("click", (event) => {
        const button = event.target.closest("button[data-page-change]");
        if (!button || button.getAttribute("aria-disabled") === "true") return;
        page += Number(button.dataset.pageChange);
        failed = false;
        commandError = undefined;
        render();
        refresh();
    });

    function connect(token) {
        if (!window.io || !token || socketToken === token) return;
        socket?.disconnect();
        socketToken = token;
        socket = window.io("/company", { auth: { csrfToken: token }, autoConnect: false });
        socket.on("company_market_changed", refresh);
        socket.on("connect", () => { render(); refresh(); });
        socket.on("disconnect", render);
        socket.connect();
    }

    section.addEventListener("click", (event) => {
        const button = event.target.closest("button[data-peer]");
        if (!button || button.disabled || pending || failed || !isLoaded()) return;
        const firm = market?.companies.find(({ id }) => id === Number(button.dataset.firm));
        if (!firm || firm.isYou) return;
        commandError = undefined;
        window.dispatchEvent(new CustomEvent("company:market-command", {
            detail: { action: `${button.dataset.peer}_peer`, firmId: firm.id, quote: firm.price },
        }));
    });

    window.addEventListener("stockfight:languagechange", render);
    window.addEventListener("company:updated", (event) => {
        cash = event.detail.cash;
        connect(event.detail.csrfToken);
        render();
        refresh();
    });
    window.addEventListener("company:busy", (event) => { pending = event.detail; render(); });
    window.addEventListener("company:command-error", (event) => {
        if (event.detail.action !== "buy_peer" && event.detail.action !== "sell_peer") return;
        commandError = event.detail.error;
        render();
        refresh();
    });
    function refreshWhileVisible() {
        if (document.visibilityState === "visible") refresh();
    }
    document.addEventListener("visibilitychange", refreshWhileVisible);
    window.setInterval(refreshWhileVisible, 5000);
    render();
})();
