(() => {
    "use strict";

    const content = document.getElementById("company-content");
    const notice = document.getElementById("company-notice");
    const copy = {
        title: ["Börsföretag", "Trading Firms"],
        home: ["Till huvudmenyn", "Main menu"],
        liveMarket: ["Livemarknaden", "Live market"],
        loading: ["Laddar börsföretaget …", "Loading your trading firm …"],
        level: ["Nivå {level}", "Level {level}"],
        day: ["Handelsdag {day}", "Trading day {day}"],
        cash: ["Kassa", "Cash"],
        profit: ["Handelsresultat", "Trading profit"],
        capacity: ["Aktier per affär", "Shares per trade"],
        progress: ["Vägen till nästa nivå", "Progress to the next level"],
        nextLevel: ["{name} på nivå {level}", "{name} at level {level}"],
        progressAmount: ["Vinstrekord {actual} av {target}", "Best profit {actual} of {target}"],
        unlock: ["Låser upp {name} ({symbol})", "Unlocks {name} ({symbol})"],
        maximumLevel: ["Högsta nivån uppnådd", "Highest level reached"],
        maxGuide: ["Fortsätt handla för att bygga kapital och träna dina handlare.", "Keep trading to build capital and train your traders."],
        trades: ["Dina affärer", "Your trades"],
        tradeGuide: ["Välj en aktie. Köpet och försäljningen sker direkt, sedan börjar nästa handelsdag.", "Choose a stock. The buy and sell happen immediately, then the next trading day begins."],
        buyPrice: ["Köpkurs", "Buy quote"],
        sellPrice: ["Säljkurs", "Sell quote"],
        net: ["Vinst", "Profit"],
        trade: ["Handla {count} aktier", "Trade {count} shares"],
        tradeOne: ["Handla 1 aktie", "Trade 1 share"],
        tradeName: ["{action} i {name}", "{action} in {name}"],
        unavailable: ["Affären är inte tillgänglig", "Trade unavailable"],
        result: ["Förra handelsdagen", "Previous trading day"],
        resultShares: ["{count} aktier i {symbol}", "{count} shares of {symbol}"],
        resultOne: ["1 aktie i {symbol}", "1 share of {symbol}"],
        personalTrade: ["Din affär", "Your trade"],
        personnel: ["Handlare", "Traders"],
        personnelGuide: ["Aktiva handlare gör egna affärer när handelsdagen avslutas. Under träningen kan de göra stora förluster.", "Active traders make their own trades when the trading day ends. They can take large losses while learning."],
        trainingGuide: ["Skickligheten ökar varje gång en handlare gör en affär.", "Each trade improves a trader’s skill."],
        skill: ["Skicklighet", "Skill"],
        strategy: ["Strategi", "Strategy"],
        careful: ["Försiktig", "Careful"],
        balanced: ["Balanserad", "Balanced"],
        aggressive: ["Aggressiv", "Aggressive"],
        carefulRisk: ["Mindre affärer med lägre vinst och förlust.", "Smaller trades with lower gains and losses."],
        balancedRisk: ["Medelstora affärer. Upp till en fjärdedel av kassan används.", "Medium-sized trades use up to a quarter of cash."],
        aggressiveRisk: ["Större affärer med högre vinst och förlust.", "Larger trades with higher gains and losses."],
        experience: ["{count} affärer", "{count} trades"],
        experienceOne: ["1 affär", "1 trade"],
        active: ["Aktiv", "Active"],
        paused: ["Pausad", "Paused"],
        pause: ["Pausa", "Pause"],
        resume: ["Aktivera", "Activate"],
        personAction: ["{action} {name}", "{action} {name}"],
        hire: ["Anställ {name} för {price}", "Hire {name} for {price}"],
        hireLocked: ["Nästa handlare blir tillgänglig på nivå {level}.", "The next trader becomes available at level {level}."],
        advance: ["Låt handlarna handla", "Let your traders trade"],
        equipment: ["Utöka kapaciteten", "Expand capacity"],
        equipmentBenefit: ["{count} extra aktier per affär", "{count} additional shares per trade"],
        equipmentOne: ["1 extra aktie per affär", "1 additional share per trade"],
        equipmentBuy: ["Uppgradera för {price}", "Upgrade for {price}"],
        signed_out: ["Logga in igen från huvudmenyn för att spela.", "Sign in again from the main menu to play."],
        reload: ["Försök igen", "Try again"],
        network: ["Anslutningen bröts. Försök igen.", "The connection was lost. Try again."],
        stale_revision: ["Företaget uppdaterades i en annan flik. Du ser nu det senaste läget.", "Your firm changed in another tab. You are now seeing its latest state."],
        stale_quote: ["Kursen har ändrats. Kontrollera den nya kursen på livemarknaden.", "The quote has changed. Check the latest quote on the live market."],
        invalid_command: ["Åtgärden gick inte att genomföra.", "The action could not be completed."],
        locked_asset: ["Aktien låses upp på en högre nivå.", "This stock unlocks at a higher level."],
        invalid_asset: ["Aktien finns inte på marknaden.", "This stock is unavailable on the market."],
        insufficient_cash: ["Kassan räcker inte till affären.", "There is not enough cash for this trade."],
        insufficient_shares: ["Du äger för få aktier för att sälja.", "You do not hold enough shares to sell."],
        upgrade_unavailable: ["Uppgraderingen är inte tillgänglig just nu.", "The upgrade is unavailable right now."],
        hire_unavailable: ["Handlaren är inte tillgänglig just nu.", "This trader is unavailable right now."],
        invalid_employee: ["Handlaren gick inte att hitta.", "The trader could not be found."],
        invalid_strategy: ["Välj en av handlarens tillgängliga strategier.", "Choose one of the trader’s available strategies."],
        no_active_employee: ["Aktivera minst en handlare för att göra en affär.", "Activate at least one trader to trade."],
        self_trade: ["Du kan bara handla aktier i andra spelares företag.", "You can only trade shares in other players’ firms."],
        invalid_firm: ["Företaget gick inte att hitta på livemarknaden.", "The firm could not be found on the live market."],
    };

    const locale = () => window.StockFightI18n?.getLocale() ?? "sv-SE";
    const english = () => locale().startsWith("en");
    const localized = (translations) => translations[english() ? "en" : "sv"];
    const escape = (value) => String(value).replace(/[&<>"']/g, (character) => ({
        "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
    })[character]);

    const text = (key, values = {}) => copy[key][english() ? 1 : 0]
        .replace(/\{(\w+)\}/g, (placeholder, name) => Object.hasOwn(values, name) ? values[name] : placeholder);
    const tx = (key, values) => escape(text(key, values));
    const number = (value, signed = false) =>
        new Intl.NumberFormat(locale(), { signDisplay: signed ? "exceptZero" : "auto" }).format(value);
    const money = (value, signed = false) => number(value, signed) + (english() ? " cr" : " kr");
    const percent = (value) => new Intl.NumberFormat(locale(), { style: "percent" }).format(value / 100);
    const tone = (value) => value < 0 ? "company-negative" : value > 0 ? "company-positive" : "";

    let state;
    let csrfToken;
    let pending = false;
    let error;

    function publishState() {
        window.dispatchEvent(new CustomEvent("company:updated", { detail: { ...state, csrfToken } }));
    }

    function setBusy(value) {
        pending = value;
        content.setAttribute("aria-busy", String(value));
        window.dispatchEvent(new CustomEvent("company:busy", { detail: value }));
    }

    function renderNotice() {
        notice.hidden = !error;
        notice.textContent = error ? text(Object.hasOwn(copy, error) ? error : "invalid_command") : "";
    }

    function renderHeader() {
        return `<header class="company-hero">
            <div>
                <div class="company-kicker"><span>${tx("level", { level: number(state.level.number) })}</span>
                    <span>${escape(localized(state.level.name))}</span></div>
                <h1 class="company-title">${tx("title")}</h1>
                <div class="company-hero-links">
                    <span>${tx("day", { day: number(state.day) })}</span>
                    <a href="#company-standings">${tx("liveMarket")} <span aria-hidden="true">↓</span></a>
                </div>
            </div>
            <dl class="company-balance" aria-live="polite">
                <div><dt>${tx("cash")}</dt><dd class="company-positive">${money(state.cash)}</dd></div>
                <div><dt>${tx("profit")}</dt><dd class="${tone(state.profit)}">${money(state.profit, true)}</dd></div>
                <div><dt>${tx("capacity")}</dt><dd>${number(state.capacity)}</dd></div>
            </dl>
        </header>`;
    }

    function renderProgress() {
        const next = state.nextLevel;
        if (!next) {
            return `<section class="company-panel company-progress" aria-labelledby="company-progress-title">
                <h2 id="company-progress-title">${tx("maximumLevel")}</h2>
                <p class="company-muted">${tx("maxGuide")}</p>
            </section>`;
        }
        const attained = Math.min(next.target, Math.max(state.peakProfit, 0));
        return `<section class="company-panel company-progress" aria-labelledby="company-progress-title">
            <div class="company-section-heading">
                <h2 id="company-progress-title">${tx("progress")}</h2>
                <strong>${tx("nextLevel", { name: localized(next.name), level: number(next.number) })}</strong>
            </div>
            <progress value="${attained}" max="${next.target}" aria-labelledby="company-progress-title"
                aria-valuetext="${tx("progressAmount", { actual: money(attained), target: money(next.target) })}"></progress>
            <div class="company-progress-footer">
                <span>${tx("progressAmount", { actual: money(attained), target: money(next.target) })}</span>
                ${next.unlock ? `<span>${tx("unlock", { name: localized(next.unlock.name), symbol: next.unlock.symbol })}</span>` : ""}
            </div>
        </section>`;
    }

    function renderAsset(asset) {
        const count = asset.quantity;
        const symbol = escape(asset.symbol);
        const action = text(count <= 0 ? "unavailable" : count === 1 ? "tradeOne" : "trade", { count: number(count) });
        return `<article class="company-asset">
            <div class="company-asset-heading"><span class="company-symbol">${symbol}</span>
                <h3>${escape(localized(asset.name))}</h3></div>
            <dl class="company-quote">
                <div><dt>${tx("buyPrice")}</dt><dd>${money(asset.buyPrice)}</dd></div>
                <div><dt>${tx("sellPrice")}</dt><dd>${money(asset.sellPrice)}</dd></div>
                <div><dt>${tx("net")}</dt><dd class="${tone(asset.profit)}">${money(asset.profit, true)}</dd></div>
            </dl>
            <button class="button button-primary" id="company-trade-${symbol}" type="button"
                data-command="trade" data-symbol="${symbol}" aria-label="${tx("tradeName", { action, name: localized(asset.name) })}"${pending || count <= 0 ? " disabled" : ""}>
                ${escape(action)}
            </button>
        </article>`;
    }

    function renderTrades() {
        return `<section class="company-panel company-trades" aria-labelledby="company-trades-title">
            <h2 id="company-trades-title">${tx("trades")}</h2>
            <p class="company-muted">${tx("tradeGuide")}</p>
            <div class="company-assets">${state.assets.filter((asset) => asset.unlocked).map(renderAsset).join("")}</div>
        </section>`;
    }

    function renderEmployee(person) {
        const action = person.active ? "pause" : "resume";
        const id = escape(person.id);
        const strategy = person.strategy || "balanced";
        return `<article class="company-employee">
            <div class="company-section-heading">
                <h3>${escape(person.name)}</h3>
                <span class="${person.active ? "company-positive" : "company-muted"}">${tx(person.active ? "active" : "paused")}</span>
            </div>
            <div class="company-skill">
                <span id="company-skill-${id}">${tx("skill")}</span><strong>${percent(person.skill)}</strong>
            </div>
            <progress value="${person.skill}" max="100" aria-labelledby="company-skill-${id}"></progress>
            <div class="company-strategy">
                <label for="company-strategy-${id}">${tx("strategy")}</label>
                <select id="company-strategy-${id}" data-employee="${id}" aria-describedby="company-risk-${id}"${pending ? " disabled" : ""}>
                    ${["careful", "balanced", "aggressive"].map((choice) => `<option value="${choice}"${choice === strategy ? " selected" : ""}>${tx(choice)}</option>`).join("")}
                </select>
                <p id="company-risk-${id}" class="company-muted">${tx(`${strategy}Risk`)}</p>
            </div>
            <div class="company-employee-footer">
                <span>${tx(person.trades === 1 ? "experienceOne" : "experience", { count: number(person.trades) })}</span>
                <strong class="${tone(person.profit)}">${money(person.profit, true)}</strong>
                <button class="button button-secondary" id="company-employee-${id}" type="button"
                    data-command="toggle_employee" data-employee="${id}" aria-label="${tx("personAction", { action: text(action), name: person.name })}"${pending ? " disabled" : ""}>${tx(action)}</button>
            </div>
        </article>`;
    }

    function renderPersonnel() {
        const hire = state.hire;
        return `<section class="company-panel company-personnel" aria-labelledby="company-personnel-title">
            <h2 id="company-personnel-title">${tx("personnel")}</h2>
            <p class="company-muted">${tx("personnelGuide")} ${tx("trainingGuide")}</p>
            <div class="company-employees">${state.employees.map(renderEmployee).join("")}</div>
            <div class="company-employee-actions">
                ${hire && state.level.number >= hire.unlockLevel ? `<button class="button button-secondary" id="company-hire" type="button"
                    data-command="hire"${pending || !hire.available ? " disabled" : ""}>${tx("hire", { name: hire.name, price: money(hire.price) })}</button>` : ""}
                ${hire && state.level.number < hire.unlockLevel ? `<p class="company-muted">${tx("hireLocked", { level: number(hire.unlockLevel) })}</p>` : ""}
                ${state.employees.length ? `<button class="button button-primary" id="company-advance" type="button" data-command="advance"${pending || !state.canAdvance ? " disabled" : ""}>${tx("advance")}</button>` : ""}
            </div>
        </section>`;
    }

    function renderUpgrade() {
        const upgrade = state.upgrade;
        if (!upgrade) return "";
        return `<section class="company-panel company-upgrade" aria-labelledby="company-upgrade-title">
            <h2 id="company-upgrade-title">${tx("equipment")}</h2>
            <p class="company-muted">${tx(upgrade.bonus === 1 ? "equipmentOne" : "equipmentBenefit", { count: number(upgrade.bonus) })}</p>
            <button class="button button-secondary" id="company-upgrade" type="button" data-command="upgrade"
                ${pending || !upgrade.available ? "disabled" : ""}>${tx("equipmentBuy", { price: money(upgrade.price) })}</button>
        </section>`;
    }

    function reportLine(name, trade) {
        const shares = text(trade.quantity === 1 ? "resultOne" : "resultShares", {
            count: number(trade.quantity),
            symbol: trade.symbol,
        });
        return `<li>
            <div><strong>${escape(name)}</strong><span>${escape(shares)}</span></div>
            <strong class="${tone(trade.profit)}">${money(trade.profit, true)}</strong>
        </li>`;
    }

    function renderReport() {
        const { lastTrade, lastEmployeeTrades } = state;
        if (!lastTrade && !lastEmployeeTrades.length) return "";
        return `<section class="company-panel company-report" aria-labelledby="company-report-title" aria-live="polite">
            <h2 id="company-report-title">${tx("result")}</h2>
            <ul>
                ${lastTrade ? reportLine(text("personalTrade"), lastTrade) : ""}
                ${lastEmployeeTrades.map((trade) => reportLine(trade.name, trade)).join("")}
            </ul>
        </section>`;
    }

    function render(focusId) {
        for (const node of document.querySelectorAll("[data-company-text]")) {
            node.textContent = text(node.dataset.companyText);
        }
        document.title = text("title") + " · Stock Fight";
        renderNotice();
        if (state) {
            content.innerHTML = `${renderHeader()}${renderProgress()}
                <div class="company-desk">
                    <div>${renderTrades()}${renderReport()}</div>
                    <div>${renderPersonnel()}${renderUpgrade()}</div>
                </div>`;
        } else if (error) {
            content.innerHTML = `<h1 class="company-title">${tx("title")}</h1>
                <div class="company-retry">${error === "signed_out" ? `<a class="button button-secondary" href="/">${tx("home")}</a>` : `<button class="button button-secondary" type="button" data-command="load">${tx("reload")}</button>`}</div>`;
        } else {
            content.innerHTML = `<h1 class="company-title">${tx("title")}</h1><p class="company-muted">${tx("loading")}</p>`;
        }
        const focus = focusId && document.getElementById(focusId);
        if (focus && !focus.disabled) focus.focus({ preventScroll: true });
    }

    async function load() {
        setBusy(true);
        error = undefined;
        render();
        try {
            const [account, company] = await Promise.all([fetch("/api/me"), fetch("/api/company")]);
            if (company.status === 401) {
                error = "signed_out";
            } else if (account.ok && company.ok) {
                csrfToken = (await account.json()).csrfToken;
                state = await company.json();
            } else {
                error = "network";
            }
        } catch {
            error = "network";
        } finally {
            setBusy(false);
            render();
            if (state) publishState();
        }
    }

    async function send(command, focusId) {
        if (pending || !state) return;
        setBusy(true);
        error = undefined;
        for (const control of content.querySelectorAll("button, select")) control.disabled = true;
        renderNotice();
        let received = false;
        try {
            const response = await fetch("/api/company/commands", {
                method: "POST",
                headers: { "Content-Type": "application/json", "X-CSRF-Token": csrfToken },
                body: JSON.stringify({ ...command, revision: state.revision }),
            });
            const payload = await response.json();
            if (response.ok) {
                state = payload;
                received = true;
            } else if (response.status === 409 && payload.state) {
                state = payload.state;
                error = payload.error || "stale_revision";
                received = true;
            } else {
                error = response.status === 401 || response.status === 403 ? "signed_out" : (payload.error || "invalid_command");
            }
        } catch {
            error = "network";
        } finally {
            setBusy(false);
            render(focusId);
            if (received) publishState();
            if (error) {
                window.dispatchEvent(new CustomEvent("company:command-error", { detail: { error, action: command.action } }));
                if (command.action !== "buy_peer" && command.action !== "sell_peer") {
                    notice.scrollIntoView({ block: "nearest" });
                }
            }
        }
    }

    content.addEventListener("click", (event) => {
        const button = event.target.closest("button[data-command]");
        if (!button || pending) return;
        const { command, symbol, employee } = button.dataset;
        if (command === "load") {
            load();
            return;
        }
        const payload = { action: command };
        if (command === "trade") payload.symbol = symbol;
        if (command === "toggle_employee") payload.employeeId = Number(employee);
        send(payload, button.id);
    });

    content.addEventListener("change", (event) => {
        const strategy = event.target.closest("select[data-employee]");
        if (strategy) send({
            action: "set_employee_strategy", employeeId: Number(strategy.dataset.employee), strategy: strategy.value,
        }, strategy.id);
    });

    window.addEventListener("company:market-command", ({ detail }) => {
        if (detail?.action === "buy_peer" || detail?.action === "sell_peer") send(detail);
    });
    window.addEventListener("stockfight:languagechange", () => render(document.activeElement?.id));
    load();
})();
