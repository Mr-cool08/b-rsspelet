(() => {
    "use strict";

    const { t, getLocale } = window.StockFightI18n;
    const byId = (id) => document.getElementById(id);
    const buttons = (action) => document.querySelectorAll(`[data-action="${action}"]`);
    const positionDirection = (position) => position.side === "short" ? t("Ner") : t("Upp");
    const reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)");
    const primaryTouch = window.matchMedia("(pointer: coarse)");
    const screenIds = ["auth", "tutorial", "menu", "queue", "invite", "match", "result", "spectate", "spectate-live"];
    const screenFocus = { auth: "auth-title", tutorial: "tutorial-title", menu: "menu-title", queue: "queue-title",
        invite: "invite-title", match: "match-screen", result: "result-outcome",
        spectate: "spectate-title", "spectate-live": "spectate-mode" };
    const phaseLabels = { normal: "Handel", market: "Marknadsstorm", final: "Slutstorm" };
    const outcomeLabels = { win: "VANN", lose: "FÖRLORADE", loss: "FÖRLORADE", draw: "OAVGJORT" };
    const spectateModeLabels = { ranked: "Handelsduell", prediction: "Ritduell", bot: "Botduell", private: "Vänduell" };
    const acknowledgements = 5000;
    const queueBotWaitSeconds = 20;
    const chartRightPadding = 24;
    const chartZoomFactor = 1.5;
    const activityActions = ["play", "play-bot", "play-prediction", "practice-prediction", "guide-start", "tutorial-replay",
        "guide-begin", "guide-bypass", "friend-create", "main-menu", "spectate"];
    const tutorialSteps = 4;
    const tutorialDirectionFeedback = {
        up: "100 ↗ 104 · +5 krediter",
        down: "100 ↘ 96 · +5 krediter",
    };
    const tutorialProfitFeedback = {
        attack: "Motståndare −20 HP · 500 krediter kvar",
        grow: "505 krediter · 102 % attackkraft · +25 bonus-HP",
    };
    const localizedValues = new Map();

    let amountFormat, integerFormat, percentFormat, predictionPercentFormat, dateFormat, marketDateFormat, marketTimeFormat;
    configureFormats();

    let soundEnabled = preference("sound", "false") === "true";
    let effectsEnabled = preference("effects", "true") === "true";
    let chartType = preference("chartType", "line") === "candlestick" ? "candlestick" : "line";
    let audio;
    let screen;
    let session = { user: null, csrfToken: "", inviteRequired: false };
    let sessionVersion = 0;
    let authMode = "login";
    let authPending = false;
    let tutorial;
    let profileVersion = 0;
    let menuProfileVersion = 0;
    let rankingVersion = 0;
    let menuProfileData;
    let profileData;
    let rankingData;
    let toastTimer;
    let onlineCountPending = false;
    let onlineCount;
    let socket;
    let queueWanted = false;
    let queueMode = "ranked";
    let queueLeavePending = false;
    let queueReconnect = false;
    let queueCommand;
    let queueData;
    let activityCommand;
    let inviteCode = new URL(window.location.href).searchParams.get("match");
    let invitation;
    let rematchOffer;
    let privateStateTimer;
    let guideRequested = false;
    let guideActive = false;
    let guideSeen = false;
    let match;
    let matchSynchronized = false;
    let result;
    let lastResultId;
    let resultTimer;
    let nextSeq;
    let tradeCommand;
    let sellChoice;
    let keptPositionId;
    let tradeFocus;
    let percent = 100;
    let lastEventId;
    let activeMatchEvent;
    let effectTimer;
    let drawPredictionChart;
    let predictionRound;
    let predictionCommand;
    let predictionSubmitFocus = false;
    let spectateCommands = Promise.resolve();
    let spectateListRequest;
    let spectateJoinRequest;
    let spectateListData;
    let spectateState;
    let spectatedMatchId;
    let spectateFinished = false;
    let drawSpectatePredictionChart;

    function put(id, value) {
        localizedValues.delete(id);
        const element = byId(id);
        element?.removeAttribute("data-i18n");
        const content = value == null ? "—" : String(value);
        if (element && element.textContent !== content) {
            element.textContent = content;
        }
    }

    function putLocalized(id, value) {
        put(id, value == null ? value : t(value));
        localizedValues.set(id, value);
    }

    function configureFormats() {
        const locale = getLocale();
        amountFormat = new Intl.NumberFormat(locale, {
            minimumFractionDigits: 2,
            maximumFractionDigits: 2,
        });
        integerFormat = new Intl.NumberFormat(locale, { maximumFractionDigits: 0 });
        percentFormat = new Intl.NumberFormat(locale, { style: "percent", maximumFractionDigits: 0 });
        predictionPercentFormat = new Intl.NumberFormat(locale, {
            style: "percent",
            signDisplay: "exceptZero",
            minimumFractionDigits: 2,
            maximumFractionDigits: 2,
        });
        dateFormat = new Intl.DateTimeFormat(locale, { dateStyle: "short" });
        marketDateFormat = new Intl.DateTimeFormat(locale, { dateStyle: "short", timeZone: "UTC" });
        marketTimeFormat = new Intl.DateTimeFormat(locale, {
            hour: "2-digit", minute: "2-digit", second: "2-digit", timeZone: "UTC",
        });
    }

    function show(id, visible) {
        const element = byId(id);
        if (element) element.hidden = !visible;
    }

    function stateAttribute(id, key, value) {
        const element = byId(id);
        if (element && element.dataset[key] !== value) element.dataset[key] = value;
    }

    function disable(action, disabled) {
        for (const button of buttons(action)) button.disabled = disabled;
    }

    function numeric(value) {
        if (value == null || value === "") return null;
        const number = Number(value);
        return Number.isFinite(number) ? number : null;
    }

    function formatNumber(value, format = integerFormat) {
        const number = numeric(value);
        return number == null ? "—" : format.format(number);
    }

    function signed(value, format = integerFormat) {
        const number = numeric(value);
        if (number == null) return "—";
        return number > 0 ? `+${format.format(number)}` : format.format(number);
    }

    function sign(value) {
        if (value > 0) return "positive";
        if (value < 0) return "negative";
        return "zero";
    }

    function clock(value) {
        const seconds = Math.max(0, Math.ceil(numeric(value) ?? 0));
        return `${String(Math.floor(seconds / 60)).padStart(2, "0")}:${String(seconds % 60).padStart(2, "0")}`;
    }

    function date(value) {
        if (!value) return "—";
        const parsed = new Date(value);
        return Number.isNaN(parsed.getTime()) ? "—" : dateFormat.format(parsed);
    }

    function period(start, end, interval) {
        const dates = [start, end].map((value) => value ? new Date(value) : null);
        const valid = (value) => value && !Number.isNaN(value.getTime());
        const [first, last] = dates.map((value) => valid(value) ? marketDateFormat.format(value) : "—");
        const calendarInterval = /[dw]$/.test(interval ?? "");
        if (!calendarInterval && dates.every(valid) && start.includes("T") && end.includes("T")) {
            const [firstTime, lastTime] = dates.map((value) => marketTimeFormat.format(value));
            if (first !== last) return `${first} ${firstTime} – ${last} ${lastTime} UTC`;
            return `${first} · ${firstTime}–${lastTime} UTC`;
        }
        return first === last ? first : `${first} – ${last}`;
    }

    function percentage(value) {
        const number = numeric(value);
        return number == null ? "—" : percentFormat.format(number / 100);
    }

    function message(id, value, tone = "info") {
        putLocalized(id, value || "");
        stateAttribute(id, "tone", tone);
        show(id, Boolean(value));
    }

    function toast(value, tone = "info") {
        window.clearTimeout(toastTimer);
        message("toast", value, tone);
        toastTimer = window.setTimeout(() => message("toast", ""), 5000);
    }

    function activate(name) {
        if (screen === name) return;
        const previousScreen = screen;
        if (previousScreen === "spectate") leaveSpectateList();
        if (previousScreen === "spectate-live") leaveSpectateMatch();
        for (const dialog of document.querySelectorAll("dialog[open]")) dialog.close();
        for (const id of screenIds) show(`${id}-screen`, id === name);
        screen = name;
        show("online-count", name === "auth" || name === "menu");
        void refreshOnlineCount();
        window.scrollTo(0, 0);
        if (previousScreen) byId(screenFocus[name]).focus({ preventScroll: true });
    }

    async function request(url, body) {
        const options = { headers: { Accept: "application/json" } };
        if (body !== undefined) {
            options.method = "POST";
            options.headers["Content-Type"] = "application/json";
            options.headers["X-CSRF-Token"] = session.csrfToken;
            options.body = JSON.stringify(body);
        }
        let response;
        try {
            response = await fetch(url, options);
        } catch {
            throw new Error("Kunde inte nå servern. Kontrollera din anslutning.");
        }
        const data = await response.json().catch(() => null);
        if (!response.ok || !data) {
            throw new Error(data?.error || "Servern kunde inte slutföra begäran.");
        }
        return data;
    }

    async function refreshOnlineCount() {
        if (onlineCountPending || document.hidden || byId("online-count").hidden) return;
        onlineCountPending = true;
        try {
            const { count } = await request("/api/online");
            onlineCount = count;
        } catch {
            onlineCount = undefined;
        } finally {
            onlineCountPending = false;
            renderOnlineCount();
        }
    }

    function renderOnlineCount() {
        if (onlineCount == null) return;
        put("online-count", t("{count} online", { count: formatNumber(onlineCount) }));
    }

    function setAuthMode(mode) {
        authMode = mode;
        const register = mode === "register";
        putLocalized("auth-title", register ? "Nytt spelarkonto" : "Spelarkonto");
        putLocalized("auth-submit", register ? "Skapa konto" : "Logga in");
        for (const name of ["login", "register"]) {
            for (const button of buttons(`auth-${name}`)) {
                const selected = String(name === mode);
                button.setAttribute("aria-pressed", selected);
                if (button.getAttribute("role") === "tab") {
                    button.setAttribute("aria-selected", selected);
                }
            }
        }
        show("invite-field", register && session.inviteRequired);
        const invite = byId("auth-form")?.elements.namedItem("inviteCode");
        if (invite) invite.required = register && session.inviteRequired;
        const password = byId("auth-form")?.elements.namedItem("password");
        if (password) password.autocomplete = register ? "new-password" : "current-password";
        message("auth-error", "");
    }

    function authBusy(busy) {
        authPending = busy;
        const submit = byId("auth-submit");
        if (submit) submit.disabled = busy;
        for (const action of ["auth-login", "auth-register", "logout"]) disable(action, busy);
    }

    function applySession(data) {
        session = data;
        const user = session.user;
        show("header-account", Boolean(user));
        show("header-logout", Boolean(user));
        put("header-name", user?.username);
        if (!user) {
            sessionVersion += 1;
            tutorial = undefined;
            setActivityCommand(undefined);
            window.clearTimeout(privateStateTimer);
            invitation = undefined;
            rematchOffer = undefined;
            guideRequested = false;
            if (socket) {
                socket.removeAllListeners();
                socket.disconnect();
                socket = undefined;
            }
            queueWanted = false;
            queueMode = "ranked";
            queueLeavePending = false;
            queueReconnect = false;
            queueCommand = undefined;
            queueData = undefined;
            menuProfileData = undefined;
            profileData = undefined;
            rankingData = undefined;
            lastResultId = undefined;
            resetMatch();
            fillTable("ranking-list", []);
            fillTable("profile-history", []);
            for (const field of ["name", "league", "elo", "matches", "wins", "losses", "draws", "win-rate"]) {
                put(`profile-${field}`, null);
            }
            connection();
            setAuthMode("login");
            show("auth-invite-note", Boolean(inviteCode));
            activate("auth");
            return;
        }
        sessionVersion += 1;
        guideSeen = preference(`guide.seen.${user.id}`, "false") === "true";
        put("menu-name", user.username);
        put("menu-level", "—");
        put("menu-elo", "—");
        put("menu-progress-label", "—");
        put("menu-next", "");
        progress("menu-progress", 0);
        if (session.duelTutorialPending) openTutorial();
        else enterLobby();
        void refreshProfile();
    }

    function enterLobby() {
        tutorial = undefined;
        activate(inviteCode ? "invite" : "menu");
        renderPrivate();
        if (!socket) connect();
    }

    function openTutorial() {
        tutorial = { step: 1, direction: null, closed: false, profit: null, saving: false };
        message("tutorial-error", "");
        renderTutorial();
        activate("tutorial");
    }

    function renderTutorial() {
        const { step, direction, closed, profit, saving } = tutorial;
        const last = step === tutorialSteps;
        const canAdvance = (step !== 2 || Boolean(direction)) && (step !== 3 || Boolean(profit));
        put("tutorial-progress", t("Steg {step} av {total}", { step, total: tutorialSteps }));
        for (let page = 1; page <= tutorialSteps; page += 1) show(`tutorial-page-${page}`, page === step);
        for (const [action, selected] of [["up", direction], ["down", direction], ["attack", profit], ["grow", profit]]) {
            for (const button of buttons(`tutorial-${action}`)) {
                button.setAttribute("aria-pressed", String(action === selected));
            }
        }
        putLocalized("tutorial-direction-feedback", tutorialDirectionFeedback[direction] ?? "");
        putLocalized("tutorial-profit-feedback", tutorialProfitFeedback[profit] ?? "");
        show("tutorial-direction-feedback", Boolean(direction));
        show("tutorial-profit-feedback", Boolean(profit));
        disable("tutorial-close-position", closed);
        show("tutorial-profit-options", closed);
        show("tutorial-exit", !session.duelTutorialPending);
        disable("tutorial-back", step === 1 || saving);
        for (const button of buttons("tutorial-next")) button.hidden = last;
        disable("tutorial-next", !canAdvance);
        for (const button of buttons("tutorial-finish")) button.hidden = !last;
        disable("tutorial-finish", saving);
    }

    function moveTutorial(increment) {
        tutorial.step += increment;
        message("tutorial-error", "");
        renderTutorial();
        byId(`tutorial-step-${tutorial.step}`).focus();
    }

    function chooseTutorialDirection(direction) {
        if (tutorial.direction !== direction) {
            tutorial.direction = direction;
            tutorial.closed = false;
            tutorial.profit = null;
            renderTutorial();
        }
    }

    async function finishTutorial() {
        if (!session.duelTutorialPending) {
            enterLobby();
            return;
        }
        const version = sessionVersion;
        tutorial.saving = true;
        message("tutorial-error", "");
        renderTutorial();
        try {
            const data = await request("/api/duel-tutorial/complete", {});
            if (version !== sessionVersion) return;
            session = data;
            enterLobby();
        } catch (error) {
            if (version !== sessionVersion) return;
            message("tutorial-error", error.message, "error");
            tutorial.saving = false;
            renderTutorial();
            buttons("tutorial-finish")[0]?.focus();
        }
    }

    async function submitAuth(event) {
        event.preventDefault();
        if (authPending) return;
        const form = event.currentTarget;
        const fields = new FormData(form);
        const mode = authMode;
        authBusy(true);
        message("auth-error", "");
        try {
            if (!session.csrfToken) session = await request("/api/me");
            const body = {
                username: String(fields.get("username") ?? "").trim(),
                password: String(fields.get("password") ?? ""),
            };
            if (mode === "register") body.inviteCode = String(fields.get("inviteCode") ?? "");
            const data = await request(`/api/${mode}`, body);
            form.reset();
            applySession(data);
        } catch (error) {
            setAuthMode(mode);
            message("auth-error", error.message, "error");
        } finally {
            authBusy(false);
        }
    }

    async function logout() {
        if (!session.user || authPending) return;
        authBusy(true);
        try {
            applySession(await request("/api/logout", {}));
        } catch (error) {
            toast(error.message, "error");
        } finally {
            authBusy(false);
        }
    }

    function progress(id, value) {
        const element = byId(id);
        if (element) element.value = Math.min(100, Math.max(0, numeric(value) ?? 0));
    }

    function fillTable(id, rows) {
        const table = byId(id);
        if (!table) return;
        const fragment = document.createDocumentFragment();
        for (const values of rows) {
            const row = document.createElement("tr");
            for (const value of values) {
                const cell = document.createElement("td");
                cell.textContent = value == null ? "—" : String(value);
                row.append(cell);
            }
            fragment.append(row);
        }
        table.replaceChildren(fragment);
    }

    async function refreshProfile(includeDialog = false) {
        const version = sessionVersion;
        const requestVersion = includeDialog ? ++profileVersion : ++menuProfileVersion;
        const ownsResponse = () => version === sessionVersion
            && requestVersion === (includeDialog ? profileVersion : menuProfileVersion);
        const mode = includeDialog ? byId("profile-mode").value : "ranked";
        if (includeDialog) {
            profileData = undefined;
            put("profile-name", session.user.username);
            for (const field of ["league", "elo", "matches", "wins", "losses", "draws", "win-rate"]) {
                put(`profile-${field}`, null);
            }
            fillTable("profile-history", []);
            message("profile-status", "Hämtar profil …");
        }
        try {
            const data = await request(mode === "prediction" ? "/api/profile?mode=prediction" : "/api/profile");
            if (!ownsResponse()) return;
            if (includeDialog) {
                profileData = data;
                renderProfile(data);
            } else {
                menuProfileData = data;
                renderMenuProfile(data);
            }
        } catch (error) {
            if (!ownsResponse()) return;
            if (includeDialog) message("profile-status", error.message, "error");
            if (!includeDialog && !byId("profile-dialog")?.open && screen === "menu") {
                toast(error.message, "error");
            }
        }
    }

    function renderMenuProfile(data) {
        putLocalized("menu-level", data.level ?? data.league);
        put("menu-elo", formatNumber(data.elo));
        progress("menu-progress", data.progress);
        put("menu-progress-label", percentage(data.progress));
        put("menu-next", data.nextLeague
            ? `${t(data.nextLeague)} · ${formatNumber(data.nextElo)} Elo` : t("Högsta ligan"));
    }

    function renderProfile(data) {
        put("profile-name", session.user.username);
        putLocalized("profile-league", data.league);
        put("profile-elo", formatNumber(data.elo));
        put("profile-matches", formatNumber(data.matches));
        put("profile-wins", formatNumber(data.wins));
        put("profile-losses", formatNumber(data.losses));
        put("profile-draws", formatNumber(data.draws));
        put("profile-win-rate", percentage(data.winRate));
        const rows = (data.history ?? []).map((item) => [
            item.opponent,
            outcomeLabels[item.outcome] ? t(outcomeLabels[item.outcome]) : null,
            item.symbol,
            `${formatNumber(item.eloBefore)} → ${formatNumber(item.eloAfter)}`,
            date(item.endedAt),
        ]);
        fillTable("profile-history", rows);
        message("profile-status", rows.length ? "" : "Inga avslutade matcher ännu.");
    }

    async function refreshRanking() {
        const version = sessionVersion;
        const requestVersion = ++rankingVersion;
        const ownsResponse = () => version === sessionVersion && requestVersion === rankingVersion;
        const mode = byId("ranking-mode").value;
        rankingData = undefined;
        fillTable("ranking-list", []);
        message("ranking-status", "Hämtar ranking …");
        try {
            const data = await request(mode === "prediction" ? "/api/leaderboard?mode=prediction" : "/api/leaderboard");
            if (!ownsResponse()) return;
            rankingData = data;
            renderRanking(data);
        } catch (error) {
            if (ownsResponse()) message("ranking-status", error.message, "error");
        }
    }

    function renderRanking(data) {
        const rows = (data.players ?? []).map((player, index) => [
            formatNumber(index + 1),
            player.username,
            formatNumber(player.elo),
            player.league ? t(player.league) : null,
            formatNumber(player.wins),
            formatNumber(player.matches),
        ]);
        fillTable("ranking-list", rows);
        message("ranking-status", rows.length ? "" : "Rankingen är tom.");
    }

    function openDialog(name) {
        const dialog = byId(`${name}-dialog`);
        if (!dialog || dialog.open) return;
        dialog.showModal();
        if (name === "profile") void refreshProfile(true);
        if (name === "ranking") void refreshRanking();
    }

    function connection(status, detail) {
        const labels = { connecting: "Ansluter …", offline: "Återansluter …", online: "Ansluten" };
        show("connection-status", Boolean(status));
        if (!status) return;
        putLocalized("connection-status", detail || labels[status]);
        stateAttribute("connection-status", "state", status);
    }

    function connect() {
        connection("connecting");
        if (typeof window.io !== "function") {
            connection("offline", "Spelanslutningen kunde inte startas");
            return;
        }
        socket = window.io({ auth: { csrfToken: session.csrfToken }, autoConnect: false });
        socket.on("connect", () => {
            spectateCommands = Promise.resolve();
            connection("online");
            void refreshOnlineCount();
            renderTradeControls();
            renderPrediction();
            renderPrivate();
            if (queueLeavePending && !match) sendQueueCommand(false);
            else if (queueWanted && screen === "queue" && !match) sendQueueCommand(true);
            queueReconnect = false;
            renderQueueActions();
            if (screen === "spectate") subscribeSpectateList();
            if (screen === "spectate-live" && !spectateFinished) subscribeSpectateMatch();
        });
        socket.on("disconnect", (reason) => {
            queueReconnect = queueWanted;
            queueCommand = undefined;
            setActivityCommand(undefined);
            if (tradeCommand) {
                message("match-feedback", "Anslutningen bröts under handeln. Kontrollera din position när du är tillbaka.");
            }
            tradeCommand = undefined;
            predictionCommand = undefined;
            predictionSubmitFocus = false;
            matchSynchronized = false;
            connection("offline");
            renderTradeControls();
            renderPrediction();
            renderPrivate();
            showSpectateConnectionStatus();
            if (reason === "io server disconnect") {
                connection("offline", "Spelanslutningen avslutades. Uppdatera sidan för att försöka igen.");
            }
        });
        socket.on("connect_error", (error) => {
            connection("offline", socket.active ? undefined : error.message || "Spelanslutningen nekades");
            renderTradeControls();
            renderPrediction();
            renderPrivate();
            showSpectateConnectionStatus();
        });
        socket.on("queue_state", receiveQueueState);
        socket.on("match_state", receiveMatchState);
        socket.on("match_result", receiveResult);
        socket.on("private_state", receivePrivateState);
        socket.on("prediction_practice_ended", receivePracticeEnded);
        socket.on("spectate_matches", receiveSpectateList);
        socket.on("spectate_state", receiveSpectateState);
        socket.connect();
    }

    function openSpectateList() {
        activate("spectate");
        subscribeSpectateList();
    }

    function sendSpectateCommand(event, payload, acknowledge) {
        const connection = socket;
        const sid = connection.id;
        // Wait for a subscription to reach the server before sending its cleanup.
        spectateCommands = spectateCommands.then(async () => {
            if (!connection.connected || connection.id !== sid) return;
            const sender = connection.timeout(acknowledgements);
            const reply = payload === undefined ? sender.emitWithAck(event) : sender.emitWithAck(event, payload);
            return reply.catch(() => undefined);
        });
        if (acknowledge) void spectateCommands.then(acknowledge);
    }

    function showSpectateConnectionStatus() {
        spectateListRequest = undefined;
        spectateJoinRequest = undefined;
        const reconnecting = Boolean(socket?.active);
        const status = reconnecting ? "Återansluter …" : "Spelanslutningen är offline.";
        if (screen === "spectate") {
            message("spectate-list-status", status);
            show("spectate-list-retry", !reconnecting && Boolean(socket));
        }
        if (screen === "spectate-live" && !spectateFinished) {
            setSpectateLiveStatus(status, "offline", !reconnecting && Boolean(socket));
        }
    }

    function subscribeSpectateList() {
        if (spectateListRequest) return;
        if (!socket?.connected) {
            showSpectateConnectionStatus();
            return;
        }
        const command = {};
        spectateListRequest = command;
        message("spectate-list-status", "Hämtar pågående matcher …");
        show("spectate-list-retry", false);
        sendSpectateCommand("spectate_list", undefined, (ack) => {
            if (spectateListRequest !== command) return;
            spectateListRequest = undefined;
            if (ack?.ok) receiveSpectateList(ack);
            else {
                message("spectate-list-status", ack?.error || "Matchlistan kunde inte hämtas.", "error");
                show("spectate-list-retry", true);
            }
        });
    }

    function receiveSpectateList(data) {
        if (screen !== "spectate" || !Array.isArray(data?.matches)) return;
        spectateListRequest = undefined;
        spectateListData = data;
        renderSpectateList(data);
        message("spectate-list-status", data.matches.length ? "" : "Inga matcher pågår just nu.");
        show("spectate-list-retry", false);
    }

    function renderSpectateList(data) {
        const list = byId("spectate-list");
        const focusedId = list.contains(document.activeElement) ? document.activeElement.dataset.matchId : undefined;
        let focusTarget;
        const rows = document.createDocumentFragment();
        for (const live of data.matches) {
            const row = document.createElement("li");
            row.className = "spectate-match";
            const details = document.createElement("div");
            details.className = "spectate-match-details";
            const players = document.createElement("strong");
            players.className = "spectate-match-players";
            players.textContent = live.players.map((player) => player.name).join(t(" mot "));
            const mode = spectateModeLabels[live.mode] ?? "Duell";
            const meta = document.createElement("span");
            meta.className = "spectate-match-meta";
            meta.textContent = [t(mode), live.symbol, live.status === "countdown" ? t("Startar snart") : t("Live")]
                .filter(Boolean).join(" · ");
            const button = document.createElement("button");
            button.type = "button";
            button.className = "button button-secondary";
            button.dataset.action = "spectate-watch";
            button.dataset.matchId = live.id;
            button.dataset.mode = mode;
            button.textContent = t("Titta live");
            button.setAttribute("aria-label", t("Titta live på {players}", { players: players.textContent }));
            if (focusedId === live.id) focusTarget = button;
            details.append(players, meta);
            row.append(details, button);
            rows.append(row);
        }
        list.replaceChildren(rows);
        if (focusedId) (focusTarget ?? byId("spectate-title")).focus({ preventScroll: true });
    }

    function leaveSpectateList() {
        spectateListRequest = undefined;
        spectateListData = undefined;
        if (socket?.connected) sendSpectateCommand("spectate_list_leave");
        byId("spectate-list").replaceChildren();
    }

    function openSpectateMatch(button) {
        spectatedMatchId = button.dataset.matchId;
        putLocalized("spectate-mode", button.dataset.mode);
        show("spectate-contest", false);
        activate("spectate-live");
        subscribeSpectateMatch();
    }

    function setSpectateLiveStatus(value, state, retry = false) {
        putLocalized("spectate-status", value);
        stateAttribute("spectate-status", "state", state);
        stateAttribute("spectate-status", "tone", state === "error" ? "error" : "info");
        show("spectate-live-retry", retry);
    }

    function subscribeSpectateMatch() {
        if (!spectatedMatchId || spectateJoinRequest) return;
        if (!socket?.connected) {
            showSpectateConnectionStatus();
            return;
        }
        const command = { matchId: spectatedMatchId };
        spectateJoinRequest = command;
        setSpectateLiveStatus("Ansluter till matchen …", "loading");
        sendSpectateCommand("spectate_join", command, (ack) => {
            if (spectateJoinRequest !== command) return;
            spectateJoinRequest = undefined;
            if (ack?.ok) receiveSpectateState(ack.state);
            else {
                spectateFinished = ack?.code === "match_unavailable";
                if (spectateFinished) putLocalized("spectate-live-phase", "Inte live");
                setSpectateLiveStatus(ack?.error || "Liveuppdateringarna kunde inte startas.",
                    spectateFinished ? "finished" : "error", !spectateFinished);
            }
        });
    }

    function leaveSpectateMatch() {
        if (socket?.connected) sendSpectateCommand("spectate_leave");
        spectatedMatchId = undefined;
        spectateJoinRequest = undefined;
        spectateState = undefined;
        spectateFinished = false;
        spectateChart.reset();
        drawSpectatePredictionChart?.();
    }

    function retrySpectating(titleId, subscribe) {
        byId(titleId).focus({ preventScroll: true });
        if (socket?.connected) subscribe();
        else if (socket) {
            socket.connect();
            showSpectateConnectionStatus();
        }
    }

    function receiveSpectateState(data) {
        if (screen !== "spectate-live" || data?.id !== spectatedMatchId) return;
        spectateJoinRequest = undefined;
        spectateFinished = data.status === "finished";
        spectateState = data;
        renderSpectateState(data);
    }

    function renderSpectateState(data, updateStatus = true) {
        const prediction = data.mode === "prediction";
        const counting = data.status === "countdown";
        const [first, second] = data.players;
        const winner = data.players.find((player) => player.id === data.winnerId);
        const phase = prediction ? (data.round?.phase === "reveal" ? "Facit" : "Prognos") : phaseLabels[data.storm];
        const timing = counting ? data.countdown : prediction && !spectateFinished ? data.remaining : data.elapsed;
        const storm = data.storm === "final" ? "KO" : data.storm === "market" ? "Slutstorm" : "Storm";
        const detail = prediction ? t("Runda {round} av {limit}", { round: data.round.number, limit: data.roundLimit })
            : t("{storm} om {time}", { storm: t(storm), time: clock(data.remaining) });
        if (updateStatus) {
            const finalStatus = winner ? t("{winner} vann matchen.", { winner: winner.name }) : "Matchen slutade oavgjort.";
            setSpectateLiveStatus(spectateFinished ? finalStatus : counting ? "Matchen startar snart" : "Live",
                spectateFinished ? "finished" : counting ? "countdown" : "live");
            putLocalized("spectate-live-phase", spectateFinished ? "Avslutad" : counting ? "Startar" : phase);
        }
        put("spectate-live-timing", clock(timing));
        put("spectate-live-detail", detail);
        show("spectate-live-detail", !counting && !spectateFinished);
        put("spectate-instrument", data.symbol);
        put("spectate-instrument-detail", [data.name, data.market, data.interval].filter(Boolean).join(" · "));
        put("spectate-price", formatNumber(data.price, amountFormat));
        show("spectate-synthetic", Boolean(data.synthetic));

        for (const [side, player] of [["first", first], ["second", second]]) {
            const prefix = `spectate-${side}`;
            health(prefix, player);
            show(`${prefix}-capital-row`, !prediction);
            put(`${prefix}-capital`, formatNumber(player.capital, amountFormat));
            const active = prediction ? data.round.phase === "predict" && player.locked : player.hasPosition;
            show(`${prefix}-activity`, active && !spectateFinished);
            putLocalized(`${prefix}-activity`, prediction ? "Prognos låst" : "Öppen position");
        }
        show("spectate-contest", true);
        show("spectate-prediction-chart-panel", prediction);
        show("spectate-trading-chart", !prediction);
        show("spectate-chart-footer", !prediction);
        stateAttribute("spectate-event", "event", data.event?.type ?? "");
        if (prediction) renderSpectatePrediction(data, first, second);
        else {
            spectateChart.update(data.bars);
            const event = data.event;
            const actor = data.players.find((player) => player.id === event?.actorId)?.name;
            const target = data.players.find((player) => player.id === event?.targetId)?.name;
            const damage = event?.damage > 0 ? ` · −${formatNumber(event.damage)} HP` : "";
            const eventLabels = {
                attack: t("{actor} · Attack{damage}", { actor, damage }),
                grow: t("{actor} · Grow", { actor }),
                loss: t("{actor} · Förlustaffär{damage}", { actor, damage }),
                ko: target ? `${target} · KO` : t("Storm · KO"),
            };
            show("spectate-prediction-reveal", false);
            message("spectate-event", eventLabels[event?.type]);
        }
    }

    function renderSpectatePrediction(data, first, second) {
        const outcome = data.round.outcome;
        show("spectate-prediction-reveal", Boolean(outcome));
        const chartOutcome = outcome ? {
            actualMoveBps: outcome.actualMoveBps,
            selfMoveBps: outcome.players.find((player) => player.id === first.id)?.moveBps,
            opponentMoveBps: outcome.players.find((player) => player.id === second.id)?.moveBps,
        } : null;
        drawSpectatePredictionChart?.({ bars: data.bars, outcome: chartOutcome, editable: false });
        if (!outcome) {
            message("spectate-event", "");
            return;
        }
        put("spectate-first-prediction-name", first.name);
        put("spectate-second-prediction-name", second.name);
        put("spectate-first-prediction", formatPrediction(chartOutcome.selfMoveBps));
        put("spectate-second-prediction", formatPrediction(chartOutcome.opponentMoveBps));
        put("spectate-actual-prediction", formatPrediction(chartOutcome.actualMoveBps));
        stateAttribute("spectate-first-prediction-card", "winner", String(first.id === outcome.winnerId));
        stateAttribute("spectate-second-prediction-card", "winner", String(second.id === outcome.winnerId));
        const winner = data.players.find((player) => player.id === outcome.winnerId);
        message("spectate-event", winner ? t("{winner} vann rundan · {damage} HP i skada", {
            winner: winner.name, damage: formatNumber(outcome.damage),
        })
            : "Oavgjord runda");
    }

    function newQueue(mode = "ranked") {
        if (!session.user || queueWanted || activityCommand) return;
        if (!socket || (!socket.connected && !socket.active)) {
            toast("Spelanslutningen är offline. Uppdatera sidan för att försöka igen.", "error");
            return;
        }
        resetMatch();
        queueWanted = true;
        queueMode = mode;
        queueData = undefined;
        queueLeavePending = false;
        queueReconnect = !socket.connected;
        renderQueue({ waited: 0 });
        activate("queue");
        if (socket.connected) sendQueueCommand(true);
    }

    function setActivityCommand(command) {
        activityCommand = command;
        for (const action of activityActions) disable(action, Boolean(command));
        putLocalized("bot-start-label", command?.event === "bot_start" ? "Startar …" : "Spela mot bot");
        renderQueueActions();
        renderPrivate();
        renderPrediction();
        renderPlayAgain();
    }

    function sendActivity(event, payload, failed, done = () => {}) {
        if (!session.user || activityCommand) return;
        if (!socket?.connected) {
            failed("Vänta tills spelet är anslutet och försök igen.");
            return;
        }
        const command = { event };
        setActivityCommand(command);
        const acknowledge = (error, ack) => {
            if (activityCommand !== command) return;
            setActivityCommand(undefined);
            if (error || !ack?.ok) failed(ack?.error || "Servern svarade inte. Försök igen.");
            else done();
        };
        const sender = socket.timeout(acknowledgements);
        if (payload === undefined) sender.emit(event, acknowledge);
        else sender.emit(event, payload, acknowledge);
    }

    function startBotMatch({ guide = false, fromQueue = false } = {}) {
        if (!session.user || activityCommand) return;
        if (fromQueue) {
            if (screen !== "queue" || !queueBotOffered() || queueCommand?.join) return;
        } else if (queueWanted) {
            return;
        }
        guideRequested = guide;
        message("guide-start-error", "");
        sendActivity("bot_start", undefined, (error) => {
            guideRequested = false;
            if (byId("bot-guide-dialog").open) message("guide-start-error", error, "error");
            else toast(error, "error");
        });
    }

    function startPractice() {
        if (queueWanted) return;
        byId("help-dialog").close();
        sendActivity("prediction_practice_start", undefined, (error) => toast(error, "error"), focusPracticeControls);
    }

    function practiceAction(event, payload) {
        if (match?.mode !== "prediction_practice" || !matchSynchronized) return;
        sendActivity(event, { matchId: match.id, ...payload }, (error) => toast(error, "error"), focusPracticeControls);
    }

    function focusPracticeControls() {
        const input = byId("prediction-move");
        if (screen === "match" && match?.mode === "prediction_practice" && !input.disabled) {
            if (primaryTouch.matches) {
                window.scrollTo(0, 0);
                byId("match-screen").focus({ preventScroll: true });
            } else {
                input.focus({ preventScroll: true });
            }
        }
    }

    function returnToMenu() {
        resetMatch();
        activate(inviteCode ? "invite" : "menu");
        renderPrivate();
    }

    function leaveResult() {
        const matchId = result?.id;
        const leave = () => {
            if (screen === "result" && result?.id === matchId) returnToMenu();
        };
        if (result?.mode === "private" && rematchOffer?.matchId === matchId && socket?.connected) {
            sendActivity("private_cancel", { matchId }, (error) => toast(error, "error"), leave);
        } else {
            leave();
        }
    }

    function receivePracticeEnded(data) {
        if (match?.mode !== "prediction_practice" || result || (data?.id != null && data.id !== match.id)) return;
        returnToMenu();
    }

    function forgetInviteCode() {
        if (!inviteCode) return;
        inviteCode = null;
        const url = new URL(window.location.href);
        url.searchParams.delete("match");
        window.history.replaceState(null, "", url);
    }

    function renderPrivate() {
        const hosting = Boolean(invitation);
        show("invite-share", hosting);
        show("invite-copy", hosting);
        if (hosting) {
            const url = new URL("/", window.location.origin);
            url.searchParams.set("match", invitation.code);
            byId("invite-link").value = url.href;
        }
        show("invite-join", Boolean(inviteCode) && !hosting);
        disable("friend-join", !socket?.connected || Boolean(activityCommand));
        disable("friend-cancel", Boolean(activityCommand) || (hosting && !socket?.connected));
        putLocalized("invite-cancel", hosting || inviteCode ? "Avbryt" : "Till huvudmenyn");
        let status = "Inbjudan är inte längre aktiv.";
        if (activityCommand?.event === "private_create") status = "Skapar inbjudan …";
        else if (hosting) status = "Dela länken och vänta på att din vän går med.";
        else if (inviteCode) status = "Du har fått en inbjudan till en orankad handelsduell.";
        putLocalized("invite-status", status);
    }

    function receivePrivateState(data) {
        if (!session.user || !data) return;
        invitation = data.invitation;
        rematchOffer = data.rematch;
        window.clearTimeout(privateStateTimer);
        const active = invitation ?? rematchOffer;
        if (active?.remaining > 0) {
            privateStateTimer = window.setTimeout(() => {
                invitation = undefined;
                rematchOffer = undefined;
                renderPrivate();
                renderPlayAgain();
            }, active.remaining * 1000);
        }
        if (invitation && screen !== "match" && screen !== "queue") activate("invite");
        renderPrivate();
        renderPlayAgain();
    }

    function privateCreate() {
        if (!socket?.connected) {
            toast("Vänta tills spelet är anslutet och försök igen.", "error");
            return;
        }
        activate("invite");
        sendActivity("private_create", undefined, (error) => {
            if (!invitation && screen === "invite") activate("menu");
            toast(error, "error");
        });
    }

    function privateCancel() {
        if (activityCommand) return;
        const leave = () => {
            forgetInviteCode();
            if (screen === "invite") activate("menu");
        };
        if (invitation) sendActivity("private_cancel", undefined, (error) => toast(error, "error"), leave);
        else leave();
    }

    async function copyInvite() {
        const input = byId("invite-link");
        try {
            await navigator.clipboard.writeText(input.value);
            toast("Inbjudningslänken är kopierad.", "success");
        } catch {
            input.focus();
            input.select();
            toast("Länken är markerad. Kopiera den för att dela den.");
        }
    }

    function leaveQueue() {
        if (activityCommand) return;
        queueWanted = false;
        queueLeavePending = true;
        queueReconnect = false;
        if (!socket?.connected) {
            renderQueueActions();
            activate("menu");
            return;
        }
        sendQueueCommand(false);
    }

    function sendQueueCommand(join) {
        if (!socket?.connected || (queueCommand && queueCommand.join === join)) return;
        const command = { join };
        queueCommand = command;
        renderQueueActions();
        const payload = join && queueMode === "prediction" ? { mode: queueMode } : {};
        socket.timeout(acknowledgements).emit(join ? "queue_join" : "queue_leave", payload, (error, ack) => {
            if (queueCommand !== command) return;
            queueCommand = undefined;
            if (error && !socket?.connected) return;
            if (error || ack?.ok === false) {
                if (join && queueWanted && screen === "queue") {
                    queueWanted = false;
                    activate("menu");
                }
                if (!join && screen === "queue") {
                    queueLeavePending = false;
                    queueWanted = true;
                }
                renderQueueActions();
                toast(ack?.error || "Kön svarade inte. Försök igen.", "error");
                return;
            }
            if (!join) {
                queueLeavePending = false;
                if (screen === "queue") activate("menu");
            }
            renderQueueActions();
        });
    }

    function receiveQueueState(data) {
        if (!data || screen === "match" || resultTimer) return;
        if (data.queued) {
            if (queueLeavePending) return;
            if (queueCommand?.join) queueCommand = undefined;
            if (!queueWanted && screen === "result") resetMatch();
            queueWanted = true;
            queueMode = data.mode === "prediction" ? "prediction" : "ranked";
            queueData = data;
            renderQueue(data);
            activate("queue");
            return;
        }
        // Socket.IO flushes the server's initial snapshot before firing "connect".
        if (queueWanted && (queueCommand?.join || queueReconnect) && !data.error) return;
        queueCommand = undefined;
        queueWanted = false;
        queueLeavePending = false;
        queueReconnect = false;
        queueData = undefined;
        renderQueueActions();
        if (screen === "queue") activate("menu");
        if (data.error) toast(data.error, "error");
    }

    function renderQueue(data) {
        put("queue-wait", clock(data.waited));
        put("queue-radius", numeric(data.radius) == null ? "—" : `±${formatNumber(data.radius)}`);
        putLocalized("queue-title", queueMode === "prediction" ? "Söker en ritduell" : "Söker motståndare");
        renderQueueActions();
    }

    function queueBotOffered() {
        return queueWanted && queueData?.waited >= queueBotWaitSeconds;
    }

    function renderQueueActions() {
        const botOffered = queueBotOffered();
        show("queue-bot", botOffered);
        disable("queue-bot", !botOffered || !socket?.connected || Boolean(queueCommand?.join || activityCommand));
        disable("leave-queue", queueCommand?.join === false || Boolean(activityCommand));
        if (botOffered) {
            const label = queueMode === "prediction" ? "Spela handelsduell mot bot" : "Spela mot bot";
            putLocalized("queue-bot-label", activityCommand?.event === "bot_start" ? "Startar …" : label);
        }
    }

    function preference(name, fallback) {
        try {
            return window.localStorage.getItem(`stockfight.${name}`) ?? fallback;
        } catch {
            return fallback;
        }
    }

    function savePreference(name, value) {
        try {
            window.localStorage.setItem(`stockfight.${name}`, String(value));
        } catch {
            // Settings still apply to the open page.
        }
    }

    function startGuideFor(data) {
        if (data.mode !== "bot") return;
        const userId = session.user.id;
        guideActive = guideRequested || preference(`guide.active.${userId}`, "") === data.id;
        if (guideActive) {
            markGuideSeen();
            savePreference(`guide.active.${userId}`, data.id);
            setPercent(25);
        }
        guideRequested = false;
    }

    function markGuideSeen() {
        guideSeen = true;
        savePreference(`guide.seen.${session.user.id}`, true);
    }

    function chooseGuideExample(choice) {
        for (const action of ["attack", "grow"]) {
            for (const button of buttons(`guide-example-${action}`)) {
                button.setAttribute("aria-pressed", String(action === choice));
            }
        }
        putLocalized("guide-example-result", tutorialProfitFeedback[choice] ?? "");
        show("guide-example-result", Boolean(choice));
    }

    function openBotGuide() {
        byId("help-dialog").close();
        chooseGuideExample();
        message("guide-start-error", "");
        openDialog("bot-guide");
    }

    function finishGuide() {
        if (!guideActive) return;
        const userId = session.user.id;
        savePreference(`guide.active.${userId}`, "");
        guideActive = false;
        renderGuide();
    }

    function renderGuide() {
        show("bot-guide", guideActive);
        if (!guideActive) return;
        const preview = visibleSellChoice();
        let step = "Välj insats och tryck UPP eller NER.";
        if (match?.self?.position) step = "Följ affären och stäng när du vill.";
        if (preview) step = preview.kind === "profit" ? "Attack gör skada. Grow sparar vinsten." : "Stäng till aktuell kurs eller fortsätt hålla.";
        putLocalized("bot-guide-step", step);
    }

    function applyEffects() {
        document.documentElement.classList.toggle("reduce-effects", !effectsEnabled || reducedMotion.matches);
    }

    function enableAudio() {
        if (!soundEnabled) return;
        try {
            const AudioContext = window.AudioContext || window.webkitAudioContext;
            if (!AudioContext) return;
            audio ||= new AudioContext();
            if (audio.state === "suspended") void audio.resume().catch(() => {});
        } catch {
            // Audio may be blocked until the next user gesture.
        }
    }

    function playSound(type) {
        if (!soundEnabled || audio?.state !== "running") return;
        const tones = {
            attack: [180, 80], grow: [340, 620], loss: [170, 120], ko: [110, 45],
            win: [440, 880], lose: [200, 100], draw: [300, 240],
        };
        const [start, end] = tones[type] ?? tones.loss;
        const oscillator = audio.createOscillator();
        const envelope = audio.createGain();
        const now = audio.currentTime;
        oscillator.type = type === "attack" || type === "ko" ? "triangle" : "sine";
        oscillator.frequency.setValueAtTime(start, now);
        oscillator.frequency.exponentialRampToValueAtTime(end, now + 0.19);
        envelope.gain.setValueAtTime(0.055, now);
        envelope.gain.exponentialRampToValueAtTime(0.001, now + 0.24);
        oscillator.connect(envelope);
        envelope.connect(audio.destination);
        oscillator.start(now);
        oscillator.stop(now + 0.24);
    }

    function clearEffect() {
        window.clearTimeout(effectTimer);
        activeMatchEvent = undefined;
        byId("match-screen")?.classList.remove("is-hit", "is-grow", "is-ko", "hit-self", "hit-opponent");
        show("match-event", false);
    }

    function resetMatch() {
        window.clearTimeout(resultTimer);
        resultTimer = undefined;
        match = undefined;
        matchSynchronized = false;
        result = undefined;
        nextSeq = undefined;
        tradeCommand = undefined;
        sellChoice = undefined;
        keptPositionId = undefined;
        tradeFocus = undefined;
        guideActive = false;
        lastEventId = undefined;
        clearEffect();
        message("match-feedback", "");
        resetPrediction();
        setPercent(100);
        matchChart.reset();
        show("sell-choice", false);
    }

    function health(prefix, player) {
        const hp = numeric(player?.hp);
        put(`${prefix}-name`, player?.name);
        const name = byId(`${prefix}-name`);
        if (name && player?.name && name.title !== player.name) name.title = player.name;
        put(`${prefix}-hp-label`, formatNumber(hp));
        progress(`${prefix}-hp`, hp);
        stateAttribute(`${prefix}-hp`, "health", hp === 0 ? "ko" : hp > 0 && hp <= 25 ? "low" : "normal");
    }

    function sameId(left, right) {
        return left != null && right != null && String(left) === String(right);
    }

    function matchEventLabel(event) {
        const acting = sameId(event.actorId, match.self?.id);
        const defending = sameId(event.targetId, match.self?.id);
        const actor = acting ? t("Du") : match.opponent?.name ?? t("Motståndaren");
        const target = defending ? t("Du") : match.opponent?.name ?? t("Motståndaren");
        const damage = numeric(event.damage);
        const messages = {
            attack: t("{actor} · ATTACK{damage}", {
                actor, damage: damage == null ? "" : ` · −${formatNumber(damage)} HP`,
            }),
            grow: t("{actor} · GROW", { actor }),
            loss: t("{actor} · Förlustaffär{damage}", {
                actor, damage: damage > 0 ? ` · −${formatNumber(damage)} HP` : "",
            }),
            ko: event.targetId == null ? t("Storm · KO") : `${target} · KO`,
        };
        return Object.hasOwn(messages, event.type) ? messages[event.type] : "";
    }

    function animateEvent(event) {
        if (!event || event.id === lastEventId) return;
        lastEventId = event.id;
        clearEffect();
        const label = matchEventLabel(event);
        if (!label) return;
        activeMatchEvent = event;
        put("match-event", label);
        stateAttribute("match-event", "event", event.type);
        show("match-event", true);
        playSound(event.type);
        const stage = byId("match-screen");
        if (stage && effectsEnabled && !reducedMotion.matches) {
            // Restart the animation when two consecutive events have the same type.
            void stage.offsetWidth;
            const effect = { attack: "is-hit", loss: "is-hit", grow: "is-grow", ko: "is-ko" }[event.type];
            const relatedId = event.type === "grow" || event.type === "loss" ? event.actorId : event.targetId;
            const ownSide = sameId(relatedId, match.self?.id);
            stage.classList.add(effect);
            if (event.targetId == null) stage.classList.add("hit-self", "hit-opponent");
            else stage.classList.add(ownSide ? "hit-self" : "hit-opponent");
        }
        effectTimer = window.setTimeout(clearEffect, 1400);
    }

    class PriceChart {
        constructor(containerId, statusId, controlsId) {
            this.containerId = containerId;
            this.statusId = statusId;
            this.controlsId = controlsId;
            this.bars = [];
            this.failed = false;
        }

        reset() {
            this.chart?.remove();
            this.chart = undefined;
            this.series = undefined;
            this.entryLine = undefined;
            this.bars = [];
            this.failed = false;
            show(this.controlsId, false);
        }

        create() {
            const library = window.LightweightCharts;
            const container = byId(this.containerId);
            if (!library || !container) throw new Error("Chart unavailable");
            const theme = getComputedStyle(container);
            const color = (key, fallback) => theme.getPropertyValue(key).trim() || fallback;
            const price = color("--chart-price", "#b9f467");
            const line = color("--chart-line", "#29334b");
            const label = color("--chart-label", "#91a0bb");
            this.chart = library.createChart(container, {
                autoSize: true,
                layout: {
                    attributionLogo: false,
                    background: { type: "solid", color: "transparent" },
                    textColor: label,
                    fontSize: 11,
                },
                grid: { vertLines: { color: line }, horzLines: { color: line } },
                rightPriceScale: { borderColor: line, scaleMargins: { top: 0.12, bottom: 0.12 } },
                timeScale: {
                    borderColor: line,
                    timeVisible: true,
                    tickMarkFormatter: (time) => String(time),
                    rightOffsetPixels: chartRightPadding,
                    rightBarStaysOnScroll: true,
                },
                localization: this.localization(),
                handleScale: { mouseWheel: false, pinch: true },
                handleScroll: { mouseWheel: false, horzTouchDrag: false, vertTouchDrag: false },
                trackingMode: { exitMode: library.TrackingModeExitMode.OnTouchEnd },
            });
            if (chartType === "candlestick") {
                const down = color("--chart-price-down", "#ff858a");
                this.series = this.chart.addSeries(library.CandlestickSeries, {
                    upColor: price,
                    downColor: down,
                    borderVisible: false,
                    wickUpColor: price,
                    wickDownColor: down,
                    priceLineColor: label,
                });
            } else {
                this.series = this.chart.addSeries(library.LineSeries, {
                    color: price,
                    lineWidth: 2,
                    priceLineColor: label,
                });
            }
            this.localize();
        }

        localization() {
            return {
                priceFormatter: (price) => formatNumber(price, amountFormat),
                timeFormatter: (time) => t("Kurspunkt {time}", { time }),
            };
        }

        localize() {
            if (!this.series) return;
            this.chart.applyOptions({ localization: this.localization() });
            byId(this.containerId).setAttribute("aria-label",
                this.series.seriesType() === "Candlestick" ? t("Kursgraf med ljusstaplar") : t("Linjegraf över aktiekursen"));
        }

        zoom(factor) {
            if (!this.bars.length || this.failed) return;
            const timeScale = this.chart.timeScale();
            const width = timeScale.width();
            if (!width) return;
            const { barSpacing, minBarSpacing } = timeScale.options();
            const spacing = Math.max(minBarSpacing, Math.min(width / 2, barSpacing * factor));
            timeScale.applyOptions({ barSpacing: spacing, rightOffsetPixels: chartRightPadding });
        }

        update(bars, position) {
            if (this.failed) return;
            if (!bars?.length) {
                message(this.statusId, "Väntar på kursgraf …");
                return;
            }
            try {
                if (!this.chart) this.create();
                const toPoint = this.series.seriesType() === "Candlestick"
                    ? ({ time, open, high, low, close }) => ({
                        time: Number(time), open: Number(open), high: Number(high), low: Number(low), close: Number(close),
                    })
                    : ({ time, close }) => ({ time: Number(time), value: Number(close) });
                const sameBar = (left, right) => left.time === right.time && left.open === right.open
                    && left.high === right.high && left.low === right.low && left.close === right.close;
                const last = this.bars.length - 1;
                const append = last >= 0 && this.bars.length <= bars.length
                    && this.bars[last].time === bars[last].time
                    && this.bars.slice(0, last).every((bar, index) => sameBar(bar, bars[index]));
                if (append) {
                    if (!sameBar(this.bars[last], bars[last])) this.series.update(toPoint(bars[last]));
                    for (const bar of bars.slice(last + 1)) this.series.update(toPoint(bar));
                } else {
                    this.series.setData(bars.map(toPoint));
                    if (!this.bars.length) {
                        this.chart.timeScale().fitContent();
                        show(this.controlsId, true);
                    }
                }
                this.bars = bars;

                const entry = numeric(position?.entryPrice);
                if (entry != null && this.entryLine) {
                    this.entryLine.applyOptions({ price: entry, title: positionDirection(position) });
                } else if (entry != null) {
                    this.entryLine = this.series.createPriceLine({
                        price: entry,
                        color: "#c4acff",
                        lineWidth: 1,
                        lineStyle: window.LightweightCharts.LineStyle.Dashed,
                        axisLabelVisible: true,
                        title: positionDirection(position),
                    });
                } else if (this.entryLine) {
                    this.series.removePriceLine(this.entryLine);
                    this.entryLine = undefined;
                }
                message(this.statusId, "");
            } catch {
                this.failed = true;
                show(this.controlsId, false);
                message(this.statusId, "Kursgrafen kunde inte visas.", "error");
            }
        }
    }

    const matchChart = new PriceChart("match-chart", "match-chart-status", "chart-controls");
    const spectateChart = new PriceChart("spectate-chart", "spectate-chart-status", "spectate-chart-controls");

    function parsePrediction(value) {
        const parts = /^([+-]?)(\d*)(?:[,.](\d{0,2}))?$/.exec(value.trim().replace("−", "-"));
        if (!parts || (!parts[2] && !parts[3])) return null;
        const [, sign, whole, fraction = ""] = parts;
        const magnitude = Number(whole + fraction.padEnd(2, "0"));
        const bps = sign === "-" ? -magnitude : magnitude;
        return Number.isSafeInteger(bps) && bps >= -10_000 ? bps : null;
    }

    function predictionInputValue(bps) {
        if (bps == null) return "";
        const magnitude = Math.abs(bps);
        const fraction = magnitude % 100;
        const whole = (magnitude - fraction) / 100;
        const separator = getLocale() === "sv-SE" ? "," : ".";
        const decimal = fraction ? separator + String(fraction).padStart(2, "0").replace(/0$/, "") : "";
        return `${bps < 0 ? "-" : ""}${whole}${decimal}`;
    }

    function formatPrediction(bps) {
        if (bps == null) return t("Inget svar");
        return predictionPercentFormat.format(bps / 10_000);
    }

    function predictionVerdict(outcome, selfId, opponentName) {
        if (outcome.winnerId == null) {
            if (outcome.selfMoveBps == null && outcome.opponentMoveBps == null) {
                return { side: "draw", title: t("Inga prognoser"), reason: t("Tiden gick ut för båda spelarna. Ingen tog skada.") };
            }
            return { side: "draw", title: t("Oavgjord runda"), reason: t("Ni kom lika nära facit. Ingen tog skada.") };
        }

        const won = String(outcome.winnerId) === String(selfId);
        const winner = won ? t("Du") : opponentName;
        const side = won ? "self" : "opponent";
        const title = t("{winner} vann rundan", { winner });
        const otherError = won ? outcome.opponentErrorBps : outcome.selfErrorBps;
        if (otherError == null) {
            return { side, title, reason: t("{winner} var ensam om att låsa en prognos.", { winner }) };
        }
        const winnerError = won ? outcome.selfErrorBps : outcome.opponentErrorBps;
        const margin = formatNumber((otherError - winnerError) / 100, amountFormat);
        return { side, title, reason: t("{winner} kom {margin} procentenheter närmare facit.", { winner, margin }) };
    }

    function predictionReady() {
        const round = match?.round;
        return Boolean(socket?.connected && matchSynchronized && isPrediction(match?.mode)
            && match.status === "active" && round?.phase === "predict"
            && !round.selfLocked && !predictionCommand && !activityCommand && !result);
    }

    function isPrediction(mode) {
        return mode === "prediction" || mode === "prediction_practice";
    }

    function resetPrediction() {
        predictionRound = undefined;
        predictionCommand = undefined;
        predictionSubmitFocus = false;
        byId("prediction-move").value = "";
        message("prediction-feedback", "");
        drawPredictionChart?.();
    }

    function syncPredictionRound() {
        const round = match.round;
        if (predictionRound !== round?.number) {
            resetPrediction();
            predictionRound = round?.number;
        }
        const focusNext = round?.phase === "reveal" && match.mode === "prediction_practice" && predictionSubmitFocus;
        if (round?.selfLocked) {
            predictionCommand = undefined;
            predictionSubmitFocus = false;
            byId("prediction-move").value = predictionInputValue(round.selfMoveBps);
            message("prediction-feedback", "");
        }
        renderPrediction();
        if (focusNext) byId("practice-next").focus();
    }

    function renderPrediction() {
        if (!isPrediction(match?.mode)) return;
        const practice = match.mode === "prediction_practice";
        const round = match.round;
        const outcome = round?.outcome;
        const input = byId("prediction-move");
        const signButton = byId("prediction-sign");
        const editable = predictionReady();
        const guess = round?.selfLocked ? round.selfMoveBps : parsePrediction(input.value);
        input.disabled = !editable;
        signButton.disabled = !editable;
        signButton.setAttribute("aria-pressed", String(/^[-−]/.test(input.value.trimStart())));
        input.setAttribute("aria-invalid", String(editable && input.value.trim() !== "" && guess == null));
        byId("prediction-lock").disabled = !editable || guess == null;
        disable("prediction-clear", !editable || input.value === "");
        show("prediction-controls", match.status === "active" && round?.phase === "predict");
        show("prediction-breakdown", Boolean(outcome));
        show("prediction-opponent-breakdown", !practice);
        show("practice-next", practice && Boolean(outcome));
        disable("practice-next", !socket?.connected || !matchSynchronized || Boolean(activityCommand) || Boolean(result));
        disable("practice-leave", !socket?.connected || !matchSynchronized || Boolean(activityCommand));
        if (practice) {
            putLocalized("practice-next", round?.number === match.roundLimit ? "Se sammanfattning" : "Nästa runda");
        }

        const opponentName = match.opponent?.name || t("Motståndaren");
        const verdict = outcome && !practice ? predictionVerdict(outcome, match.self?.id, opponentName) : null;
        stateAttribute("prediction-verdict", "side", verdict?.side ?? "");
        stateAttribute("prediction-self-breakdown", "winner", String(verdict?.side === "self"));
        stateAttribute("prediction-opponent-breakdown", "winner", String(verdict?.side === "opponent"));
        show("prediction-reason", Boolean(verdict));
        if (outcome) {
            put("prediction-actual", formatPrediction(outcome.actualMoveBps));
            put("prediction-self", formatPrediction(outcome.selfMoveBps));
            put("prediction-opponent-name", opponentName);
            put("prediction-opponent", formatPrediction(outcome.opponentMoveBps));
            for (const [side, bps] of [["self", outcome.selfErrorBps], ["opponent", outcome.opponentErrorBps]]) {
                const id = `prediction-${side}-error`;
                show(id, bps != null);
                if (bps != null) put(id, t("{error} procentenheter fel", { error: formatNumber(bps / 100, amountFormat) }));
            }
            put("prediction-status", verdict?.title ?? t("Facit för rundan"));
            if (verdict) {
                const damage = outcome.damage ? t("{player} förlorade {damage} HP.", {
                    player: verdict.side === "self" ? opponentName : t("Du"),
                    damage: formatNumber(outcome.damage),
                }) : null;
                put("prediction-reason", [verdict.reason, damage].filter(Boolean).join(" "));
            }
        } else if (match.status === "countdown") {
            putLocalized("prediction-status", "Gör dig redo att gissa nästa kursrörelse.");
        } else if (round?.selfLocked) {
            putLocalized("prediction-status", "Prognosen är låst. Väntar på facit.");
        } else if (predictionCommand) {
            putLocalized("prediction-status", "Låser prognosen …");
        } else if (!socket?.connected || !matchSynchronized) {
            putLocalized("prediction-status", "Väntar på anslutning …");
        } else {
            putLocalized("prediction-status", round?.opponentLocked ? "Motståndaren har låst sin prognos." : "Hur rör sig kursen härnäst?");
        }
        drawPredictionChart?.({ bars: match.bars, guess, outcome, editable });
    }

    function setPredictionDraft(bps) {
        if (!predictionReady()) return;
        byId("prediction-move").value = predictionInputValue(bps);
        message("prediction-feedback", "");
        renderPrediction();
    }

    function predictionInputChanged() {
        const value = byId("prediction-move").value.trim();
        const incomplete = /^[-+−]?[,.]?$/.test(value);
        const error = !incomplete && parsePrediction(value) == null;
        message("prediction-feedback", error ? "Ange minst −100 % med högst två decimaler." : "", "error");
        renderPrediction();
    }

    function togglePredictionSign() {
        if (!predictionReady()) return;
        const input = byId("prediction-move");
        const value = input.value.trim();
        const unsigned = value.replace(/^[-+−]/, "");
        input.value = /^[-−]/.test(value) ? unsigned : `-${unsigned}`;
        predictionInputChanged();
    }

    function submitPrediction(event) {
        event.preventDefault();
        if (!predictionReady()) return;
        const moveBps = parsePrediction(byId("prediction-move").value);
        if (moveBps == null) return;
        enableAudio();

        const command = { matchId: match.id, round: match.round.number, moveBps };
        predictionCommand = command;
        predictionSubmitFocus = event.currentTarget.contains(document.activeElement);
        message("prediction-feedback", "");
        renderPrediction();
        socket.timeout(acknowledgements).emit("prediction_submit", command, (error, ack) => {
            if (predictionCommand !== command || (!error && ack?.ok)) return;
            predictionCommand = undefined;
            const restoreFocus = predictionSubmitFocus;
            predictionSubmitFocus = false;
            message("prediction-feedback", ack?.error || "Prognosen kunde inte bekräftas. Försök igen.", "error");
            renderPrediction();
            if (restoreFocus) byId("prediction-move").focus();
        });
    }

    function receiveMatchState(data) {
        if (!data?.id || !session.user || lastResultId === data.id) return;
        if (match?.id !== data.id) {
            resetMatch();
            startGuideFor(data);
        }
        queueWanted = false;
        queueLeavePending = false;
        queueReconnect = false;
        queueCommand = undefined;
        queueData = undefined;
        renderQueueActions();
        match = data;
        matchSynchronized = true;
        if (numeric(data.nextSeq) != null) nextSeq = Math.max(nextSeq ?? 0, Number(data.nextSeq));
        sellChoice = data.self?.position?.closePreview ?? undefined;
        if (!sellChoice || sellChoice.positionId !== keptPositionId) keptPositionId = undefined;
        if (data.mode === "private") forgetInviteCode();
        activate("match");
        renderMatch(data, true);
        animateEvent(data.event);
    }

    function renderMatch(data, syncRound = false) {
        stateAttribute("match-screen", "mode", data.mode ?? "ranked");
        stateAttribute("match-screen", "phase", data.status);
        stateAttribute("match-screen", "storm", data.storm ?? "normal");
        const prediction = isPrediction(data.mode);
        const practice = data.mode === "prediction_practice";
        const counting = data.status === "countdown";
        const finished = data.status === "finished";
        const phase = prediction ? (data.round?.phase === "reveal" ? "Facit" : "Prognos")
            : phaseLabels[data.storm] ?? "Handel";
        putLocalized("match-phase", counting ? "Startar" : finished ? "Avslutad" : phase);
        const remaining = prediction ? data.remaining : data.elapsed;
        put("match-time", clock(counting ? data.countdown : remaining));
        const stormTime = clock(data.remaining);
        const storm = data.storm === "final" ? "KO" : data.storm === "market" ? "Slutstorm" : "Storm";
        const stormClock = t("{storm} om {time}", { storm: t(storm), time: stormTime });
        const roundLabel = t("Runda {round} av {limit}", { round: data.round?.number, limit: data.roundLimit ?? 8 });
        put("match-clock-detail", prediction ? roundLabel : stormClock);
        put("practice-round", roundLabel);
        show("match-hud", !practice);
        show("practice-header", practice);
        show("match-clock-detail", !counting && !finished);
        put("countdown-number", Math.max(1, Math.ceil(numeric(data.countdown) ?? 3)));
        show("countdown-overlay", counting);
        put("match-symbol", instrumentSymbol(data, practice));
        put("match-name", instrumentName(data, practice));
        put("match-market", [data.market, data.interval].filter(Boolean).join(" · "));
        put("match-price", formatNumber(data.price, amountFormat));
        show("match-synthetic", Boolean(data.synthetic));
        health("self", data.self);
        health("opponent", data.opponent);
        const botElo = data.mode === "bot" ? numeric(data.opponent?.elo) : null;
        const opponentHasPosition = Boolean(data.opponent?.hasPosition);
        if (botElo != null) put("opponent-elo", `${formatNumber(botElo)} Elo`);
        show("opponent-elo", botElo != null);
        show("opponent-position", opponentHasPosition);
        show("self-trade-details", !prediction);
        show("opponent-capital-stat", !prediction);
        show("opponent-details", !prediction || botElo != null || opponentHasPosition);
        show("trade-panel", !prediction);
        show("match-chart", !prediction);
        show("chart-footer", !prediction);
        show("prediction-panel", prediction);
        show("prediction-chart", prediction);
        renderGuide();
        if (prediction) {
            show("match-chart-status", false);
            if (syncRound) syncPredictionRound();
            else {
                if (data.round?.selfLocked) byId("prediction-move").value = predictionInputValue(data.round.selfMoveBps);
                renderPrediction();
            }
            return;
        }
        const position = data.self?.position;
        const attackPower = numeric(data.self?.attackPower);
        put("self-capital", formatNumber(data.self?.capital, amountFormat));
        put("opponent-capital", formatNumber(data.opponent?.capital, amountFormat));
        put("self-attack-power", percentage(attackPower));
        stateAttribute("self-attack-power", "sign", sign((attackPower ?? 100) - 100));
        put("match-cash", formatNumber(data.self?.cash, amountFormat));
        put("match-invested", formatNumber(position?.invested ?? 0, amountFormat));
        put("match-grow", formatNumber(data.self?.growBonus));
        stateAttribute("grow-stat", "charged", String(data.self?.growBonus > 0));
        const directionArrow = position?.side === "short" ? "↘" : "↗";
        put("match-direction", position ? `${directionArrow} ${positionDirection(position)}` : null);
        stateAttribute("match-direction", "side", position?.side ?? "");
        put("match-entry", formatNumber(position?.entryPrice, amountFormat));
        put("match-pnl", signed(position?.pnl, amountFormat));
        stateAttribute("match-pnl", "sign", sign(numeric(position?.pnl)));
        matchChart.update(data.bars, position);
        renderTradeControls();
    }

    function instrumentSymbol(data, practice) {
        return practice && data.symbol === "ÖVNING" ? t("ÖVNING") : data.symbol;
    }

    function instrumentName(data, practice) {
        return practice && data.name === "Ritduell" ? t("Ritduell") : data.name;
    }

    function setPercent(value) {
        if (![25, 50, 75, 100].includes(value)) return;
        percent = value;
        for (const button of document.querySelectorAll("[data-percent]")) {
            button.setAttribute("aria-pressed", String(Number(button.dataset.percent) === value));
        }
    }

    function renderStake() {
        const cash = numeric(match?.self?.cash);
        for (const stake of [25, 50, 75, 100]) {
            put(`stake-${stake}`, cash == null ? "—" : formatNumber(cash * stake / 100, amountFormat));
        }
    }

    function tradeReady() {
        return Boolean(socket?.connected && matchSynchronized && match?.status === "active" && !tradeCommand
            && !result && nextSeq != null && (sellChoice || Number(match.nextSeq) >= nextSeq));
    }

    function visibleSellChoice() {
        return sellChoice?.positionId === keptPositionId ? undefined : sellChoice;
    }

    function keepHolding() {
        if (!tradeReady() || !visibleSellChoice()) return;
        keptPositionId = sellChoice.positionId;
        tradeFocus = "sell";
        message("match-feedback", "");
        renderGuide();
        renderTradeControls();
    }

    function renderTradeControls() {
        const ready = tradeReady();
        const position = match?.self?.position;
        const preview = visibleSellChoice();
        const choosing = ready && Boolean(preview);
        const profitable = preview?.kind === "profit";
        const canOpen = ready && !position && numeric(match?.self?.cash) > 0;
        const step = preview ? "exit" : position ? "hold" : "entry";
        for (const item of byId("trade-steps").children) {
            const current = item.dataset.tradeStep === step;
            if (current !== item.hasAttribute("aria-current")) {
                if (current) item.setAttribute("aria-current", "step");
                else item.removeAttribute("aria-current");
            }
        }
        const focusedAction = tradeFocus ?? document.activeElement?.dataset.action;
        if (choosing && profitable && focusedAction === "confirm-close") tradeFocus = "attack";
        if (choosing && !profitable && ["attack", "grow"].includes(focusedAction)) tradeFocus = "confirm-close";
        disable("buy", !canOpen);
        disable("short", !canOpen);
        disable("sell", !ready || !position || Boolean(preview));
        disable("attack", !choosing || !profitable);
        disable("grow", !choosing || !profitable);
        disable("confirm-close", !choosing || profitable);
        disable("keep-holding", !choosing);
        show("open-order", !position);
        show("position-summary", Boolean(position));
        show("close-order", Boolean(position) && !preview);
        show("sell-choice", Boolean(preview));
        show("profit-actions", profitable);
        show("pending-close", Boolean(preview) && !profitable);
        renderStake();
        if (preview) {
            putLocalized("sell-choice-title", profitable ? "Använd vinsten" : "Avsluta affären");
            let hint = t("Vid aktuell kurs");
            if (profitable) {
                put("attack-preview", t("{damage} HP skada", { damage: formatNumber(preview.attackDamage) }));
                put("grow-preview", t("{credits} krediter · {bonus} bonus-HP", {
                    credits: signed(preview.growCredits, amountFormat), bonus: formatNumber(preview.growBonus),
                }));
            } else if (preview.kind === "loss") {
                hint = t("{credits} krediter · {damage} HP", {
                    credits: signed(-Number(preview.lossCredits), amountFormat), damage: signed(-preview.lossDamage),
                });
            } else {
                hint = t("±0 krediter");
            }
            put("sell-choice-hint", hint);
        }
        for (const button of document.querySelectorAll("[data-percent]")) {
            button.disabled = !canOpen;
        }
        if (ready && tradeFocus) {
            const target = document.querySelector(`[data-action="${tradeFocus}"]:enabled`);
            if (target) {
                tradeFocus = undefined;
                target.focus({ preventScroll: true });
            }
        }
    }

    function trade(action, choice) {
        if (!tradeReady()) return;
        if (action === "sell" && sellChoice && !visibleSellChoice()) {
            keptPositionId = undefined;
            tradeFocus = sellChoice.kind === "profit" ? "attack" : "confirm-close";
            renderGuide();
            renderTradeControls();
            return;
        }
        if (action === "confirm_sell" && !visibleSellChoice()) return;
        const buttonAction = action === "confirm_sell" && sellChoice?.kind !== "profit" ? "confirm-close" : choice ?? action;
        const opensPosition = action === "buy" || action === "short";
        const reopenAction = match.self?.position?.side === "short" ? "short" : "buy";
        const restoreFocus = document.activeElement?.dataset.action === buttonAction;
        tradeFocus = undefined;
        const command = { matchId: match.id, seq: nextSeq, action };
        if (action === "confirm_sell") {
            command.positionId = sellChoice.positionId;
            command.choice = choice;
        } else if (opensPosition) {
            command.percent = percent;
        }
        tradeCommand = command;
        message("match-feedback", "");
        renderTradeControls();
        socket.timeout(acknowledgements).emit("trade", command, (error, ack) => {
            if (tradeCommand !== command) return;
            tradeCommand = undefined;
            if (error || !ack?.ok) {
                if (restoreFocus) tradeFocus = buttonAction;
                message("match-feedback", ack?.error || "Handeln kunde inte bekräftas. Kontrollera din position.", "error");
            } else {
                nextSeq = Math.max(nextSeq, command.seq + 1);
                if (ack.requiresChoice && ack.positionId) {
                    if (restoreFocus) tradeFocus = sellChoice?.kind === "profit" ? "attack" : "confirm-close";
                } else if (!opensPosition) {
                    sellChoice = undefined;
                    if (action === "confirm_sell" && buttonAction !== "confirm-close") finishGuide();
                    if (restoreFocus) tradeFocus = reopenAction;
                } else if (restoreFocus) {
                    tradeFocus = "sell";
                }
            }
            renderTradeControls();
        });
    }

    function receiveResult(data) {
        if (!data?.id || !session.user || lastResultId === data.id
            || (match && match.id !== data.id)) return;
        finishGuide();
        result = data;
        lastResultId = data.id;
        queueWanted = false;
        queueLeavePending = false;
        queueReconnect = false;
        queueCommand = undefined;
        sellChoice = undefined;
        renderTradeControls();
        renderPrediction();
        const stage = byId("match-screen");
        if (screen === "match" && stage?.classList.contains("is-ko") && effectsEnabled && !reducedMotion.matches) {
            resultTimer = window.setTimeout(() => renderResult(data), 650);
        } else {
            renderResult(data);
        }
    }

    function renderPlayAgain() {
        if (!result) return;
        const mode = result.mode ?? match?.mode ?? "ranked";
        if (mode !== "private") {
            putLocalized("result-rematch", activityCommand ? "Startar …" : "Spela igen");
            disable("play-again", Boolean(activityCommand));
            message("result-revenge-status", "");
            return;
        }
        const offer = rematchOffer?.matchId === result.id ? rematchOffer : null;
        putLocalized("result-rematch", "Revansch mot samma spelare");
        disable("play-again", !socket?.connected || Boolean(activityCommand) || !offer?.available || offer.selfAccepted);
        let status = "Revansch är inte tillgänglig.";
        if (activityCommand?.event === "private_rematch") status = "Skickar ditt svar …";
        else if (offer && !offer.available) status = "Motståndaren är inte ansluten.";
        else if (offer?.selfAccepted) status = "Väntar på att motståndaren accepterar.";
        else if (offer?.opponentAccepted) status = "Motståndaren vill ha revansch.";
        else if (offer) status = "Revanschen startar när båda accepterar.";
        message("result-revenge-status", status);
    }

    function matchExplanation(data) {
        const self = data.endActor === "self";
        const opponent = data.endActor === "opponent";
        switch (data.endReason) {
            case "attack": return t(self ? "Din attack avgjorde matchen." : opponent ? "Motståndarens attack avgjorde matchen." : "Matchen avgjordes av en attack.");
            case "trade_loss": return t(self ? "Din förlustaffär avslutade matchen." : "Motståndarens förlustaffär avslutade matchen.");
            case "market_storm":
            case "final_storm": {
                const storm = data.endReason === "market_storm" ? "marknadsstormen" : "slutstormen";
                if (numeric(data.hp) === 0 && numeric(data.opponentHp) === 0) {
                    const tiebreak = {
                        capital: "Högst slutkapital avgjorde.",
                        attack_damage: "Kapitalet var lika, så mest attackskada avgjorde.",
                    }[data.tiebreak] ?? "Ni hade lika mycket kapital och gjorde lika mycket attackskada.";
                    return t("Båda slogs ut i {storm}. {tiebreak}", { storm: t(storm), tiebreak: t(tiebreak) });
                }
                return t("Matchen avgjordes i {storm}.", { storm: t(storm) });
            }
            case "knockout": return t("Matchen avgjordes genom knockout.");
            case "round_limit": return t("Matchen avgjordes av slut-HP efter sista rundan.");
            default: return "";
        }
    }

    function predictionMatchExplanation(data, opponentName) {
        if (data.endReason === "knockout") {
            const knockout = t(data.outcome === "win" ? "Du sänkte {opponent} till 0 HP." : "{opponent} sänkte dig till 0 HP.", {
                opponent: opponentName,
            });
            const round = data.lastRound ?? data.rounds?.at(-1);
            return round ? `${knockout} ${predictionVerdict(round, session.user.id, opponentName).reason}` : knockout;
        }
        if (data.endReason === "round_limit") {
            if (data.outcome === "draw") return t("Ni hade lika mycket HP kvar efter sista rundan.");
            const winner = data.outcome === "win" ? t("Du") : opponentName;
            return t("{winner} hade mest HP kvar efter sista rundan.", { winner });
        }
        return matchExplanation(data);
    }

    function renderResultDetails(data, mode, preserveDetails) {
        const practice = mode === "prediction_practice";
        const prediction = mode === "prediction";
        const opponentName = data.opponentName || match?.opponent?.name || t("Motståndaren");
        const explanation = prediction ? predictionMatchExplanation(data, opponentName) : matchExplanation(data);
        const comparison = numeric(data.opponentHp) != null;
        show("result-explanation", comparison || Boolean(explanation));
        show("result-comparison", comparison);
        show("result-decisive", Boolean(explanation));
        put("result-decisive", explanation);
        put("result-self-hp", formatNumber(data.hp));
        put("result-opponent-hp", formatNumber(data.opponentHp));
        put("result-opponent-label", prediction ? t("{opponent} · slut-HP", { opponent: opponentName })
            : t("Motståndarens slut-HP"));
        show("result-trade-hp-stat", !comparison);
        show("result-prediction-hp-stat", !practice && !comparison);

        const tradeLabels = { attack: "Attack", grow: "Grow", loss: "Förlust", flat: "Ingen vinst eller förlust" };
        const trades = (data.tradeDetails ?? []).map((trade) => [
            clock(trade.time), positionDirection(trade), tradeLabels[trade.choice] ? t(tradeLabels[trade.choice]) : null,
            t("{credits} krediter", { credits: signed(trade.profit, amountFormat) }), `${formatNumber(trade.damage)} HP`,
        ]);
        if (!preserveDetails) byId("result-trade-detail").open = false;
        show("result-trade-detail", trades.length > 0);
        fillTable("result-trade-list", trades);

        const forecast = (value) => value == null ? t("Ingen prognos") : formatPrediction(value);
        const error = (value) => value == null ? "—" : t("{error} procentenheter", {
            error: formatNumber(value / 100, amountFormat),
        });
        const rounds = (data.rounds ?? []).map((round) => {
            const values = [formatPrediction(round.actualMoveBps), forecast(round.selfMoveBps), error(round.selfErrorBps)];
            if (practice) return [round.number, ...values];
            const verdict = predictionVerdict(round, session.user.id, opponentName);
            const impact = round.damage ? " · " + t("{damage} HP i skada", { damage: formatNumber(round.damage) }) : "";
            return [round.number, verdict.title + impact, ...values, forecast(round.opponentMoveBps), error(round.opponentErrorBps)];
        });
        if (!preserveDetails) byId("result-round-detail").open = rounds.length > 0;
        show("result-round-detail", rounds.length > 0);
        put("round-opponent-header", opponentName);
        show("round-opponent-header", !practice);
        show("round-opponent-error-header", !practice);
        show("round-outcome-header", !practice);
        fillTable("result-round-list", rounds);
    }

    function renderResult(data) {
        resultTimer = undefined;
        if (result !== data || !session.user) return;
        const mode = data.mode ?? match?.mode ?? "ranked";
        renderResultView(data, mode);
        activate("result");
        if (mode !== "prediction_practice") playSound(data.outcome);
        if (mode === "ranked") void refreshProfile();
    }

    function renderResultView(data, mode, preserveDetails = false) {
        const practice = mode === "prediction_practice";
        const prediction = isPrediction(mode);
        const rated = mode === "ranked" || mode === "prediction";
        stateAttribute("result-screen", "mode", mode);
        stateAttribute("result-screen", "outcome", data.outcome);
        const labels = { prediction: "Ritduell", prediction_practice: "Ritduell · Övning",
            bot: "Botduell · Orankad", private: "Vänduell · Orankad" };
        const label = labels[mode] ?? "Matchresultat";
        putLocalized("result-mode", label);
        const predictionOutcomes = { win: "Du vann", lose: "Du förlorade", draw: "Oavgjort" };
        const outcomes = prediction ? predictionOutcomes : outcomeLabels;
        putLocalized("result-outcome", practice ? "Övning klar" : outcomes[data.outcome] ?? "MATCH SLUT");
        show("result-elo", rated);
        if (rated) {
            put("result-elo-before", formatNumber(data.eloBefore));
            put("result-elo-after", formatNumber(data.eloAfter));
            const before = numeric(data.eloBefore);
            const after = numeric(data.eloAfter);
            const delta = before == null || after == null ? null : after - before;
            put("result-elo-delta", signed(delta));
            stateAttribute("result-elo-delta", "sign", sign(delta));
        }
        show("result-trade-stats", !prediction);
        show("result-prediction-stats", prediction);
        show("result-prediction-attack-stat", !practice);
        if (prediction) {
            put("result-rounds", formatNumber(data.roundsPlayed));
            put("result-prediction-hp", formatNumber(data.hp));
            put("result-prediction-attack", formatNumber(data.attackDamage));
            put("result-prediction-duration", clock(data.duration));
        } else {
            put("result-hp", formatNumber(data.hp));
            put("result-capital", formatNumber(data.capital, amountFormat));
            show("result-opponent-capital-stat", numeric(data.opponentCapital) != null);
            put("result-opponent-capital", formatNumber(data.opponentCapital, amountFormat));
            put("result-attack", formatNumber(data.attackDamage));
            put("result-grow", formatNumber(data.growCount));
            put("result-trades", formatNumber(data.trades));
            put("result-wins", formatNumber(data.winningTrades));
            put("result-losses", formatNumber(data.losingTrades));
            put("result-peak", formatNumber(data.peakCapital, amountFormat));
            put("result-duration", clock(data.duration));
        }
        const instrument = [instrumentSymbol(data, practice), instrumentName(data, practice), data.market, data.interval].filter(Boolean);
        if (data.synthetic) instrument.push(t("Syntetisk"));
        put("result-symbol", instrument.join(" · "));
        put("result-period", period(data.periodStart, data.periodEnd, data.interval));
        renderResultDetails(data, mode, preserveDetails);
        renderPlayAgain();
    }

    function refreshLanguage() {
        configureFormats();
        for (const [id, value] of [...localizedValues]) putLocalized(id, value);
        renderOnlineCount();
        if (menuProfileData) renderMenuProfile(menuProfileData);
        if (profileData) renderProfile(profileData);
        if (rankingData) renderRanking(rankingData);
        if (screen === "tutorial") renderTutorial();
        if (screen === "queue" && queueData) renderQueue(queueData);
        if (screen === "spectate" && spectateListData) renderSpectateList(spectateListData);
        if (screen === "spectate-live" && spectateState) {
            const state = byId("spectate-status").dataset.state;
            spectateChart.localize();
            renderSpectateState(spectateState, ["live", "countdown", "finished"].includes(state));
        }
        if (screen === "match" && match) {
            matchChart.localize();
            renderMatch(match);
            if (activeMatchEvent) put("match-event", matchEventLabel(activeMatchEvent));
        }
        if (screen === "result" && result) {
            renderResultView(result, result.mode ?? match?.mode ?? "ranked", true);
        }
    }

    function onClick(event) {
        const button = event.target.closest("[data-action], [data-percent]");
        if (!button || button.disabled) return;
        enableAudio();
        if (button.hasAttribute("data-percent")) {
            setPercent(Number(button.dataset.percent));
            return;
        }
        switch (button.dataset.action) {
            case "auth-login": setAuthMode("login"); break;
            case "auth-register": setAuthMode("register"); break;
            case "tutorial-replay":
                if (screen === "menu") openTutorial();
                break;
            case "tutorial-exit": enterLobby(); break;
            case "tutorial-back": moveTutorial(-1); break;
            case "tutorial-next": moveTutorial(1); break;
            case "tutorial-up": chooseTutorialDirection("up"); break;
            case "tutorial-down": chooseTutorialDirection("down"); break;
            case "tutorial-close-position":
                tutorial.closed = true;
                renderTutorial();
                buttons("tutorial-attack")[0]?.focus();
                break;
            case "tutorial-attack":
            case "tutorial-grow":
                tutorial.profit = button.dataset.action === "tutorial-attack" ? "attack" : "grow";
                renderTutorial();
                break;
            case "tutorial-finish": void finishTutorial(); break;
            case "play": newQueue(); break;
            case "play-bot":
                if (guideSeen) startBotMatch();
                else openBotGuide();
                break;
            case "queue-bot": startBotMatch({ fromQueue: true }); break;
            case "guide-start": openBotGuide(); break;
            case "guide-example-attack": chooseGuideExample("attack"); break;
            case "guide-example-grow": chooseGuideExample("grow"); break;
            case "guide-begin": startBotMatch({ guide: true }); break;
            case "guide-bypass": markGuideSeen(); startBotMatch(); break;
            case "guide-skip": finishGuide(); break;
            case "play-prediction": newQueue("prediction"); break;
            case "practice-prediction": startPractice(); break;
            case "practice-next": practiceAction("prediction_practice_next", { round: match.round.number }); break;
            case "practice-leave": practiceAction("prediction_practice_leave", {}); break;
            case "prediction-clear": setPredictionDraft(null); break;
            case "prediction-sign": togglePredictionSign(); break;
            case "friend-create": privateCreate(); break;
            case "friend-cancel": privateCancel(); break;
            case "friend-copy": void copyInvite(); break;
            case "friend-join": sendActivity("private_join", { code: inviteCode }, (error) => toast(error, "error")); break;
            case "spectate":
                if (screen === "menu" && !activityCommand) openSpectateList();
                break;
            case "spectate-menu": activate("menu"); break;
            case "spectate-watch": openSpectateMatch(button); break;
            case "spectate-back": openSpectateList(); break;
            case "spectate-list-retry": retrySpectating("spectate-title", subscribeSpectateList); break;
            case "spectate-live-retry": retrySpectating("spectate-mode", subscribeSpectateMatch); break;
            case "spectate-zoom-out": spectateChart.zoom(1 / chartZoomFactor); break;
            case "spectate-zoom-in": spectateChart.zoom(chartZoomFactor); break;
            case "play-again": {
                const mode = result?.mode ?? match?.mode;
                if (mode === "bot") startBotMatch();
                else if (mode === "prediction_practice") startPractice();
                else if (mode === "private") {
                    sendActivity("private_rematch", { matchId: result.id }, (error) => toast(error, "error"));
                }
                else newQueue(mode);
                break;
            }
            case "leave-queue": leaveQueue(); break;
            case "main-menu": leaveResult(); break;
            case "leagues":
            case "ranking":
            case "profile":
            case "help":
            case "settings": openDialog(button.dataset.action); break;
            case "close-dialog": button.closest("dialog")?.close(); break;
            case "logout": void logout(); break;
            case "chart-zoom-out": matchChart.zoom(1 / chartZoomFactor); break;
            case "chart-zoom-in": matchChart.zoom(chartZoomFactor); break;
            case "buy":
            case "short":
            case "sell": trade(button.dataset.action); break;
            case "attack": trade("confirm_sell", "attack"); break;
            case "grow": trade("confirm_sell", "grow"); break;
            case "confirm-close": trade("confirm_sell", "close"); break;
            case "keep-holding": keepHolding(); break;
        }
    }

    async function initialize() {
        document.addEventListener("click", onClick);
        window.addEventListener("stockfight:languagechange", refreshLanguage);
        document.addEventListener("visibilitychange", refreshOnlineCount);
        window.setInterval(refreshOnlineCount, 10_000);
        byId("auth-form")?.addEventListener("submit", submitAuth);
        byId("ranking-mode")?.addEventListener("change", refreshRanking);
        byId("profile-mode")?.addEventListener("change", () => void refreshProfile(true));
        byId("prediction-controls")?.addEventListener("submit", submitPrediction);
        const predictionInput = byId("prediction-move");
        predictionInput.addEventListener("input", predictionInputChanged);
        byId("prediction-sign").addEventListener("mousedown", (event) => {
            if (document.activeElement === predictionInput) event.preventDefault();
        });
        drawPredictionChart = window.createPredictionChart?.(
            byId("prediction-chart"), byId("prediction-draw-target"), setPredictionDraft,
        );
        drawSpectatePredictionChart = window.createPredictionChart?.(byId("spectate-prediction-chart"));
        const chartSetting = byId("setting-chart-type");
        if (chartSetting) {
            chartSetting.value = chartType;
            chartSetting.addEventListener("change", () => {
                chartType = chartSetting.value;
                savePreference("chartType", chartType);
            });
        }
        const soundSetting = byId("setting-sound");
        if (soundSetting) {
            soundSetting.checked = soundEnabled;
            soundSetting.addEventListener("change", () => {
                soundEnabled = soundSetting.checked;
                savePreference("sound", soundEnabled);
                enableAudio();
            });
        }
        const effectSetting = byId("setting-effects");
        if (effectSetting) {
            effectSetting.checked = effectsEnabled;
            effectSetting.addEventListener("change", () => {
                effectsEnabled = effectSetting.checked;
                savePreference("effects", effectsEnabled);
                applyEffects();
            });
        }
        reducedMotion.addEventListener("change", applyEffects);
        applyEffects();
        setAuthMode("login");
        show("auth-invite-note", Boolean(inviteCode));
        activate("auth");
        authBusy(true);
        try {
            applySession(await request("/api/me"));
        } catch (error) {
            message("auth-error", error.message, "error");
        } finally {
            authBusy(false);
        }
    }

    void initialize();
})();
