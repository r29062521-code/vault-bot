import asyncio
import os
import logging
from telegram import (
    Update, InlineKeyboardButton, InlineKeyboardMarkup,
    ReplyKeyboardMarkup, KeyboardButton
)
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    CallbackQueryHandler, ContextTypes, filters
)

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

BOT_TOKEN = os.getenv("BOT_TOKEN", "8702310063:AAEeFYzvq2IcHHXya-0Ik-3qTQ7ILJWi38I")

# ID оператора — замени на свой Telegram user ID (узнать: @userinfobot)
OPERATOR_ID = int(os.getenv("OPERATOR_ID", "8780910726"))

# Храним язык пользователя: {user_id: "ru" | "en"}
user_lang: dict[int, str] = {}

# Храним тикеты: {operator_msg_id: user_id} для ответов оператора
tickets: dict[int, int] = {}

# ─── Тексты ──────────────────────────────────────────────────────────────────

WELCOME = {
    "ru": (
        "👋 *Добро пожаловать в Core Liquidity Lab Support!*\n\n"
        "Этот бот саппорт находится на нашем сайте внутри нашего проекта.\n\n"
        "📌 *Что мы можем помочь:*\n"
        "• Депозиты и вывод средств\n"
        "• APY и распределение наград\n"
        "• Технические вопросы\n"
        "• Проблемы с транзакциями\n\n"
        "Выберите действие ниже 👇"
    ),
    "en": (
        "👋 *Welcome to Core Liquidity Lab Support!*\n\n"
        "This support bot is located on our website inside our project.\n\n"
        "📌 *How we can help:*\n"
        "• Deposits and withdrawals\n"
        "• APY and reward distribution\n"
        "• Technical questions\n"
        "• Transaction issues\n\n"
        "Choose an action below 👇"
    ),
}

FAQ = {
    "ru": [
        ("💰 Как сделать депозит?", (
            "📥 *Как сделать депозит в Core Liquidity Lab*\n\n"
            "1. Откройте приложение и подключите кошелёк\n"
            "2. Перейдите на страницу Vault\n"
            "3. Выберите сумму USDC для депозита\n"
            "4. Нажмите *Deposit* и подтвердите транзакцию в кошельке\n\n"
            "⚡ Средства начинают работать сразу после подтверждения блока.\n\n"
            "Если возникли проблемы — напишите нам, оператор ответит в ближайшее время."
        )),
        ("📤 Как вывести средства?", (
            "📤 *Как вывести средства из Core Liquidity Lab*\n\n"
            "1. Подключите кошелёк с которым делали депозит\n"
            "2. Перейдите на страницу Vault\n"
            "3. Нажмите *Withdraw* и укажите сумму\n"
            "4. Подтвердите транзакцию в кошельке\n\n"
            "⏱ Вывод обрабатывается мгновенно.\n"
            "🔸 Убедитесь, что на балансе есть ETH для оплаты газа.\n\n"
            "Остались вопросы? Напишите нам 👇"
        )),
        ("📊 Откуда берётся APY?", (
            "📊 *Откуда берётся APY в Core Liquidity Lab*\n\n"
            "Доходность формируется из двух источников:\n\n"
            "🔹 *Base APY* — доходность от предоставления ликвидности USDC на Aave/Compound\n"
            "🔸 *ARB Rewards* — дополнительные награды в токенах ARB от протокола Arbitrum\n\n"
            "Итоговый APY отображается на главной странице и обновляется каждый час.\n\n"
            "Если у вас вопросы по расчёту — спросите оператора 👇"
        )),
        ("🔒 Безопасность протокола", (
            "🔒 *Безопасность Core Liquidity Lab*\n\n"
            "Протокол прошёл аудиты от:\n"
            "• *Certora* — формальная верификация смарт-контрактов\n"
            "• *Oxorio* — полный аудит безопасности\n\n"
            "🛡 Средства хранятся в смарт-контракте без возможности управления командой.\n"
            "📄 Исходный код открыт и верифицирован на Arbiscan.\n\n"
            "Дополнительные вопросы по безопасности? Напишите нам 👇"
        )),
        ("⛽ Проблемы с газом / транзакцией", (
            "⛽ *Проблемы с транзакцией*\n\n"
            "Частые причины:\n\n"
            "1. *Недостаточно ETH* для оплаты газа — пополните баланс ETH в сети Arbitrum\n"
            "2. *Слишком низкий gas limit* — увеличьте в настройках кошелька\n"
            "3. *Stuck transaction* — попробуйте отменить или ускорить в кошельке\n\n"
            "Если проблема остаётся — напишите нам хеш транзакции и опишите ситуацию 👇"
        )),
    ],
    "en": [
        ("💰 How to deposit?", (
            "📥 *How to deposit into Core Liquidity Lab*\n\n"
            "1. Open the app and connect your wallet\n"
            "2. Navigate to the Vault page\n"
            "3. Enter the USDC amount you want to deposit\n"
            "4. Click *Deposit* and confirm the transaction in your wallet\n\n"
            "⚡ Funds start earning immediately after block confirmation.\n\n"
            "If you encounter any issues — message us and an operator will respond shortly."
        )),
        ("📤 How to withdraw?", (
            "📤 *How to withdraw from Core Liquidity Lab*\n\n"
            "1. Connect the same wallet you used for deposit\n"
            "2. Navigate to the Vault page\n"
            "3. Click *Withdraw* and enter the amount\n"
            "4. Confirm the transaction in your wallet\n\n"
            "⏱ Withdrawals are processed instantly.\n"
            "🔸 Make sure you have ETH for gas fees.\n\n"
            "Still have questions? Message us below 👇"
        )),
        ("📊 Where does APY come from?", (
            "📊 *Where does APY come from in Core Liquidity Lab*\n\n"
            "Yield is generated from two sources:\n\n"
            "🔹 *Base APY* — yield from providing USDC liquidity on Aave/Compound\n"
            "🔸 *ARB Rewards* — additional ARB token rewards from the Arbitrum protocol\n\n"
            "The total APY is displayed on the main page and updated every hour.\n\n"
            "Questions about calculations? Ask an operator below 👇"
        )),
        ("🔒 Protocol security", (
            "🔒 *Core Liquidity Lab Security*\n\n"
            "The protocol has been audited by:\n"
            "• *Certora* — formal verification of smart contracts\n"
            "• *Oxorio* — full security audit\n\n"
            "🛡 Funds are stored in a smart contract with no team control.\n"
            "📄 Source code is open and verified on Arbiscan.\n\n"
            "More security questions? Message us below 👇"
        )),
        ("⛽ Gas / transaction issues", (
            "⛽ *Transaction Issues*\n\n"
            "Common causes:\n\n"
            "1. *Not enough ETH* for gas — top up your ETH balance on Arbitrum\n"
            "2. *Gas limit too low* — increase it in your wallet settings\n"
            "3. *Stuck transaction* — try to cancel or speed up in your wallet\n\n"
            "If the issue persists — send us the transaction hash and describe the situation 👇"
        )),
    ],
}

