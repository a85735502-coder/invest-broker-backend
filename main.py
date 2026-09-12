"""
Invest Broker — Backend (ma'lumotlar markazi), Flask asosida.

Bu versiya ataylab Flask bilan yozilgan (pydantic/FastAPI emas),
chunki ba'zi hosting xizmatlarida yangi Python versiyalari bilan
pydantic o'rnatilishida compilyatsiya xatosi chiqishi mumkin.
Flask'da bunday muammo umuman bo'lmaydi.

O'RNATISH:
  pip install -r requirements.txt
  python main.py
"""

import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone

from flask import Flask, request, jsonify
from flask_cors import CORS

DB_PATH = "data.db"

app = Flask(__name__)
CORS(app)


@contextmanager
def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db():
    with get_db() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                type TEXT NOT NULL,
                amount REAL NOT NULL,
                category TEXT,
                date TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS rates (
                user_id TEXT PRIMARY KEY,
                vat REAL DEFAULT 12,
                property_rate REAL DEFAULT 2,
                property_value REAL DEFAULT 0,
                profit REAL DEFAULT 15
            )
            """
        )


init_db()


@app.get("/health")
def health():
    return jsonify({"status": "ok"})


@app.post("/transactions")
def add_transaction():
    data = request.get_json(force=True)
    user_id = data.get("user_id")
    tx_type = data.get("type")
    amount = data.get("amount")
    category = data.get("category", "")
    date = data.get("date")

    if not user_id or tx_type not in ("income", "expense") or amount is None or not date:
        return jsonify({"error": "user_id, type (income/expense), amount, date majburiy"}), 400

    with get_db() as conn:
        conn.execute(
            "INSERT INTO transactions (user_id, type, amount, category, date, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (user_id, tx_type, float(amount), category, date, datetime.now(timezone.utc).isoformat()),
        )
    return jsonify({"status": "saqlandi"})


@app.get("/transactions/<user_id>")
def list_transactions(user_id):
    with get_db() as conn:
        rows = conn.execute(
            "SELECT * FROM transactions WHERE user_id = ? ORDER BY date DESC, id DESC",
            (user_id,),
        ).fetchall()
    return jsonify([dict(r) for r in rows])


@app.delete("/transactions/<int:tx_id>")
def delete_transaction(tx_id):
    with get_db() as conn:
        conn.execute("DELETE FROM transactions WHERE id = ?", (tx_id,))
    return jsonify({"status": "o'chirildi"})


@app.post("/rates")
def set_rates():
    data = request.get_json(force=True)
    user_id = data.get("user_id")
    if not user_id:
        return jsonify({"error": "user_id majburiy"}), 400

    with get_db() as conn:
        conn.execute(
            """
            INSERT INTO rates (user_id, vat, property_rate, property_value, profit)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET
                vat=excluded.vat,
                property_rate=excluded.property_rate,
                property_value=excluded.property_value,
                profit=excluded.profit
            """,
            (
                user_id,
                float(data.get("vat", 12)),
                float(data.get("property_rate", 2)),
                float(data.get("property_value", 0)),
                float(data.get("profit", 15)),
            ),
        )
    return jsonify({"status": "saqlandi"})


@app.get("/rates/<user_id>")
def get_rates(user_id):
    with get_db() as conn:
        row = conn.execute("SELECT * FROM rates WHERE user_id = ?", (user_id,)).fetchone()
    if not row:
        return jsonify({"user_id": user_id, "vat": 12, "property_rate": 2, "property_value": 0, "profit": 15})
    return jsonify(dict(row))


@app.get("/all-user-ids")
def all_user_ids():
    """Bot har oy shu ro'yxatni olib, har bir mijozga hisobot yuborish uchun ishlatadi."""
    with get_db() as conn:
        rows = conn.execute("SELECT DISTINCT user_id FROM transactions").fetchall()
    return jsonify([r["user_id"] for r in rows])


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)
