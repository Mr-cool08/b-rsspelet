(() => {
    "use strict";

    const { t } = window.StockFightI18n;
    const logLimit = 30;
    const errors = {
        chat_rate_limited: "Vänta lite innan du skickar nästa duellmeddelande.",
        chat_unavailable: "Duellchatten är stängd.",
    };

    function createDuelChat(acknowledgements) {
        const panel = document.getElementById("duel-chat");
        const matchSlot = document.getElementById("match-duel-chat-slot");
        const resultSlot = document.getElementById("result-duel-chat-slot");
        const log = document.getElementById("duel-chat-log");
        const empty = document.getElementById("duel-chat-empty");
        const status = document.getElementById("duel-chat-status");
        const presets = new Map([...panel.querySelectorAll("[data-chat-preset]")]
            .map((button) => [button.dataset.chatPreset, button]));
        const seen = new Set();

        let matchId;
        let userId;
        let socket;
        let connectionId;
        let request;
        let pendingSend;
        let unavailable;

        function setStatus(key) {
            if (status.dataset.i18n === key) return;
            if (key) status.dataset.i18n = key;
            else delete status.dataset.i18n;
            status.textContent = key ? t(key) : "";
            status.hidden = !key;
        }

        function renderButtons() {
            const disabled = !connectionId || unavailable;
            for (const button of presets.values()) {
                button.disabled = disabled;
                if (pendingSend) button.setAttribute("aria-disabled", "true");
                else button.removeAttribute("aria-disabled");
            }
        }

        function drawMessage(message, preset) {
            const row = document.createElement("div");
            row.className = "chat-message";
            row.dataset.messageId = String(message.id);
            const name = document.createElement("bdi");
            name.className = "chat-sender";
            name.textContent = message.name;
            if (message.userId === userId) {
                row.dataset.own = "true";
                name.dataset.i18n = "Du";
                name.textContent = t("Du");
            }
            const text = document.createElement("span");
            text.className = "chat-text";
            text.textContent = preset.textContent;
            if (preset.dataset.i18n) text.dataset.i18n = preset.dataset.i18n;
            if (preset.dataset.i18nAriaLabel) {
                text.setAttribute("role", "img");
                text.setAttribute("aria-label", preset.getAttribute("aria-label"));
                text.dataset.i18nAriaLabel = preset.dataset.i18nAriaLabel;
            }
            row.append(name, text);
            return row;
        }

        function appendMessages(messages) {
            const stickToEnd = log.scrollHeight - log.scrollTop - log.clientHeight <= 24;
            for (const message of messages) {
                const preset = presets.get(message?.preset);
                if (!preset || message.matchId !== matchId || !Number.isSafeInteger(message.id)
                    || seen.has(message.id) || typeof message.name !== "string") continue;
                if (log.childElementCount >= logLimit && message.id <= Number(log.firstElementChild.dataset.messageId)) continue;
                const next = [...log.children].find((row) => Number(row.dataset.messageId) > message.id);
                log.insertBefore(drawMessage(message, preset), next ?? null);
                seen.add(message.id);
                while (log.childElementCount > logLimit) {
                    seen.delete(Number(log.firstElementChild.dataset.messageId));
                    log.firstElementChild.remove();
                }
            }
            const hasMessages = log.childElementCount > 0;
            log.hidden = !hasMessages;
            empty.hidden = hasMessages;
            if (stickToEnd && hasMessages) log.scrollTop = log.scrollHeight;
        }

        function reportError(reply, fallback) {
            if (reply?.error === "chat_unavailable") {
                unavailable = true;
                renderButtons();
            }
            const key = Object.hasOwn(errors, reply?.error) ? errors[reply.error] : fallback;
            setStatus(key);
        }

        function loadHistory() {
            const current = {};
            request = current;
            socket.timeout(acknowledgements).emit("duel_chat_history", { matchId }, (error, reply) => {
                if (request !== current) return;
                if (!error && reply?.ok && Array.isArray(reply.messages)) appendMessages(reply.messages);
                else reportError(reply, "Duellchatten kunde inte laddas.");
            });
        }

        function send(preset) {
            if (!connectionId || !socket.connected || unavailable || pendingSend) return;
            const current = {};
            pendingSend = current;
            renderButtons();
            setStatus("");
            socket.timeout(acknowledgements).emit("duel_chat_send", { matchId, preset }, (error, reply) => {
                if (pendingSend !== current) return;
                pendingSend = undefined;
                renderButtons();
                if (error || !reply?.ok) reportError(reply, "Duellmeddelandet kunde inte skickas. Försök igen.");
            });
        }

        function reset() {
            matchId = undefined;
            socket = undefined;
            connectionId = undefined;
            request = undefined;
            pendingSend = undefined;
            unavailable = false;
            panel.hidden = true;
            log.replaceChildren();
            log.hidden = true;
            empty.hidden = false;
            seen.clear();
            setStatus("");
            renderButtons();
        }

        function sync({ id, player, connection, synchronized, atResult }) {
            if (matchId !== id) reset();
            if (!id) return;
            matchId = id;
            userId = player;
            const slot = atResult ? resultSlot : matchSlot;
            if (panel.parentElement !== slot) slot.append(panel);
            panel.hidden = false;

            const nextConnectionId = synchronized && connection?.connected ? connection.id : undefined;
            if (socket === connection && connectionId === nextConnectionId) return;
            socket = connection;
            connectionId = nextConnectionId;
            request = undefined;
            pendingSend = undefined;
            unavailable = false;
            renderButtons();
            setStatus(connectionId ? "" : "Ansluter till duellchatten …");
            if (connectionId) loadHistory();
        }

        for (const [preset, button] of presets) button.addEventListener("click", () => send(preset));
        return { sync, reset, receive: (message) => appendMessages([message]) };
    }

    window.createDuelChat = createDuelChat;
})();
