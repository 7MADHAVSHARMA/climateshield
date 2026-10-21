let savedLatitude = null;
let savedLongitude = null;
let savedLocationName = null;

async function searchAndSave() {
    const query = document
        .getElementById("place")
        .value
        .trim();

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
            throw new Error(data.error);
        }

        savedLatitude = data.latitude;
        savedLongitude = data.longitude;
        savedLocationName = data.name;

        await saveLocation();

    } catch (error) {
        setStatus(error.message);
    }
}

async function saveLocation() {
    setStatus("Saving location...");

    try {
        const response = await fetch("/save-location", {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({
                location_name: savedLocationName,
                latitude: savedLatitude,
                longitude: savedLongitude
            })
        });

        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.error);
        }

        setStatus(
            `${savedLocationName} saved successfully. ` +
            "Enable email alerts to receive High or Severe risk notifications."
        );

    } catch (error) {
        setStatus(error.message);
    }
}

async function enableAlerts() {
    try {
        const response = await fetch("/enable-alerts", {
            method: "POST"
        });

        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.error);
        }

        setStatus(data.message);

    } catch (error) {
        setStatus(error.message);
    }
}
