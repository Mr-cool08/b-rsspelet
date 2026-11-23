(() => {
    "use strict";

    const content = document.getElementById("company-content");
    const workspace = document.getElementById("company-workspace");
    const operations = document.getElementById("company-admin");
    const tradeHistory = document.getElementById("company-reports");
    const views = [...workspace.querySelectorAll("[data-company-view]")];
    const notice = document.getElementById("company-notice");
    const copy = {
        title: ["Börsföretag", "Trading Firms"],
        home: ["Huvudmeny", "Main menu"],
        liveMarket: ["Börs", "Market"],
        administration: ["Firma", "Firm"],
        otherFirms: ["Spelarbörs", "Player exchange"],
        sections: ["Börsföretagets vyer", "Trading firm views"],
        loading: ["Laddar …", "Loading …"],
        level: ["Nivå {level}", "Level {level}"],
        day: ["Dag {day}", "Day {day}"],
        cash: ["Kassa", "Cash"],
        profit: ["Resultat", "Profit"],
        capacity: ["Max per order", "Max per order"],
        progress: ["Nästa nivå", "Next level"],
        progressAmount: ["Vinstrekord {actual} av {target}", "Best profit {actual} of {target}"],
        progressShort: ["Vinstrekord {actual} / {target}", "Best profit {actual} / {target}"],
        unlock: ["Låser upp {symbol}", "Unlocks {symbol}"],
        maximumLevel: ["Maxnivå", "Max level"],
        personnel: ["Handlare", "Traders"],
        personnelGuide: ["Botar handlar med firmans kassa, även när du är borta.", "Bots trade with firm cash, even while you’re away."],
        skill: ["Skicklighet", "Skill"],
        strategy: ["Riskbudget", "Risk budget"],
        careful: ["Försiktig", "Careful"],
        balanced: ["Balanserad", "Balanced"],
        aggressive: ["Aggressiv", "Aggressive"],
        experience: ["{count} affärer", "{count} trades"],
        experienceOne: ["1 affär", "1 trade"],
        active: ["Aktiv", "Active"],
        paused: ["Pausad", "Paused"],
        pausedGuide: ["Pausade botar kan fortfarande stänga positioner.", "Paused bots can still close positions."],
        pause: ["Pausa", "Pause"],
        resume: ["Aktivera", "Activate"],
        personAction: ["{action} {name}", "{action} {name}"],
        hire: ["Anställ {name} · {price}", "Hire {name} · {price}"],
        hireLocked: ["Ny handlare på nivå {level}", "New trader at level {level}"],
        dailyResults: ["Dagens resultat", "Today’s results"],
        closeDay: ["Stäng dagen", "Close day"],
        closingGuide: ["Driften betalas. Öppna positioner följer med.", "Costs are paid. Open positions carry over."],
        closingCost: ["Driftkostnad", "Operating cost"],
        operations: ["Driftinställningar", "Operating settings"],
        reserve: ["Kassareserv", "Cash reserve"],
        reserveGuide: ["Kassa som sparas till driften.", "Cash set aside for costs."],
        standard: ["Standard", "Standard"],
        buffered: ["Buffert", "Buffered"],
        defensive: ["Defensiv", "Defensive"],
        riskOption: ["{policy} · {amount}", "{policy} · {amount}"],
        desk: ["Handelsbord", "Trading desk"],
        deskOption: ["{name} · {cost}/dag", "{name} · {cost}/day"],
        lean: ["Basdrift", "Lean"],
        research: ["Analys", "Research"],
        execution: ["Orderutförande", "Execution"],
        leanDesk: ["", ""],
        researchDesk: ["+{ticks} kurser i botarnas analys", "+{ticks} quotes in bot analysis"],
        executionDesk: ["+{count} aktier per botorder · +{points} procentenheter till riskbudgeten", "+{count} shares per bot order · +{points} percentage points to risk budget"],
        focus: ["Aktiefokus", "Stock focus"],
        allStocks: ["Alla upplåsta aktier", "All unlocked stocks"],
        strategySettings: ["Inställningar", "Settings"],
        signal: ["Handelssignal", "Trading signal"],
        momentum: ["Momentum", "Momentum"],
        mean_reversion: ["Återgång till snittet", "Mean reversion"],
        breakout: ["Utbrott", "Breakout"],
        momentumGuide: ["Följer trenden.", "Follows the trend."],
        mean_reversionGuide: ["Handlar mot snittkursen.", "Trades toward the average price."],
        breakoutGuide: ["Följer utbrott ur kursintervallet.", "Follows breakouts from the price range."],
        lookback: ["Analysfönster (kurser)", "Analysis window (quotes)"],
        threshold: ["Signaltröskel (%)", "Signal threshold (%)"],
        stopLoss: ["Stop-loss (%)", "Stop-loss (%)"],
        takeProfit: ["Vinstmål (%)", "Take profit (%)"],
        saveBot: ["Spara", "Save"],
        reportsTab: ["Rapporter", "Reports"],
        reports: ["Dagsrapporter", "Daily reports"],
        noReports: ["Första rapporten skapas när du stänger dagen.", "Close the day to create your first report."],
        reportDay: ["Dag", "Day"],
        reportTrading: ["Egna affärer", "Own trades"],
        reportEmployees: ["Handlare", "Traders"],
        reportCost: ["Drift", "Costs"],
        reportNet: ["Netto", "Net"],
        equipment: ["Orderkapacitet", "Order capacity"],
        equipmentBenefit: ["+{count} aktier per order", "+{count} shares per order"],
        equipmentOne: ["+1 aktie per order", "+1 share per order"],
        equipmentBuy: ["Uppgradera · {price}", "Upgrade · {price}"],
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
        invalid_reserve_policy: ["Välj en tillgänglig kassareserv.", "Choose an available cash reserve."],
        invalid_desk: ["Välj ett tillgängligt arbetsbord.", "Choose an available desk."],
        invalid_bot: ["Kontrollera signaltröskeln, analysfönstret och botens riskgränser.", "Check the signal threshold, analysis window and bot risk limits."],
        closing_cost_unavailable: ["Kassan räcker inte till driftskostnaden. Byt arbetsbord eller frigör kapital.", "Cash is too low to cover operating costs. Change the desk or free up cash."],
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
        new Intl.NumberFormat(locale(), { maximumFractionDigits: 2, signDisplay: signed ? "exceptZero" : "auto" }).format(value);
    const money = (value, signed = false) => number(value, signed) + (english() ? " cr" : " kred.");
    const percent = (value) => new Intl.NumberFormat(locale(), { style: "percent" }).format(value / 100);
    const tone = (value) => value < 0 ? "company-negative" : value > 0 ? "company-positive" : "";

    let state;
    let csrfToken;
    let pending = false;
    let error;
    let refreshing = false;
    const botDrafts = new Map();
    let openBotEditors = new Set();

    function publishState() {
        window.dispatchEvent(new CustomEvent("company:updated", { detail: { ...state, csrfToken } }));
    }

    function setBusy(value) {
        pending = value;
        workspace.setAttribute("aria-busy", String(value));
        window.dispatchEvent(new CustomEvent("company:busy", { detail: value }));
    }

    function renderNotice() {
        notice.hidden = !error;
        notice.textContent = error ? text(Object.hasOwn(copy, error) ? error : "invalid_command") : "";
    }

    function renderHeader() {
        return `<header class="company-hero">
            <div>
                <h1 class="company-title">${tx("title")}</h1>
                <div class="company-kicker">
                    <span>${tx("level", { level: number(state.level.number) })}</span>
                    <span>${escape(localized(state.level.name))}</span>
                    <span>${tx("day", { day: number(state.day) })}</span>
                </div>
            </div>
            <div class="company-hero-stats">
                <dl class="company-balance" aria-live="polite">
                    <div><dt>${tx("cash")}</dt><dd class="company-positive">${money(state.cash)}</dd></div>
                    <div><dt>${tx("profit")}</dt><dd class="${tone(state.profit)}">${money(state.profit, true)}</dd></div>
                    <div><dt>${tx("capacity")}</dt><dd>${number(state.capacity)}</dd></div>
                </dl>
                ${renderProgress()}
            </div>
        </header>`;
    }

    function renderNavigation() {
        return `<nav class="company-navigation" aria-label="${tx("sections")}">
            <a id="company-tab-market" href="#company-market"><span class="company-nav-icon company-nav-market" aria-hidden="true"></span>${tx("liveMarket")}</a>
            <a id="company-tab-admin" href="#company-admin"><span class="company-nav-icon" aria-hidden="true">⚙︎</span>${tx("administration")}</a>
            <a id="company-tab-reports" href="#company-reports"><span class="company-nav-icon" aria-hidden="true">▤</span>${tx("reportsTab")}</a>
            <a id="company-tab-standings" href="#company-standings"><span class="company-nav-icon" aria-hidden="true">♟︎</span>${tx("otherFirms")}</a>
        </nav>`;
    }

    function showView() {
        const selected = views.find((view) => `#${view.id}` === location.hash) ?? views[0];
        for (const view of views) view.hidden = !state || view !== selected;
        for (const link of content.querySelectorAll(".company-navigation a")) {
            if (link.hash === `#${selected.id}`) link.setAttribute("aria-current", "location");
            else link.removeAttribute("aria-current");
        }
    }

    function renderProgress() {
        const next = state.nextLevel;
        if (!next) return `<p class="company-progress company-positive">${tx("maximumLevel")}</p>`;
        const attained = Math.min(next.target, Math.max(state.peakProfit, 0));
        const amount = { actual: number(attained), target: money(next.target) };
        return `<div class="company-progress">
            <div class="company-progress-footer">
                <span id="company-progress-title">${tx("progress")} · ${tx("progressShort", amount)}</span>
                ${next.liveUnlock ? `<strong>${tx("unlock", { symbol: next.liveUnlock.symbol })}</strong>` : ""}
            </div>
            <progress value="${attained}" max="${next.target}" aria-labelledby="company-progress-title"
                aria-valuetext="${tx("progressAmount", { actual: money(attained), target: money(next.target) })}"></progress>
        </div>`;
    }

    function renderAdministration() {
        const admin = state.administration;
        if (!admin) return "";
        const desk = admin.desks.find(({ id }) => id === admin.desk);
        const deskGuide = tx(`${desk.id}Desk`, {
            points: number(desk.stakeBonus), count: number(desk.capacityBonus), ticks: number(desk.lookbackBonus),
        });
        const options = (items, current, format) => items.map((item) =>
            `<option value="${escape(item.id)}"${item.id === current ? " selected" : ""}>${format(item)}</option>`).join("");
        return `<section class="company-panel company-admin" aria-labelledby="company-admin-title">
            <h2 id="company-admin-title">${tx("dailyResults")}</h2>
            <div class="company-close-day">
                <dl>
                    <div><dt>${tx("reportTrading")}</dt><dd class="${tone(admin.dayTradingProfit)}">${money(admin.dayTradingProfit, true)}</dd></div>
                    <div><dt>${tx("reportEmployees")}</dt><dd class="${tone(admin.dayEmployeeProfit)}">${money(admin.dayEmployeeProfit, true)}</dd></div>
                    <div><dt>${tx("closingCost")}</dt><dd class="company-cost">${money(admin.closingCost)}</dd></div>
                </dl>
                <button class="button button-primary" id="company-close-day" type="button" data-command="close_day"
                    aria-describedby="company-close-guide"${pending || state.cash < admin.closingCost ? " disabled" : ""}>${tx("closeDay")}<span aria-hidden="true">→</span></button>
                <p class="company-muted" id="company-close-guide">${tx(state.cash < admin.closingCost ? "closing_cost_unavailable" : "closingGuide")}</p>
            </div>
            <details id="company-operating-settings" class="company-details"${document.getElementById("company-operating-settings")?.open ? " open" : ""}>
                <summary>${tx("operations")}</summary>
                <div class="company-admin-settings">
                    <label for="company-reserve">${tx("reserve")}</label>
                    <select id="company-reserve" data-policy="reserve" aria-describedby="company-reserve-guide"${pending ? " disabled" : ""}>
                        ${options(admin.reservePolicies, admin.reservePolicy, ({ id, amount }) => tx("riskOption", { policy: text(id), amount: money(amount) }))}
                    </select>
                    <p id="company-reserve-guide" class="company-muted">${tx("reserveGuide")}</p>
                    <label for="company-admin-desk">${tx("desk")}</label>
                    <select id="company-admin-desk" data-policy="desk"${deskGuide ? ' aria-describedby="company-desk-guide"' : ""}${pending ? " disabled" : ""}>
                        ${options(admin.desks, admin.desk, ({ id, cost }) => tx("deskOption", { name: text(id), cost: money(cost) }))}
                    </select>
                    ${deskGuide ? `<p id="company-desk-guide" class="company-muted">${deskGuide}</p>` : ""}
                </div>
            </details>
        </section>`;
    }

    function renderBotFields(person) {
        if (!person.bot) return "";
        const id = escape(person.id);
        const draft = botDrafts.get(person.id) ?? person.bot;
        const fields = [["lookback", 3, 12, 1], ["threshold", 0.1, 10, 0.1], ["stopLoss", 1, 20, 1], ["takeProfit", 1, 25, 1]];
        return `<form id="company-bot-${id}" data-bot="${id}">
                <label for="company-bot-strategy-${id}">${tx("signal")}</label>
                <select id="company-bot-strategy-${id}" class="company-field" name="strategy" aria-describedby="company-bot-guide-${id}">
                    ${["momentum", "mean_reversion", "breakout"].map((strategy) => `<option value="${strategy}"${strategy === draft.strategy ? " selected" : ""}>${tx(strategy)}</option>`).join("")}
                </select>
                <p id="company-bot-guide-${id}" class="company-muted" data-bot-guide>${tx(`${draft.strategy}Guide`)}</p>
                <div class="company-bot-fields">
                    ${fields.map(([name, min, max, step]) => `<label for="company-bot-${name}-${id}">${tx(name)}
                        <input class="company-field" id="company-bot-${name}-${id}" type="number" name="${name}" min="${min}" max="${max}" step="${step}" value="${escape(draft[name])}" required>
                    </label>`).join("")}
                </div>
                <button id="company-bot-save-${id}" type="submit" class="button button-secondary">${tx("saveBot")}</button>
            </form>`;
    }

    function renderEmployee(person) {
        const action = person.active ? "pause" : "resume";
        const id = escape(person.id);
        const strategy = person.strategy || "balanced";
        const focus = person.focus || "all";
        return `<article class="company-employee">
            <div class="company-section-heading">
                <h3>${escape(person.name)}</h3>
                <span class="company-trader-status ${person.active ? "company-positive" : "company-muted"}">${tx(person.active ? "active" : "paused")}</span>
            </div>
            <div class="company-skill">
                <span id="company-skill-${id}">${tx("skill")}</span><strong>${percent(person.skill)}</strong>
            </div>
            <progress value="${person.skill}" max="100" aria-labelledby="company-skill-${id}"></progress>
            <div class="company-employee-footer">
                <span>${tx(person.trades === 1 ? "experienceOne" : "experience", { count: number(person.trades) })}</span>
                <strong class="${tone(person.profit)}">${money(person.profit, true)}</strong>
                <button class="button button-secondary" id="company-employee-${id}" type="button"
                    data-command="toggle_employee" data-employee="${id}" aria-label="${tx("personAction", { action: text(action), name: person.name })}"${pending ? " disabled" : ""}>
                    <span aria-hidden="true">${person.active ? "Ⅱ" : "▶︎"}</span>${tx(action)}</button>
            </div>
            <details class="company-details company-bot-settings" data-bot-editor="${id}"${openBotEditors.has(person.id) ? " open" : ""}>
                <summary>${tx("strategySettings")}${person.bot ? `<strong>${tx(person.bot.strategy)}</strong>` : ""}</summary>
                <div class="company-strategy">
                    <label for="company-strategy-${id}">${tx("strategy")}</label>
                    <select id="company-strategy-${id}" data-employee="${id}" data-setting="strategy"${pending ? " disabled" : ""}>
                        ${["careful", "balanced", "aggressive"].map((choice) => `<option value="${choice}"${choice === strategy ? " selected" : ""}>${tx(choice)}</option>`).join("")}
                    </select>
                    <label for="company-focus-${id}">${tx("focus")}</label>
                    <select id="company-focus-${id}" data-employee="${id}" data-setting="focus"${pending ? " disabled" : ""}>
                        <option value="all">${tx("allStocks")}</option>
                        ${(state.liveAssets ?? []).filter((asset) => asset.unlocked).map((asset) => `<option value="${escape(asset.symbol)}"${asset.symbol === focus ? " selected" : ""}>${escape(localized(asset.name))}</option>`).join("")}
                    </select>
                </div>
                ${renderBotFields(person)}
                ${person.active ? "" : `<p class="company-muted">${tx("pausedGuide")}</p>`}
            </details>
        </article>`;
    }

    function renderPersonnel() {
        const hire = state.hire;
        return `<section class="company-panel company-personnel" aria-labelledby="company-personnel-title">
            <h2 id="company-personnel-title">${tx("personnel")}</h2>
            <p class="company-muted">${tx("personnelGuide")}</p>
            <div class="company-employees">${state.employees.map(renderEmployee).join("")}</div>
            <div class="company-employee-actions">
                ${hire && state.level.number >= hire.unlockLevel ? `<button class="button button-secondary" id="company-hire" type="button"
                    data-command="hire"${pending || !hire.available ? " disabled" : ""}><span aria-hidden="true">+</span>${tx("hire", { name: hire.name, price: money(hire.price) })}</button>` : ""}
                ${hire && state.level.number < hire.unlockLevel ? `<p class="company-muted">${tx("hireLocked", { level: number(hire.unlockLevel) })}</p>` : ""}
            </div>
        </section>`;
    }

    function renderUpgrade() {
        const upgrade = state.upgrade;
        if (!upgrade) return "";
        return `<section class="company-panel company-upgrade" aria-labelledby="company-upgrade-title">
            <div>
                <h2 id="company-upgrade-title">${tx("equipment")}</h2>
                <p class="company-positive">${tx(upgrade.bonus === 1 ? "equipmentOne" : "equipmentBenefit", { count: number(upgrade.bonus) })}</p>
            </div>
            <button class="button button-secondary" id="company-upgrade" type="button" data-command="upgrade"
                ${pending || !upgrade.available ? "disabled" : ""}><span aria-hidden="true">↑</span>${tx("equipmentBuy", { price: money(upgrade.price) })}</button>
        </section>`;
    }

    function renderReport() {
        const reports = state.administration?.reports ?? [];
        const headings = ["reportDay", "reportTrading", "reportEmployees", "reportCost", "reportNet"];
        return `<section class="company-panel company-report" aria-labelledby="company-report-title">
            <h2 id="company-report-title">${tx("reports")}</h2>
            ${reports.length ? `<div class="company-table-scroll"><table class="company-data-table" aria-labelledby="company-report-title">
                <thead><tr>${headings.map((heading) => `<th scope="col">${tx(heading)}</th>`).join("")}</tr></thead>
                <tbody>${reports.map((report) => `<tr>
                    <th scope="row">${number(report.day)}</th>
                    <td class="${tone(report.tradingProfit)}">${money(report.tradingProfit, true)}</td>
                    <td class="${tone(report.employeeProfit)}">${money(report.employeeProfit, true)}</td>
                    <td>${money(-report.operatingCost, true)}</td>
                    <td class="${tone(report.net)}"><strong>${money(report.net, true)}</strong></td>
                </tr>`).join("")}</tbody>
            </table></div>` : `<div class="company-report-empty"><p class="company-muted">${tx("noReports")}</p>
                <a class="button button-secondary" href="#company-admin">${tx("administration")}<span aria-hidden="true">→</span></a></div>`}
        </section>`;
    }

    function render(focusId) {
        for (const node of document.querySelectorAll("[data-company-text]")) {
            node.textContent = text(node.dataset.companyText);
        }
        document.title = text("title") + " · Stock Fight";
        renderNotice();
        if (state) {
            openBotEditors = new Set([...operations.querySelectorAll("[data-bot-editor][open]")].map((editor) => Number(editor.dataset.botEditor)));
            content.innerHTML = `${renderHeader()}${renderNavigation()}`;
            tradeHistory.innerHTML = renderReport();
            operations.innerHTML = `${renderAdministration()}${renderPersonnel()}${renderUpgrade()}`;
        } else if (error) {
            content.innerHTML = `<h1 class="company-title">${tx("title")}</h1>
                <div class="company-retry">${error === "signed_out" ? `<a class="button button-secondary" href="/">${tx("home")}</a>` : `<button class="button button-secondary" type="button" data-command="load">${tx("reload")}</button>`}</div>`;
        } else {
            content.innerHTML = `<h1 class="company-title">${tx("title")}</h1><p class="company-muted">${tx("loading")}</p>`;
        }
        showView();
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

    async function refreshCompany() {
        if (pending || refreshing || !state) return;
        refreshing = true;
        try {
            const response = await fetch("/api/company");
            if (!response.ok) return;
            const latest = await response.json();
            if (!pending && latest.revision > state.revision) {
                state = latest;
                render(document.activeElement?.id);
                publishState();
            }
        } catch {
            // The market will request the updated company again on its next refresh.
        } finally {
            refreshing = false;
        }
    }

    async function send(command, focusId) {
        if (pending || !state) return;
        setBusy(true);
        error = undefined;
        for (const control of workspace.querySelectorAll("button[data-command], select[data-policy], select[data-employee], form[data-bot] :is(button, select, input)")) {
            control.disabled = true;
        }
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
                if (command.action === "set_employee_bot") botDrafts.delete(command.employeeId);
            } else if (response.status === 409 && payload.state) {
                state = payload.state;
                if (payload.market) state.market = payload.market;
                error = payload.error || "stale_revision";
                received = true;
            } else {
                error = response.status === 401 || response.status === 403 ? "signed_out" : (payload.error || "invalid_command");
            }
        } catch {
            error = "network";
        } finally {
            const commandError = error;
            const marketAction = ["buy_peer", "sell_peer", "market_trade"].includes(command.action);
            if (marketAction && error !== "signed_out") error = undefined;
            setBusy(false);
            render(focusId);
            if (received) publishState();
            if (commandError) {
                window.dispatchEvent(new CustomEvent("company:command-error", { detail: { error: commandError, action: command.action } }));
                if (error) notice.scrollIntoView({ block: "nearest" });
            }
        }
    }

    workspace.addEventListener("click", (event) => {
        const link = event.target.closest("a[href^='#company-']");
        if (link && !event.metaKey && !event.ctrlKey && !event.shiftKey && !event.altKey) {
            event.preventDefault();
            if (location.hash !== link.hash) history.pushState(null, "", link.hash);
            showView();
            if (!content.contains(link)) content.querySelector("[aria-current='location']")?.focus({ preventScroll: true });
            return;
        }
        const button = event.target.closest("button[data-command]");
        if (!button || pending) return;
        const { command, employee } = button.dataset;
        if (command === "load") {
            load();
            return;
        }
        const payload = { action: command };
        if (command === "toggle_employee") payload.employeeId = Number(employee);
        send(payload, button.id);
    });

    workspace.addEventListener("change", (event) => {
        const policy = event.target.closest("select[data-policy]");
        if (policy) {
            const command = policy.dataset.policy === "reserve"
                ? { action: "set_reserve_policy", policy: policy.value }
                : { action: "set_desk", desk: policy.value };
            send(command, policy.id);
        }
        const strategy = event.target.closest("select[data-employee]");
        if (strategy) {
            const employeeId = Number(strategy.dataset.employee);
            const command = strategy.dataset.setting === "focus"
                ? { action: "set_employee_focus", employeeId, symbol: strategy.value }
                : { action: "set_employee_strategy", employeeId, strategy: strategy.value };
            send(command, strategy.id);
        }
    });

    workspace.addEventListener("input", (event) => {
        const form = event.target.closest("form[data-bot]");
        if (!form) return;
        const draft = Object.fromEntries(new FormData(form));
        botDrafts.set(Number(form.dataset.bot), draft);
        if (event.target.name === "strategy") form.querySelector("[data-bot-guide]").textContent = text(`${draft.strategy}Guide`);
    });

    workspace.addEventListener("submit", (event) => {
        const form = event.target.closest("form[data-bot]");
        if (!form) return;
        event.preventDefault();
        const { strategy, lookback, threshold, stopLoss, takeProfit } = Object.fromEntries(new FormData(form));
        send({
            action: "set_employee_bot", employeeId: Number(form.dataset.bot), strategy,
            lookback: Number(lookback), threshold: Number(threshold), stopLoss: Number(stopLoss), takeProfit: Number(takeProfit),
        }, event.submitter?.id);
    });

    window.addEventListener("company:market-command", ({ detail }) => {
        if (detail?.action === "market_trade") send(detail, "company-market-submit");
        if (detail?.action === "buy_peer" || detail?.action === "sell_peer") send(detail);
    });
    window.addEventListener("company:refresh", refreshCompany);
    window.addEventListener("hashchange", showView);
    window.addEventListener("stockfight:languagechange", () => render(document.activeElement?.id));
    load();
})();
