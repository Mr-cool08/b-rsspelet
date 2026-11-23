(() => {
    "use strict";

    const byId = (id) => document.getElementById(id);
    const buttons = (action) => document.querySelectorAll(`[data-action="${action}"]`);
    const positionDirection = (position) => position.side === "short" ? "Ner" : "Upp";
    const amountFormat = new Intl.NumberFormat("sv-SE", {
        minimumFractionDigits: 2,
        maximumFractionDigits: 2,
    });
    const integerFormat = new Intl.NumberFormat("sv-SE", { maximumFractionDigits: 0 });
    const dateFormat = new Intl.DateTimeFormat("sv-SE", { dateStyle: "short" });
    const marketDateFormat = new Intl.DateTimeFormat("sv-SE", { dateStyle: "short", timeZone: "UTC" });
    const marketTimeFormat = new Intl.DateTimeFormat("sv-SE", {
        hour: "2-digit", minute: "2-digit", second: "2-digit", timeZone: "UTC",
    });
    const reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)");
    const primaryTouch = window.matchMedia("(pointer: coarse)");
    const screenIds = ["auth", "menu", "queue", "invite", "match", "result"];
    const screenFocus = { auth: "auth-title", menu: "menu-name", queue: "queue-title",
        invite: "invite-title", match: "match-screen", result: "result-outcome" };
    const phaseLabels = { normal: "Handel", market: "Marknadsstorm", final: "Slutstorm" };
    const outcomeLabels = { win: "WIN", lose: "LOSE", loss: "LOSE", draw: "DRAW" };
    const acknowledgements = 5000;
    const chartRightPadding = 24;
    const chartZoomFactor = 1.5;
    const activityActions = ["play", "play-bot", "play-prediction", "practice-prediction", "guide-start",
        "guide-begin", "guide-bypass", "friend-create", "main-menu"];

    let soundEnabled = preference("sound", "false") === "true";
    let effectsEnabled = preference("effects", "true") === "true";
    let chartType = preference("chartType", "line") === "candlestick" ? "candlestick" : "line";
    let audio;
    let screen;
    let session = { user: null, csrfToken: "", inviteRequired: false };
    let sessionVersion = 0;
    let authMode = "login";
    let authPending = false;
    let profileVersion = 0;
    let menuProfileVersion = 0;
    let rankingVersion = 0;
    let toastTimer;
    let socket;
    let queueWanted = false;
    let queueMode = "ranked";
    let queueLeavePending = false;
    let queueReconnect = false;
    let queueCommand;
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
    let tradeFocus;
    let percent = 100;
    let lastEventId;
    let effectTimer;
    let chart;
    let priceSeries;
    let entryLine;
    let chartBars = [];
    let chartFailed = false;
    let drawPredictionChart;
    let predictionRound;
    let predictionCommand;
    let predictionSubmitFocus = false;

    function put(id, value) {
        const element = byId(id);
        const content = value == null ? "—" : String(value);
        if (element && element.textContent !== content) {
            element.textContent = content;
        }
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

    function period(start, end) {
        const dates = [start, end].map((value) => value ? new Date(value) : null);
        const valid = (value) => value && !Number.isNaN(value.getTime());
        const [first, last] = dates.map((value) => valid(value) ? marketDateFormat.format(value) : "—");
        if (dates.every(valid) && start.includes("T") && end.includes("T")) {
            const [firstTime, lastTime] = dates.map((value) => marketTimeFormat.format(value));
            if (first !== last) return `${first} ${firstTime} – ${last} ${lastTime} UTC`;
            return `${first} · ${firstTime}–${lastTime} UTC`;
        }
        return first === last ? first : `${first} – ${last}`;
    }

    function percentage(value) {
        return numeric(value) == null ? "—" : `${formatNumber(value)} %`;
    }

    function message(id, value, tone = "info") {
        put(id, value || "");
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
        for (const dialog of document.querySelectorAll("dialog[open]")) dialog.close();
        for (const id of screenIds) show(`${id}-screen`, id === name);
        screen = name;
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

    function setAuthMode(mode) {
        authMode = mode;
        const register = mode === "register";
        put("auth-title", register ? "Nytt spelarkonto" : "Spelarkonto");
        put("auth-submit", register ? "Skapa konto" : "Logga in");
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
        activate(inviteCode ? "invite" : "menu");
        renderPrivate();
        connect();
        void refreshProfile();
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
            if (!includeDialog) {
                put("menu-level", data.level ?? data.league);
                put("menu-elo", formatNumber(data.elo));
                progress("menu-progress", data.progress);
                put("menu-progress-label", percentage(data.progress));
                put("menu-next", data.nextLeague
                    ? `${data.nextLeague} · ${formatNumber(data.nextElo)} Elo` : "Högsta ligan");
                return;
            }
            put("profile-name", session.user.username);
            put("profile-league", data.league);
            put("profile-elo", formatNumber(data.elo));
            put("profile-matches", formatNumber(data.matches));
            put("profile-wins", formatNumber(data.wins));
            put("profile-losses", formatNumber(data.losses));
            put("profile-draws", formatNumber(data.draws));
            put("profile-win-rate", percentage(data.winRate));
            const rows = (data.history ?? []).map((item) => [
                item.opponent,
                outcomeLabels[item.outcome],
                item.symbol,
                `${formatNumber(item.eloBefore)} → ${formatNumber(item.eloAfter)}`,
                date(item.endedAt),
            ]);
            fillTable("profile-history", rows);
            message("profile-status", rows.length ? "" : "Inga avslutade matcher ännu.");
        } catch (error) {
            if (!ownsResponse()) return;
            if (includeDialog) message("profile-status", error.message, "error");
            if (!includeDialog && !byId("profile-dialog")?.open && screen === "menu") {
                toast(error.message, "error");
            }
        }
    }

    async function refreshRanking() {
        const version = sessionVersion;
        const requestVersion = ++rankingVersion;
        const ownsResponse = () => version === sessionVersion && requestVersion === rankingVersion;
        const mode = byId("ranking-mode").value;
        fillTable("ranking-list", []);
        message("ranking-status", "Hämtar ranking …");
        try {
            const data = await request(mode === "prediction" ? "/api/leaderboard?mode=prediction" : "/api/leaderboard");
            if (!ownsResponse()) return;
            const rows = (data.players ?? []).map((player, index) => [
                index + 1,
                player.username,
                formatNumber(player.elo),
                player.league,
                formatNumber(player.wins),
                formatNumber(player.matches),
            ]);
            fillTable("ranking-list", rows);
            message("ranking-status", rows.length ? "" : "Rankingen är tom.");
        } catch (error) {
            if (ownsResponse()) message("ranking-status", error.message, "error");
        }
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
        put("connection-status", detail || labels[status]);
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
            connection("online");
            renderTradeControls();
            renderPrediction();
            renderPrivate();
            if (queueLeavePending && !match) sendQueueCommand(false);
            else if (queueWanted && screen === "queue" && !match) sendQueueCommand(true);
            queueReconnect = false;
        });
        socket.on("disconnect", (reason) => {
            queueReconnect = queueWanted;
            queueCommand = undefined;
            setActivityCommand(undefined);
            disable("leave-queue", false);
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
            if (reason === "io server disconnect") {
                connection("offline", "Spelanslutningen avslutades. Uppdatera sidan för att försöka igen.");
            }
        });
        socket.on("connect_error", (error) => {
            connection("offline", socket.active ? undefined : error.message || "Spelanslutningen nekades");
            renderTradeControls();
            renderPrediction();
            renderPrivate();
        });
        socket.on("queue_state", receiveQueueState);
        socket.on("match_state", receiveMatchState);
        socket.on("match_result", receiveResult);
        socket.on("private_state", receivePrivateState);
        socket.on("prediction_practice_ended", receivePracticeEnded);
        socket.connect();
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
        queueLeavePending = false;
        queueReconnect = !socket.connected;
        put("queue-wait", clock(0));
        put("queue-radius", "—");
        put("queue-title", mode === "prediction" ? "Söker en ritduell" : "Söker motståndare");
        disable("leave-queue", false);
        activate("queue");
        if (socket.connected) sendQueueCommand(true);
    }

    function setActivityCommand(command) {
        activityCommand = command;
        for (const action of activityActions) disable(action, Boolean(command));
        put("bot-start-label", command?.event === "bot_start" ? "Startar …" : "Spela mot bot");
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

    function startBotMatch(forceGuide = false) {
        if (!session.user || queueWanted || activityCommand) return;
        guideRequested = forceGuide;
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
        put("invite-cancel", hosting || inviteCode ? "Avbryt" : "Till huvudmenyn");
        let status = "Inbjudan är inte längre aktiv.";
        if (activityCommand?.event === "private_create") status = "Skapar inbjudan …";
        else if (hosting) status = "Dela länken och vänta på att din vän går med.";
        else if (inviteCode) status = "Du har fått en inbjudan till en orankad handelsduell.";
        put("invite-status", status);
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
        queueWanted = false;
        queueLeavePending = true;
        queueReconnect = false;
        if (!socket?.connected) {
            activate("menu");
            return;
        }
        sendQueueCommand(false);
    }

    function sendQueueCommand(join) {
        if (!socket?.connected || (queueCommand && queueCommand.join === join)) return;
        const command = { join };
        queueCommand = command;
        disable("leave-queue", !join);
        const payload = join && queueMode === "prediction" ? { mode: queueMode } : {};
        socket.timeout(acknowledgements).emit(join ? "queue_join" : "queue_leave", payload, (error, ack) => {
            if (queueCommand !== command) return;
            queueCommand = undefined;
            disable("leave-queue", false);
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
                toast(ack?.error || "Kön svarade inte. Försök igen.", "error");
                return;
            }
            if (!join) {
                queueLeavePending = false;
                if (screen === "queue") activate("menu");
            }
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
            put("queue-wait", clock(data.waited));
            put("queue-radius", numeric(data.radius) == null ? "—" : `±${formatNumber(data.radius)}`);
            put("queue-title", queueMode === "prediction" ? "Söker en ritduell" : "Söker motståndare");
            activate("queue");
            return;
        }
        // Socket.IO flushes the server's initial snapshot before firing "connect".
        if (queueWanted && (queueCommand?.join || queueReconnect) && !data.error) return;
        queueCommand = undefined;
        queueWanted = false;
        queueLeavePending = false;
        queueReconnect = false;
        disable("leave-queue", false);
        if (screen === "queue") activate("menu");
        if (data.error) toast(data.error, "error");
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
        const outcomes = {
            attack: "Attack gör upp till 20 HP skada och förbrukar vinsten.",
            grow: "Grow ger 10 krediter, höjer attackkraften till 102 % och laddar nästa attack med 25 bonus-HP.",
        };
        put("guide-example-result", outcomes[choice] ?? "");
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
        const position = match?.self?.position;
        let step = "Välj en insats och tryck UPP eller NER beroende på vart du tror kursen går.";
        if (position) step = "Följ affärens resultat och tryck Stäng position när du vill avsluta.";
        if (sellChoice?.kind === "profit") step = "Attack använder vinsten till skada. Grow sparar vinsten, bygger attackkraft och laddar nästa attack.";
        if (sellChoice?.kind === "flat" || sellChoice?.kind === "loss") {
            step = "Kursen har ändrats. Stäng positionen vid den nya kursen.";
        }
        put("bot-guide-step", step);
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
        tradeFocus = undefined;
        guideActive = false;
        lastEventId = undefined;
        clearEffect();
        message("match-feedback", "");
        resetPrediction();
        setPercent(100);
        chart?.remove();
        chart = undefined;
        priceSeries = undefined;
        entryLine = undefined;
        chartBars = [];
        chartFailed = false;
        show("chart-controls", false);
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

    function animateEvent(event) {
        if (!event || event.id === lastEventId) return;
        lastEventId = event.id;
        clearEffect();
        const same = (left, right) => left != null && right != null && String(left) === String(right);
        const acting = same(event.actorId, match.self?.id);
        const defending = same(event.targetId, match.self?.id);
        const actor = acting ? "Du" : match.opponent?.name ?? "Motståndaren";
        const target = defending ? "Du" : match.opponent?.name ?? "Motståndaren";
        const damage = numeric(event.damage);
        const messages = {
            attack: `${actor} · ATTACK${damage == null ? "" : ` · −${formatNumber(damage)} HP`}`,
            grow: `${actor} · GROW`,
            loss: `${actor} · Förlustaffär${damage > 0 ? ` · −${formatNumber(damage)} HP` : ""}`,
            ko: event.targetId == null ? "Storm · KO" : `${target} · KO`,
        };
        if (!Object.hasOwn(messages, event.type)) return;
        put("match-event", messages[event.type]);
        stateAttribute("match-event", "event", event.type);
        show("match-event", true);
        playSound(event.type);
        const stage = byId("match-screen");
        if (stage && effectsEnabled && !reducedMotion.matches) {
            // Restart the animation when two consecutive events have the same type.
            void stage.offsetWidth;
            const effect = { attack: "is-hit", loss: "is-hit", grow: "is-grow", ko: "is-ko" }[event.type];
            const ownSide = event.type === "grow" || event.type === "loss" ? acting : defending;
            stage.classList.add(effect);
            if (event.targetId == null) stage.classList.add("hit-self", "hit-opponent");
            else stage.classList.add(ownSide ? "hit-self" : "hit-opponent");
        }
        effectTimer = window.setTimeout(clearEffect, 1400);
    }

    function createChart() {
        const library = window.LightweightCharts;
        const container = byId("match-chart");
        if (!library || !container) throw new Error("Chart unavailable");
        const theme = getComputedStyle(container);
        const color = (key, fallback) => theme.getPropertyValue(key).trim() || fallback;
        const price = color("--chart-price", "#b9f467");
        const line = color("--chart-line", "#29334b");
        const label = color("--chart-label", "#91a0bb");
        chart = library.createChart(container, {
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
            localization: {
                priceFormatter: (price) => formatNumber(price, amountFormat),
                timeFormatter: (time) => `Kurspunkt ${time}`,
            },
            handleScale: { mouseWheel: false, pinch: true },
            handleScroll: { mouseWheel: false, horzTouchDrag: false, vertTouchDrag: false },
            trackingMode: { exitMode: library.TrackingModeExitMode.OnTouchEnd },
        });
        if (chartType === "candlestick") {
            const down = color("--chart-price-down", "#ff858a");
            priceSeries = chart.addSeries(library.CandlestickSeries, {
                upColor: price,
                downColor: down,
                borderVisible: false,
                wickUpColor: price,
                wickDownColor: down,
                priceLineColor: label,
            });
            container.setAttribute("aria-label", "Kursgraf med ljusstaplar");
        } else {
            priceSeries = chart.addSeries(library.LineSeries, {
                color: price,
                lineWidth: 2,
                priceLineColor: label,
            });
            container.setAttribute("aria-label", "Linjegraf över aktiekursen");
        }
    }

    function zoomChart(factor) {
        if (!chartBars.length || chartFailed) return;
        const timeScale = chart.timeScale();
        const width = timeScale.width();
        if (!width) return;
        const { barSpacing, minBarSpacing } = timeScale.options();
        const spacing = Math.max(minBarSpacing, Math.min(width / 2, barSpacing * factor));
        timeScale.applyOptions({ barSpacing: spacing, rightOffsetPixels: chartRightPadding });
    }

    function updateChart(bars, position) {
        if (chartFailed) return;
        if (!bars?.length) {
            message("match-chart-status", "Väntar på kursgraf …");
            return;
        }
        try {
            if (!chart) createChart();
            const toPoint = priceSeries.seriesType() === "Candlestick"
                ? ({ time, open, high, low, close }) => ({
                    time: Number(time), open: Number(open), high: Number(high), low: Number(low), close: Number(close),
                })
                : ({ time, close }) => ({ time: Number(time), value: Number(close) });
            const sameBar = (left, right) => left.time === right.time && left.open === right.open
                && left.high === right.high && left.low === right.low && left.close === right.close;
            const last = chartBars.length - 1;
            const append = last >= 0 && chartBars.length <= bars.length
                && chartBars[last].time === bars[last].time
                && chartBars.slice(0, last).every((bar, index) => sameBar(bar, bars[index]));
            if (append) {
                if (!sameBar(chartBars[last], bars[last])) priceSeries.update(toPoint(bars[last]));
                for (const bar of bars.slice(last + 1)) priceSeries.update(toPoint(bar));
            } else {
                priceSeries.setData(bars.map(toPoint));
                if (!chartBars.length) {
                    chart.timeScale().fitContent();
                    show("chart-controls", true);
                }
            }
            chartBars = bars;

            const entry = numeric(position?.entryPrice);
            if (entry != null && entryLine) {
                entryLine.applyOptions({ price: entry, title: positionDirection(position) });
            } else if (entry != null) {
                entryLine = priceSeries.createPriceLine({
                    price: entry,
                    color: "#c4acff",
                    lineWidth: 1,
                    lineStyle: window.LightweightCharts.LineStyle.Dashed,
                    axisLabelVisible: true,
                    title: positionDirection(position),
                });
            } else if (entryLine) {
                priceSeries.removePriceLine(entryLine);
                entryLine = undefined;
            }
            message("match-chart-status", "");
        } catch {
            chartFailed = true;
            show("chart-controls", false);
            message("match-chart-status", "Kursgrafen kunde inte visas.", "error");
        }
    }

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
        const decimal = fraction ? `,${String(fraction).padStart(2, "0").replace(/0$/, "")}` : "";
        return `${bps < 0 ? "-" : ""}${whole}${decimal}`;
    }

    function formatPrediction(bps) {
        if (bps == null) return "Inget svar";
        return `${signed(bps / 100, amountFormat)} %`;
    }

    function predictionVerdict(outcome, selfId, opponentName) {
        if (outcome.winnerId == null) {
            if (outcome.selfMoveBps == null && outcome.opponentMoveBps == null) {
                return { side: "draw", title: "Inga prognoser", reason: "Tiden gick ut för båda spelarna. Ingen tog skada." };
            }
            return { side: "draw", title: "Oavgjord runda", reason: "Ni kom lika nära facit. Ingen tog skada." };
        }

        const won = String(outcome.winnerId) === String(selfId);
        const winner = won ? "Du" : opponentName;
        const side = won ? "self" : "opponent";
        const title = `${winner} vann rundan`;
        const otherError = won ? outcome.opponentErrorBps : outcome.selfErrorBps;
        if (otherError == null) {
            return { side, title, reason: `${winner} var ensam om att låsa en prognos.` };
        }
        const winnerError = won ? outcome.selfErrorBps : outcome.opponentErrorBps;
        const margin = formatNumber((otherError - winnerError) / 100, amountFormat);
        return { side, title, reason: `${winner} kom ${margin} procentenheter närmare facit.` };
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
            put("practice-next", round?.number === match.roundLimit ? "Se sammanfattning" : "Nästa runda");
        }

        const opponentName = match.opponent?.name || "Motståndaren";
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
                if (bps != null) put(id, `${formatNumber(bps / 100, amountFormat)} procentenheter fel`);
            }
            put("prediction-status", verdict?.title ?? "Facit för rundan");
            if (verdict) {
                const damage = outcome.damage ? ` ${verdict.side === "self" ? opponentName : "Du"} förlorade ${formatNumber(outcome.damage)} HP.` : "";
                put("prediction-reason", verdict.reason + damage);
            }
        } else if (match.status === "countdown") {
            put("prediction-status", "Gör dig redo att gissa nästa kursrörelse.");
        } else if (round?.selfLocked) {
            put("prediction-status", "Prognosen är låst. Väntar på facit.");
        } else if (predictionCommand) {
            put("prediction-status", "Låser prognosen …");
        } else if (!socket?.connected || !matchSynchronized) {
            put("prediction-status", "Väntar på anslutning …");
        } else {
            put("prediction-status", round?.opponentLocked ? "Motståndaren har låst sin prognos." : "Hur rör sig kursen härnäst?");
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
        match = data;
        matchSynchronized = true;
        if (numeric(data.nextSeq) != null) nextSeq = Math.max(nextSeq ?? 0, Number(data.nextSeq));
        sellChoice = data.self?.position?.closePreview ?? undefined;
        if (data.mode === "private") forgetInviteCode();
        activate("match");
        stateAttribute("match-screen", "mode", data.mode ?? "ranked");
        stateAttribute("match-screen", "phase", data.status);
        stateAttribute("match-screen", "storm", data.storm ?? "normal");
        const prediction = isPrediction(data.mode);
        const practice = data.mode === "prediction_practice";
        const counting = data.status === "countdown";
        const finished = data.status === "finished";
        const phase = prediction ? (data.round?.phase === "reveal" ? "Facit" : "Prognos")
            : phaseLabels[data.storm] ?? "Handel";
        put("match-phase", counting ? "Startar" : finished ? "Avslutad" : phase);
        const remaining = prediction ? data.remaining : data.elapsed;
        put("match-time", clock(counting ? data.countdown : remaining));
        const stormTime = clock(data.remaining);
        const stormClock = data.storm === "final" ? `KO om ${stormTime}`
            : data.storm === "market" ? `Slutstorm om ${stormTime}` : `Storm om ${stormTime}`;
        const roundLabel = `Runda ${data.round?.number} av ${data.roundLimit ?? 8}`;
        put("match-clock-detail", prediction ? roundLabel : stormClock);
        put("practice-round", roundLabel);
        show("match-hud", !practice);
        show("practice-header", practice);
        show("match-clock-detail", !counting && !finished);
        put("countdown-number", Math.max(1, Math.ceil(numeric(data.countdown) ?? 3)));
        show("countdown-overlay", counting);
        put("match-symbol", data.symbol);
        put("match-name", data.name);
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
            syncPredictionRound();
            animateEvent(data.event);
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
        put("match-direction", position ? positionDirection(position) : null);
        put("match-entry", formatNumber(position?.entryPrice, amountFormat));
        put("match-pnl", signed(position?.pnl, amountFormat));
        stateAttribute("match-pnl", "sign", sign(numeric(position?.pnl)));
        updateChart(data.bars, position);
        renderTradeControls();
        animateEvent(data.event);
    }

    function setPercent(value) {
        if (![25, 50, 75, 100].includes(value)) return;
        percent = value;
        for (const button of document.querySelectorAll("[data-percent]")) {
            button.setAttribute("aria-pressed", String(Number(button.dataset.percent) === value));
        }
        renderStake();
    }

    function renderStake() {
        const cash = numeric(match?.self?.cash);
        put("stake-amount", cash == null ? "—" : formatNumber(cash * percent / 100, amountFormat));
    }

    function tradeReady() {
        return Boolean(socket?.connected && matchSynchronized && match?.status === "active" && !tradeCommand
            && !result && nextSeq != null && (sellChoice || Number(match.nextSeq) >= nextSeq));
    }

    function renderTradeControls() {
        const ready = tradeReady();
        const position = match?.self?.position;
        const choosing = ready && Boolean(sellChoice);
        const profitable = sellChoice?.kind === "profit";
        const canOpen = ready && !position && numeric(match?.self?.cash) > 0;
        const focusedAction = tradeFocus ?? document.activeElement?.dataset.action;
        if (choosing && profitable && focusedAction === "confirm-close") tradeFocus = "attack";
        if (choosing && !profitable && ["attack", "grow"].includes(focusedAction)) tradeFocus = "confirm-close";
        disable("buy", !canOpen);
        disable("short", !canOpen);
        disable("sell", !ready || !position || Boolean(sellChoice));
        disable("attack", !choosing || !profitable);
        disable("grow", !choosing || !profitable);
        disable("confirm-close", !choosing || profitable);
        show("open-order", !position);
        show("close-order", Boolean(position) && !sellChoice);
        show("sell-choice", Boolean(sellChoice));
        show("profit-actions", profitable);
        show("pending-close", Boolean(sellChoice) && !profitable);
        renderStake();
        if (sellChoice) {
            let hint = "Uppskattning vid aktuell kurs. Kursen kan ändras före avslut.";
            if (profitable) {
                put("attack-preview", `${formatNumber(sellChoice.attackDamage)} HP skada`);
                put("grow-preview", `${signed(sellChoice.growCredits, amountFormat)} krediter · ${formatNumber(sellChoice.growBonus)} bonus-HP`);
            } else if (sellChoice.kind === "loss") {
                hint = `Vid aktuell kurs förlorar du ${formatNumber(sellChoice.lossCredits, amountFormat)} krediter och ${formatNumber(sellChoice.lossDamage)} HP.`;
            } else {
                hint = "Vid aktuell kurs stänger du positionen utan vinst eller förlust.";
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
        if (action === "confirm_sell" && !sellChoice) return;
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
            put("result-rematch", activityCommand ? "Startar …" : mode === "ranked" ? "PLAY AGAIN" : "Spela igen");
            disable("play-again", Boolean(activityCommand));
            message("result-revenge-status", "");
            return;
        }
        const offer = rematchOffer?.matchId === result.id ? rematchOffer : null;
        put("result-rematch", "Revansch mot samma spelare");
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
            case "attack": return self ? "Din attack avgjorde matchen." : opponent ? "Motståndarens attack avgjorde matchen." : "Matchen avgjordes av en attack.";
            case "trade_loss": return self ? "Din förlustaffär avslutade matchen." : "Motståndarens förlustaffär avslutade matchen.";
            case "market_storm":
            case "final_storm": {
                const storm = data.endReason === "market_storm" ? "marknadsstormen" : "slutstormen";
                if (numeric(data.hp) === 0 && numeric(data.opponentHp) === 0) {
                    const tiebreak = {
                        capital: "Högst slutkapital avgjorde.",
                        attack_damage: "Kapitalet var lika, så mest attackskada avgjorde.",
                    }[data.tiebreak] ?? "Ni hade lika mycket kapital och gjorde lika mycket attackskada.";
                    return `Båda slogs ut i ${storm}. ${tiebreak}`;
                }
                return `Matchen avgjordes i ${storm}.`;
            }
            case "knockout": return "Matchen avgjordes genom knockout.";
            case "round_limit": return "Matchen avgjordes av slut-HP efter sista rundan.";
            default: return "";
        }
    }

    function predictionMatchExplanation(data, opponentName) {
        if (data.endReason === "knockout") {
            const knockout = data.outcome === "win" ? `Du sänkte ${opponentName} till 0 HP.` : `${opponentName} sänkte dig till 0 HP.`;
            const round = data.lastRound ?? data.rounds?.at(-1);
            return round ? `${knockout} ${predictionVerdict(round, session.user.id, opponentName).reason}` : knockout;
        }
        if (data.endReason === "round_limit") {
            if (data.outcome === "draw") return "Ni hade lika mycket HP kvar efter sista rundan.";
            const winner = data.outcome === "win" ? "Du" : opponentName;
            return `${winner} hade mest HP kvar efter sista rundan.`;
        }
        return matchExplanation(data);
    }

    function renderResultDetails(data, mode) {
        const practice = mode === "prediction_practice";
        const prediction = mode === "prediction";
        const opponentName = data.opponentName || match?.opponent?.name || "Motståndaren";
        const explanation = prediction ? predictionMatchExplanation(data, opponentName) : matchExplanation(data);
        const comparison = numeric(data.opponentHp) != null;
        show("result-explanation", comparison || Boolean(explanation));
        show("result-comparison", comparison);
        show("result-decisive", Boolean(explanation));
        put("result-decisive", explanation);
        put("result-self-hp", formatNumber(data.hp));
        put("result-opponent-hp", formatNumber(data.opponentHp));
        put("result-opponent-label", prediction ? `${opponentName} · slut-HP` : "Motståndarens slut-HP");
        show("result-trade-hp-stat", !comparison);
        show("result-prediction-hp-stat", !practice && !comparison);

        const tradeLabels = { attack: "Attack", grow: "Grow", loss: "Förlust", flat: "Ingen vinst eller förlust" };
        const trades = (data.tradeDetails ?? []).map((trade) => [
            clock(trade.time), positionDirection(trade), tradeLabels[trade.choice],
            `${signed(trade.profit, amountFormat)} krediter`, `${formatNumber(trade.damage)} HP`,
        ]);
        byId("result-trade-detail").open = false;
        show("result-trade-detail", trades.length > 0);
        fillTable("result-trade-list", trades);

        const forecast = (value) => value == null ? "Ingen prognos" : formatPrediction(value);
        const error = (value) => value == null ? "—" : `${formatNumber(value / 100, amountFormat)} procentenheter`;
        const rounds = (data.rounds ?? []).map((round) => {
            const values = [formatPrediction(round.actualMoveBps), forecast(round.selfMoveBps), error(round.selfErrorBps)];
            if (practice) return [round.number, ...values];
            const verdict = predictionVerdict(round, session.user.id, opponentName);
            const impact = round.damage ? ` · ${formatNumber(round.damage)} HP i skada` : "";
            return [round.number, verdict.title + impact, ...values, forecast(round.opponentMoveBps), error(round.opponentErrorBps)];
        });
        byId("result-round-detail").open = rounds.length > 0;
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
        const practice = mode === "prediction_practice";
        const prediction = isPrediction(mode);
        const rated = mode === "ranked" || mode === "prediction";
        stateAttribute("result-screen", "mode", mode);
        stateAttribute("result-screen", "outcome", data.outcome);
        const labels = { prediction: "Ritduell", prediction_practice: "Ritduell · Övning",
            bot: "Botduell · Orankad", private: "Vänduell · Orankad" };
        const label = labels[mode] ?? "Matchresultat";
        put("result-mode", label);
        const predictionOutcomes = { win: "Du vann", lose: "Du förlorade", draw: "Oavgjort" };
        const outcomes = prediction ? predictionOutcomes : outcomeLabels;
        put("result-outcome", practice ? "Övning klar" : outcomes[data.outcome] ?? "MATCH SLUT");
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
        const instrument = [data.symbol, data.name, data.market, data.interval].filter(Boolean);
        if (data.synthetic) instrument.push("Syntetisk");
        put("result-symbol", instrument.join(" · "));
        put("result-period", period(data.periodStart, data.periodEnd));
        renderResultDetails(data, mode);
        renderPlayAgain();
        activate("result");
        if (!practice) playSound(data.outcome);
        if (mode === "ranked") void refreshProfile();
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
            case "play": newQueue(); break;
            case "play-bot":
                if (guideSeen) startBotMatch();
                else openBotGuide();
                break;
            case "guide-start": openBotGuide(); break;
            case "guide-example-attack": chooseGuideExample("attack"); break;
            case "guide-example-grow": chooseGuideExample("grow"); break;
            case "guide-begin": startBotMatch(true); break;
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
            case "ranking":
            case "profile":
            case "help":
            case "settings": openDialog(button.dataset.action); break;
            case "close-dialog": button.closest("dialog")?.close(); break;
            case "logout": void logout(); break;
            case "chart-zoom-out": zoomChart(1 / chartZoomFactor); break;
            case "chart-zoom-in": zoomChart(chartZoomFactor); break;
            case "buy":
            case "short":
            case "sell": trade(button.dataset.action); break;
            case "attack": trade("confirm_sell", "attack"); break;
            case "grow": trade("confirm_sell", "grow"); break;
            case "confirm-close": trade("confirm_sell", "close"); break;
        }
    }

    async function initialize() {
        document.addEventListener("click", onClick);
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
