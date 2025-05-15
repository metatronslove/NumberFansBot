import logging
from telegram.ext import Application, InlineQueryHandler, ContextTypes
from telegram import Update, InlineQueryResultArticle, InputTextMessageContent
from Bot.InlineCommands import (
    abjad, bastet, nutket, unsur, huddam, magic_square,
    transliterate, convert_numbers, numerology
)
from Bot.config import Config
from Bot.database import Database
from Bot.Helpers.i18n import I18n
from Bot.utils import register_user_if_not_exists
from datetime import datetime

logger = logging.getLogger(__name__)

async def inline_query(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.inline_query.query
    user = update.inline_query.from_user
    logger.info(f"Processing inline query '{query}' from user {user.id if user else 'unknown'}")

    try:
        config = Config()
        db = Database()
        i18n = I18n()
        user_id = user.id if user else 0
        language = db.get_user_language(user_id) if user_id else "en"
        await register_user_if_not_exists(update, context, user)

        if user_id:
            db.set_user_attribute(user_id, "last_interaction", datetime.now())
            db.increment_command_usage("inline", user_id)

        results = []

        # Split query into command and text
        parts = query.strip().split(" ", 1)
        command = parts[0].lower() if parts else ""
        text = parts[1] if len(parts) > 1 else ""

        # Handle empty query
        if not command:
            results.append(
                InlineQueryResultArticle(
                    id="help",
                    title=i18n.t("INLINE_HELP_TITLE", language),
                    description=i18n.t("INLINE_HELP_DESC", language),
                    input_message_content=InputTextMessageContent(
                        i18n.t("INLINE_HELP_MESSAGE", language),
                        parse_mode="Markdown"
                    )
                )
            )
            await update.inline_query.answer(results)
            return

        # Map commands to handlers
        handlers = {
            "abjad": abjad.handle,
            "bastet": bastet.handle,
            "nutket": nutket.handle,
            "unsur": unsur.handle,
            "huddam": huddam.handle,
            "magic_square": magic_square.handle,
            "transliterate": transliterate.handle,
            "convert_numbers": convert_numbers.handle,
            "numerology": numerology.handle
        }

        if command in handlers:
            results = await handlers[command](update, context, text, language)
        else:
            results.append(
                InlineQueryResultArticle(
                    id="unknown",
                    title=i18n.t("UNKNOWN_COMMAND_TITLE", language),
                    description=i18n.t("UNKNOWN_COMMAND_DESC", language, command=command),
                    input_message_content=InputTextMessageContent(
                        i18n.t("UNKNOWN_COMMAND_MESSAGE", language, command=command),
                        parse_mode="Markdown"
                    )
                )
            )

        # Limit results to 50 per Telegram API
        if len(results) > 50:
            results = results[:50]
            logger.warning(f"Truncated results to 50 for query '{query}'")

        await update.inline_query.answer(results, cache_time=10)

    except Exception as e:
        logger.error(f"Error in inline_query: {str(e)}")
        results.append(
            InlineQueryResultArticle(
                id="error",
                title=i18n.t("ERROR_TITLE", language),
                description=i18n.t("ERROR_DESC", language, error=str(e)),
                input_message_content=InputTextMessageContent(
                    i18n.t("ERROR_GENERAL", language, error=str(e)),
                    parse_mode="Markdown"
                )
            )
        )
        await update.inline_query.answer(results)

def get_inline_handler():
    try:
        handler = InlineQueryHandler(inline_query)
        logger.info("Inline query handler initialized successfully")
        return handler
    except Exception as e:
        logger.error(f"Failed to initialize inline query handler: {str(e)}")
        raise