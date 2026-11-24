(() => {
    "use strict";

    const panels = Array.from(document.querySelectorAll("[data-public-chat]"), (section) => ({
        log: section.querySelector("[role=log]"),
        empty: section.querySelector("[data-chat-empty]"),
        rows: section.querySelector("[data-chat-messages]"),
        form: section.querySelector("form"),
        input: section.querySelector("input"),
        send: section.querySelector("[type=submit]"),
        status: section.querySelector("[role=status]"),
        retry: section.querySelector("[data-chat-retry]"),
        follow: true,
    }));
    if (!panels.length) return;

    const maxLength = 240;
    const maxMessages = 50;
    const requestTimeout = 5000;
    const connecting = "Ansluter till chatten …";
    const disconnected = "Anslutningen till chatten bröts. Försöker igen …";
    const unavailable = "Chatten kunde inte ansluta. Ladda om sidan.";
    const failedHistory = "Det gick inte att hämta chatten.";
    const failedSend = "Meddelandet kunde inte skickas.";
    const errors = new Map([
        ["chat_invalid", "Skriv ett meddelande på högst 240 tecken."],
        ["chat_links", "Länkar är inte tillåtna i chatten."],
        ["chat_rate_limited", "Du skickar meddelanden för snabbt. Vänta en stund."],
    ]);
    const t = (text) => window.StockFightI18n?.t(text) ?? text;
    const validMessage = (item) => Number.isSafeInteger(item?.id) &&
        typeof item.name === "string" && typeof item.text === "string";

    let socket;
    let ownedToken;
    let messages = [];
    let loaded = false;
    let pendingHistory;
    let status = window.io ? connecting : unavailable;

    function paint(panel) {
        const message = t(status || panel.error || "");
        if (panel.status.textContent !== message) panel.status.textContent = message;
        panel.empty.hidden = !loaded || messages.length !== 0;
        panel.send.disabled = Boolean(status || panel.sending || !panel.input.value.trim());
        panel.retry.hidden = status !== failedHistory;
    }

    function followLatest(panel) {
        if (panel.follow) panel.log.scrollTop = panel.log.scrollHeight;
    }

    function messageNode(item) {
        const row = document.createElement("p");
        row.className = "game-chat-message";
        const author = document.createElement("bdi");
        author.className = "game-chat-author";
        author.textContent = item.name;
        const body = document.createElement("span");
        body.className = "game-chat-text";
        body.dir = "auto";
        body.textContent = item.text;
        row.append(author, " ", body);
        return row;
    }

    function receive(item) {
        if (!validMessage(item)) return;
        pendingHistory?.push(item);
        const firstNewer = messages.findIndex(({ id }) => id >= item.id);
        if (messages[firstNewer]?.id === item.id || (firstNewer === 0 && messages.length === maxMessages)) return;
        const index = firstNewer < 0 ? messages.length : firstNewer;
        messages.splice(index, 0, item);
        const overflow = messages.length > maxMessages;
        if (overflow) messages.shift();
        for (const panel of panels) {
            panel.rows.insertBefore(messageNode(item), panel.rows.children[index] ?? null);
            if (overflow) panel.rows.firstElementChild.remove();
            followLatest(panel);
            paint(panel);
        }
    }

    function loadHistory() {
        if (!socket?.connected || pendingHistory) return;
        status = connecting;
        const recent = [];
        pendingHistory = recent;
        panels.forEach(paint);
        socket.timeout(requestTimeout).emit("company_chat_history", {}, (error, response) => {
            if (pendingHistory !== recent) return;
            pendingHistory = undefined;
            if (error || !response?.ok || !Array.isArray(response.messages)) {
                status = failedHistory;
                panels.forEach(paint);
                return;
            }
            const byId = new Map([...response.messages, ...recent].filter(validMessage).map((item) => [item.id, item]));
            messages = [...byId.values()].sort((a, b) => a.id - b.id).slice(-maxMessages);
            loaded = true;
            status = "";
            for (const panel of panels) {
                panel.rows.replaceChildren(...messages.map(messageNode));
                followLatest(panel);
                paint(panel);
            }
        });
    }

    function connectionLost() {
        pendingHistory = undefined;
        status = socket.active ? disconnected : unavailable;
        panels.forEach(paint);
    }

    function disconnect() {
        if (!socket) return;
        socket.off("connect", loadHistory);
        socket.off("disconnect", connectionLost);
        socket.off("connect_error", connectionLost);
        socket.off("company_chat_message", receive);
        if (ownedToken) socket.disconnect();
        socket = undefined;
        ownedToken = undefined;
        messages = [];
        pendingHistory = undefined;
        loaded = false;
        status = connecting;
        for (const panel of panels) {
            panel.rows.replaceChildren();
            panel.input.value = "";
            panel.error = "";
            panel.sending = undefined;
            panel.follow = true;
            paint(panel);
        }
    }

    function attach(connection) {
        if (socket === connection) return;
        disconnect();
        socket = connection;
        socket.on("connect", loadHistory);
        socket.on("disconnect", connectionLost);
        socket.on("connect_error", connectionLost);
        socket.on("company_chat_message", receive);
        if (socket.connected) loadHistory();
    }

    function connect(csrfToken) {
        if (!csrfToken || ownedToken === csrfToken) return;
        if (!window.io) {
            status = unavailable;
            panels.forEach(paint);
            return;
        }
        attach(window.io("/company", { auth: { csrfToken }, autoConnect: false }));
        ownedToken = csrfToken;
        socket.connect();
    }

    function send(panel) {
        if (!socket?.connected || status || panel.sending) return;
        const draft = panel.input.value;
        const text = draft.trim();
        if (!text || Array.from(text).length > maxLength) {
            panel.error = errors.get("chat_invalid");
            paint(panel);
            return;
        }
        if (document.activeElement === panel.send) panel.input.focus();
        const attempt = {};
        panel.sending = attempt;
        panel.error = "";
        paint(panel);
        socket.timeout(requestTimeout).emit("company_chat_send", { text }, (error, response) => {
            if (panel.sending !== attempt) return;
            panel.sending = undefined;
            if (!error && response?.ok) {
                if (panel.input.value === draft) panel.input.value = "";
            } else {
                panel.error = errors.get(response?.error) || failedSend;
            }
            paint(panel);
        });
    }

    for (const panel of panels) {
        panel.log.addEventListener("scroll", () => {
            if (panel.log.clientHeight) {
                panel.follow = panel.log.scrollHeight - panel.log.clientHeight - panel.log.scrollTop <= 8;
            }
        });
        if (window.ResizeObserver) new ResizeObserver(() => followLatest(panel)).observe(panel.log);
        panel.input.addEventListener("input", () => {
            panel.error = "";
            paint(panel);
        });
        panel.form.addEventListener("submit", (event) => {
            event.preventDefault();
            send(panel);
        });
        panel.retry.addEventListener("click", () => {
            panel.input.focus();
            loadHistory();
        });
        paint(panel);
    }
    window.addEventListener("stockfight:languagechange", () => panels.forEach(paint));
    window.StockFightPublicChat = { attach, connect, disconnect };
})();
