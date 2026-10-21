import os
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash

DB_PATH = os.path.join(os.path.dirname(__file__), "climateshield.db")


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            email_alerts_enabled INTEGER DEFAULT 0,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
        """
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS saved_locations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            location_name TEXT NOT NULL,
            latitude REAL NOT NULL,
            longitude REAL NOT NULL,
            is_active INTEGER DEFAULT 1,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
        """
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS alert_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            location_id INTEGER NOT NULL,
            risk_type TEXT NOT NULL,
            risk_level TEXT NOT NULL,
            email_sent_at TEXT DEFAULT CURRENT_TIMESTAMP,
            weather_snapshot TEXT,
            FOREIGN KEY (user_id) REFERENCES users(id),
            FOREIGN KEY (location_id) REFERENCES saved_locations(id)
        )
        """
    )

    conn.commit()
    conn.close()


def create_user(name, email, password):
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("SELECT id FROM users WHERE email = ?", (email,))
    if cursor.fetchone():
        conn.close()
        return False

    cursor.execute(
        "INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)",
        (name, email, generate_password_hash(password))
    )

    conn.commit()
    conn.close()
    return True


def get_user_by_email(email):
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM users WHERE email = ?", (email,))
    user = cursor.fetchone()

    conn.close()
    return user


def verify_user(email, password):
    user = get_user_by_email(email)

    if user and check_password_hash(user["password_hash"], password):
        return user

    return None


def save_location(user_id, location_name, latitude, longitude):
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute(
        """
        INSERT INTO saved_locations
        (user_id, location_name, latitude, longitude)
        VALUES (?, ?, ?, ?)
        """,
        (user_id, location_name, latitude, longitude)
    )

    conn.commit()
    conn.close()


def get_active_locations():
    conn = get_db()
    cursor = conn.cursor()

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
        WHERE users.email_alerts_enabled = 1
        AND saved_locations.is_active = 1
        """
    )

    locations = cursor.fetchall()
    conn.close()
    return locations


def was_alert_sent_recently(user_id, location_id, risk_type, risk_level):
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT id FROM alert_logs
        WHERE user_id = ?
        AND location_id = ?
        AND risk_type = ?
        AND risk_level = ?
        AND email_sent_at >= datetime('now', '-12 hours')
        """,
        (user_id, location_id, risk_type, risk_level)
    )

    result = cursor.fetchone()
    conn.close()
    return result is not None


def log_alert(
    user_id,
    location_id,
    risk_type,
    risk_level,
    weather_snapshot
):
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute(
        """
        INSERT INTO alert_logs
        (user_id, location_id, risk_type, risk_level, weather_snapshot)
        VALUES (?, ?, ?, ?, ?)
        """,
        (
            user_id,
            location_id,
            risk_type,
            risk_level,
            weather_snapshot
        )
    )

    conn.commit()
    conn.close()


def enable_email_alerts(email):
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute(
        "UPDATE users SET email_alerts_enabled = 1 WHERE email = ?",
        (email,)
    )

    conn.commit()
    conn.close()


def disable_email_alerts(email):
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute(
        "UPDATE users SET email_alerts_enabled = 0 WHERE email = ?",
        (email,)
    )

    conn.commit()
    conn.close()