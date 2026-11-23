(() => {
    "use strict";

    const section = document.getElementById("company-standings");
    if (!section) return;
    section.setAttribute("aria-labelledby", "company-standings-title");

    const copy = {
        title: ["Börslistan", "Market leaderboard"],
        description: ["Avslutade veckor avgör placeringen, följt av kassa och innehavens anskaffningsvärde.",
            "Rankings start with weeks completed, then cash plus the cost of current holdings."],
        loading: ["Hämtar handelsfirmor …", "Loading trading firms …"],
        empty: ["Din firma visas här när du har avslutat din första handelsvecka.",
            "Your firm appears here once you have completed your first trading week."],
        error: ["Börslistan kunde inte uppdateras just nu.", "The market leaderboard could not be updated."],
        rank: ["Plats", "Rank"],
        name: ["Firma", "Firm"],
        weeks: ["Veckor", "Weeks"],
        equity: ["Firmavärde", "Firm value"],
        you: ["Din firma", "Your firm"],
        planning: ["Pågående", "In progress"],
        failed: ["Kapitlet missat", "Chapter missed"],
        won: ["Kampanj klar", "Campaign complete"],
    };
    const locale = () => window.StockFightI18n?.getLocale() ?? "sv-SE";
    const text = (key) => copy[key][locale() === "en-GB" ? 1 : 0];
    const escape = (value) => String(value).replace(/[&<>"']/g, (character) => ({
        "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
    })[character]);

    let companies = null;
    let failed = false;
    let fetching = false;

    function render() {
        const format = new Intl.NumberFormat(locale());
        const table = companies?.length ? `<table class="company-standings-table">
            <thead><tr><th scope="col">${text("rank")}</th><th scope="col">${text("name")}</th>
            <th scope="col">${text("weeks")}</th><th scope="col">${text("equity")}</th></tr></thead>
            <tbody>${companies.map((firm) => `<tr${firm.isYou ? ' class="company-standing-own"' : ""}>
                <td>${format.format(firm.rank)}</td>
                <th scope="row"><span>${escape(firm.name)}</span>
                    <small>${firm.isYou ? `${text("you")} · ` : ""}${text(firm.status)}</small></th>
                <td>${format.format(firm.week)}</td><td>${format.format(firm.equity)}</td>
            </tr>`).join("")}</tbody>
        </table>` : `<p class="company-standings-message">${text(failed ? "error" : companies ? "empty" : "loading")}</p>`;

        section.innerHTML = `<header class="company-standings-heading">
            <h2 id="company-standings-title">${text("title")}</h2><p>${text("description")}</p>
        </header>${table}${failed && companies?.length ? `<p class="company-standings-message">${text("error")}</p>` : ""}`;
    }

    async function refresh() {
        if (fetching) return;
        fetching = true;
        try {
            const response = await fetch("/api/company/standings");
            if (!response.ok) throw new Error("standings");
            const updated = (await response.json()).companies;
            const changed = failed || JSON.stringify(companies) !== JSON.stringify(updated);
            companies = updated;
            failed = false;
            if (changed) render();
        } catch {
            if (!failed) {
                failed = true;
                render();
            }
        } finally {
            fetching = false;
        }
    }

    window.addEventListener("stockfight:languagechange", render);
    window.addEventListener("company:updated", refresh);
    function refreshWhileVisible() {
        if (document.visibilityState === "visible") refresh();
    }
    document.addEventListener("visibilitychange", refreshWhileVisible);
    window.setInterval(refreshWhileVisible, 15000);
    render();
    refresh();
})();
