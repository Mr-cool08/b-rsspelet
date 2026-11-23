(() => {
    "use strict";

    const content = document.getElementById("company-content");
    const notice = document.getElementById("company-notice");
    const copy = {
        title: ["Börsföretag", "Trading Firms"],
        home: ["Till huvudmenyn", "Main menu"],
        leaderboard: ["Börslistan", "Market leaderboard"],
        loading: ["Laddar börsföretaget …", "Loading your trading firm …"],
        chapterNumber: ["Kapitel {number} av {total}", "Chapter {number} of {total}"],
        chapterWeek: ["Vecka {number} av {total}", "Week {number} of {total}"],
        cash: ["Kassa", "Cash"],
        stockValue: ["Anskaffningsvärde", "Position cost basis"],
        stockSpace: ["Positionsgräns", "Position limit"],
        stockAvailable: ["{count} av {capacity} aktier", "{count} of {capacity} shares"],
        market: ["Veckans marknad", "This week’s market"],
        marketGuide: ["Köp aktier och välj en säljlimit för varje bolag. Lägre kurser lockar fler köpare. Osålda aktier ligger kvar i portföljen.", "Buy shares and choose a sell limit for each stock. Lower prices draw more buyers. Unsold shares carry over."],
        inventory: ["Ägda aktier", "Shares held"],
        unitPrice: ["Köpkurs", "Buy quote"],
        supply: ["Tillgängligt", "Shares on offer"],
        buy: ["Köp aktier", "Buy shares"],
        decreaseBuy: ["Köp en färre aktie i {product}", "Buy one fewer share of {product}"],
        increaseBuy: ["Köp en till aktie i {product}", "Buy one more share of {product}"],
        buyProduct: ["Antal aktier att köpa i {product}", "Shares of {product} to buy"],
        retailPrice: ["Säljlimit", "Sell limit"],
        low: ["Låg", "Low"],
        regular: ["Mellan", "Standard"],
        premium: ["Hög", "High"],
        demand: ["Efterfrågan {count} st.", "Demand {count} shares"],
        retailSales: ["Säljs till marknaden", "Market sales"],
        stockLeft: ["Aktier kvar", "Shares remaining"],
        contract: ["Blockaffär", "Block trade"],
        contractDetails: ["{customer} köper {count} aktier i {product} för {price} per aktie. Blockaffären går före vanliga säljorder.", "{customer} will buy {count} shares of {product} at {price} each. Block trades execute before other sell orders."],
        contractCustomer: ["En extern köpare", "An outside buyer"],
        accept: ["Tacka ja till blockaffären", "Accept the block trade"],
        contractReady: ["Du har tillräckligt många aktier för affären.", "You have enough shares to fill this trade."],
        contractShort: ["Det saknas {count} aktier för affären.", "You need {count} more shares to fill this trade."],
        forecast: ["Nästa veckas marknad", "Next week’s market"],
        forecastGuide: ["Högre köpkurs eller mindre utbud nästa vecka kan göra det lönsamt att behålla aktier.", "A higher buy quote or lower supply next week can make it worthwhile to hold shares."],
        forecastPrice: ["Köpkurs", "Buy quote"],
        forecastProduct: ["Bolag", "Company"],
        forecastTier: ["{price} · {count} st.", "{price} · {count} shares"],
        forecastContract: ["{customer} vill köpa {count} aktier i {product} för {price} per aktie.", "{customer} wants {count} shares of {product} at {price} each."],
        closePreview: ["Beräknat veckoslut", "Projected week end"],
        purchases: ["Inköp", "Purchases"],
        revenue: ["Intäkter", "Revenue"],
        overhead: ["Driftkostnader", "Operating costs"],
        cashAfter: ["Kassa vid veckoslut", "Cash at week end"],
        submit: ["Stäng veckan", "Close the week"],
        rules: ["Köp sker först. Sedan genomförs försäljningen och veckans driftkostnader dras.", "Buys execute first, then sales go through and weekly operating costs are deducted."],
        cashWarning: ["Den här planen ger en negativ kassa. Då får du börja om kapitlet.", "This plan leaves cash below zero. You will have to retry the chapter."],
        goals: ["Kapitlets mål", "Chapter goals"],
        goalProgress: ["{actual} av {target}", "{actual} of {target}"],
        goalProfit: ["Samlad vinst", "Total profit"],
        goalCash: ["Kassa vid kapitlets slut", "Closing cash"],
        goalContracts: ["Genomförda blockaffärer", "Block trades filled"],
        goalUnits: ["Sålda aktier", "Shares sold"],
        met: ["Målet uppnått", "Goal met"],
        weekReport: ["Resultat vecka {week}", "Week {week} results"],
        reportChapter: ["Kapitel {chapter}", "Chapter {chapter}"],
        costOfGoods: ["Anskaffningsvärde för sålda aktier", "Cost basis of shares sold"],
        profit: ["Veckans vinst", "Weekly profit"],
        sold: ["Sålda", "Sold"],
        orderFilled: ["Blockaffären genomförd", "Block trade filled"],
        passed: ["Kapitel {number} avklarat", "Chapter {number} complete"],
        failed: ["Kapitlet behöver spelas om", "Retry this chapter"],
        failedCash: ["Kassan blev negativ den här veckan.", "Cash fell below zero this week."],
        failedGoals: ["Kapitlets mål behöver vara uppnådda när den sista veckan stängs.", "All chapter goals must be met at the end of the final week."],
        retry: ["Spela om kapitlet", "Retry chapter"],
        retryDetails: ["Kassa och aktieinnehav återställs till hur företaget såg ut när kapitlet började.", "Cash and holdings return to where they were at the start of this chapter."],
        won: ["Hela börskarriären är avklarad", "Trading Firms campaign complete"],
        restart: ["Starta ett nytt företag", "Start a new business"],
        restartWarning: ["Vill du starta om hela börskarriären från första veckan?", "Restart the campaign from week one?"],
        reload: ["Försök igen", "Try again"],
        session: ["Logga in igen från huvudmenyn för att spela.", "Sign in again from the main menu to play."],
        network: ["Anslutningen till företaget bröts. Försök igen.", "The connection to your business was lost. Try again."],
        stale_revision: ["Företaget har uppdaterats i en annan flik. Veckans senaste sparade läge visas nu.", "Your business changed in another tab. The latest saved week is now shown."],
        invalid_command: ["Åtgärden gick inte att genomföra.", "The action could not be completed."],
        invalid_status: ["Åtgärden är inte tillgänglig just nu.", "This action is unavailable right now."],
        invalid_purchase: ["Ange ett helt antal aktier inom tillgängligt antal.", "Enter a whole number within the available share quantity."],
        insufficient_cash: ["Kassan räcker inte till inköpen.", "There is not enough cash to pay for the purchases."],
        storage_limit: ["Aktierna får inte överstiga positionsgränsen före försäljningen.", "Your holdings must stay within the position limit before sales."],
        invalid_tier: ["Välj en säljlimit för varje bolag.", "Choose a sell limit for each stock."],
        invalid_contract: ["Ingen blockaffär är tillgänglig den här veckan.", "There is no block trade available this week."],
        insufficient_contract_stock: ["Du har för få aktier för att genomföra blockaffären.", "You need more shares to fill the block trade."],
    };
    const goalLabels = { profit: "goalProfit", cash: "goalCash", contracts: "goalContracts", units: "goalUnits" };
    const locale = () => window.StockFightI18n?.getLocale() || "sv-SE";
    const english = () => locale().startsWith("en");
    const localized = (item) => item[english() ? "en" : "sv"];
    const number = (value, options) => new Intl.NumberFormat(locale(), options).format(value);
    const money = (value, signed = false) => number(value, { maximumFractionDigits: 0, signDisplay: signed ? "exceptZero" : "auto" });
    const byId = (id) => document.getElementById(id);
    const escape = (value) => String(value).replace(/[&<>"']/g, (character) => ({
        "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
    })[character]);

    let state;
    let csrfToken;
    let draft;
    let pending = false;
    let error;

    function text(key, values = {}) {
        return copy[key][english() ? 1 : 0].replace(/\{(\w+)\}/g, (match, name) => Object.hasOwn(values, name) ? values[name] : match);
    }

    const tx = (key, values) => escape(text(key, values));

    function goalValue(goal, value) {
        return goal.type === "cash" || goal.type === "profit" ? money(value) : number(value);
    }

    function receive(next) {
        state = next;
        draft = { purchases: {}, tiers: {}, acceptContract: false };
    }

    function updateNotice() {
        notice.hidden = !error;
        notice.textContent = error ? text(Object.hasOwn(copy, error) ? error : "invalid_command") : "";
    }

    function renderHeader() {
        const { chapter, weekInChapter, weeksInChapter, inventory, capacity } = state;
        const used = Object.values(inventory).reduce((total, units) => total + units, 0);
        return `<header class="company-hero">
            <div>
                <div class="company-calendar">
                    <span>${tx("chapterNumber", { number: chapter.number, total: chapter.total })}</span>
                    <span>${tx("chapterWeek", { number: weekInChapter, total: weeksInChapter })}</span>
                </div>
                <h1 class="company-title" id="company-heading" tabindex="-1">${tx("title")}</h1>
                <h2 class="company-chapter">${escape(localized(chapter.name))}</h2>
                <p class="company-description">${escape(localized(chapter.description))}</p>
                <a class="company-leaderboard-jump" href="#company-standings">${tx("leaderboard")} <span aria-hidden="true">↓</span></a>
            </div>
            <dl class="company-balance">
                <div><dt>${tx("cash")}</dt><dd class="company-cash">${money(state.cash)}</dd></div>
                <div><dt>${tx("stockValue")}</dt><dd>${money(state.inventoryValue)}</dd></div>
                <div class="company-storage"><dt>${tx("stockSpace")}</dt>
                    <dd>${tx("stockAvailable", { count: number(used), capacity: number(capacity) })}
                        <progress value="${used}" max="${capacity}" aria-label="${tx("stockSpace")}"></progress>
                    </dd>
                </div>
            </dl>
        </header>`;
    }

    function renderGoals() {
        return `<section class="company-panel company-goals" aria-labelledby="company-goals-title">
            <h2 id="company-goals-title">${tx("goals")}</h2>
            <ul>${state.chapter.goals.map((goal) => {
                const label = tx(goalLabels[goal.type]);
                const actual = goalValue(goal, goal.actual);
                const target = goalValue(goal, goal.target);
                return `<li><div class="company-goal-line">
                    <span>${label}</span>
                    <strong class="${goal.met ? "company-positive" : ""}">${tx("goalProgress", { actual, target })}</strong>
                </div>
                <progress value="${Math.min(goal.target, Math.max(0, goal.actual))}" max="${goal.target}" aria-label="${label}"></progress>
                ${goal.met ? `<span class="company-goal-met">${tx("met")}</span>` : ""}
                </li>`;
            }).join("")}</ul>
        </section>`;
    }

    function findProductName(market, id) {
        const product = market?.products.find((item) => item.id === id);
        return product ? localized(product.name) : id;
    }

    function contractText(label, market) {
        const contract = market.contract;
        return tx(label, {
            customer: contract.customer ? localized(contract.customer) : text("contractCustomer"),
            count: number(contract.units),
            product: findProductName(market, contract.productId),
            price: money(contract.price),
        });
    }

    function renderForecast(open) {
        const next = state.nextMarket;
        if (!next) return "";
        return `<details class="company-forecast" id="company-forecast"${open ? " open" : ""}>
            <summary>${tx("forecast")}</summary>
            <p class="company-market-note">${escape(localized(next.note))}</p>
            <div class="company-forecast-table" tabindex="0" role="region" aria-label="${tx("forecast")}">
                <table>
                    <thead><tr><th scope="col">${tx("forecastProduct")}</th><th scope="col">${tx("forecastPrice")}</th>
                        <th scope="col">${tx("supply")}</th><th scope="col">${tx("low")}</th>
                        <th scope="col">${tx("regular")}</th><th scope="col">${tx("premium")}</th></tr></thead>
                    <tbody>${next.products.map((product) => `<tr>
                        <th scope="row">${escape(localized(product.name))}</th>
                        <td>${money(product.buyPrice)}</td>
                        <td>${number(product.supply)}</td>
                        ${product.tiers.map((tier) => `<td>${tx("forecastTier", { price: money(tier.price), count: number(tier.demand) })}</td>`).join("")}
                    </tr>`).join("")}</tbody>
                </table>
            </div>
            ${next.contract ? `<p class="company-forecast-order">${contractText("forecastContract", next)}</p>` : ""}
            <p class="company-muted">${tx("forecastGuide")}</p>
        </details>`;
    }

    function renderProduct(product) {
        const id = escape(product.id);
        const name = localized(product.name);
        const tierChoice = draft.tiers[product.id] || "regular";
        const purchase = draft.purchases[product.id] ?? "0";
        return `<section class="company-product" aria-labelledby="product-name-${id}">
            <div class="company-product-top">
                <h3 id="product-name-${id}"><span class="company-symbol company-symbol-${id}">${id}</span>${escape(name)}</h3>
                <dl class="company-product-facts">
                    <div><dt>${tx("inventory")}</dt><dd>${number(state.inventory[product.id] || 0)}</dd></div>
                    <div><dt>${tx("unitPrice")}</dt><dd>${money(product.buyPrice)}</dd></div>
                    <div><dt>${tx("supply")}</dt><dd>${number(product.supply)}</dd></div>
                </dl>
            </div>
            <div class="company-product-actions">
                <div class="company-purchase">
                    <label for="buy-${id}">${tx("buy")}</label>
                    <div class="company-stepper">
                        <button id="less-${id}" type="button" data-step-quantity="-1" data-product="${id}" aria-label="${tx("decreaseBuy", { product: name })}">−</button>
                        <input id="buy-${id}" type="number" inputmode="numeric" min="0" max="${product.supply}" step="1" value="${escape(purchase)}"
                            data-purchase="${id}" aria-label="${tx("buyProduct", { product: name })}">
                        <button id="more-${id}" type="button" data-step-quantity="1" data-product="${id}" aria-label="${tx("increaseBuy", { product: name })}">+</button>
                    </div>
                </div>
                <fieldset class="company-prices">
                    <legend>${tx("retailPrice")}</legend>
                    <div class="company-tiers">${product.tiers.map((tier) => `<label class="company-tier">
                        <input type="radio" name="tier-${id}" id="tier-${id}-${escape(tier.id)}" value="${escape(tier.id)}" data-tier="${id}"${tier.id === tierChoice ? " checked" : ""}>
                        <span class="company-tier-label">${tx(tier.id)}</span>
                        <strong>${money(tier.price)}</strong>
                        <span>${tx("demand", { count: number(tier.demand) })}</span>
                    </label>`).join("")}</div>
                </fieldset>
            </div>
            <dl class="company-product-projection">
                <div><dt>${tx("retailSales")}</dt><dd id="project-sold-${id}"></dd></div>
                <div><dt>${tx("stockLeft")}</dt><dd id="project-stock-${id}"></dd></div>
            </dl>
        </section>`;
    }

    function renderContract() {
        if (!state.market.contract) return "";
        return `<section class="company-contract" aria-labelledby="company-contract-title">
            <h3 id="company-contract-title">${tx("contract")}</h3>
            <p>${contractText("contractDetails", state.market)}</p>
            <label class="company-contract-picker"><input type="checkbox" id="company-contract" ${draft.acceptContract ? "checked" : ""}>
                <span>${tx("accept")}</span></label>
            <p id="company-contract-stock" class="company-muted"></p>
        </section>`;
    }

    function renderMarket(forecastOpen) {
        return `<section class="company-panel company-market" aria-labelledby="company-market-title">
            <div class="company-panel-head"><h2 id="company-market-title">${tx("market")}</h2>
                <p class="company-market-note">${escape(localized(state.market.note))}</p>
            </div>
            ${renderForecast(forecastOpen)}
            <p class="company-guide">${tx("marketGuide")}</p>
            <form id="company-plan" novalidate>
                <div class="company-product-list">${state.market.products.map(renderProduct).join("")}</div>
                ${renderContract()}
                <section class="company-projection" aria-labelledby="projection-title">
                    <h3 id="projection-title">${tx("closePreview")}</h3>
                    <dl class="company-projection-totals">
                        <div><dt>${tx("purchases")}</dt><dd id="project-purchases"></dd></div>
                        <div><dt>${tx("revenue")}</dt><dd id="project-revenue"></dd></div>
                        <div><dt>${tx("overhead")}</dt><dd>${money(-state.overhead, true)}</dd></div>
                        <div><dt>${tx("cashAfter")}</dt><dd id="project-cash"></dd></div>
                    </dl>
                    <dl class="company-projection-storage"><dt>${tx("stockSpace")}</dt><dd id="project-storage"></dd></dl>
                    <p class="company-muted">${tx("rules")}</p>
                    <p id="company-plan-message" class="company-warning" role="status" hidden></p>
                    <button class="button button-primary company-submit" type="submit" id="company-settle">${tx("submit")}</button>
                </section>
            </form>
        </section>`;
    }

    function renderOutcome() {
        const outcome = state.chapterOutcome;
        const restart = `<button class="button button-secondary" id="company-restart" type="button" data-command="restart">${tx("restart")}</button>`;
        if (state.status === "failed") {
            return `<section class="company-panel company-outcome company-loss" aria-labelledby="company-outcome-title">
                <h2 id="company-outcome-title">${tx("failed")}</h2>
                <p>${tx(outcome?.reason === "cash" ? "failedCash" : "failedGoals")}</p>
                <p class="company-muted">${tx("retryDetails")}</p>
                <div class="company-outcome-actions">
                    <button class="button button-primary" id="company-retry" type="button" data-command="retry">${tx("retry")}</button>
                    ${restart}
                </div>
            </section>`;
        }
        if (state.status === "won") {
            return `<section class="company-panel company-outcome company-win" aria-labelledby="company-outcome-title">
                <h2 id="company-outcome-title">${tx("won")}</h2>
                ${restart}
            </section>`;
        }
        return outcome?.status === "passed" ? `<p class="company-stage-complete">${tx("passed", { number: outcome.chapter })}</p>` : "";
    }

    function renderReport() {
        const report = state.lastReport;
        if (!report) return "";
        const market = state.market || state.nextMarket;
        return `<section class="company-panel company-report" aria-labelledby="company-report-title">
            <h2 id="company-report-title">${tx("weekReport", { week: report.weekInChapter })}</h2>
            <p class="company-muted">${tx("reportChapter", { chapter: report.chapter })}</p>
            <dl>
                <div><dt>${tx("revenue")}</dt><dd>${money(report.revenue)}</dd></div>
                <div><dt>${tx("costOfGoods")}</dt><dd>${money(-report.costOfGoods, true)}</dd></div>
                <div><dt>${tx("overhead")}</dt><dd>${money(-report.overhead, true)}</dd></div>
                <div class="company-report-profit"><dt>${tx("profit")}</dt><dd class="${report.profit < 0 ? "company-negative" : "company-positive"}">${money(report.profit, true)}</dd></div>
                <div><dt>${tx("cashAfter")}</dt><dd>${money(report.cash)}</dd></div>
            </dl>
            ${report.contractFulfilled ? `<p class="company-goal-met">${tx("orderFilled")}</p>` : ""}
            <table>
                <thead><tr><th scope="col">${tx("forecastProduct")}</th><th scope="col">${tx("sold")}</th><th scope="col">${tx("inventory")}</th></tr></thead>
                <tbody>${report.products.map((product) => `<tr><th scope="row">${escape(findProductName(market, product.id))}</th>
                    <td>${number(product.sold)}</td><td>${number(product.stock)}</td></tr>`).join("")}</tbody>
            </table>
        </section>`;
    }

    function buildPlan() {
        const items = state.market.products.map((product) => {
            const quantity = Number(draft.purchases[product.id] || 0);
            const valid = Number.isInteger(quantity) && quantity >= 0 && quantity <= product.supply;
            const purchased = valid ? quantity : 0;
            const available = (state.inventory[product.id] || 0) + purchased;
            const tier = product.tiers.find(({ id }) => id === (draft.tiers[product.id] || "regular"));
            return { product, valid, purchased, available, tier };
        });
        const contract = state.market.contract;
        const contractProduct = contract && items.find(({ product }) => product.id === contract.productId);
        const shortfall = contract ? Math.max(0, contract.units - contractProduct.available) : 0;
        const rows = items.map((item) => {
            const reserved = item === contractProduct && draft.acceptContract && shortfall === 0 ? contract.units : 0;
            const sold = Math.min(item.available - reserved, item.tier.demand);
            return { ...item, sold, stock: item.available - reserved - sold, revenue: sold * item.tier.price + reserved * (contract?.price || 0) };
        });
        const purchaseCost = rows.reduce((total, { purchased, product }) => total + purchased * product.buyPrice, 0);
        const revenue = rows.reduce((total, row) => total + row.revenue, 0);
        const storage = rows.reduce((total, row) => total + row.available, 0);
        const cash = state.cash - purchaseCost + revenue - state.overhead;
        let problem;
        if (rows.some(({ valid }) => !valid)) problem = "invalid_purchase";
        else if (purchaseCost > state.cash) problem = "insufficient_cash";
        else if (storage > state.capacity) problem = "storage_limit";
        else if (draft.acceptContract && shortfall > 0) problem = "insufficient_contract_stock";
        return { rows, purchaseCost, revenue, storage, cash, shortfall, problem };
    }

    function paintPlan() {
        if (state?.status !== "planning") return;
        const plan = buildPlan();
        const write = (id, value) => { byId(id).textContent = value; };
        for (const { product, sold, stock, purchased, valid } of plan.rows) {
            const id = product.id;
            write(`project-sold-${id}`, number(sold));
            write(`project-stock-${id}`, number(stock));
            byId(`less-${id}`).disabled = pending || (valid && purchased === 0);
            byId(`more-${id}`).disabled = pending || (valid && purchased === product.supply);
            byId(`buy-${id}`).setAttribute("aria-invalid", String(!valid));
        }

        write("project-purchases", money(-plan.purchaseCost, true));
        write("project-revenue", money(plan.revenue, true));
        write("project-cash", money(plan.cash));
        write("project-storage", text("stockAvailable", { count: number(plan.storage), capacity: number(state.capacity) }));
        byId("project-cash").classList.toggle("company-negative", plan.cash < 0);
        byId("project-storage").classList.toggle("company-negative", plan.storage > state.capacity);

        if (state.market.contract) {
            write("company-contract-stock", plan.shortfall ?
                text("contractShort", { count: number(plan.shortfall) }) : text("contractReady"));
        }

        const warning = plan.problem || (plan.cash < 0 ? "cashWarning" : null);
        const message = byId("company-plan-message");
        message.hidden = !warning;
        message.textContent = warning ? text(warning) : "";
        byId("company-settle").disabled = pending || Boolean(plan.problem);
    }

    function render(focusId) {
        const active = document.activeElement;
        const focus = focusId ?? (content.contains(active) ? active.id : "");
        const forecastOpen = byId("company-forecast")?.open ?? false;
        for (const item of document.querySelectorAll("[data-company-text]")) {
            item.textContent = text(item.dataset.companyText);
        }
        document.title = `${text("title")} · Stock Fight`;
        updateNotice();
        content.setAttribute("aria-busy", String(pending));
        if (state) {
            const planning = state.status === "planning";
            content.innerHTML = `${renderHeader()}
                <div class="company-workspace">
                    ${renderGoals()}
                    <div class="company-desk">${renderOutcome()}${planning ? renderMarket(forecastOpen) : ""}</div>
                    ${renderReport()}
                </div>`;
            paintPlan();
        } else if (error) {
            content.innerHTML = `<h1 class="company-title" id="company-heading" tabindex="-1">${tx("title")}</h1>
                <div class="company-load-actions">${error === "session" ? `<a class="button button-secondary" href="/">${tx("home")}</a>` :
                `<button class="button button-secondary" type="button" id="company-load" data-load>${tx("reload")}</button>`}</div>`;
        } else {
            content.innerHTML = `<h1 class="company-title">${tx("title")}</h1><p class="company-description">${tx("loading")}</p>`;
        }
        if (focus) byId(focus)?.focus({ preventScroll: !focusId });
    }

    async function load() {
        pending = true;
        error = undefined;
        render();
        try {
            const [account, company] = await Promise.all([fetch("/api/me"), fetch("/api/company")]);
            if (company.status === 401) {
                error = "session";
            } else if (account.ok && company.ok) {
                csrfToken = (await account.json()).csrfToken;
                receive(await company.json());
            } else {
                error = "network";
            }
        } catch {
            error = "network";
        } finally {
            pending = false;
            render();
        }
    }

    async function send(command) {
        if (pending) return;
        pending = true;
        error = undefined;
        updateNotice();
        content.setAttribute("aria-busy", "true");
        for (const button of content.querySelectorAll("button")) button.disabled = true;
        let shouldFocus = false;
        try {
            const response = await fetch("/api/company/commands", {
                method: "POST",
                headers: { "Content-Type": "application/json", "X-CSRF-Token": csrfToken },
                body: JSON.stringify({ ...command, revision: state.revision }),
            });
            const payload = await response.json();
            if (response.ok) {
                receive(payload);
                shouldFocus = true;
            } else if (response.status === 409 && payload.state) {
                receive(payload.state);
                error = "stale_revision";
                shouldFocus = true;
            } else {
                error = response.status === 401 || response.status === 403 ? "session" : (payload.error || "invalid_command");
            }
        } catch {
            error = "network";
        } finally {
            pending = false;
            render(shouldFocus ? "company-heading" : undefined);
            if (shouldFocus) window.dispatchEvent(new Event("company:updated"));
            if (error) notice.scrollIntoView({ block: "nearest" });
        }
    }

    content.addEventListener("input", (event) => {
        if (event.target.dataset.purchase) {
            draft.purchases[event.target.dataset.purchase] = event.target.validity.badInput ? "invalid" : event.target.value;
            paintPlan();
        }
    });

    content.addEventListener("change", (event) => {
        const control = event.target;
        if (control.dataset.tier) {
            draft.tiers[control.dataset.tier] = control.value;
            paintPlan();
        } else if (control.id === "company-contract") {
            draft.acceptContract = control.checked;
            paintPlan();
        }
    });

    content.addEventListener("click", (event) => {
        const button = event.target.closest("button");
        if (!button || pending) return;
        const { product, stepQuantity, command } = button.dataset;
        if (stepQuantity) {
            const input = byId(`buy-${product}`);
            const current = Math.trunc(Number(input.value)) || 0;
            input.value = Math.min(Number(input.max), Math.max(0, current + Number(stepQuantity)));
            draft.purchases[product] = input.value;
            paintPlan();
        } else if (command) {
            if (command === "restart" && !window.confirm(text("restartWarning"))) return;
            send({ action: command });
        } else if (button.hasAttribute("data-load")) {
            load();
        }
    });

    content.addEventListener("submit", (event) => {
        if (event.target.id !== "company-plan") return;
        event.preventDefault();
        const plan = buildPlan();
        if (plan.problem) return;
        send({
            action: "settle",
            purchases: Object.fromEntries(plan.rows.map(({ product, purchased }) => [product.id, purchased])),
            tiers: Object.fromEntries(plan.rows.map(({ product, tier }) => [product.id, tier.id])),
            acceptContract: draft.acceptContract,
        });
    });

    window.addEventListener("stockfight:languagechange", () => render());
    load();
})();
