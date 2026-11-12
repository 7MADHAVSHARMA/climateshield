let map;
let marker;
let suggestionTimer = null;

document.addEventListener("DOMContentLoaded", function () {
    const searchButton = document.getElementById("searchButton");
    const gpsButton = document.getElementById("gpsButton");
    const placeInput = document.getElementById("place");

    if (searchButton) {
        searchButton.addEventListener("click", searchPlace);
    }

    if (gpsButton) {
        gpsButton.addEventListener("click", useGPS);
    }

    if (placeInput) {
        placeInput.addEventListener("input", handleSuggestionInput);

        placeInput.addEventListener("keypress", function (event) {
            if (event.key === "Enter") {
                event.preventDefault();
                hideSuggestions();
                searchPlace();
            }
        });
    }

    document.addEventListener("click", function (event) {
        const suggestionsBox = document.getElementById("suggestions");
        const placeInput = document.getElementById("place");

        if (
            suggestionsBox &&
            placeInput &&
            !suggestionsBox.contains(event.target) &&
            event.target !== placeInput
        ) {
            hideSuggestions();
        }
    });
});

function handleSuggestionInput() {
    const query = document
        .getElementById("place")
        .value
        .trim();

    clearTimeout(suggestionTimer);

    if (query.length < 3) {
        hideSuggestions();
        return;
    }

    suggestionTimer = setTimeout(function () {
        getSuggestions(query);
    }, 600);
}

async function getSuggestions(query) {
    try {
        const response = await fetch(
            `/api/suggestions?q=${encodeURIComponent(query)}`
        );

        const data = await response.json();

        if (!response.ok) {
            hideSuggestions();
            return;
        }

        showSuggestions(data.suggestions || []);

    } catch (error) {
        hideSuggestions();
    }
}

function showSuggestions(suggestions) {
    const suggestionsBox = document.getElementById("suggestions");

    if (!suggestionsBox) {
        return;
    }

    if (suggestions.length === 0) {
        suggestionsBox.innerHTML =
            `<button type="button" class="list-group-item list-group-item-action text-muted" disabled>
                No location suggestions found
            </button>`;

        suggestionsBox.style.display = "block";
        return;
    }

    suggestionsBox.innerHTML = suggestions
        .map(function (item) {
            return `
                <button
                    type="button"
                    class="list-group-item list-group-item-action"
                    onclick="selectSuggestion(
                        '${escapeJavaScript(item.name)}',
                        ${item.latitude},
                        ${item.longitude}
                    )"
                >
                    ${escapeHTML(item.name)}
                </button>
            `;
        })
        .join("");

    suggestionsBox.style.display = "block";
}

function selectSuggestion(name, latitude, longitude) {
    const placeInput = document.getElementById("place");

    if (placeInput) {
        placeInput.value = name;
    }

    hideSuggestions();

    loadRisk(latitude, longitude, name);
}

function hideSuggestions() {
    const suggestionsBox = document.getElementById("suggestions");

    if (suggestionsBox) {
        suggestionsBox.style.display = "none";
        suggestionsBox.innerHTML = "";
    }
}

async function searchPlace() {
    const placeInput = document.getElementById("place");

    if (!placeInput) {
        setStatus("Search box not found.");
        return;
    }

    const query = placeInput.value.trim();

    if (!query) {
        setStatus("Please enter a location.");
        return;
    }

    showLoading();
    setStatus("Finding location...");

    try {
        const response = await fetch(
            `/api/location?q=${encodeURIComponent(query)}`
        );

        const data = await response.json();

        if (!response.ok) {
            throw new Error(
                data.error || "Location search failed."
            );
        }

        await loadRisk(
            data.latitude,
            data.longitude,
            data.name
        );

    } catch (error) {
        hideLoading();
        setStatus(error.message);
    }
}

function useGPS() {
    if (!navigator.geolocation) {
        setStatus(
            "Geolocation is not supported by this browser."
        );

        return;
    }

    showLoading();
    setStatus("Requesting your location...");

    navigator.geolocation.getCurrentPosition(
        function (position) {
            const latitude = position.coords.latitude;
            const longitude = position.coords.longitude;

            loadRisk(
                latitude,
                longitude,
                "Your Current Location"
            );
        },
        function (error) {
            hideLoading();

            if (error.code === error.PERMISSION_DENIED) {
                setStatus(
                    "Location permission was denied. Please allow location access."
                );
            } else if (error.code === error.POSITION_UNAVAILABLE) {
                setStatus(
                    "Your location is currently unavailable."
                );
            } else if (error.code === error.TIMEOUT) {
                setStatus(
                    "Location request timed out. Please try again."
                );
            } else {
                setStatus(
                    "Unable to get your location."
                );
            }
        },
        {
            enableHighAccuracy: true,
            timeout: 10000,
            maximumAge: 0
        }
    );
}

async function loadRisk(latitude, longitude, name) {
    setStatus("Loading climate data...");

    try {
        const response = await fetch(
            `/api/risk?latitude=${latitude}&longitude=${longitude}`
        );

        const data = await response.json();

        if (!response.ok) {
            throw new Error(
                data.error || "Weather data request failed."
            );
        }

        renderResult(data, name, latitude, longitude);

        hideLoading();

        setStatus(
            "Data loaded. This is an awareness prototype, not an official warning service."
        );

    } catch (error) {
        hideLoading();
        setStatus(error.message);
    }
}

const risks = data.risks;