LABELS = {
    "ru": {
        "faq": "❓ Частые вопросы",
        "contact": "💬 Написать оператору",
        "back": "◀️ Назад",
        "lang": "🌐 English",
        "app": "🚀 Открыть приложение",
        "docs": "📄 Документация",
        "ask_prompt": (
            "✍️ *Напишите ваш вопрос* — оператор ответит в ближайшее время.\n\n"
            "Среднее время ответа: *до 30 минут*"
        ),
        "msg_sent": "✅ Ваше сообщение отправлено. Оператор ответит вам в ближайшее время.",
        "operator_note": "📩 *Новый вопрос от пользователя*",
        "op_reply": "💬 *Ответ оператора:*\n\n",
    },
    "en": {
        "faq": "❓ FAQ",
        "contact": "💬 Contact operator",
        "back": "◀️ Back",
        "lang": "🌐 Русский",
        "app": "🚀 Open App",
        "docs": "📄 Documentation",
        "ask_prompt": (
            "✍️ *Write your question* — an operator will respond shortly.\n\n"
            "Average response time: *up to 30 minutes*"
        ),
        "msg_sent": "✅ Your message has been sent. An operator will reply shortly.",
        "operator_note": "📩 *New question from user*",
        "op_reply": "💬 *Operator reply:*\n\n",
    },
}

# ─── Клавиатуры ──────────────────────────────────────────────────────────────

def main_keyboard(lang: str) -> InlineKeyboardMarkup:
    L = LABELS[lang]
    other = "en" if lang == "ru" else "ru"
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(L["faq"],     callback_data="faq")],
        [InlineKeyboardButton(L["contact"], callback_data="contact")],
        [
            InlineKeyboardButton(L["app"],  url="https://coreliquiditylab.com"),
            InlineKeyboardButton(L["docs"], url="https://coreliquiditylab.com/docs"),
        ],
        [InlineKeyboardButton(L["lang"],    callback_data=f"lang_{other}")],
    ])

