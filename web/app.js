let chart;

// ----------------------------
// DOM refs
// ----------------------------

const loading = document.getElementById("loading");
const loadingText = document.getElementById("loadingText");
const app = document.getElementById("app");
const errorBox = document.getElementById("errorBox");
const errorText = document.getElementById("errorText");
const retryButton = document.getElementById("retryButton");
const chartFallback = document.getElementById("chartFallback");

// ----------------------------
// Config
// ----------------------------

// Hard ceiling: if init() hasn't finished by this point, stop waiting
// and show an error instead of hanging on the loading screen forever.
const INIT_TIMEOUT_MS = 8000;

// ----------------------------
// Helpers
// ----------------------------

function withTimeout(promise, ms, label) {

    return Promise.race([

        promise,

        new Promise((_, reject) => {

            setTimeout(
                () => reject(new Error(`Timed out: ${label}`)),
                ms
            );

        })

    ]);

}

function showApp() {

    loading.classList.add("hidden");

    errorBox.classList.add("hidden");

    app.classList.remove("hidden");

}

function showError(message) {

    loading.classList.add("hidden");

    app.classList.add("hidden");

    errorText.textContent =
        message || "Market data temporarily unavailable.";

    errorBox.classList.remove("hidden");

}

// Detect whether the Chart.js library actually loaded.
// If the CDN request hung or failed, "Chart" will be undefined
// even though our own scripts ran fine.
function chartLibAvailable() {

    return typeof window.Chart !== "undefined";

}

// ----------------------------
// Init
// ----------------------------

async function init() {

    // Failsafe: no matter what happens inside the try block below,
    // never leave the user staring at "Loading market..." forever.
    const failsafe = setTimeout(() => {

        if (loading.classList.contains("hidden")) return;

        showError(
            "This is taking longer than expected. Please retry."
        );

    }, INIT_TIMEOUT_MS + 2000);

    try {

        console.log("[init] step 1: checking marketApi");

        if (typeof marketApi === "undefined") {

            throw new Error("marketApi.js failed to load");

        }

        console.log("[init] step 2: fetching market");

        const market = await withTimeout(
            marketApi.getMarket(),
            INIT_TIMEOUT_MS,
            "getMarket"
        );

        console.log("[init] step 3: market received", market);

        renderMarket(market);

        console.log("[init] step 4: market rendered, loading chart");

        // Chart rendering is best-effort. If Chart.js didn't load
        // (e.g. CDN blocked or unreachable), we still show the rest
        // of the app instead of hanging or hard-failing.
        try {

            await withTimeout(
                loadHistory("24H"),
                INIT_TIMEOUT_MS,
                "loadHistory"
            );

            console.log("[init] step 5: chart loaded ok");

        }

        catch (chartError) {

            console.error("Chart failed to load:", chartError);

            chartFallback.classList.remove("hidden");

            console.log("[init] step 5: chart skipped, continuing");

        }

        console.log("[init] step 6: fetching operations");

        const operations = await withTimeout(
            marketApi.getRecentOperations(),
            INIT_TIMEOUT_MS,
            "getRecentOperations"
        );

        console.log("[init] step 7: operations received", operations);

        renderOperations(operations);

        console.log("[init] step 8: operations rendered, showing app");

        clearTimeout(failsafe);

        showApp();

        console.log("[init] step 9: showApp() called, loading should be hidden now", {
            loadingHiddenClassPresent: loading.classList.contains("hidden"),
            loadingElement: loading
        });

        initButtons();

        console.log("[init] step 10: done");

    }

    catch (e) {

        console.error("[init] caught error, showing error box:", e);

        clearTimeout(failsafe);

        showError();

    }

}

// ----------------------------

function renderMarket(market) {

    document.getElementById("currentPrice").textContent = market.price;

    document.getElementById("availableCodes").textContent =
        `${market.availableCodes} / ${market.capacity}`;

    document.getElementById("marketStatus").textContent =
        market.status;

    document.getElementById("statPrice").textContent =
        market.price + " P6T";

    document.getElementById("statCodes").textContent =
        market.availableCodes;

    document.getElementById("statCapacity").textContent =
        market.capacity;

    document.getElementById("statChange").textContent =
        (market.priceChange > 0 ? "+" : "") +
        market.priceChange +
        "%";

    document.getElementById("statStatus").textContent =
        market.status;

}

// ----------------------------

async function loadHistory(range) {

    if (!chartLibAvailable()) {

        throw new Error("Chart.js not available");

    }

    const history =
        await marketApi.getPriceHistory(range);

    const labels =
        history.map(item => item.timestamp);

    const prices =
        history.map(item => item.price);

    if (chart) {

        chart.destroy();

    }

    const ctx =
        document
            .getElementById("marketChart")
            .getContext("2d");

    chart = new Chart(ctx, {

        type: "line",

        data: {

            labels,

            datasets: [

                {

                    data: prices,

                    borderColor: "#ffffff",

                    borderWidth: 2,

                    pointRadius: 0,

                    tension: .35,

                    fill: false

                }

            ]

        },

        options: {

            responsive: true,

            maintainAspectRatio: false,

            plugins: {

                legend: {

                    display: false

                }

            },

            scales: {

                x: {

                    ticks: {

                        color: "#777"

                    },

                    grid: {

                        color: "#222"

                    }

                },

                y: {

                    ticks: {

                        color: "#777"

                    },

                    grid: {

                        color: "#222"

                    }

                }

            }

        }

    });

    chartFallback.classList.add("hidden");

}

// ----------------------------

function renderOperations(list) {

    const container =
        document.getElementById("operationsList");

    container.innerHTML = "";

    list.forEach(op => {

        const div =
            document.createElement("div");

        div.className = "operation";

        div.innerHTML = `

<div class="operation-left">

<div class="operation-type">

${op.type}

</div>

<div>

${op.amount} code${op.amount > 1 ? "s" : ""}

</div>

<div class="operation-time">

${op.timestamp}

</div>

</div>

<strong class="${op.type === "BUY" ? "buy" : "sell"}">

${op.total > 0 ? "+" : ""}${op.total} P6T

</strong>

`;

        container.appendChild(div);

    });

}

// ----------------------------

function initButtons() {

    document
        .querySelectorAll("[data-range]")
        .forEach(button => {

            button.onclick = async () => {

                document
                    .querySelectorAll("[data-range]")
                    .forEach(b => b.classList.remove("active"));

                button.classList.add("active");

                try {

                    await loadHistory(button.dataset.range);

                }

                catch (e) {

                    console.error(e);

                    chartFallback.classList.remove("hidden");

                }

            };

        });

    retryButton.onclick = () => {

        errorBox.classList.add("hidden");

        loading.classList.remove("hidden");

        loadingText.textContent = "Retrying...";

        init();

    };

}

// ----------------------------

init();