import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler, CallbackQueryHandler,
    ConversationHandler, filters
)
from telegram.constants import ParseMode
from ...database import Database
from ...i18n import I18n
from ...config import config
from ...Abjad import Abjad
from datetime import datetime
from ...utils import get_warning_description  # Import helper
import requests

logger = logging.getLogger(__name__)

# Conversation states
REPETITION, TABLE, LANGUAGE = range(3)

async def register_user_if_not_exists(update: Update, context: CallbackContext, user):
    db = Database()
    if not db.check_if_user_exists(user.id):
        db.add_new_user(
            user_id=user.id,
            chat_id=update.message.chat_id,
            username=user.username or "",
            first_name=user.first_name or "",
            last_name=user.last_name or "",
        )

async def get_ai_commentary(response: str, lang: str) -> str:
    i18n = I18n()
    prompt = i18n.t("AI_PROMPT", lang, response=response)
    try:
        headers = {"Authorization": f"Bearer {config.huggingface_access_token}"}
        payload = {
            "inputs": prompt,
            "parameters": {"max_length": 200, "temperature": 0.7}
        }
        response = requests.post(
            config.ai_model_url,
            headers=headers,
            json=payload
        )
        if response.status_code == 200:
            return response.json()[0]["generated_text"].split("[/INST]")[-1].strip()
        else:
            logger.error(f"AI API error: {response.status_code}")
            return ""
    except Exception as e:
        logger.error(f"AI commentary error: {str(e)}")
        return ""

async def bastet_start(update: Update, context: CallbackContext):
    user = update.message.from_user
    await register_user_if_not_exists(update, context, user)
    user_id = user.id
    db = Database()
    i18n = I18n()
    language = db.get_user_language(user_id)

    args = context.args
    if not args or not args[0].isdigit():
        await update.message.reply_text(
            i18n.t("BASTET_USAGE", language),
            parse_mode=ParseMode.MARKDOWN
        )
        return ConversationHandler.END

    number = int(args[0])
    context.user_data["bastet_number"] = number

    # Prompt for Repetition Amount
    await update.message.reply_text(
        i18n.t("BASTET_PROMPT_REPETITION", language)
    )
    return REPETITION

async def bastet_repetition(update: Update, context: CallbackContext):
    user_id = update.message.from_user.id
    db = Database()
    i18n = I18n()
    language = db.get_user_language(user_id)

    repetition = update.message.text
    if not repetition.isdigit() or int(repetition) < 1:
        await update.message.reply_text(
            i18n.t("ERROR_INVALID_INPUT", language, error="Repetition must be a positive integer")
        )
        return REPETITION

    context.user_data["repetition"] = int(repetition)

    # Prompt for Table (0-35)
    keyboard = [
        [InlineKeyboardButton(str(i), callback_data=str(i)) for i in range(j, min(j + 6, 36))]
        for j in range(0, 36, 6)
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        i18n.t("BASTET_PROMPT_TABLE", language),
        reply_markup=reply_markup
    )
    return TABLE

async def bastet_table(update: Update, context: CallbackContext):
    query = update.callback_query
    user_id = query.from_user.id
    db = Database()
    i18n = I18n()
    language = db.get_user_language(user_id)

    table = int(query.data)
    context.user_data["table"] = table

    # Prompt for Language
    keyboard = [
        [InlineKeyboardButton(lang.capitalize(), callback_data=lang)]
        for lang in ["arabic", "hebrew", "turkish", "english", "latin"]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.message.reply_text(
        i18n.t("BASTET_PROMPT_LANGUAGE", language),
        reply_markup=reply_markup
    )
    await query.answer()
    return LANGUAGE

async def bastet_language(update: Update, context: CallbackContext):
    query = update.callback_query
    user_id = query.from_user.id
    db = Database()
    i18n = I18n()
    language = db.get_user_language(user_id)
    db.set_user_attribute(user_id, "last_interaction", datetime.now())
    db.increment_command_usage("bastet", user_id)

    try:
        lang = query.data
        context.user_data["language"] = lang

        number = context.user_data["bastet_number"]
        repetition = context.user_data["repetition"]
        table = context.user_data["table"]

        abjad = Abjad()
        value = number
        for _ in range(repetition):
            result = abjad.abjad(str(value), tablo=table, shadda=1, detail=0, lang=lang)
            value = result["sum"] if isinstance(result, dict) else result

        if isinstance(value, str) and value.startswith("Error"):
            await query.message.reply_text(
                i18n.t("ERROR_GENERAL", language, error=value),
                parse_mode=ParseMode.MARKDOWN
            )
            await query.answer()
            return ConversationHandler.END

        response = i18n.t("BASTET_RESULT", language, number=number, repetition=repetition, table=table, value=value)

        # Check warningNumbers.json
        warning_desc = get_warning_description(value, language)
        if warning_desc:
            response += "\n\n" + i18n.t("WARNING_NUMBER", language, value=value, description=warning_desc)

        # Get AI commentary
        commentary = await get_ai_commentary(response, language)
        if commentary:
            response += "\n\n" + i18n.t("AI_COMMENTARY", language, commentary=commentary)

        # Add buttons
        keyboard = []
        if value >= 15:
            keyboard.append([InlineKeyboardButton(
                i18n.t("CREATE_MAGIC_SQUARE", language),
                callback_data=f"magic_square_{value}"
            )])
        keyboard.append([InlineKeyboardButton(
            i18n.t("SPELL_NUMBER", language),
            callback_data=f"nutket_{value}_{lang}"
        )])
        reply_markup = InlineKeyboardMarkup(keyboard)

        await query.message.reply_text(
            response,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=reply_markup
        )
        await query.answer()
        return ConversationHandler.END

    except Exception as e:
        logger.error(f"Bastet error: {str(e)}")
        await query.message.reply_text(
            i18n.t("ERROR_GENERAL", language),
            parse_mode=ParseMode.MARKDOWN
        )
        await query.answer()
        return ConversationHandler.END

async def bastet_cancel(update: Update, context: CallbackContext):
    user_id = update.message.from_user.id
    db = Database()
    i18n = I18n()
    language = db.get_user_language(user_id)
    await update.message.reply_text(
        i18n.t("BASTET_CANCEL", language),
        parse_mode=ParseMode.MARKDOWN
    )
    return ConversationHandler.END

def get_bastet_conversation_handler():
    return ConversationHandler(
        entry_points=[CommandHandler("bastet", bastet_start)],
        states={
            REPETITION: [MessageHandler(filters.TEXT & ~filters.COMMAND, bastet_repetition)],
            TABLE: [CallbackQueryHandler(bastet_table)],
            LANGUAGE: [CallbackQueryHandler(bastet_language)],
        },
        fallbacks=[CommandHandler("cancel", bastet_cancel)],
    )