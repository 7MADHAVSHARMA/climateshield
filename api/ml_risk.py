import numpy as np
from sklearn.ensemble import RandomForestRegressor


class ClimateRiskModel:
    """
    Lightweight ML-based climate risk model.

    It estimates:
    - Flood risk
    - Thunderstorm risk
    - Sand/dust storm risk
    - Air pollution / PM2.5 risk
    - Overall climate risk
    """

    def __init__(self):
        self.flood_model = self._train_model(
            feature_count=6,
            risk_type="flood"
        )

        self.thunder_model = self._train_model(
            feature_count=6,
            risk_type="thunderstorm"
        )

        self.dust_model = self._train_model(
            feature_count=6,
            risk_type="dust"
        )

        self.pollution_model = self._train_model(
            feature_count=7,
            risk_type="pollution"
        )

    def _train_model(self, feature_count, risk_type):
        """
        Trains a RandomForest model using physically realistic
        synthetic training data.

        For a student project, this creates a real ML model without
        needing a large labelled historical disaster dataset.
        """

        rng = np.random.default_rng(42)
        samples = 3000

        X = rng.random((samples, feature_count))

        if risk_type == "flood":
            precipitation, soil_moisture, drainage, elevation, river_proximity, urbanization = (
                X[:, 0], X[:, 1], X[:, 2], X[:, 3], X[:, 4], X[:, 5]
            )

            y = (
                precipitation * 0.55 +
                soil_moisture * 0.20 +
                (1 - drainage) * 0.10 +
                (1 - elevation) * 0.08 +
                river_proximity * 0.05 +
                urbanization * 0.02
            )

        elif risk_type == "thunderstorm":
            cape, wind_gust, precipitation, humidity, temperature, pressure = (
                X[:, 0], X[:, 1], X[:, 2], X[:, 3], X[:, 4], X[:, 5]
            )

            y = (
                cape * 0.40 +
                wind_gust * 0.25 +
                precipitation * 0.20 +
                humidity * 0.10 +
                temperature * 0.03 +
                (1 - pressure) * 0.02
            )

        elif risk_type == "dust":
            wind_speed, wind_gust, precipitation, humidity, temperature, vegetation = (
                X[:, 0], X[:, 1], X[:, 2], X[:, 3], X[:, 4], X[:, 5]
            )

            y = (
                wind_speed * 0.35 +
                wind_gust * 0.30 +
                (1 - precipitation) * 0.15 +
                (1 - humidity) * 0.10 +
                temperature * 0.05 +
                (1 - vegetation) * 0.05
            )

        else:
            pm25, pm10, no2, so2, o3, co, aqi = (
                X[:, 0], X[:, 1], X[:, 2], X[:, 3], X[:, 4], X[:, 5], X[:, 6]
            )

            y = (
                pm25 * 0.35 +
                pm10 * 0.20 +
                no2 * 0.12 +
                so2 * 0.10 +
                o3 * 0.10 +
                co * 0.05 +
                aqi * 0.08
            )

        y = np.clip(y, 0, 1)

        model = RandomForestRegressor(
            n_estimators=180,
            max_depth=14,
            min_samples_leaf=4,
            random_state=42,
            n_jobs=-1
        )

        model.fit(X, y)

        return model

    def calculate_flood_risk(
        self,
        precipitation,
        soil_moisture,
        drainage,
        elevation,
        river_proximity,
        urbanization
    ):
        features = np.array([[
            self._scale(precipitation, 0, 120),
            self._scale(soil_moisture, 0, 1),
            self._scale(drainage, 0, 1),
            self._scale(elevation, 0, 1),
            self._scale(river_proximity, 0, 1),
            self._scale(urbanization, 0, 1)
        ]])

        return float(self.flood_model.predict(features)[0])

    def calculate_thunderstorm_risk(
        self,
        cape,
        wind_gust,
        precipitation,
        humidity,
        temperature,
        pressure
    ):
        features = np.array([[
            self._scale(cape, 0, 4000),
            self._scale(wind_gust, 0, 120),
            self._scale(precipitation, 0, 120),
            self._scale(humidity, 0, 100),
            self._scale(temperature, -10, 50),
            self._scale(pressure, 950, 1050)
        ]])

        return float(self.thunder_model.predict(features)[0])

    def calculate_dust_risk(
        self,
        wind_speed,
        wind_gust,
        precipitation,
        humidity,
        temperature,
        vegetation
    ):
        features = np.array([[
            self._scale(wind_speed, 0, 120),
            self._scale(wind_gust, 0, 120),
            self._scale(precipitation, 0, 120),
            self._scale(humidity, 0, 100),
            self._scale(temperature, -10, 55),
            self._scale(vegetation, 0, 1)
        ]])

        return float(self.dust_model.predict(features)[0])

    def calculate_pollution_risk(
        self,
        pm25,
        pm10,
        no2,
        so2,
        o3,
        co,
        aqi
    ):
        features = np.array([[
            self._scale(pm25, 0, 250),
            self._scale(pm10, 0, 350),
            self._scale(no2, 0, 200),
            self._scale(so2, 0, 200),
            self._scale(o3, 0, 240),
            self._scale(co, 0, 10000),
            self._scale(aqi, 0, 200)
        ]])

        return float(self.pollution_model.predict(features)[0])

    def calculate_overall_risk(self, risks):
        weights = {
            "flood": 0.30,
            "thunderstorm": 0.25,
            "dust": 0.20,
            "pollution": 0.25
        }

        overall = (
            risks["flood"] * weights["flood"] +
            risks["thunderstorm"] * weights["thunderstorm"] +
            risks["dust"] * weights["dust"] +
            risks["pollution"] * weights["pollution"]
        )

        return min(1.0, max(0.0, overall))

    def get_risk_level(self, score):
        if score >= 0.80:
            return "Severe"
        elif score >= 0.60:
            return "High"
        elif score >= 0.40:
            return "Moderate"
        elif score >= 0.20:
            return "Low"
        else:
            return "Minimal"

    def _scale(self, value, minimum, maximum):
        value = float(value or 0)
        value = min(max(value, minimum), maximum)

        return (value - minimum) / (maximum - minimum)


climate_risk_model = ClimateRiskModel()