def faq_keyboard(lang: str) -> InlineKeyboardMarkup:
    rows = []
    for label, _ in FAQ[lang]:
        idx = FAQ[lang].index((label, _))
        rows.append([InlineKeyboardButton(label, callback_data=f"faq_{idx}")])
    rows.append([InlineKeyboardButton(LABELS[lang]["back"], callback_data="main")])
    return InlineKeyboardMarkup(rows)

def back_keyboard(lang: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(LABELS[lang]["back"], callback_data="faq")],
        [InlineKeyboardButton(LABELS[lang]["contact"], callback_data="contact")],
    ])

# ─── Хендлеры ────────────────────────────────────────────────────────────────

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    lang = user_lang.get(user.id, "ru")

    await update.message.reply_text(
        WELCOME[lang],
        parse_mode="Markdown",
        reply_markup=main_keyboard(lang),
    )


async def button(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    lang = user_lang.get(user_id, "ru")
    data = query.data

    # Смена языка
    if data.startswith("lang_"):
        new_lang = data.split("_")[1]
        user_lang[user_id] = new_lang
        lang = new_lang
        await query.edit_message_text(
            WELCOME[lang],
            parse_mode="Markdown",
            reply_markup=main_keyboard(lang),
        )
        return

    # Главное меню
    if data == "main":
        await query.edit_message_text(
            WELCOME[lang],
            parse_mode="Markdown",
            reply_markup=main_keyboard(lang),
        )
        return

    # Список FAQ
    if data == "faq":
        await query.edit_message_text(
            "❓ *FAQ* — выберите тему:" if lang == "ru" else "❓ *FAQ* — choose a topic:",
            parse_mode="Markdown",
            reply_markup=faq_keyboard(lang),
        )
        return

    # Конкретный FAQ
    if data.startswith("faq_"):
        idx = int(data.split("_")[1])
        _, text = FAQ[lang][idx]
        await query.edit_message_text(
            text,
            parse_mode="Markdown",
            reply_markup=back_keyboard(lang),
        )
        return

    # Написать оператору
    if data == "contact":
        context.user_data["awaiting_message"] = True
        await query.edit_message_text(
            LABELS[lang]["ask_prompt"],
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton(LABELS[lang]["back"], callback_data="main")]
            ]),
        )
        return


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    lang = user_lang.get(user.id, "ru")
    text = update.message.text

    # Если ждём вопрос от пользователя
    if context.user_data.get("awaiting_message"):
        context.user_data["awaiting_message"] = False

        # Уведомляем оператора
        if OPERATOR_ID:
            op_text = (
                f"{LABELS[lang]['operator_note']}\n\n"
                f"👤 *От:* [{user.full_name}](tg://user?id={user.id})\n"
                f"🆔 ID: `{user.id}`\n"
                f"🌐 Язык: {'🇷🇺 RU' if lang == 'ru' else '🇬🇧 EN'}\n\n"
                f"💬 *Вопрос:*\n{text}"
            )
            sent = await context.bot.send_message(
                chat_id=OPERATOR_ID,
                text=op_text,
                parse_mode="Markdown",
            )
            # Запоминаем чтобы оператор мог ответить реплаем
            tickets[sent.message_id] = user.id

        await update.message.reply_text(
            LABELS[lang]["msg_sent"],
            reply_markup=main_keyboard(lang),
        )
        return

    # Если это оператор отвечает реплаем на тикет
    if user.id == OPERATOR_ID and update.message.reply_to_message:
        replied_id = update.message.reply_to_message.message_id
        target_user_id = tickets.get(replied_id)
        if target_user_id:
            target_lang = user_lang.get(target_user_id, "ru")
            await context.bot.send_message(
                chat_id=target_user_id,
                text=LABELS[target_lang]["op_reply"] + text,
                parse_mode="Markdown",
                reply_markup=main_keyboard(target_lang),
            )
            await update.message.reply_text("✅ Ответ отправлен пользователю.")
            return

    # Обычное сообщение — показываем меню
    await update.message.reply_text(
        WELCOME[lang],
        parse_mode="Markdown",
        reply_markup=main_keyboard(lang),
    )


async def main() -> None:
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    logger.info("Bot started.")
    async with app:
        await app.start()
        await app.updater.start_polling(allowed_updates=Update.ALL_TYPES)
        # Keep running until interrupted
        await asyncio.Event().wait()


if __name__ == "__main__":
    asyncio.run(main())
