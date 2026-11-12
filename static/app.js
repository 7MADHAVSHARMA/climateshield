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
    const placeInput = document.getElementById("place");

    if (!placeInput) {
        return;
    }

    const query = placeInput.value.trim();

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

    if (!suggestions || suggestions.length === 0) {
        suggestionsBox.innerHTML = `
            <button
                type="button"
                class="list-group-item list-group-item-action text-muted"
                disabled
            >
                No location suggestions found
            </button>
        `;

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
    showLoading();
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

function renderResult(data, name, latitude, longitude) {
    const resultSection = document.getElementById("result");
    const locationElement = document.getElementById("location");
    const timeElement = document.getElementById("time");
    const levelElement = document.getElementById("level");
    const metricsElement = document.getElementById("metrics");
    const guidanceElement = document.getElementById("guidance");
    const weatherIcon = document.getElementById("weatherIcon");
    const airQualityElement = document.getElementById("airQuality");

    if (resultSection) {
        resultSection.classList.remove("d-none");
    }

    if (locationElement) {
        locationElement.textContent = name;
    }

    if (timeElement) {
        timeElement.textContent = new Date().toLocaleString();
    }

    const overallRisk = data.risks.overall;
    const overallLevel = overallRisk.level;

    if (levelElement) {
        levelElement.textContent = overallLevel.toUpperCase();
        levelElement.className = `badge rounded-pill fs-6 p-2 mb-3 bg-${getBootstrapColor(overallLevel)}`;
    }

    if (metricsElement) {
        metricsElement.innerHTML = `
            <div class="row g-2">
                <div class="col-6">
                    <div class="border rounded p-2">
                        <small class="text-muted">Temperature</small>
                        <div class="fw-bold">
                            ${data.current.temperature_2m}°C
                        </div>
                    </div>
                </div>

                <div class="col-6">
                    <div class="border rounded p-2">
                        <small class="text-muted">Humidity</small>
                        <div class="fw-bold">
                            ${data.current.relative_humidity_2m}%
                        </div>
                    </div>
                </div>

                <div class="col-6">
                    <div class="border rounded p-2">
                        <small class="text-muted">Wind</small>
                        <div class="fw-bold">
                            ${data.current.wind_speed_10m} km/h
                        </div>
                    </div>
                </div>

                <div class="col-6">
                    <div class="border rounded p-2">
                        <small class="text-muted">Precipitation</small>
                        <div class="fw-bold">
                            ${data.current.precipitation} mm
                        </div>
                    </div>
                </div>
            </div>
        `;
    }

    if (weatherIcon) {
        weatherIcon.className = `weather-icon ${getWeatherAnimationClass(
            data.current.weather_code
        )}`;

        weatherIcon.textContent = getWeatherEmoji(
            data.current.weather_code
        );
    }

    if (airQualityElement) {
        const pm25 = data.current.pm2_5;
        const pm10 = data.current.pm10;
        const aqi = data.current.european_aqi;

        airQualityElement.innerHTML = `
            <strong>Air Quality</strong><br>
            PM2.5: ${pm25} µg/m³<br>
            PM10: ${pm10} µg/m³<br>
            European AQI: ${aqi}
        `;
    }

    if (guidanceElement) {
        guidanceElement.innerHTML = getSafetyGuidance(data.risks)
            .map(function (item) {
                return `<li class="list-group-item">${escapeHTML(item)}</li>`;
            })
            .join("");
    }

    renderRiskCards(data.risks);
    updateMap(latitude, longitude, name);
}

function renderRiskCards(risks) {
    const riskContainer = document.getElementById("riskCards");

    if (!riskContainer) {
        return;
    }

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

function getSafetyGuidance(risks) {
    const guidance = [];

    if (risks.flood.score >= 60) {
        guidance.push(
            "Avoid low-lying areas, drains, and flooded roads. Move to higher ground if flooding begins."
        );
    }

    if (risks.thunderstorm.score >= 60) {
        guidance.push(
            "Stay indoors during thunderstorms. Avoid open fields, tall trees, and metal objects."
        );
    }

    if (risks.sandstorm.score >= 60) {
        guidance.push(
            "Cover your nose and mouth, wear protective eyewear, and avoid outdoor travel during dust storms."
        );
    }

    if (risks.air_pollution.score >= 60) {
        guidance.push(
            "Limit outdoor activity, especially for children, older adults, and people with breathing problems."
        );
    }

    if (risks.overall.score >= 80) {
        guidance.push(
            "Severe conditions detected. Follow official local emergency advisories immediately."
        );
    }

    if (guidance.length === 0) {
        guidance.push(
            "No major climate risks detected at this time. Continue normal activities with general weather awareness."
        );
    }

    return guidance;
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

    setTimeout(function () {
        map.invalidateSize();
    }, 300);
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