const riskCards = [
    {
        title: "Flood Risk",
        value: risks.flood.score,
        level: risks.flood.level
    },
    {
        title: "Thunderstorm Risk",
        value: risks.thunderstorm.score,
        level: risks.thunderstorm.level
    },
    {
        title: "Sandstorm Risk",
        value: risks.sandstorm.score,
        level: risks.sandstorm.level
    },
    {
        title: "Air Pollution Risk",
        value: risks.air_pollution.score,
        level: risks.air_pollution.level
    },
    {
        title: "Overall Climate Risk",
        value: risks.overall.score,
        level: risks.overall.level
    }
];

const riskContainer = document.getElementById("riskCards");

if (riskContainer) {
    riskContainer.innerHTML = "";

    riskCards.forEach(function (risk) {
        const color = getBootstrapColor(risk.level);

        const card = document.createElement("div");
        card.className = "col-md-6";

        card.innerHTML = `
            <div class="card border-${color} h-100">
                <div class="card-body">
                    <h6 class="card-title fw-bold">
                        ${risk.title}
                    </h6>

                    <h2 class="mb-1 text-${color}">
                        ${risk.value}%
                    </h2>

                    <span class="badge bg-${color}">
                        ${risk.level}
                    </span>
                </div>
            </div>
        `;

        riskContainer.appendChild(card);
    });
}
const airQuality = document.getElementById("airQuality");

if (airQuality) {
    const pm25 = data.current.pm2_5;
    const pm10 = data.current.pm10;
    const aqi = data.current.european_aqi;

    airQuality.innerHTML = `
        <strong>Air Quality</strong><br>
        PM2.5: ${pm25} µg/m³<br>
        PM10: ${pm10} µg/m³<br>
        European AQI: ${aqi}
    `;
}
function updateMap(latitude, longitude, name) {
    const mapElement = document.getElementById("map");

    if (!mapElement) {
        return;
    }

    if (!map) {
        map = L.map("map").setView(
            [latitude, longitude],
            10
        );

        L.tileLayer(
            "https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png",
            {
                attribution: "© OpenStreetMap contributors"
            }
        ).addTo(map);
    } else {
        map.setView(
            [latitude, longitude],
            10
        );
    }

    if (marker) {
        marker.remove();
    }

    marker = L.marker([latitude, longitude])
        .addTo(map)
        .bindPopup(name)
        .openPopup();
}

function getWeatherEmoji(weatherCode) {
    const code = Number(weatherCode);

    if (code === 0) {
        return "☀️";
    }

    if (code === 1 || code === 2) {
        return "🌤️";
    }

    if (code === 3) {
        return "☁️";
    }

    if (code === 45 || code === 48) {
        return "🌫️";
    }

    if (
        code >= 51 && code <= 67 ||
        code >= 80 && code <= 82
    ) {
        return "🌧️";
    }

    if (
        code >= 71 && code <= 77 ||
        code === 85 || code === 86
    ) {
        return "❄️";
    }

    if (
        code >= 95 && code <= 99
    ) {
        return "⛈️";
    }

    return "🌍";
}

function getWeatherAnimationClass(weatherCode) {
    const code = Number(weatherCode);

    if (
        code >= 51 && code <= 67 ||
        code >= 80 && code <= 82
    ) {
        return "rain";
    }

    if (
        code >= 95 && code <= 99
    ) {
        return "thunderstorm";
    }

    if (code >= 35) {
        return "wind";
    }

    return "";
}

function getBootstrapColor(level) {
    if (level === "Severe") {
        return "dark";
    }

    if (level === "High") {
        return "danger";
    }

    if (level === "Moderate") {
        return "warning text-dark";
    }

    return "success";
}

function showLoading() {
    const loadingArea = document.getElementById("loading");

    if (loadingArea) {
        loadingArea.classList.remove("d-none");
    }
}

function hideLoading() {
    const loadingArea = document.getElementById("loading");

    if (loadingArea) {
        loadingArea.classList.add("d-none");
    }
}

function setStatus(message) {
    const statusElement = document.getElementById("status");

    if (statusElement) {
        statusElement.textContent = message;
    }
}

function escapeHTML(text) {
    return String(text)
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");
}

function escapeJavaScript(text) {
    return String(text)
        .replace(/\\/g, "\\\\")
        .replace(/'/g, "\\'")
        .replace(/"/g, '\\"')
        .replace(/\n/g, "\\n")
        .replace(/\r/g, "\\r");
}
function setStatus(message) {
    const statusElement = document.getElementById("status");

    if (statusElement) {
        statusElement.textContent = message;
    }
}

function getWeatherEmoji(weatherCode) {
    const code = Number(weatherCode);

    if (code === 0) {
        return "☀️";
    }

    if (code === 1 || code === 2) {
        return "🌤️";
    }

    if (code === 3) {
        return "☁️";
    }

    if (code === 45 || code === 48) {
        return "🌫️";
    }

    if (
        (code >= 51 && code <= 67) ||
        (code >= 80 && code <= 82)
    ) {
        return "🌧️";
    }

    if (
        (code >= 71 && code <= 77) ||
        code === 85 ||
        code === 86
    ) {
        return "❄️";
    }

    if (code >= 95 && code <= 99) {
        return "⛈️";
    }

    return "🌍";
}

function getWeatherAnimationClass(weatherCode) {
    const code = Number(weatherCode);

    if (
        (code >= 51 && code <= 67) ||
        (code >= 80 && code <= 82)
    ) {
        return "rain";
    }

    if (code >= 95 && code <= 99) {
        return "thunderstorm";
    }

    if (code >= 35) {
        return "wind";
    }

    return "";
}

