"""
Invest Broker — Backend (ma'lumotlar markazi)

Bu kichik server mini-app'dan kelgan kirim-chiqim yozuvlarini
saqlaydi (SQLite bazada), shunda:
- Mijoz istalgan qurilmadan kirsa, o'sha ma'lumotlarni ko'radi
- Bot har oy oxirida bu ma'lumotlar asosida hisobotni AVTOMATIK hisoblab,
  mijozga Telegram orqali o'zi yuborishi mumkin bo'ladi

Hech qanday tashqi API (bank, soliq.uz va h.k.) kerak emas —
faqat mijozning botga kiritgan o'z ma'lumotlari ishlatiladi.

O'RNATISH:
  pip install -r requirements.txt
  python main.pyfastapi==0.115.0
uvicorn==0.30.6
pydantic==2.9.2

Server manzili: http://0.0.0.0:8000
(Buni ham mini-app kabi https bilan internetga chiqarish kerak —
 masalan Render.com, Railway.app kabi bepul xizmatlar orqali.)
"""

import sqlite3
from contextlib import contextmanager
from datetime import datetime

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

DB_PATH = "data.db"

app = FastAPI(title="Invest Broker Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # mini-app har qanday domendan chaqira oladi
    allow_methods=["*"],
    allow_headers=["*"],
)


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


class Transaction(BaseModel):
    user_id: str
    type: str  # "income" | "expense"
    amount: float
    category: str = ""
    date: str  # "YYYY-MM-DD"


class Rates(BaseModel):
    user_id: str
    vat: float = 12
    property_rate: float = 2
    property_value: float = 0
    profit: float = 15


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/transactions")
def add_transaction(tx: Transaction):
    if tx.type not in ("income", "expense"):
        raise HTTPException(400, "type 'income' yoki 'expense' bo'lishi kerak")
    with get_db() as conn:
        conn.execute(
            "INSERT INTO transactions (user_id, type, amount, category, date, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (tx.user_id, tx.type, tx.amount, tx.category, tx.date, datetime.utcnow().isoformat()),
        )
    return {"status": "saqlandi"}


@app.get("/transactions/{user_id}")
def list_transactions(user_id: str):
    with get_db() as conn:
        rows = conn.execute(
            "SELECT * FROM transactions WHERE user_id = ? ORDER BY date DESC, id DESC",
            (user_id,),
        ).fetchall()
    return [dict(r) for r in rows]


@app.delete("/transactions/{tx_id}")
def delete_transaction(tx_id: int):
    with get_db() as conn:
        conn.execute("DELETE FROM transactions WHERE id = ?", (tx_id,))
    return {"status": "o'chirildi"}


@app.post("/rates")
def set_rates(r: Rates):
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
            (r.user_id, r.vat, r.property_rate, r.property_value, r.profit),
        )
    return {"status": "saqlandi"}


@app.get("/rates/{user_id}")
def get_rates(user_id: str):
    with get_db() as conn:
        row = conn.execute("SELECT * FROM rates WHERE user_id = ?", (user_id,)).fetchone()
    if not row:
        return {"user_id": user_id, "vat": 12, "property_rate": 2, "property_value": 0, "profit": 15}
    return dict(row)


@app.get("/all-user-ids")
def all_user_ids():
    """Bot har oy shu ro'yxatni olib, har bir mijozga hisobot yuborish uchun ishlatadi."""
    with get_db() as conn:
        rows = conn.execute("SELECT DISTINCT user_id FROM transactions").fetchall()
    return [r["user_id"] for r in rows]


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
