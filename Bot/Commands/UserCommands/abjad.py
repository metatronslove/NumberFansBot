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
import re

logger = logging.getLogger(__name__)

# Conversation states
ALPHABET_ORDER, ABJAD_TYPE, SHADDA, DETAIL = range(4)

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

async def abjad_start(update: Update, context: CallbackContext):
    user = update.message.from_user
    await register_user_if_not_exists(update, context, user)
    user_id = user.id
    db = Database()
    i18n = I18n()
    language = db.get_user_language(user_id)

    args = context.args
    if not args:
        await update.message.reply_text(
            i18n.t("ABJAD_USAGE", language),
            parse_mode=ParseMode.MARKDOWN
        )
        return ConversationHandler.END

    text = " ".join(args)
    context.user_data["abjad_text"] = text

    # Check if text is Arabic (U+0600–U+06FF)
    is_arabic = bool(re.search(r'[\u0600-\u06FF]', text))

    # Prompt for Alphabet Order
    keyboard = [
        [InlineKeyboardButton(lang.capitalize(), callback_data=lang)]
        for lang in ["arabic", "hebrew", "turkish", "english", "latin"]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        i18n.t("ABJAD_PROMPT_ALPHABET", language),
        reply_markup=reply_markup
    )
    context.user_data["is_arabic"] = is_arabic
    return ALPHABET_ORDER

async def abjad_alphabet_order(update: Update, context: CallbackContext):
    query = update.callback_query
    user_id = query.from_user.id
    db = Database()
    i18n = I18n()
    language = db.get_user_language(user_id)

    alphabet_order = query.data
    context.user_data["alphabet_order"] = alphabet_order

    # Prompt for Abjad Type
    keyboard = [
        [InlineKeyboardButton(typ.capitalize(), callback_data=typ)]
        for typ in ["standard", "reduced"]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.message.reply_text(
        i18n.t("ABJAD_PROMPT_TYPE", language),
        reply_markup=reply_markup
    )
    await query.answer()
    return ABJAD_TYPE

async def abjad_type(update: Update, context: CallbackContext):
    query = update.callback_query
    user_id = query.from_user.id
    db = Database()
    i18n = I18n()
    language = db.get_user_language(user_id)

    abjad_type = query.data
    context.user_data["abjad_type"] = abjad_type

    # Prompt for Shadda if Arabic text
    if context.user_data.get("is_arabic"):
        keyboard = [
            [InlineKeyboardButton("1 (Include)", callback_data="1")],
            [InlineKeyboardButton("2 (Exclude)", callback_data="2")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.message.reply_text(
            i18n.t("ABJAD_PROMPT_SHADDA", language),
            reply_markup=reply_markup
        )
        await query.answer()
        return SHADDA
    else:
        context.user_data["shadda"] = 1
        return await abjad_shadda(update, context)

async def abjad_shadda(update: Update, context: CallbackContext):
    query = update.callback_query
    user_id = query.from_user.id
    db = Database()
    i18n = I18n()
    language = db.get_user_language(user_id)

    if query:
        shadda = int(query.data)
        context.user_data["shadda"] = shadda
        await query.answer()
    else:
        shadda = context.user_data.get("shadda", 1)

    # Prompt for Detail
    keyboard = [
        [InlineKeyboardButton("0 (No Details)", callback_data="0")],
        [InlineKeyboardButton("1 (Show Details)", callback_data="1")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await (query.message.reply_text if query else update.message.reply_text)(
        i18n.t("ABJAD_PROMPT_DETAIL", language),
        reply_markup=reply_markup
    )
    return DETAIL

async def abjad_detail(update: Update, context: CallbackContext):
    query = update.callback_query
    user_id = query.from_user.id
    db = Database()
    i18n = I18n()
    language = db.get_user_language(user_id)
    db.set_user_attribute(user_id, "last_interaction", datetime.now())
    db.increment_command_usage("abjad", user_id)

    try:
        detail = int(query.data)
        context.user_data["detail"] = detail

        text = context.user_data["abjad_text"]
        alphabet_order = context.user_data["alphabet_order"]
        abjad_type = context.user_data["abjad_type"]
        shadda = context.user_data["shadda"]

        abjad = Abjad()
        result = abjad.abjad(
            text,
            tablo=1 if abjad_type == "standard" else 2,
            shadda=shadda,
            detail=detail,
            lang=alphabet_order
        )

        if isinstance(result, str) and result.startswith("Error"):
            await query.message.reply_text(
                i18n.t("ERROR_GENERAL", language, error=result),
                parse_mode=ParseMode.MARKDOWN
            )
            await query.answer()
            return ConversationHandler.END

        value = result["sum"] if isinstance(result, dict) else result
        details = result.get("details", "") if isinstance(result, dict) and detail == 1 else ""

        response = i18n.t("ABJAD_RESULT", language, text=text, value=value)
        if details:
            response += "\n" + i18n.t("ABJAD_DETAILS", language, details=details)

        # Check warningNumbers.json when detail=0
        if detail == 0:
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
            callback_data=f"nutket_{value}_{alphabet_order}"
        )])
        if details:
            keyboard.append([InlineKeyboardButton(
                i18n.t("SHOW_DETAILS", language),
                callback_data=f"abjad_details_{user_id}"
            )])
        reply_markup = InlineKeyboardMarkup(keyboard)

        await query.message.reply_text(
            response,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=reply_markup
        )
        context.user_data["abjad_result"] = result

        await query.answer()
        return ConversationHandler.END

    except Exception as e:
        logger.error(f"Abjad error: {str(e)}")
        await query.message.reply_text(
            i18n.t("ERROR_GENERAL", language),
            parse_mode=ParseMode.MARKDOWN
        )
        await query.answer()
        return ConversationHandler.END

async def abjad_cancel(update: Update, context: CallbackContext):
    user_id = update.message.from_user.id
    db = Database()
    i18n = I18n()
    language = db.get_user_language(user_id)
    await update.message.reply_text(
        i18n.t("ABJAD_CANCEL", language),
        parse_mode=ParseMode.MARKDOWN
    )
    return ConversationHandler.END

def get_abjad_conversation_handler():
    return ConversationHandler(
        entry_points=[CommandHandler("abjad", abjad_start)],
        states={
            ALPHABET_ORDER: [CallbackQueryHandler(abjad_alphabet_order)],
            ABJAD_TYPE: [CallbackQueryHandler(abjad_type)],
            SHADDA: [CallbackQueryHandler(abjad_shadda)],
            DETAIL: [CallbackQueryHandler(abjad_detail)],
        },
        fallbacks=[CommandHandler("cancel", abjad_cancel)],
    )