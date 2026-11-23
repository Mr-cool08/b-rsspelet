(() => {
    "use strict";

    const section = document.getElementById("company-standings");
    if (!section) return;
    section.setAttribute("aria-labelledby", "company-standings-title");

    const copy = {
        title: ["Livemarknaden", "Live market"],
        live: ["Live", "Live"],
        refreshing: ["Löpande uppdatering", "Periodic updates"],
        description: ["Köp och sälj en aktie åt gången. Kurserna följer firmornas handelsresultat.",
            "Buy and sell one share at a time. Share prices follow each firm's trading results."],
        loading: ["Hämtar börskurser …", "Loading share prices …"],
        empty: ["Firmor blir synliga här när de börjar spela.", "Firms appear here when their players start playing."],
        error: ["Marknaden kunde inte uppdateras just nu.", "The market could not be refreshed."],
        firm: ["Handelsfirma", "Trading firm"],
        price: ["Kurs", "Price"],
        level: ["Nivå", "Level"],
        profit: ["Handelsresultat", "Trading profit"],
        held: ["Äger", "Owned"],
        trade: ["Handel", "Trade"],
        own: ["Din firma", "Your firm"],
        buy: ["Köp", "Buy"],
        sell: ["Sälj", "Sell"],
        holdingsValue: ["Aktieportföljens värde", "Share portfolio value"],
        reserve: ["Rörelsekassa som måste vara kvar", "Cash kept for operations"],
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
    const text = (key) => copy[key][locale() === "en-GB" ? 1 : 0];
    const escape = (value) => String(value).replace(/[&<>"']/g, (character) => ({
        "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
    })[character]);

    let market;
    let cash;
    let pending = false;
    let failed = false;
    let fetching = false;
    let refreshQueued = false;
    let commandError;
    let socket;
    let socketToken;

    function render() {
        const focusId = section.contains(document.activeElement) ? document.activeElement.id : "";
        const format = new Intl.NumberFormat(locale());
        const signed = new Intl.NumberFormat(locale(), { signDisplay: "exceptZero" });
        const rows = market?.companies ?? [];
        const heldValue = rows.reduce((total, firm) => total + firm.held * firm.price, 0);
        const title = `<header class="company-standings-heading"><div class="company-exchange-title">
            <h2 id="company-standings-title">${text("title")}</h2>
            <span class="company-exchange-status${socket?.connected ? " company-exchange-connected" : ""}">${text(socket?.connected ? "live" : "refreshing")}</span>
        </div><p>${text("description")}</p></header>`;
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
                const button = (action, disabled) => `<button class="button button-secondary company-exchange-button" type="button"
                    id="peer-${action}-${firm.id}" data-peer="${action}" data-firm="${firm.id}"
                    aria-label="${text(action)} ${escape(firm.name)}"${disabled ? " disabled" : ""}>${text(action)}</button>`;
                return `<tr${firm.isYou ? ' class="company-standing-own"' : ""}>
                    <th scope="row"><span>${escape(firm.name)}</span><small>${text("level")} ${format.format(firm.level)} ·
                    ${text("profit")} ${signed.format(firm.profit)}</small></th>
                    <td class="company-exchange-quote">${format.format(firm.price)}</td><td>${format.format(firm.held)}</td>
                    <td>${firm.isYou ? `<small>${text("own")}</small>` : `<div class="company-exchange-controls">
                        ${button("buy", buyDisabled)}${button("sell", sellDisabled)}</div>`}</td>
                </tr>`;
            }).join("")}</tbody>
        </table>` : `<p class="company-standings-message">${text(market ? "empty" : "loading")}</p>`;
        const networkError = failed ? `<p class="company-standings-message" role="status">${text("error")}</p>` : "";
        section.innerHTML = title + balances + error + networkError + (failed && !market ? "" : table);
        if (focusId) document.getElementById(focusId)?.focus({ preventScroll: true });
    }

    async function refresh() {
        if (fetching) {
            refreshQueued = true;
            return;
        }
        fetching = true;
        try {
            const response = await fetch("/api/company/standings");
            if (!response.ok) throw new Error("market");
            const updated = await response.json();
            const changed = failed || JSON.stringify(market) !== JSON.stringify(updated);
            market = updated;
            failed = false;
            if (changed) render();
        } catch {
            if (!failed) {
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
        if (!button || button.disabled || pending || failed) return;
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
