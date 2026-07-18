import os
from typing import Optional

from telegram import ReplyKeyboardMarkup, Update
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters

from app.calculator import calculate_position_size_usdt
from app.journal import TradeJournal

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
journal = TradeJournal()


def build_keyboard() -> ReplyKeyboardMarkup:
    buttons = [
        ["/new", "/active"],
        ["/history", "/stats"],
        ["/export", "/calc"],
    ]
    return ReplyKeyboardMarkup(buttons, resize_keyboard=True, one_time_keyboard=False)


def format_rr(entry_price: float, stop_loss: float, take_profit: float) -> str:
    risk = abs(entry_price - stop_loss)
    reward = abs(entry_price - take_profit)
    if risk == 0:
        return "—"
    return f"{reward / risk:.2f}"


def format_active(record) -> str:
    return (
        f"⌛ <b>#{record.id} {record.ticker}</b>\n"
        f"🎯 Вход: {record.entry_price}\n"
        f"🛑 Стоп: {record.stop_loss}\n"
        f"🚀 Тейк: {record.take_profit}\n"
        f"📈 R/R: 1:{format_rr(record.entry_price, record.stop_loss, record.take_profit)}\n"
        f"📝 Идея: {record.comment or '-'}"
    )


def format_closed(record) -> str:
    return (
        f"✅ <b>#{record.id} {record.ticker}</b> | {record.result or '-'}\n"
        f"🏁 Вход: {record.entry_price} | Выход: {record.exit_price or '-'}\n"
        f"💰 PnL: {record.pnl_usdt or 0:.2f} USDT | Причина: {record.close_reason or '-'}\n"
        f"📝 {record.close_note or '-'}"
    )


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        (
            "Привет! Я твой торговый журнал. Выбери команду или нажми кнопку:\n\n"
            "/new — новая сделка\n"
            "/active — активные позиции\n"
            "/history — история\n"
            "/stats — статистика\n"
            "/calc — калькулятор PM\n"
            "/export — экспорт журнала"
        ),
        parse_mode="HTML",
        reply_markup=build_keyboard(),
    )


async def new_trade(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = update.message.text or ""
    parts = text.split()
    if len(parts) < 5:
        await update.message.reply_text(
            "Формат: /new BTCUSDT 100 110 95 Почему открываю\nПример: /new BTCUSDT 100 110 95 Ожидаю откат",
            reply_markup=build_keyboard(),
        )
        return

    ticker = parts[1]
    entry_price = float(parts[2])
    take_profit = float(parts[3])
    stop_loss = float(parts[4])
    comment = " ".join(parts[5:]) if len(parts) > 5 else ""

    record = journal.create_record(ticker, entry_price, take_profit, stop_loss, comment)
    await update.message.reply_text(
        (
            f"✅ <b>Запись создана</b> #{record.id} {ticker}\n"
            f"🎯 Вход: {record.entry_price}\n"
            f"🚀 Тейк: {record.take_profit}\n"
            f"🛑 Стоп: {record.stop_loss}\n"
            f"📝 Идея: {comment or '-'}"
        ),
        parse_mode="HTML",
        reply_markup=build_keyboard(),
    )


async def active(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    records = journal.active_records()
    if not records:
        await update.message.reply_text(
            "Нет активных позиций. Добавь первую сделку через /new.",
            reply_markup=build_keyboard(),
        )
        return

    await update.message.reply_text(
        "\n\n".join(format_active(record) for record in records),
        parse_mode="HTML",
        reply_markup=build_keyboard(),
    )


async def history(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    records = journal.closed_records()
    if not records:
        await update.message.reply_text(
            "История пуста.",
            reply_markup=build_keyboard(),
        )
        return

    await update.message.reply_text(
        "\n\n".join(format_closed(record) for record in records),
        parse_mode="HTML",
        reply_markup=build_keyboard(),
    )


async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    closed = journal.closed_records()
    wins = sum(1 for record in closed if record.result and record.result.lower() == "победа")
    losses = sum(1 for record in closed if record.result and record.result.lower() == "проигрыш")
    total = len(closed)
    pnl = sum(record.pnl_usdt or 0 for record in closed)

    await update.message.reply_text(
        (
            f"📊 <b>Статистика</b>\n"
            f"Активных: {len(journal.active_records())}\n"
            f"Закрытых: {total}\n"
            f"Побед: {wins} | Поражений: {losses}\n"
            f"Общий PnL: {pnl:.2f} USDT"
        ),
        parse_mode="HTML",
        reply_markup=build_keyboard(),
    )


async def calc(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = update.message.text or ""
    parts = text.split()
    if len(parts) < 5:
        await update.message.reply_text(
            "Формат: /calc 100 95 10 100\nПример: /calc 100 95 10 100",
            reply_markup=build_keyboard(),
        )
        return

    entry_price = float(parts[1])
    stop_loss_price = float(parts[2])
    leverage = float(parts[3])
    risk_usdt = float(parts[4])

    size, margin = calculate_position_size_usdt(entry_price, stop_loss_price, leverage, risk_usdt)
    await update.message.reply_text(
        (
            f"🧮 <b>Калькулятор PM</b>\n"
            f"Размер позиции: {size:.2f} USDT\n"
            f"Маржа: {margin:.2f} USDT"
        ),
        parse_mode="HTML",
        reply_markup=build_keyboard(),
    )


async def export(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "Экспорт пока не реализован. Можно сохранить файл data/journal.json вручную.",
        reply_markup=build_keyboard(),
    )


async def close_trade(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = update.message.text or ""
    parts = text.split()
    if len(parts) < 6:
        await update.message.reply_text(
            "Формат: /close 1 tp 100 10 Победа\nПример: /close 1 tp 100 10 Победа",
            reply_markup=build_keyboard(),
        )
        return

    record_id = int(parts[1])
    close_reason = parts[2]
    exit_price = float(parts[3])
    pnl_usdt = float(parts[4])
    result = " ".join(parts[5:])

    journal.close_record(record_id, result, close_reason, pnl_usdt, result, exit_price)
    await update.message.reply_text(
        f"✅ Сделка #{record_id} закрыта",
        reply_markup=build_keyboard(),
    )


async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = (update.message.text or "").strip().lower()
    if text in {"/new", "новая сделка"}:
        await update.message.reply_text(
            "Создай новую запись через команду /new\nПример: /new BTCUSDT 100 110 95 Ожидаю откат",
            reply_markup=build_keyboard(),
        )
    elif text in {"/active", "активные"}:
        await active(update, context)
    elif text in {"/history", "история"}:
        await history(update, context)
    elif text in {"/stats", "статистика"}:
        await stats(update, context)
    elif text in {"/export", "экспорт"}:
        await export(update, context)
    elif text.startswith("/calc"):
        await calc(update, context)
    elif text.startswith("/close"):
        await close_trade(update, context)
    else:
        await update.message.reply_text(
            "Не понял команду. Используй клавиатуру ниже или /start.",
            reply_markup=build_keyboard(),
        )


def main() -> None:
    if not TOKEN:
        raise RuntimeError("TELEGRAM_BOT_TOKEN is not set")
    application = Application.builder().token(TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("new", new_trade))
    application.add_handler(CommandHandler("active", active))
    application.add_handler(CommandHandler("history", history))
    application.add_handler(CommandHandler("stats", stats))
    application.add_handler(CommandHandler("calc", calc))
    application.add_handler(CommandHandler("export", export))
    application.add_handler(CommandHandler("close", close_trade))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    application.run_polling()


if __name__ == "__main__":
    main()
