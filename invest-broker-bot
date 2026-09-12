"""
Invest Broker — Telegram bot
Mijoz botga /start yozganda, "Moliya panelini ochish" tugmasi chiqadi.
Tugma bosilganda Telegram Mini App (WebApp) ochiladi — bu esa
../app/index.html faylida joylashgan kirim-chiqim va soliq hisobot paneli.

O'RNATISH:
1) pip install -r requirements.txt
2) Quyida BOT_TOKEN va WEBAPP_URL ni o'zingiznikiga almashtiring
3) python bot.py

ESLATMA: WEBAPP_URL httpS bo'lishi SHART (Telegram talabi).
app/index.html faylini biror hostingga (masalan GitHub Pages,python-telegram-bot[job-queue]==21.4
httpx==0.27.2
flask==3.0.3

Vercel, Netlify) joylab, shu havolani shu yerga qo'ying.
"""

import logging
import os
import threading
from datetime import datetime, timedelta

import httpx
from flask import Flask
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo, Update
from telegram.ext import Application, CommandHandler, ContextTypes

logging.basicConfig(level=logging.INFO)

# Render "Web Service" turi biror portni tinglab turishni talab qiladi.
# Bot o'zi port ochmaydi (u Telegram bilan "polling" orqali gaplashadi),
# shuning uchun shunchaki mavjudligini ko'rsatib turadigan mayda server ishga tushiramiz.
_health_app = Flask(__name__)


@_health_app.get("/")
def _health():
    return "Bot ishlayapti"


def _run_health_server():
    port = int(os.environ.get("PORT", 8080))
    _health_app.run(host="0.0.0.0", port=port)

# ====== SOZLAMALAR (shu yerni to'ldiring) ======
BOT_TOKEN = "8871207103:AAEIgZHCHONi5XHAzKPn2KSCBUNtq0bgoyI"
WEBAPP_URL = "https://clever-malasada-8260b6.netlify.app"
BACKEND_URL = "https://invest-broker-backend.onrender.com"
# ================================================


def fmt(n):
    return f"{n:,.0f}".replace(",", " ")


async def build_monthly_report(user_id: str) -> str:
    """Backend'dan shu foydalanuvchining o'tgan oylik ma'lumotlarini olib,
    QQS, foyda solig'i va mol-mulk solig'ini hisoblab, tayyor matn qaytaradi."""
    prev_month = (datetime.utcnow().replace(day=1) - timedelta(days=1)).strftime("%Y-%m")

    async with httpx.AsyncClient(timeout=10) as client:
        tx_resp = await client.get(f"{BACKEND_URL}/transactions/{user_id}")
        rates_resp = await client.get(f"{BACKEND_URL}/rates/{user_id}")

    transactions = tx_resp.json()
    rates = rates_resp.json()

    income = sum(t["amount"] for t in transactions if t["date"].startswith(prev_month) and t["type"] == "income")
    expense = sum(t["amount"] for t in transactions if t["date"].startswith(prev_month) and t["type"] == "expense")

    if income == 0 and expense == 0:
        return None  # shu oyda yozuv bo'lmagan foydalanuvchiga hisobot yuborilmaydi

    vat_amount = income * rates["vat"] / 100
    profit_base = max(0, income - expense)
    profit_amount = profit_base * rates["profit"] / 100
    property_amount = rates["property_value"] * rates["property_rate"] / 100

    return (
        f"📊 {prev_month} uchun avtomatik hisobot\n\n"
        f"Kirim: {fmt(income)} so'm\n"
        f"Chiqim: {fmt(expense)} so'm\n\n"
        f"QQS ({rates['vat']}%): {fmt(vat_amount)} so'm\n"
        f"Foyda solig'i ({rates['profit']}%): {fmt(profit_amount)} so'm\n"
        f"Mol-mulk solig'i (yillik, {rates['property_rate']}%): {fmt(property_amount)} so'm\n\n"
        f"To'liq tafsilot uchun mini-appni oching."
    )


async def send_monthly_reports(context: ContextTypes.DEFAULT_TYPE):
    """Har oyning 1-kuni ishga tushadi: barcha foydalanuvchilarga
    o'tgan oy hisobotini AVTOMATIK yuboradi — hech kim tugma bosmasa ham."""
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(f"{BACKEND_URL}/all-user-ids")
    user_ids = resp.json()

    for user_id in user_ids:
        if user_id == "demo":
            continue
        try:
            report = await build_monthly_report(user_id)
            if report:
                await context.bot.send_message(chat_id=int(user_id), text=report)
        except Exception as e:
            logging.error(f"Hisobot yuborishda xato ({user_id}): {e}")


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    "📊 Moliya panelini ochish",
                    web_app=WebAppInfo(url=WEBAPP_URL),
                )
            ]
        ]
    )
    await update.message.reply_text(
        "Assalomu alaykum!\n\n"
        "Invest Broker moliya boti orqali:\n"
        "• Kirim-chiqimlaringizni yuritasiz\n"
        "• QQS, Mol-mulk va Foyda solig'i hisobotlarini ko'rasiz\n\n"
        "Boshlash uchun quyidagi tugmani bosing 👇",
        reply_markup=keyboard,
    )


async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "/start — moliya panelini ochish\n"
        "/hisobot — o'tgan oy hisobotini hozir olish\n"
        "/help — yordam"
    )


async def hisobot_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    report = await build_monthly_report(user_id)
    if report:
        await update.message.reply_text(report)
    else:
        await update.message.reply_text(
            "O'tgan oy uchun hali yozuvlar topilmadi. "
            "Avval mini-appda kirim-chiqim kiritib boring."
        )


async def remind_daily(context: ContextTypes.DEFAULT_TYPE):
    """Ixtiyoriy: har kuni belgilangan vaqtda barcha foydalanuvchilarga
    kirim-chiqim kiritishni eslatadi. Kerak bo'lmasa, main() dagi
    job_queue.run_daily qatorini o'chirib qo'yishingiz mumkin."""
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(f"{BACKEND_URL}/all-user-ids")
    user_ids = resp.json()
    for user_id in user_ids:
        if user_id == "demo":
            continue
        try:
            await context.bot.send_message(
                chat_id=int(user_id),
                text="💡 Eslatma: bugungi kirim-chiqimni kiritishni unutmang.",
            )
        except Exception as e:
            logging.error(f"Eslatma yuborishda xato ({user_id}): {e}")


def main():
    threading.Thread(target=_run_health_server, daemon=True).start()

    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_cmd))
    app.add_handler(CommandHandler("hisobot", hisobot_cmd))

    # Har oyning 1-kuni, ertalab 09:00 da avtomatik hisobot yuboriladi
    app.job_queue.run_monthly(send_monthly_reports, when=datetime.strptime("09:00", "%H:%M").time(), day=1)

    # Ixtiyoriy: har kuni kechqurun 20:00 da eslatma (xohlamasangiz shu qatorni o'chiring)
    app.job_queue.run_daily(remind_daily, time=datetime.strptime("20:00", "%H:%M").time())

    print("Bot ishga tushdi...")
    app.run_polling()


if __name__ == "__main__":
    main()
