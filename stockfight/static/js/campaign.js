(() => {
    "use strict";

    const content = document.getElementById("career-content");
    const notice = document.getElementById("career-notice");
    const copy = {
        career: ["Börskarriär", "Market Career"],
        office: ["Fondkontoret", "Fund office"],
        home: ["Till huvudmenyn", "Main menu"],
        loading: ["Laddar fondkontoret …", "Loading the fund office …"],
        role: ["Din roll", "Your role"],
        roleProgress: ["Fasta {fixed}/3 · Valbara {elective}/5", "Core {fixed}/3 · Electives {elective}/5"],
        roleComplete: ["Hela karriären klar", "Career complete"],
        stages: ["Karriärsteg", "Career stages"],
        ranks: ["Lärling|Analytiker|Juniorförvaltare|Portföljförvaltare|Seniorförvaltare|Fondchef",
            "Trainee|Analyst|Junior fund manager|Portfolio manager|Senior fund manager|Fund director"],
        cleared: ["Avklarat", "Completed"],
        current: ["Aktuellt", "Current"],
        locked: ["Låst", "Locked"],
        mandates: ["Kundmandat", "Client mandates"],
        fixed: ["Fasta mandat", "Core mandates"],
        elective: ["Valbara mandat", "Elective mandates"],
        exam: ["Slutprov", "Crisis exam"],
        comeback: ["Comebackuppdrag", "Recovery mandate"],
        passed: ["Godkänt", "Passed"],
        mastery: ["Mästarmål", "Mastery target"],
        best: ["Bästa resultat", "Best result"],
        examDuration: ["{count} min realtid", "{count} min of live trading"],
        dayDuration: ["{count} börsdagar", "{count} market days"],
        requirements: ["Mål", "Goals"],
        stocks: ["Aktier", "Stocks"],
        details: ["Om uppdraget", "About the mandate"],
        capital: ["Startkapital", "Starting capital"],
        credits: ["{amount} krediter", "{amount} credits"],
        tools: ["Verktyg", "Tools"],
        slots: ["{used} av {max} valda", "{used} of {max} selected"],
        analysis: ["Analysvy", "Correlation view"],
        analysisDesc: ["Se vilka aktier som rör sig tillsammans.", "See which stocks move together."],
        stop: ["Automatisk säljorder", "Automatic sell order"],
        stopDesc: ["Sälj vid en stoppkurs eller ett vinstmål.", "Sell at a stop price or profit target."],
        extra: ["Extra ombalansering", "Extra rebalance"],
        extraDesc: ["Ändra din portfölj en extra gång.", "Change your portfolio one more time."],
        start: ["Starta mandat", "Start mandate"],
        startExam: ["Starta slutprov", "Start exam"],
        startComeback: ["Starta comeback", "Start recovery mandate"],
        replay: ["Spela om", "Play again"],
        lockedExam: ["Klara tre fasta och fem valbara mandat för att låsa upp slutprovet.", "Pass three core and five elective mandates to unlock the exam."],
        lockedComeback: ["Klara comebackuppdraget för att försöka igen.", "Pass the recovery mandate to try again."],
        lockedStage: ["Klara det föregående karriärsteget för att spela här.", "Complete the previous career stage to play here."],
        lockedFirst: ["Klara ditt första mandat för att låsa upp resten.", "Complete your first mandate to unlock the rest."],
        activeExists: ["Avsluta ditt pågående mandat innan du startar ett nytt.", "Finish your current mandate before starting a new one."],
        active: ["Pågående mandat", "Mandate in progress"],
        resume: ["Fortsätt mandat", "Resume mandate"],
        results: ["Se resultat", "View report"],
        toOffice: ["Till fondkontoret", "Fund office"],
        trading: ["Handel", "Trading"],
        preview: ["Inför första börsdagen", "Before the first market day"],
        day: ["Dag {day} av {total}", "Day {day} of {total}"],
        phase: ["Fas {phase} av 3", "Phase {phase} of 3"],
        value: ["Portföljvärde", "Portfolio value"],
        cash: ["Kassa", "Cash"],
        return: ["Din avkastning", "Your return"],
        benchmark: ["Index", "Benchmark"],
        marketChart: ["Följ kurserna", "Market prices"],
        portfolioChart: ["Jämför portföljen", "Compare portfolio"],
        portfolio: ["Portföljen", "Portfolio"],
        chartLabel: ["Kursgraf, indexerad till 100 vid start", "Price chart, indexed to 100 at the start"],
        chartUnavailable: ["Kursgrafen kunde inte laddas.", "The chart could not load."],
        allocate: ["Fördela startkapitalet", "Allocate your starting capital"],
        rebalance: ["Ändra portföljen", "Rebalance your portfolio"],
        feesDesc: ["Handelsavgift 0,1 %", "Trading fee 0.1%"],
        allocateSubmit: ["Bekräfta fördelning", "Confirm allocation"],
        rebalanceSubmit: ["Bekräfta ändring", "Confirm changes"],
        rebalances: ["{count} ändringar kvar", "{count} changes left"],
        evenSplit: ["Jämn mix", "Even split"],
        allCash: ["Allt i kassa", "All cash"],
        lessWeight: ["Minska {asset} med 10 procentenheter", "Decrease {asset} by 10 percentage points"],
        moreWeight: ["Öka {asset} med 10 procentenheter", "Increase {asset} by 10 percentage points"],
        weightLimit: ["Högst {value} per aktie", "Up to {value} per stock"],
        nextDay: ["Nästa handelsdag", "Next trading day"],
        lastDay: ["Spela sista dagen", "Play final day"],
        phaseFirst: ["Ny kurs var 5:e sekund", "New prices every 5 seconds"],
        phaseStart: ["Starta fas", "Start phase"],
        timeLeft: ["Tid kvar", "Time left"],
        holdings: ["Innehav", "Holdings"],
        price: ["Kurs", "Price"],
        move: ["Rörelse", "Move"],
        weight: ["Vikt", "Weight"],
        newWeight: ["Ny vikt", "New weight"],
        stockWeight: ["Ny vikt för {asset}", "New weight for {asset}"],
        cashAfter: ["Kassa efter ändring", "Cash after allocation"],
        placeStop: ["Lägg säljorder", "Place sell order"],
        lossStop: ["Stoppkurs", "Stop-loss"],
        profitStop: ["Vinstmål", "Take-profit"],
        currentQuote: ["Nu {price}", "Now {price}"],
        holdTarget: ["Målkurs", "Target price"],
        stopPrice: ["Stoppkurs", "Stop price"],
        stopStatus: ["Sälj {asset} vid {comparison} {price}", "Sell {asset} at {comparison} {price}"],
        analysisPair: ["{asset} och {other}", "{asset} and {other}"],
        analysisMethod: ["Samvariation utifrån de senaste visade kurserna. +1 betyder att kurserna rört sig åt samma håll och −1 åt motsatt håll.", "Correlation uses recent revealed prices. +1 means prices moved together and −1 means prices moved in opposite directions."],
        abandon: ["Avsluta mandat", "End mandate"],
        confirmAbandon: ["Vill du avsluta det här försöket?", "End this attempt?"],
        examAbandon: ["Avslutar du efter att krisen har startat behöver du klara comebackuppdraget inför nästa försök.", "If you end an exam after the crisis starts, you must pass the recovery mandate before trying again."],
        goalIndex: ["Mot index", "Vs. benchmark"],
        beatIndex: ["Matcha eller slå index", "Match or beat the benchmark"],
        goalDrawdown: ["Högsta nedgång", "Maximum drawdown"],
        goalCash: ["Kassa vid handelsdag {step}", "Cash on trading day {step}"],
        goalPhaseCash: ["Kassa vid slutet av fas {phase}", "Cash at the end of phase {phase}"],
        goalStepCash: ["Kassa vid kurspunkt {step}", "Cash at price point {step}"],
        goalExposure: ["Lägsta aktieandel", "Minimum stock exposure"],
        goalConcentration: ["Högsta målvikt per aktie", "Maximum target weight per stock"],
        goalReturn: ["Slutavkastning", "Final return"],
        minimum: ["Minst {value}", "At least {value}"],
        maximum: ["Högst {value}", "At most {value}"],
        actual: ["Utfall {value}", "Actual {value}"],
        met: ["Uppnått", "Met"],
        missed: ["Missat", "Missed"],
        waiting: ["Väntar", "Pending"],
        progress: ["Hittills {value}", "So far {value}"],
        report: ["Resultatrapport", "Mandate report"],
        reportPassed: ["Mandatet godkänt", "Mandate passed"],
        reportFailed: ["Mandatet behöver spelas om", "Mandate needs another try"],
        reportAbandoned: ["Mandatet avbrutet", "Mandate ended early"],
        reportMastered: ["Mästarmålet uppnått", "Mastery target met"],
        fees: ["Avgifter", "Fees"],
        worst: ["Störst nedgång", "Worst drawdown"],
        worstAt: ["Nedgången var som störst vid steg {step}.", "The largest drawdown was at step {step}."],
        finalPromotion: ["Fondchef – karriären klar", "Fund director – career complete"],
        promotion: ["Befordran till {rank}", "Promoted to {rank}"],
        afterPromotion: ["Välj nya mandat eller förbättra dina tidigare resultat från fondkontoret.", "Choose new mandates or improve your past results from the fund office."],
        viewRecovery: ["Se comebackuppdrag", "View recovery mandate"],
        toExam: ["Till slutprovet", "Go to exam"],
        loadError: ["Fondkontoret gick inte att öppna.", "The fund office could not be opened."],
        loadRetry: ["Försök igen", "Try again"],
        login_required: ["Din session har gått ut. Logga in igen via huvudmenyn.", "Your session has expired. Sign in again from the main menu."],
        connection: ["Kontrollera anslutningen och försök igen.", "Check your connection and try again."],
        invalid_mission: ["Mandatet finns inte.", "This mandate does not exist."],
        locked_mission: ["Mandatet är låst.", "This mandate is locked."],
        attempt_active: ["Du har redan ett pågående mandat.", "A mandate is already in progress."],
        no_attempt: ["Du har inget pågående mandat.", "There is no active mandate."],
        invalid_tools: ["Välj tillgängliga verktyg inom gränsen för din roll.", "Choose available tools within your role's limit."],
        invalid_weights: ["Ange vikterna i steg om 10 %. Summan får vara högst 100 %.", "Use increments of 10%. The weights must add up to 100% or less."],
        concentration_limit: ["En vikt är högre än mandatet tillåter.", "A weight exceeds the mandate's limit."],
        invalid_phase: ["Du kan inte göra det här i den aktuella fasen.", "This action is unavailable in the current phase."],
        no_rebalances: ["Dina ombalanseringar är slut.", "You have no rebalances left."],
        stale_quote: ["Kursen hann ändras. Kontrollera den senaste kursen och försök igen.", "The price changed. Review the latest quote and try again."],
        invalid_stop: ["Välj ett innehav och ange en stoppkurs under nuvarande kurs.", "Choose a holding and enter a stop price below the current price."],
        invalid_profit_target: ["Välj ett innehav och sätt vinstmålet över aktuell kurs.", "Choose a holding and set the profit target above the current price."],
        stop_unavailable: ["Stopporder är inte tillgänglig.", "The stop order is unavailable."],
        stale_revision: ["Mandatet har uppdaterats. Kontrollera läget och försök igen.", "The mandate has changed. Review the current state and try again."],
        invalid_command: ["Åtgärden gick inte att genomföra.", "The action could not be completed."],
        sessionExpired: ["Uppdatera sidan för att återansluta till ditt konto.", "Reload the page to reconnect to your account."],
    };

    let state;
    let csrf;
    let pending = false;
    let polling = false;
    let browseRank = 0;
    let selectedMission;
    let chosenTools = [];
    let office = true;
    let chartMode = "market";
    let chart;
    let weights = {};
    let stopDraft = {};
    let deadline;
    let errorCode;

    const locale = () => window.StockFightI18n?.getLocale() ?? "sv-SE";
    const isEnglish = () => locale().startsWith("en");
    function translate(key, params = {}) {
        const translation = copy[key]?.[Number(isEnglish())] ?? key;
        return translation.replace(/\{(\w+)\}/g, (match, name) => params[name] ?? match);
    }

    function escapeHTML(str) {
        return String(str ?? "").replace(/[&<>"']/g, (character) => ({
            "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
        })[character]);
    }

    const tx = (key, params) => escapeHTML(translate(key, params));
    const title = (mission) => escapeHTML(isEnglish() ? mission.titleEn : mission.title);
    const brief = (mission) => escapeHTML(isEnglish() ? mission.briefEn : mission.brief);
    const findMission = (id) => state.missions.find((mission) => mission.id === id);
    const last = (items) => items[items.length - 1];
    const maxRank = () => state.ranks.length - 1;
    const currentStage = () => Math.min(state.rank, maxRank() - 1);
    const rankName = (index) => translate("ranks").split("|")[index] ?? state.ranks[index];

    function number(value, digits = 2) {
        if (value == null) return "–";
        return new Intl.NumberFormat(locale(), { minimumFractionDigits: digits, maximumFractionDigits: digits }).format(value);
    }

    function percent(value, signed = false) {
        if (value == null) return "–";
        return new Intl.NumberFormat(locale(), {
            style: "percent", signDisplay: signed ? "exceptZero" : "auto", maximumFractionDigits: 2,
        }).format(value / 100);
    }

    function button(label, action, { primary = false, disabled = false } = {}) {
        const icon = { start: "▶", retry: "↻", resume: "▶", phase: "▶", advance: "→", office: "←" }[action];
        return `<button type="button" class="career-button${primary ? " career-button-primary" : ""}"
            id="button-${action}" data-action="${action}"${disabled ? " disabled" : ""}>
            ${icon ? `<span class="career-button-icon" aria-hidden="true">${icon}</span>` : ""}${tx(label)}</button>`;
    }

    function goalTitle(goal, mission) {
        const titles = { index: "goalIndex", drawdown: "goalDrawdown", exposure: "goalExposure",
            concentration: "goalConcentration", return: "goalReturn" };
        if (goal.type === "cash") {
            if (mission.kind !== "exam") return tx("goalCash", { step: goal.step });
            return goal.step % 12 === 0 ? tx("goalPhaseCash", { phase: goal.step / 12 }) : tx("goalStepCash", { step: goal.step });
        }
        return tx(titles[goal.type] ?? goal.type);
    }

    const goalValue = (goal, value) => goal.type === "index" ? number(value) + (isEnglish() ? " pp" : " p.e.") : percent(value);

    function goalsList(goals, mission, showActual = false) {
        return `<ul class="career-goals">${goals.map((goal) => {
            const atMost = goal.type === "drawdown" || goal.type === "concentration";
            const target = tx(atMost ? "maximum" : "minimum", { value: goalValue(goal, goal.value) });
            let outcome = target;
            if (showActual) {
                const live = showActual === "live" && goal.type !== "cash";
                const actual = goal.actual == null ? tx("waiting") : tx(live ? "progress" : "actual", { value: goalValue(goal, goal.actual) });
                const verdict = goal.met == null || live ? "" : `<strong class="${goal.met ? "career-goal-pass" : "career-goal-fail"}">${tx(goal.met ? "met" : "missed")}</strong>`;
                outcome = verdict ? `${verdict}<small>${actual}</small>` : actual;
            }
            const matchIndex = goal.type === "index" && goal.value === 0;
            const label = matchIndex && !showActual ? tx("beatIndex") : goalTitle(goal, mission);
            return `<li><span>${label}${showActual ? `<small>${target}</small>` : ""}</span>${matchIndex && !showActual ? "" : `<span>${outcome}</span>`}</li>`;
        }).join("")}</ul>`;
    }

    function renderNotice(code) {
        errorCode = code;
        notice.hidden = !code;
        notice.textContent = code ? translate(copy[code] ? code : "invalid_command") : "";
    }

    function rankProgress() {
        let fixed = 0;
        let elective = 0;
        for (const mission of state.missions) {
            if (mission.rank !== state.rank || !state.achievements[mission.id]?.passed) continue;
            if (mission.kind === "fixed") fixed++;
            if (mission.kind === "elective") elective++;
        }
        return { fixed, elective: Math.min(elective, 5) };
    }

    function missionStatus(mission) {
        const award = state.achievements[mission.id];
        if (award?.mastered) return [tx("mastery"), "career-mastered", "★"];
        if (award?.passed) return [tx("passed"), "career-goal-pass", "✓"];
        if (!mission.available) return [tx("locked"), ""];
        return [tx(mission.kind === "exam" ? "examDuration" : "dayDuration", {
            count: mission.kind === "exam" ? 3 : mission.steps,
        }), ""];
    }

    function missionList(missions, kind) {
        if (!missions.length) return "";
        return `<h3>${tx(kind)}</h3><ul class="career-options">${missions.map((mission) => {
            const [caption, statusClass, mark] = missionStatus(mission);
            return `<li><button class="career-mission" type="button" id="pick-${escapeHTML(mission.id)}" data-action="pick"
                data-kind="${escapeHTML(mission.kind)}" data-mission="${escapeHTML(mission.id)}" aria-pressed="${selectedMission === mission.id}">
                <strong>${title(mission)}</strong><small class="${statusClass}">${mark ? `<span aria-hidden="true">${mark} </span>` : ""}${caption}</small></button></li>`;
        }).join("")}</ul>`;
    }

    function lockedReason(mission) {
        if (mission.rank > state.rank) return "lockedStage";
        if (state.comeback && mission.kind === "exam") return "lockedComeback";
        return mission.kind === "exam" ? "lockedExam" : "lockedFirst";
    }

    function renderBriefing(mission) {
        const active = state.attempt && state.attempt.status !== "complete";
        const tools = state.tools.filter((tool) => tool.available);
        const award = state.achievements[mission.id];
        const startLabel = award?.passed ? "replay" :
            ({ exam: "startExam", comeback: "startComeback" })[mission.kind] ?? "start";
        return `<section id="career-briefing" class="career-briefing" aria-labelledby="career-briefing-title">
            <div class="career-briefing-header">
                <h2 tabindex="-1" id="career-briefing-title">${title(mission)}</h2>
                <div class="career-funding"><span>${tx("capital")}</span>
                    <strong>${tx("credits", { amount: number(mission.capital, 0) })}</strong></div>
            </div>
            <div class="career-briefing-block">
                <h3>${tx("requirements")}</h3>${goalsList(mission.goals, mission)}
            </div>
            ${award ? `<div class="career-briefing-block">
                <dl class="career-best"><dt>${tx("best")}</dt><dd>${escapeHTML(percent(award.score, true))}</dd></dl>
            </div>` : ""}
            ${tools.length && mission.available ? `<div class="career-briefing-block">
                <div class="career-section-header"><h3>${tx("tools")}</h3>
                <span class="career-muted career-slot-caption" id="career-tool-count">${tx("slots", { used: chosenTools.length, max: state.toolSlots })}</span></div>
                ${tools.map((tool) => {
                    const checked = chosenTools.includes(tool.id);
                    return `<label class="career-tool">
                        <input type="checkbox" data-tool="${escapeHTML(tool.id)}"${checked ? " checked" : ""}
                            ${!checked && chosenTools.length >= state.toolSlots ? " disabled" : ""}>
                        <span>${tx(tool.id)}<small>${tx(tool.id + "Desc")}</small></span>
                    </label>`;
                }).join("")}</div>` : ""}
            <div class="career-actions">${button(startLabel, "start", { primary: true, disabled: Boolean(active) || !mission.available })}
                ${!mission.available ? `<p class="career-catalog-note">${tx(lockedReason(mission))}</p>` :
                    active ? `<p class="career-catalog-note">${tx("activeExists")}</p>` : ""}
            </div>
            <details class="career-briefing-block career-briefing-details">
                <summary>${tx("details")}</summary>
                <p class="career-catalog-note">${brief(mission)}</p>
                <ul class="career-symbols" aria-label="${tx("stocks")}">${mission.assets.map((asset) =>
                    `<li><strong>${escapeHTML(asset)}</strong> ${escapeHTML(state.assetNames?.[asset] ?? "")}</li>`).join("")}</ul>
                ${mission.mastery ? `<h3>${tx("mastery")}</h3>${goalsList([mission.mastery], mission)}` : ""}
            </details>
        </section>`;
    }

    function renderOffice() {
        const progress = rankProgress();
        const stageMissions = state.missions.filter((mission) => mission.rank === browseRank &&
            (mission.kind !== "comeback" || state.comeback === mission.id));
        if (!stageMissions.some((mission) => mission.id === selectedMission)) {
            selectedMission = (stageMissions.find((mission) => mission.id === state.comeback) ?? stageMissions[0])?.id;
        }
        const mission = findMission(selectedMission);
        const resume = state.attempt && findMission(state.attempt.missionId);
        const isComplete = state.attempt?.status === "complete";
        return `<header class="career-intro">
            <div><p class="career-kicker">${tx("office")}</p><h1 tabindex="-1" id="career-heading">${tx("career")}</h1></div>
            <div class="career-rank"><p class="career-kicker">${tx("role")}</p><strong>${escapeHTML(rankName(state.rank))}</strong>
                <small>${state.rank === maxRank() ? tx("roleComplete") : tx("roleProgress", progress)}</small>
                <progress class="career-progress" max="8" value="${state.rank === maxRank() ? 8 : progress.fixed + progress.elective}" aria-label="${tx("role")}"></progress>
            </div>
        </header>
        ${resume ? `<aside class="career-resume">
            <div><strong>${title(resume)}</strong><p class="career-muted">${tx(isComplete ? "report" : "active")}</p></div>
            ${button(isComplete ? "results" : "resume", "resume", { primary: true })}</aside>` : ""}
        <nav class="career-rank-tabs" aria-label="${tx("stages")}">
            ${state.ranks.slice(0, -1).map((_, index) =>
                `<button type="button" id="rank-${index}" data-action="rank" data-rank="${index}" aria-pressed="${index === browseRank}">
                    ${escapeHTML(rankName(index))}<span>${tx(index < state.rank ? "cleared" : index === state.rank ? "current" : "locked")}</span></button>`
            ).join("")}
        </nav>
        <div class="career-office">
            <section class="career-list" aria-labelledby="career-catalog-title">
                <div class="career-section-header"><h2 id="career-catalog-title">${tx("mandates")}</h2></div>
                ${["comeback", "fixed", "elective", "exam"].map((kind) =>
                    missionList(stageMissions.filter((item) => item.kind === kind), kind)).join("")}
            </section>
            ${mission ? renderBriefing(mission) : ""}
        </div>`;
    }

    function metrics(items) {
        return `<dl class="career-metrics">${items.map(([label, value, color, detail]) =>
            `<div><dt>${tx(label)}</dt><dd class="${color ?? ""}">${escapeHTML(value)}
                ${detail ? `<small>${escapeHTML(detail)}</small>` : ""}</dd></div>`).join("")}</dl>`;
    }

    const signedClass = (value) => value > 0 ? "career-goal-pass" : value < 0 ? "career-goal-fail" : "";

    function chartOptions() {
        return `<div class="career-chart-controls">
            <button type="button" id="chart-market" class="career-button" data-action="chart" data-mode="market" aria-pressed="${chartMode === "market"}">${tx("marketChart")}</button>
            <button type="button" id="chart-portfolio" class="career-button" data-action="chart" data-mode="portfolio" aria-pressed="${chartMode === "portfolio"}">${tx("portfolioChart")}</button>
        </div>
        <div id="career-chart-slot"></div><ul class="career-chart-legend" id="career-chart-legend"></ul>`;
    }

    function holdings(mission, attempt, editable) {
        const prices = last(attempt.prices).prices;
        const prior = attempt.prices.at(-2).prices;
        const setup = attempt.status === "setup";
        return `<table class="career-allocation-items">
            <thead><tr><th scope="col">${tx("stocks")}</th><th scope="col">${tx("price")}</th><th scope="col">${tx("move")}</th>
                ${setup ? "" : `<th scope="col">${tx("weight")}</th>`}
                ${editable ? `<th scope="col">${tx("newWeight")}</th>` : ""}</tr></thead>
            <tbody>${mission.assets.map((asset, index) => {
                const symbol = escapeHTML(asset);
                const move = (prices[index] / prior[index] - 1) * 100;
                return `<tr><th scope="row" title="${escapeHTML(state.assetNames[asset])}">
                    <span class="career-symbol-dot" style="--stock-color:${colors[index]}" aria-hidden="true"></span>${symbol}</th>
                    <td>${escapeHTML(number(prices[index]))}</td>
                    <td class="${signedClass(move)}">${escapeHTML(percent(move, true))}</td>
                    ${setup ? "" : `<td>${escapeHTML(percent(attempt.weights[asset]))}</td>`}
                    ${editable ? `<td><div class="career-stepper" role="group" aria-label="${tx("stockWeight", { asset })}">
                        <button type="button" id="less-${symbol}" data-action="weight" data-asset="${symbol}" data-delta="-10" aria-label="${tx("lessWeight", { asset })}">−</button>
                        <output id="weight-${symbol}" for="less-${symbol} more-${symbol}"></output>
                        <button type="button" id="more-${symbol}" data-action="weight" data-asset="${symbol}" data-delta="10" aria-label="${tx("moreWeight", { asset })}">+</button>
                    </div></td>` : ""}</tr>`;
            }).join("")}</tbody></table>`;
    }

    function maxWeight(mission) {
        const cap = mission.goals.find((goal) => goal.type === "concentration")?.value ?? 100;
        return Math.floor(cap / 10) * 10;
    }

    function allocation(mission, attempt) {
        const setup = attempt.status === "setup";
        const planning = attempt.status === "phaseReady";
        const active = ["trading", "phaseActive"].includes(attempt.status);
        const canTrade = active && (attempt.rebalances > 0 || attempt.extraAvailable);
        const changes = attempt.rebalances + Number(attempt.extraAvailable);
        if (!setup && !canTrade && !planning) {
            return `<h3>${tx("holdings")}</h3>
                <p class="career-trade-hints">${tx("rebalances", { count: changes })}</p>
                ${holdings(mission, attempt, false)}`;
        }
        const limit = maxWeight(mission);
        return `<form id="career-allocation">
            <fieldset class="career-allocation">
                <legend>${tx(setup ? "allocate" : "rebalance")}</legend>
                <div class="career-trade-hints"><span>${tx("feesDesc")}</span>
                    ${setup || planning ? "" : `<span>${tx("rebalances", { count: changes })}</span>`}
                    ${limit < 100 ? `<span>${tx("weightLimit", { value: percent(limit) })}</span>` : ""}</div>
                <div class="career-presets">${button("evenSplit", "split")}${button("allCash", "cash")}</div>
                ${holdings(mission, attempt, true)}
                <div class="career-allocation-bar" aria-hidden="true">${mission.assets.map((asset, index) =>
                    `<span id="mix-${escapeHTML(asset)}" style="--stock-color:${colors[index]}"></span>`).join("")}</div>
                <p class="career-allocation-total"><span>${tx("cashAfter")}</span><strong id="career-allocation-total" aria-live="polite"></strong></p>
            </fieldset>
            ${planning ? "" : `<div class="career-actions"><button id="career-allocate" class="career-button${setup ? " career-button-primary" : ""}" type="submit">
                <span class="career-button-icon" aria-hidden="true">✓</span>${tx(setup ? "allocateSubmit" : "rebalanceSubmit")}</button></div>`}
        </form>`;
    }

    function stopForm(mission, attempt) {
        if (!attempt.tools.includes("stop")) return "";
        const order = attempt.stopOrder;
        const positions = mission.assets.filter((asset) => Number(attempt.weights[asset]) > 0);
        const enabled = attempt.stopAvailable && positions.length;
        if (!enabled && !order) return "";
        if (order) return `<section aria-label="${tx("stop")}"><p class="career-order-status" id="career-order-status" tabindex="-1">
            ${tx("stopStatus", { asset: order.asset, comparison: order.trigger === "profit" ? "≥" : "≤", price: number(order.price) })}</p></section>`;
        return `<section aria-label="${tx("stop")}"><details id="career-order">
            <summary>${tx("stop")}</summary>
            <form id="career-stop-form">
                <fieldset class="career-stop-modes"><legend class="sr-only">${tx("stop")}</legend>
                    ${[["loss", "lossStop", "↘"], ["profit", "profitStop", "↗"]].map(([trigger, label, icon]) =>
                        `<label><input type="radio" name="trigger" id="stop-${trigger}" value="${trigger}"${(stopDraft.trigger ?? "loss") === trigger ? " checked" : ""}>
                            <span><b aria-hidden="true">${icon}</b> ${tx(label)}</span></label>`).join("")}
                </fieldset>
                <div class="career-stop">
                    <label>${tx("stocks")}<select class="career-input" id="career-stop-asset">
                        ${positions.map((asset) => `<option value="${escapeHTML(asset)}"${stopDraft.asset === asset ? " selected" : ""}>${escapeHTML(asset)}</option>`).join("")}
                    </select></label>
                    <label><span id="career-stop-label"></span><input class="career-input" type="number" id="career-stop-price"
                        step="0.01" min="0.01" inputmode="decimal" required aria-describedby="career-stop-quote" value="${escapeHTML(stopDraft.price ?? "")}"></label>
                </div>
                <p id="career-stop-quote" class="career-catalog-note"></p>
                <button class="career-button" type="submit" id="career-submit-stop">${tx("placeStop")}</button>
            </form></details></section>`;
    }

    function pairedCorrelation(first, second) {
        const firstAverage = first.reduce((total, value) => total + value, 0) / first.length;
        const secondAverage = second.reduce((total, value) => total + value, 0) / second.length;
        let together = 0;
        let firstSpread = 0;
        let secondSpread = 0;
        for (let i = 0; i < first.length; i++) {
            const x = first[i] - firstAverage;
            const y = second[i] - secondAverage;
            together += x * y;
            firstSpread += x * x;
            secondSpread += y * y;
        }
        return firstSpread && secondSpread ? together / Math.sqrt(firstSpread * secondSpread) : null;
    }

    function analysisPanel(mission, attempt) {
        if (!attempt.tools.includes("analysis")) return "";
        const prices = attempt.prices.slice(-8).map((item) => item.prices);
        const returns = mission.assets.map((_, index) =>
            prices.slice(1).map((row, step) => row[index] / prices[step][index] - 1));
        return `<section class="career-card"><details id="career-analysis">
            <summary>${tx("analysis")}</summary>
            <p class="career-catalog-note">${tx("analysisMethod")}</p>
            <ul class="career-goals">${mission.assets.flatMap((asset, index) =>
                mission.assets.slice(index + 1).map((other, offset) => `<li>
                    <span>${tx("analysisPair", { asset, other })}</span>
                    <span>${escapeHTML(number(pairedCorrelation(returns[index], returns[index + 1 + offset])))}</span></li>`)).join("")}
            </ul></details></section>`;
    }

    function activeIntro(mission, kicker) {
        return `<header class="career-intro career-active-intro">
            <div><p class="career-kicker">${tx(kicker)}</p><h1 id="career-heading" tabindex="-1">${title(mission)}</h1></div>
            ${button("toOffice", "office")}
        </header>`;
    }

    function renderTrading(mission, attempt) {
        const exam = mission.kind === "exam";
        const phaseReady = attempt.status === "phaseReady";
        const phaseActive = attempt.status === "phaseActive";
        const progress = exam ? tx("phase", { phase: attempt.phase }) : attempt.step === 0 ? tx("preview") : tx("day", { day: attempt.step, total: mission.steps });
        return `${activeIntro(mission, "trading")}
        <div class="career-trading">
            <section class="career-card career-trade-summary" aria-label="${tx("trading")}">
                <div class="career-day-controls">
                    <div><h2>${progress}</h2>
                        ${phaseReady ? `<p class="career-catalog-note">${tx("phaseFirst")}</p>` : ""}
                        <progress class="career-progress" max="${mission.steps}" value="${attempt.step}" aria-label="${progress}"></progress>
                    </div>
                    ${attempt.status === "trading" ? button(attempt.step + 1 === mission.steps ? "lastDay" : "nextDay", "advance", { primary: true }) : ""}
                    ${phaseReady ? button("phaseStart", "phase", { primary: true }) : ""}
                    ${phaseActive ? `<span id="career-clock" class="career-clock" aria-label="${tx("timeLeft")}"></span>` : ""}
                </div>
                ${metrics([
                    ["value", number(attempt.value)], ["cash", number(attempt.cash), "", percent(attempt.cashPercent)],
                    ["return", percent(attempt.returnPercent, true), signedClass(attempt.returnPercent)],
                    ["benchmark", percent(attempt.indexReturn, true), signedClass(attempt.indexReturn)],
                ])}
            </section>
            <section class="career-trade-panel career-trade-controls" aria-label="${tx("portfolio")}">
                <section>
                    ${allocation(mission, attempt)}
                </section>
                ${stopForm(mission, attempt)}
                <section><h3>${tx("requirements")}</h3>${goalsList(attempt.goals, mission, "live")}</section>
                <button class="career-abandon" type="button" id="career-abandon" data-action="abandon">${tx("abandon")}</button>
            </section>
            <div class="career-market-panel">
                <section class="career-card" aria-label="${tx("marketChart")}">${chartOptions()}</section>
                ${analysisPanel(mission, attempt)}
            </div>
        </div>`;
    }

    function renderReport(mission, attempt) {
        const report = attempt.report;
        const verdict = report.abandoned ? "reportAbandoned" : report.passed ? "reportPassed" : "reportFailed";
        const promoted = report.promoted;
        const mayReplay = findMission(mission.id)?.available && (mission.kind !== "comeback" || !report.passed);
        return `${activeIntro(mission, "report")}
            <div class="career-trading">
                <section class="career-card career-report" aria-labelledby="career-report-title">
                    <h2 id="career-report-title" class="${report.passed ? "career-goal-pass" : "career-goal-fail"}">${tx(verdict)}</h2>
                    ${report.mastered ? `<p class="career-mastered">${tx("reportMastered")}</p>` : ""}
                    ${promoted ? `<div class="career-briefing-block">
                        <h3>${tx(state.rank === maxRank() ? "finalPromotion" : "promotion", { rank: rankName(state.rank) })}</h3>
                        <p class="career-catalog-note">${tx("afterPromotion")}</p>
                    </div>` : ""}
                    <div class="career-briefing-block">
                        ${metrics([
                            ["return", percent(attempt.returnPercent, true), signedClass(attempt.returnPercent)],
                            ["benchmark", percent(attempt.indexReturn, true), signedClass(attempt.indexReturn)],
                            ["worst", percent(attempt.drawdown)], ["fees", number(attempt.fees)],
                        ])}
                        ${attempt.worstStep > 0 ? `<p class="career-catalog-note">${tx("worstAt", { step: attempt.worstStep })}</p>` : ""}
                        ${chartOptions()}
                    </div>
                </section>
                <section class="career-card">
                    <h3>${tx("requirements")}</h3>${goalsList(report.goals, mission, true)}
                    ${report.mastery ? `<div class="career-briefing-block"><h3>${tx("mastery")}</h3>
                        ${goalsList([report.mastery], mission, true)}</div>` : ""}
                    <div class="career-actions">
                        ${state.comeback && mission.kind === "exam" && !report.passed ? button("viewRecovery", "recovery", { primary: true }) : ""}
                        ${mission.kind === "comeback" && report.passed ? button("toExam", "exam", { primary: true }) : ""}
                        ${mayReplay ? button("replay", "retry", { primary: !promoted }) : ""}
                    </div>
                </section>
            </div>`;
    }

    const colors = ["#7ce5cc", "#ffd477", "#c1adfa", "#ffa3ae", "#78afff"];
    const startDate = Date.UTC(2020, 0, 15) / 1000;
    const timeOfStep = (step) => startDate + step * 86400;
    const chartTime = (time) => String(Math.round((time - startDate) / 86400));

    function plotData(mission, attempt) {
        if (chartMode === "portfolio") {
            return [["value", "portfolio"], ["indexValue", "benchmark"]].map(([key, label], index) => ({
                label: translate(label),
                color: colors[index],
                data: attempt.history.map((point) => ({
                    time: timeOfStep(point.step), value: (point[key] / mission.capital) * 100,
                })),
            }));
        }
        const base = attempt.prices.find((item) => item.step === 0).prices;
        return mission.assets.map((asset, index) => ({
            label: asset,
            color: colors[index],
            data: attempt.prices.map((item) => ({
                time: timeOfStep(item.step), value: (item.prices[index] / base[index]) * 100,
            })),
        }));
    }

    function updateChart(mission, attempt) {
        const slot = document.getElementById("career-chart-slot");
        if (!slot) {
            chart?.api?.remove();
            chart = undefined;
            return;
        }
        const key = attempt.id + "|" + chartMode + "|" + locale();
        const changed = chart?.key !== key;
        if (changed) {
            chart?.api?.remove();
            const element = document.createElement("div");
            element.className = "career-chart";
            element.setAttribute("role", "img");
            chart = { key, element, lines: [] };
        }
        slot.append(chart.element);
        chart.element.setAttribute("aria-label", translate("chartLabel"));
        const library = window.LightweightCharts;
        if (!library) {
            chart.element.classList.add("career-chart-placeholder");
            chart.element.textContent = translate("chartUnavailable");
            return;
        }
        if (!chart.api) {
            chart.api = library.createChart(chart.element, {
                autoSize: true,
                layout: { attributionLogo: false, background: { type: "solid", color: "#141f2a" }, textColor: "#acbecb" },
                grid: { vertLines: { color: "#263641" }, horzLines: { color: "#263641" } },
                localization: { locale: locale(), timeFormatter: chartTime, priceFormatter: (price) => number(price) },
                rightPriceScale: { borderColor: "#344654" },
                timeScale: { borderColor: "#344654", tickMarkFormatter: chartTime },
                handleScroll: { mouseWheel: false, vertTouchDrag: false },
                handleScale: { mouseWheel: false },
            });
        }
        const lines = plotData(mission, attempt);
        for (const [index, line] of lines.entries()) {
            const series = chart.lines[index] ??= chart.api.addSeries(library.LineSeries, {
                color: line.color, lineWidth: 2, priceLineVisible: false, lastValueVisible: false,
            });
            series.setData(line.data);
        }
        chart.api.timeScale().fitContent();
        document.getElementById("career-chart-legend").innerHTML = lines.map((line) =>
            `<li><i style="background:${line.color}" aria-hidden="true"></i>${escapeHTML(line.label)} ·
                ${escapeHTML(number(last(line.data)?.value))}</li>`).join("");
    }

    function updateAllocation() {
        const total = document.getElementById("career-allocation-total");
        if (!total) return;
        const attempt = state.attempt;
        const limit = maxWeight(attempt.mission);
        const sum = Object.values(weights).reduce((accumulated, item) => accumulated + item, 0);
        const remaining = 100 - sum;
        total.textContent = percent(remaining);
        for (const [asset, weight] of Object.entries(weights)) {
            document.getElementById(`weight-${asset}`).value = percent(weight);
            document.getElementById(`mix-${asset}`).style.width = `${weight}%`;
            document.getElementById(`less-${asset}`).setAttribute("aria-disabled", weight === 0);
            document.getElementById(`more-${asset}`).setAttribute("aria-disabled", remaining < 10 || weight >= limit);
        }
    }

    function updateStopForm() {
        const picker = document.getElementById("career-stop-asset");
        if (!picker) return;
        const attempt = state.attempt;
        const index = attempt.mission.assets.indexOf(picker.value);
        const price = last(attempt.prices).prices[index];
        document.getElementById("career-stop-quote").textContent = translate("currentQuote", { price: number(price) });
        document.getElementById("career-stop-label").textContent = translate(stopDraft.trigger === "profit" ? "holdTarget" : "stopPrice");
    }

    function updateClock() {
        const clock = document.getElementById("career-clock");
        if (!clock || deadline == null) return;
        const seconds = Math.max(0, Math.min(60, Math.ceil((deadline - performance.now()) / 1000)));
        clock.textContent = Math.floor(seconds / 60) + ":" + String(seconds % 60).padStart(2, "0");
    }

    function render(focusId) {
        document.querySelector(".career-home").textContent = translate("home");
        document.title = translate("career") + " · Stock Fight";
        if (!state) return;
        const activeElement = document.activeElement;
        const focus = focusId ?? (content.contains(activeElement) ? activeElement.id : "");
        const ranks = content.querySelector(".career-rank-tabs");
        const rankScroll = ranks?.scrollLeft ?? 0;
        const analysisOpen = document.getElementById("career-analysis")?.open ?? false;
        const orderOpen = document.getElementById("career-order")?.open ?? false;
        const attempt = state.attempt;
        const mission = attempt && (attempt.mission ?? findMission(attempt.missionId));
        const showAttempt = !office && mission;
        content.innerHTML = !showAttempt ? renderOffice() : attempt.status === "complete"
            ? renderReport(mission, attempt) : renderTrading(mission, attempt);
        if (ranks) {
            const nextRanks = content.querySelector(".career-rank-tabs");
            if (nextRanks) nextRanks.scrollLeft = rankScroll;
        }
        const analysis = document.getElementById("career-analysis");
        if (analysis) analysis.open = analysisOpen;
        const order = document.getElementById("career-order");
        if (order) order.open = orderOpen;
        updateChart(mission, attempt);
        updateAllocation();
        updateStopForm();
        updateClock();
        if (focus) document.getElementById(focus)?.focus({ preventScroll: true });
    }

    function selectOffice(id) {
        office = true;
        const mission = findMission(id);
        selectedMission = mission?.id;
        browseRank = mission?.rank ?? currentStage();
        render("career-heading");
        window.scrollTo(0, 0);
    }

    function resetDrafts(attempt) {
        weights = {};
        let unassigned = 100;
        const limit = attempt ? maxWeight(attempt.mission) : 100;
        for (const [asset, current] of Object.entries(attempt?.weights ?? {})) {
            const weight = Math.min(unassigned, limit, Math.round(current / 10) * 10);
            weights[asset] = weight;
            unassigned -= weight;
        }
        stopDraft = {};
    }

    function updateState(next, { phasePoll = false, action } = {}) {
        if (state && next.revision < state.revision) return;
        const previous = state?.attempt;
        const attempt = next.attempt;
        if (phasePoll && next.revision === state?.revision && attempt?.serverNow < previous?.serverNow) return;
        const attemptChanged = previous?.id !== attempt?.id;
        const statusChanged = previous?.status !== attempt?.status;
        const cursorChanged = previous?.step !== attempt?.step;
        const revisionChanged = state?.revision !== next.revision;
        const first = !state;
        state = next;
        if (first) {
            browseRank = currentStage();
            office = !attempt;
            chartMode = attempt?.status === "complete" ? "portfolio" : "market";
        }
        if (attemptChanged || action === "allocate") resetDrafts(attempt);
        if (action === "start") {
            office = false;
            chartMode = "market";
        }
        if (action === "leave" && !attempt) {
            office = true;
            browseRank = currentStage();
            selectedMission = undefined;
        }
        if (statusChanged && attempt?.status === "complete") chartMode = "portfolio";
        deadline = attempt?.phaseEndsAt == null ? null :
            performance.now() + (attempt.phaseEndsAt - attempt.serverNow) * 1000;
        if (first || attemptChanged || statusChanged || cursorChanged || revisionChanged || !phasePoll) {
            let focus;
            if (action === "start" || (statusChanged && attempt?.status === "complete" && !office)) focus = "career-heading";
            if (action === "allocate" && previous?.status === "setup") {
                focus = attempt.status === "phaseReady" ? "button-phase" : "button-advance";
            }
            if (action === "stop") focus = "career-order-status";
            render(focus);
            if (focus && action !== "stop") window.scrollTo(0, 0);
        } else {
            updateClock();
        }
    }

    async function loadOffice() {
        content.setAttribute("aria-busy", "true");
        renderNotice();
        try {
            const [account, campaign] = await Promise.all([fetch("/api/me"), fetch("/api/campaign")]);
            if (campaign.status === 401 || account.status === 401) {
                renderNotice("login_required");
                throw new Error("login_required");
            }
            if (!account.ok || !campaign.ok) throw new Error("connection");
            csrf = (await account.json()).csrfToken;
            updateState(await campaign.json());
        } catch {
            content.innerHTML = `<section class="career-card career-entry-error">
                <h1>${tx("career")}</h1><p>${tx("loadError")}</p>
                <div class="career-actions">${button("loadRetry", "load", { primary: true })}
                <a class="career-button" href="/">${tx("home")}</a></div></section>`;
        } finally {
            content.removeAttribute("aria-busy");
        }
    }

    async function send(command) {
        if (pending || !state) return;
        pending = true;
        renderNotice();
        try {
            const response = await fetch("/api/campaign/commands", {
                method: "POST",
                headers: { "Content-Type": "application/json", "X-CSRF-Token": csrf },
                body: JSON.stringify({ ...command, revision: state.revision }),
            });
            const next = await response.json();
            if (!response.ok) {
                if (next.state) updateState(next.state);
                renderNotice(response.status === 401 ? "login_required" : response.status === 403 ? "sessionExpired" : next.error);
                return;
            }
            updateState(next, { action: command.action });
        } catch {
            renderNotice("connection");
        } finally {
            pending = false;
        }
    }

    async function poll() {
        if (polling || pending || state?.attempt?.status !== "phaseActive" || document.hidden) return;
        polling = true;
        try {
            const response = await fetch("/api/campaign");
            if (response.status === 401) renderNotice("login_required");
            if (!response.ok || pending) return;
            const next = await response.json();
            if (pending) return;
            updateState(next, { phasePoll: true });
            if (errorCode === "connection") renderNotice();
        } catch {
            renderNotice("connection");
        } finally {
            polling = false;
        }
    }

    function setTools() {
        const boxes = [...content.querySelectorAll("[data-tool]")];
        chosenTools = boxes.filter((box) => box.checked).map((box) => box.dataset.tool);
        const count = document.getElementById("career-tool-count");
        if (count) count.textContent = translate("slots", { used: chosenTools.length, max: state.toolSlots });
        for (const box of boxes) box.disabled = !box.checked && chosenTools.length >= state.toolSlots;
    }

    content.addEventListener("click", (event) => {
        const button = event.target.closest("[data-action]");
        if (!button || pending || button.getAttribute("aria-disabled") === "true") return;
        const { action, mode, mission, rank, asset, delta } = button.dataset;
        const attempt = state?.attempt;
        switch (action) {
            case "load": loadOffice(); break;
            case "rank":
                browseRank = Number(rank);
                selectedMission = undefined;
                render();
                break;
            case "pick":
                selectedMission = mission;
                render();
                if (window.matchMedia("(max-width: 830px)").matches) {
                    document.getElementById("career-briefing-title")?.focus();
                }
                break;
            case "start": send({ action, missionId: selectedMission, tools: chosenTools }); break;
            case "retry": send({ action: "start", missionId: attempt.missionId, tools: attempt.tools }); break;
            case "resume":
                office = false;
                render("career-heading");
                window.scrollTo(0, 0);
                break;
            case "office": selectOffice(); break;
            case "recovery": selectOffice(state.comeback); break;
            case "exam":
                selectOffice(state.missions.find((item) => item.kind === "exam" && item.rank === findMission(attempt.missionId).rank)?.id);
                break;
            case "advance":
            case "phase":
                send({ action });
                break;
            case "abandon": {
                const startedExam = findMission(attempt.missionId).kind === "exam" &&
                    (attempt.status === "phaseActive" || attempt.step > 0);
                const confirm = startedExam
                    ? translate("confirmAbandon") + "\n\n" + translate("examAbandon")
                    : translate("confirmAbandon");
                if (window.confirm(confirm)) send({ action: "leave" });
                break;
            }
            case "chart":
                chartMode = mode;
                render();
                break;
            case "weight":
                weights[asset] += Number(delta);
                updateAllocation();
                break;
            case "split":
            case "cash": {
                const assets = attempt.mission.assets;
                const weight = action === "cash" ? 0 : Math.min(maxWeight(attempt.mission), Math.floor(10 / assets.length) * 10);
                weights = Object.fromEntries(assets.map((symbol) => [symbol, weight]));
                updateAllocation();
                break;
            }
        }
    });

    content.addEventListener("change", (event) => {
        const target = event.target;
        if (target.hasAttribute("data-tool")) setTools();
        if (target.id === "career-stop-asset" || target.name === "trigger") {
            if (target.name === "trigger") stopDraft.trigger = target.value;
            else stopDraft.asset = target.value;
            document.getElementById("career-stop-price").value = stopDraft.price = "";
            updateStopForm();
        }
    });
    content.addEventListener("input", (event) => {
        const target = event.target;
        if (target.id === "career-stop-price") stopDraft.price = target.value;
    });
    content.addEventListener("submit", (event) => {
        event.preventDefault();
        const step = state.attempt.step;
        if (event.target.id === "career-allocation" && state.attempt.status !== "phaseReady") {
            send({ action: "allocate", weights, step });
        }
        if (event.target.id === "career-stop-form") {
            const asset = document.getElementById("career-stop-asset").value;
            const price = document.getElementById("career-stop-price").value;
            send({ action: "stop", asset, price, step, trigger: stopDraft.trigger ?? "loss" });
        }
    });
    window.addEventListener("stockfight:languagechange", () => {
        render();
        renderNotice(errorCode);
        if (!state) {
            for (const node of document.querySelectorAll("[data-career-text]")) node.textContent = translate(node.dataset.careerText);
        }
    });
    document.addEventListener("visibilitychange", poll);
    window.setInterval(updateClock, 200);
    window.setInterval(poll, 850);
    for (const node of document.querySelectorAll("[data-career-text]")) node.textContent = translate(node.dataset.careerText);
    loadOffice();
})();
