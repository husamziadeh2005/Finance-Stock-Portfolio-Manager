(function () {
    const root = document.documentElement;
    const savedTheme = localStorage.getItem("finora-theme");
    if (savedTheme === "dark") root.setAttribute("data-theme", "dark");

    document.addEventListener("DOMContentLoaded", () => {
        const toggle = document.getElementById("themeToggle");
        if (toggle) {
            toggle.addEventListener("click", () => {
                const isDark = root.getAttribute("data-theme") === "dark";
                if (isDark) {
                    root.removeAttribute("data-theme");
                    localStorage.setItem("finora-theme", "light");
                } else {
                    root.setAttribute("data-theme", "dark");
                    localStorage.setItem("finora-theme", "dark");
                }
            });
        }
    });
})();

async function fetchQuote(symbol) {
    const response = await fetch(`/api/quote?symbol=${encodeURIComponent(symbol)}`);
    const data = await response.json();
    if (!response.ok || !data.ok) throw new Error(data.message || "Quote unavailable");
    return data.stock;
}

function initTradePreview(mode) {
    const symbol = document.getElementById("symbol");
    const shares = document.getElementById("shares");
    const preview = document.getElementById("quotePreview");
    if (!symbol || !shares || !preview) return;

    let timer;
    async function updatePreview() {
        const ticker = symbol.value.trim().toUpperCase();
        const quantity = Number(shares.value || 0);
        if (!ticker) {
            preview.classList.add("d-none");
            return;
        }
        preview.classList.remove("d-none");
        preview.textContent = "Loading current price…";
        try {
            const stock = await fetchQuote(ticker);
            const total = quantity > 0 ? stock.price * quantity : stock.price;
            const action = mode === "sell" ? "Estimated proceeds" : "Estimated cost";
            preview.innerHTML = `<div class="d-flex justify-content-between gap-3"><span><strong>${stock.symbol}</strong> · $${Number(stock.price).toFixed(2)} / share</span><span><strong>${action}: $${Number(total).toFixed(2)}</strong></span></div>`;
        } catch (error) {
            preview.textContent = error.message;
        }
    }

    function delayedUpdate() {
        clearTimeout(timer);
        timer = setTimeout(updatePreview, 450);
    }

    symbol.addEventListener("change", updatePreview);
    symbol.addEventListener("input", delayedUpdate);
    shares.addEventListener("input", delayedUpdate);
}

function initLiveQuoteSearch() {
    const form = document.getElementById("quoteSearchForm");
    const input = document.getElementById("quoteSymbol");
    const result = document.getElementById("liveQuoteResult");
    if (!form || !input || !result) return;

    form.addEventListener("submit", async (event) => {
        event.preventDefault();
        const symbol = input.value.trim().toUpperCase();
        if (!symbol) return;
        result.classList.remove("d-none");
        result.textContent = "Searching market data…";
        try {
            const stock = await fetchQuote(symbol);
            result.innerHTML = `<div class="d-flex flex-column flex-sm-row align-items-sm-center justify-content-between gap-3"><div><span class="eyebrow mb-1">${stock.symbol}</span><h3 class="mb-1">${stock.name}</h3><span class="text-muted">Latest available price</span></div><div class="text-sm-end"><div class="fs-2 fw-bold">$${Number(stock.price).toFixed(2)}</div><a class="text-link" href="/buy">Buy stock →</a></div></div>`;
        } catch (error) {
            result.innerHTML = `<strong>Could not find that stock.</strong><div class="text-muted small mt-1">Check the ticker symbol and try again.</div>`;
        }
    });
}

function initHistoryFilter() {
    const search = document.getElementById("historySearch");
    const filter = document.getElementById("historyFilter");
    const table = document.getElementById("historyTable");
    const empty = document.getElementById("historyEmpty");
    if (!search || !filter || !table) return;

    const rows = Array.from(table.querySelectorAll("tbody tr"));
    function apply() {
        const query = search.value.trim().toLowerCase();
        const type = filter.value;
        let visible = 0;
        rows.forEach((row) => {
            const matchesSymbol = row.dataset.symbol.includes(query);
            const matchesType = type === "all" || row.dataset.type === type;
            const show = matchesSymbol && matchesType;
            row.classList.toggle("d-none", !show);
            if (show) visible += 1;
        });
        if (empty) empty.classList.toggle("d-none", visible !== 0);
        table.classList.toggle("d-none", visible === 0);
    }

    search.addEventListener("input", apply);
    filter.addEventListener("change", apply);
}

function initQuickAmounts() {
    const input = document.getElementById("amount");
    if (!input) return;
    document.querySelectorAll("[data-amount]").forEach((button) => {
        button.addEventListener("click", () => {
            input.value = button.dataset.amount;
            input.focus();
        });
    });
}
