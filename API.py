# api_monitor.py
import sqlite3
import requests
import datetime
import time
import threading
from flask import Flask, jsonify

DB_PATH = "metrics.db"
TARGET_API = "https://example.com/api"   # <-- Change this to the API you want to monitor
CHECK_INTERVAL = 30  # seconds


# ----------------------------------------
# DATABASE SETUP
# ----------------------------------------
def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS api_metrics (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT,
            endpoint TEXT,
            response_time REAL,
            status_code INTEGER,
            error_message TEXT
        )
    """)
    conn.commit()
    conn.close()


# ----------------------------------------
# METRICS COLLECTION
# ----------------------------------------
def collect_metrics(url):
    start = datetime.datetime.utcnow()

    try:
        response = requests.get(url)
        duration = (datetime.datetime.utcnow() - start).total_seconds() * 1000

        status = response.status_code
        error = None

    except Exception as e:
        duration = None
        status = 0
        error = str(e)

    conn = get_db()
    conn.execute("""
        INSERT INTO api_metrics (timestamp, endpoint, response_time, status_code, error_message)
        VALUES (?, ?, ?, ?, ?)
    """, (datetime.datetime.utcnow(), url, duration, status, error))
    conn.commit()
    conn.close()


# ----------------------------------------
# BACKGROUND SCHEDULER
# ----------------------------------------
def scheduler():
    while True:
        collect_metrics(TARGET_API)
        time.sleep(CHECK_INTERVAL)


# ----------------------------------------
# FLASK APP
# ----------------------------------------
app = Flask(__name__)


@app.route("/")
def home():
    return jsonify({"message": "API Performance Monitor Running"})


@app.route("/run-check")
def run_check():
    collect_metrics(TARGET_API)
    return jsonify({"status": "ok", "message": "Manual check executed"})


@app.route("/metrics")
def get_metrics():
    conn = get_db()
    rows = conn.execute("SELECT * FROM api_metrics ORDER BY timestamp DESC LIMIT 100").fetchall()
    conn.close()
    return jsonify([dict(row) for row in rows])


# ----------------------------------------
# MAIN
# ----------------------------------------
if __name__ == "__main__":
    init_db()

    # Start background monitoring thread
    t = threading.Thread(target=scheduler, daemon=True)
    t.start()

    app.run(host="0.0.0.0", port=5000)
