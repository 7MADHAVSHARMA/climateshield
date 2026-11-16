import os
import psycopg2
import psycopg2.extras

from werkzeug.security import generate_password_hash, check_password_hash


DATABASE_URL = os.environ.get("DATABASE_URL")


def get_db():
    if not DATABASE_URL:
        raise Exception(
            "DATABASE_URL environment variable is missing."
        )

    connection = psycopg2.connect(DATABASE_URL)

    return connection


def init_db():
    try:
        connection = get_db()
        cursor = connection.cursor()

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id SERIAL PRIMARY KEY,
                name TEXT NOT NULL,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                email_alerts_enabled BOOLEAN DEFAULT FALSE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS saved_locations (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL,
                location_name TEXT NOT NULL,
                latitude DOUBLE PRECISION NOT NULL,
                longitude DOUBLE PRECISION NOT NULL,
                is_active BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
            """
        )

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS alert_logs (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL,
                location_id INTEGER NOT NULL,
                risk_type TEXT NOT NULL,
                risk_level TEXT NOT NULL,
                email_sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                weather_snapshot TEXT,
                FOREIGN KEY (user_id) REFERENCES users(id),
                FOREIGN KEY (location_id) REFERENCES saved_locations(id)
            )
            """
        )

        connection.commit()
        cursor.close()
        connection.close()

    except Exception as error:
        print("Database initialization warning:", error)


def create_user(name, email, password):
    connection = None
    cursor = None

    try:
        connection = get_db()
        cursor = connection.cursor()

        cursor.execute(
            "SELECT id FROM users WHERE email = %s",
            (email,)
        )

        existing_user = cursor.fetchone()

        if existing_user:
            return False

        cursor.execute(
            """
            INSERT INTO users
            (name, email, password_hash)
            VALUES (%s, %s, %s)
            """,
            (
                name,
                email,
                generate_password_hash(password)
            )
        )

        connection.commit()
        return True

    except Exception as error:
        print("User creation error:", error)

        if connection:
            connection.rollback()

        return False

    finally:
        if cursor:
            cursor.close()

        if connection:
            connection.close()


def get_user_by_email(email):
    connection = None
    cursor = None

    try:
        connection = get_db()
        cursor = connection.cursor(
            cursor_factory=psycopg2.extras.RealDictCursor
        )

        cursor.execute(
            "SELECT * FROM users WHERE email = %s",
            (email,)
        )

        user = cursor.fetchone()

        return dict(user) if user else None

    except Exception as error:
        print("Get user error:", error)
        return None

    finally:
        if cursor:
            cursor.close()

        if connection:
            connection.close()


def verify_user(email, password):
    user = get_user_by_email(email)

    if user and check_password_hash(
        user["password_hash"],
        password
    ):
        return user

    return None


def save_location(
    user_id,
    location_name,
    latitude,
    longitude
):
    connection = None
    cursor = None

    try:
        connection = get_db()
        cursor = connection.cursor()

        cursor.execute(
            """
            INSERT INTO saved_locations
            (user_id, location_name, latitude, longitude)
            VALUES (%s, %s, %s, %s)
            """,
            (
                user_id,
                location_name,
                latitude,
                longitude
            )
        )

        connection.commit()

    except Exception as error:
        print("Save location error:", error)

        if connection:
            connection.rollback()

    finally:
        if cursor:
            cursor.close()

        if connection:
            connection.close()


def get_active_locations():
    connection = None
    cursor = None

    try:
        connection = get_db()
        cursor = connection.cursor(
            cursor_factory=psycopg2.extras.RealDictCursor
        )

        cursor.execute(
            """
            SELECT
                users.id AS user_id,
                users.name AS user_name,
                users.email AS user_email,
                saved_locations.id AS location_id,
                saved_locations.location_name,
                saved_locations.latitude,
                saved_locations.longitude
            FROM users
            JOIN saved_locations
            ON users.id = saved_locations.user_id
            WHERE users.email_alerts_enabled = TRUE
            AND saved_locations.is_active = TRUE
            """
        )

        locations = cursor.fetchall()

        return [dict(location) for location in locations]

    except Exception as error:
        print("Get active locations error:", error)
        return []

    finally:
        if cursor:
            cursor.close()

        if connection:
            connection.close()


def was_alert_sent_recently(
    user_id,
    location_id,
    risk_type,
    risk_level
):
    connection = None
    cursor = None

    try:
        connection = get_db()
        cursor = connection.cursor()

        cursor.execute(
            """
            SELECT id FROM alert_logs
            WHERE user_id = %s
            AND location_id = %s
            AND risk_type = %s
            AND risk_level = %s
            AND email_sent_at >= NOW() - INTERVAL '12 hours'
            """,
            (
                user_id,
                location_id,
                risk_type,
                risk_level
            )
        )

        result = cursor.fetchone()

        return result is not None

    except Exception as error:
        print("Alert check error:", error)
        return False

    finally:
        if cursor:
            cursor.close()

        if connection:
            connection.close()


def log_alert(
    user_id,
    location_id,
    risk_type,
    risk_level,
    weather_snapshot
):
    connection = None
    cursor = None

    try:
        connection = get_db()
        cursor = connection.cursor()

        cursor.execute(
            """
            INSERT INTO alert_logs
            (user_id, location_id, risk_type, risk_level, weather_snapshot)
            VALUES (%s, %s, %s, %s, %s)
            """,
            (
                user_id,
                location_id,
                risk_type,
                risk_level,
                weather_snapshot
            )
        )

        connection.commit()

    except Exception as error:
        print("Alert logging error:", error)

        if connection:
            connection.rollback()

    finally:
        if cursor:
            cursor.close()

        if connection:
            connection.close()


def enable_email_alerts(email):
    connection = None
    cursor = None

    try:
        connection = get_db()
        cursor = connection.cursor()

        cursor.execute(
            """
            UPDATE users
            SET email_alerts_enabled = TRUE
            WHERE email = %s
            """,
            (email,)
        )

        connection.commit()

    except Exception as error:
        print("Enable alerts error:", error)

        if connection:
            connection.rollback()

    finally:
        if cursor:
            cursor.close()

        if connection:
            connection.close()


def disable_email_alerts(email):
    connection = None
    cursor = None

    try:
        connection = get_db()
        cursor = connection.cursor()

        cursor.execute(
            """
            UPDATE users
            SET email_alerts_enabled = FALSE
            WHERE email = %s
            """,
            (email,)
        )

        connection.commit()

    except Exception as error:
        print("Disable alerts error:", error)

        if connection:
            connection.rollback()

    finally:
        if cursor:
            cursor.close()

        if connection:
            connection.close()
