from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler, CallbackQueryHandler,
    ConversationHandler, filters, ContextTypes
)
from telegram.constants import ParseMode
from telegram.error import BadRequest
from Bot.config import Config  # Updated import
from Bot.database import Database
from Bot.i18n import I18n
from Bot.utils import register_user_if_not_exists
from datetime import datetime

async def language_handle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user
    await register_user_if_not_exists(update, context, user)
    user_id = user.id
    config = Config()
    db = Database()
    i18n = I18n()
    telegram_lang = user.language_code or "en"
    current_lang = db.get_user_language(user_id) or telegram_lang

    if current_lang not in configavailable_languages:
        current_lang = "en"

    db.increment_command_usage("language", user_id)

    try:
        args = context.args
        lang_code = args[0].lower() if args else ""

        if not lang_code:
            await show_language_selection(update, current_lang)
            return

        if lang_code not in configavailable_languages:
            await update.message.reply_text(
                i18n.t("LANGUAGE_INVALID", current_lang, languages=", ".join(configavailable_languages)),
                parse_mode=ParseMode.MARKDOWN
            )
            return

        db.set_user_language(user_id, lang_code)
        db.set_user_attribute(user_id, "last_interaction", datetime.now())

        await update.message.reply_text(
            i18n.t("LANGUAGE_CHANGED", lang_code, selected_lang=lang_code.upper()),
            parse_mode=ParseMode.MARKDOWN
        )

    except Exception as e:
        logger.error(f"LanguageCommand error: {str(e)}")
        await update.message.reply_text(
            i18n.t("LANGUAGE_ERROR_GENERAL", current_lang),
            parse_mode=ParseMode.MARKDOWN
        )

async def show_language_selection(update: Update, current_lang: str):
    # Implementation unchanged
    pass