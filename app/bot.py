import os
from typing import Optional

from telegram import ReplyKeyboardMarkup, ReplyKeyboardRemove, Update
from telegram.ext import (
    Application,
    CommandHandler,
    ConversationHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from app.calculator import calculate_position_size_usdt
from app.journal import TradeJournal

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
journal = TradeJournal()

TICKER, ENTRY_PRICE, STOP_LOSS, TAKE_PROFIT, COMMENT, CHART = range(6)


def build_keyboard() -> ReplyKeyboardMarkup:
    buttons = [
        ["Новая сделка", "Активные"],
        ["История", "Статистика"],
        ["Калькулятор", "Экспорт"],
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
            "Привет! Я твой торговый журнал. Выбери кнопку или команду:\n\n"
            "Новая сделка, Активные, История, Статистика, Калькулятор, Экспорт"
        ),
        parse_mode="HTML",
        reply_markup=build_keyboard(),
    )


async def new_trade_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text(
        "Открываем новую сделку.\nВведи тикер (например, BTC):",
        reply_markup=ReplyKeyboardRemove(),
    )
    return TICKER


async def new_trade_ticker(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    ticker = update.message.text.strip().upper()
    context.user_data["trade"] = {"ticker": ticker}
    await update.message.reply_text("Хорошо. Введи входную цену:")
    return ENTRY_PRICE


async def new_trade_entry(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    try:
        entry_price = float(update.message.text.strip())
    except ValueError:
        await update.message.reply_text("Пожалуйста, введи число для входной цены.")
        return ENTRY_PRICE

    context.user_data["trade"]["entry_price"] = entry_price
    await update.message.reply_text("Отлично. Введи стоп-лосс:")
    return STOP_LOSS


async def new_trade_stop(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    try:
        stop_loss = float(update.message.text.strip())
    except ValueError:
        await update.message.reply_text("Пожалуйста, введи число для стоп-лосса.")
        return STOP_LOSS

    context.user_data["trade"]["stop_loss"] = stop_loss
    await update.message.reply_text("Теперь введи тейк-профит:")
    return TAKE_PROFIT


async def new_trade_take_profit(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    try:
        take_profit = float(update.message.text.strip())
    except ValueError:
        await update.message.reply_text("Пожалуйста, введи число для тейк-профита.")
        return TAKE_PROFIT

    context.user_data["trade"]["take_profit"] = take_profit
    await update.message.reply_text(
        "Теперь можешь прикрепить график или отправить любое сообщение без фото, чтобы продолжить.",
    )
    return CHART


async def new_trade_chart(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    trade_data = context.user_data.get("trade", {})

    if update.message.photo:
        photo = update.message.photo[-1]
        trade_data["chart_file_id"] = photo.file_id
        await update.message.reply_text("График получен. Теперь введи комментарий к сделке:")
    else:
        await update.message.reply_text("График не добавлен. Введи комментарий к сделке:")

    return COMMENT


async def new_trade_comment(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    comment = update.message.text.strip()
    trade_data = context.user_data.get("trade", {})
    trade_data["comment"] = comment

    record = journal.create_record(
        trade_data["ticker"],
        trade_data["entry_price"],
        trade_data["take_profit"],
        trade_data["stop_loss"],
        trade_data["comment"],
    )
    record.chart_file_id = trade_data.get("chart_file_id")
    journal._save()

    await update.message.reply_text(
        (
            f"✅ <b>Сделка сохранена</b> #{record.id} {record.ticker}\n"
            f"🎯 Вход: {record.entry_price}\n"
            f"🛑 Стоп: {record.stop_loss}\n"
            f"🚀 Тейк: {record.take_profit}\n"
            f"📝 Идея: {record.comment or '-'}"
        ),
        parse_mode="HTML",
        reply_markup=build_keyboard(),
    )
    return ConversationHandler.END


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text(
        "Создание сделки отменено.",
        reply_markup=build_keyboard(),
    )
    return ConversationHandler.END


async def active(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    records = journal.active_records()
    if not records:
        await update.message.reply_text(
            "Нет активных позиций. Нажми 'Новая сделка', чтобы добавить.",
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
    await update.message.reply_text(
        "Используй команду: /calc 100 95 10 100\nПример: /calc 100 95 10 100",
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
    if text == "новая сделка":
        await new_trade_start(update, context)
    elif text == "активные":
        await active(update, context)
    elif text == "история":
        await history(update, context)
    elif text == "статистика":
        await stats(update, context)
    elif text == "калькулятор":
        await calc(update, context)
    elif text == "экспорт":
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

    new_trade_handler = ConversationHandler(
        entry_points=[
            CommandHandler("new", new_trade_start),
            MessageHandler(filters.Regex("^(Новая сделка)$"), new_trade_start),
        ],
        states={
            TICKER: [MessageHandler(filters.TEXT & ~filters.COMMAND, new_trade_ticker)],
            ENTRY_PRICE: [MessageHandler(filters.TEXT & ~filters.COMMAND, new_trade_entry)],
            STOP_LOSS: [MessageHandler(filters.TEXT & ~filters.COMMAND, new_trade_stop)],
            TAKE_PROFIT: [MessageHandler(filters.TEXT & ~filters.COMMAND, new_trade_take_profit)],
            CHART: [MessageHandler(filters.PHOTO | (filters.TEXT & ~filters.COMMAND), new_trade_chart)],
            COMMENT: [MessageHandler(filters.TEXT & ~filters.COMMAND, new_trade_comment)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    application.add_handler(CommandHandler("start", start))
    application.add_handler(new_trade_handler)
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
