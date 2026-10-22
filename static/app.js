let map;
let marker;

document.addEventListener("DOMContentLoaded", function () {
    const searchButton = document.getElementById("searchButton");
    const gpsButton = document.getElementById("gpsButton");

    if (searchButton) {
        searchButton.addEventListener("click", searchPlace);
    }

    if (gpsButton) {
        gpsButton.addEventListener("click", useGPS);
    }

    const placeInput = document.getElementById("place");

    if (placeInput) {
        placeInput.addEventListener("keypress", function (event) {
            if (event.key === "Enter") {
                searchPlace();
            }
        });
    }
});

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

        setStatus(
            "Data loaded. This is an awareness prototype, not an official warning service."
        );

    } catch (error) {
        setStatus(error.message);
    }
}

function renderResult(data, name, latitude, longitude) {
    const resultSection = document.getElementById("result");

    if (resultSection) {
        resultSection.classList.remove("d-none");
    }

    const locationElement = document.getElementById("location");

    if (locationElement) {
        locationElement.textContent = name;
    }

    const timeElement = document.getElementById("time");

    if (timeElement) {
        timeElement.textContent =
            `Updated: ${data.current.time || "Now"} · ${data.timezone}`;
    }

    const levelElement = document.getElementById("level");

    if (levelElement) {
        levelElement.textContent = data.level.toUpperCase();
        levelElement.className =
            `badge rounded-pill fs-6 p-2 mb-3 bg-${getBootstrapColor(data.level)}`;
    }

    const metricsElement = document.getElementById("metrics");

    if (metricsElement) {
        const current = data.current;

        metricsElement.innerHTML = `
            <p>
                <strong>Temperature:</strong>
                ${current.temperature_2m ?? "—"} °C
            </p>

            <p>
                <strong>Rainfall:</strong>
                ${current.rain ?? "—"} mm
            </p>

            <p>
                <strong>Wind Speed:</strong>
                ${current.wind_speed_10m ?? "—"} km/h
            </p>

            <p>
                <strong>Humidity:</strong>
                ${current.relative_humidity_2m ?? "—"}%
            </p>
        `;
    }

    const guidanceElement = document.getElementById("guidance");

    if (guidanceElement) {
        guidanceElement.innerHTML = data.guidance
            .map(function (item) {
                return `<li class="list-group-item">${item}</li>`;
            })
            .join("");
    }

    const risksElement = document.getElementById("risks");

    if (risksElement) {
        if (data.risks.length === 0) {
            risksElement.innerHTML =
                "<p>No project-defined climate risk threshold was reached.</p>";
        } else {
            risksElement.innerHTML = data.risks
                .map(function (risk) {
                    return `
                        <div class="risk ${risk.level}">
                            <strong>
                                ${risk.type} — ${risk.level}
                            </strong>
                            <br>
                            ${risk.detail}
                        </div>
                    `;
                })
                .join("");
        }
    }

    updateMap(latitude, longitude, name);
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

function setStatus(message) {
    const statusElement = document.getElementById("status");

    if (statusElement) {
        statusElement.textContent = message;
    }
}
