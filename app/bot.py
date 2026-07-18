import os
from typing import Optional

from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters

from app.calculator import calculate_position_size_usdt
from app.journal import TradeJournal

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
journal = TradeJournal()


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "Привет! Я журнал трейдера.\n"
        "Команды:\n"
        "/new — создать запись\n"
        "/active — активные позиции\n"
        "/history — история сделок\n"
        "/calc — рассчитать размер позиции по PM"
    )


async def new_trade(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = update.message.text or ""
    parts = text.split()
    if len(parts) < 5:
        await update.message.reply_text("Формат: /new BTCUSDT 100 110 95 Почему открываю")
        return

    ticker = parts[1]
    entry_price = float(parts[2])
    take_profit = float(parts[3])
    stop_loss = float(parts[4])
    comment = " ".join(parts[5:]) if len(parts) > 5 else ""

    record = journal.create_record(ticker, entry_price, take_profit, stop_loss, comment)
    await update.message.reply_text(
        f"Запись создана: #{record.id} {ticker}\n"
        f"Entry: {entry_price}\nTP: {take_profit}\nSL: {stop_loss}\n"
        f"Комментарий: {comment or '-'}"
    )


async def active(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not journal.active_records():
        await update.message.reply_text("Нет активных позиций")
        return

    lines = [f"#{record.id} {record.ticker} | TP {record.take_profit} | SL {record.stop_loss}" for record in journal.active_records()]
    await update.message.reply_text("\n".join(lines))


async def history(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not journal.closed_records():
        await update.message.reply_text("История пока пуста")
        return

    lines = [
        f"#{record.id} {record.ticker} | {record.result} | {record.close_reason} | PnL {record.pnl_usdt}"
        for record in journal.closed_records()
    ]
    await update.message.reply_text("\n".join(lines))


async def calc(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = update.message.text or ""
    parts = text.split()
    if len(parts) < 5:
        await update.message.reply_text("Формат: /calc 100 95 10 100")
        return

    entry_price = float(parts[1])
    stop_loss_price = float(parts[2])
    leverage = float(parts[3])
    risk_usdt = float(parts[4])

    size, margin = calculate_position_size_usdt(entry_price, stop_loss_price, leverage, risk_usdt)
    await update.message.reply_text(
        f"Размер позиции: {size:.2f} USDT\n"
        f"Маржа: {margin:.2f} USDT"
    )


async def close_trade(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = update.message.text or ""
    parts = text.split()
    if len(parts) < 6:
        await update.message.reply_text("Формат: /close 1 tp 100 10 Победа")
        return

    record_id = int(parts[1])
    close_reason = parts[2]
    exit_price = float(parts[3])
    pnl_usdt = float(parts[4])
    result = " ".join(parts[5:])

    journal.close_record(record_id, result, close_reason, pnl_usdt, result, exit_price)
    await update.message.reply_text(f"Сделка #{record_id} закрыта")


async def main() -> None:
    if not TOKEN:
        raise RuntimeError("TELEGRAM_BOT_TOKEN is not set")
    application = Application.builder().token(TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("new", new_trade))
    application.add_handler(CommandHandler("active", active))
    application.add_handler(CommandHandler("history", history))
    application.add_handler(CommandHandler("calc", calc))
    application.add_handler(CommandHandler("close", close_trade))
    application.run_polling()


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
