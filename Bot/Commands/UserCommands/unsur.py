import logging
import re
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler, CallbackQueryHandler,
    ConversationHandler, filters, ContextTypes
)
from telegram.constants import ParseMode
from ...database import Database
from ...i18n import I18n
from ...element_classifier import ElementClassifier
from ...utils import register_user_if_not_exists, get_ai_commentary
from datetime import datetime

logger = logging.getLogger(__name__)

INPUT, LANGUAGE, TABLE, SHADDA = range(4)

async def unsur_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user
    await register_user_if_not_exists(update, context, user)
    user_id = user.id
    db = Database()
    i18n = I18n()
    language = db.get_user_language(user_id)

    await update.message.reply_text(
        i18n.t("UNSUR_PROMPT_INPUT", language),
        parse_mode=ParseMode.MARKDOWN
    )
    return INPUT

async def unsur_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    db = Database()
    i18n = I18n()
    language = db.get_user_language(user_id)

    input_text = update.message.text.strip()
    if not input_text:
        await update.message.reply_text(
            i18n.t("ERROR_INVALID_INPUT", language, error="Input is required"),
            parse_mode=ParseMode.MARKDOWN
        )
        return INPUT

    context.user_data["input_text"] = input_text
    is_arabic = bool(re.search(r'[\u0600-\u06FF]', input_text))
    context.user_data["is_arabic"] = is_arabic

    keyboard = [
        [InlineKeyboardButton(i18n.t("ALPHABET_ORDER_TURKISH", language), callback_data="unsur_lang_TURKCE")],
        [InlineKeyboardButton(i18n.t("ALPHABET_ORDER_ARABI", language), callback_data="unsur_lang_ARABI")],
        [InlineKeyboardButton(i18n.t("ALPHABET_ORDER_BUNI", language), callback_data="unsur_lang_BUNI")],
        [InlineKeyboardButton(i18n.t("ALPHABET_ORDER_HUSEYNI", language), callback_data="unsur_lang_HUSEYNI")],
        [InlineKeyboardButton(i18n.t("ALPHABET_ORDER_HEBREW", language), callback_data="unsur_lang_HEBREW")],
        [InlineKeyboardButton(i18n.t("ALPHABET_ORDER_ENGLISH", language), callback_data="unsur_lang_ENGLISH")],
        [InlineKeyboardButton(i18n.t("ALPHABET_ORDER_LATIN", language), callback_data="unsur_lang_LATIN")],
        [InlineKeyboardButton(i18n.t("ALPHABET_ORDER_DEFAULT", language), callback_data="unsur_lang_DEFAULT")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        i18n.t("UNSUR_PROMPT_LANGUAGE", language),
        reply_markup=reply_markup
    )
    return LANGUAGE

async def unsur_language(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    db = Database()
    i18n = I18n()
    language = db.get_user_language(user_id)

    if not query.data.startswith("unsur_lang_"):
        logger.debug(f"Ignoring unrelated callback in unsur_language: {query.data}")
        return LANGUAGE
    lang = query.data.split("unsur_lang_")[1]
    context.user_data["language"] = lang

    keyboard = [
        [InlineKeyboardButton(i18n.t("ELEMENT_FIRE", language), callback_data="unsur_table_fire")],
        [InlineKeyboardButton(i18n.t("ELEMENT_WATER", language), callback_data="unsur_table_water")],
        [InlineKeyboardButton(i18n.t("ELEMENT_AIR", language), callback_data="unsur_table_air")],
        [InlineKeyboardButton(i18n.t("ELEMENT_EARTH", language), callback_data="unsur_table_earth")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.message.reply_text(
        i18n.t("UNSUR_PROMPT_TABLE", language),
        reply_markup=reply_markup
    )
    await query.answer()
    return TABLE

async def unsur_table(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    db = Database()
    i18n = I18n()
    language = db.get_user_language(user_id)

    if not query.data.startswith("unsur_table_"):
        logger.debug(f"Ignoring unrelated callback in unsur_table: {query.data}")
        return TABLE
    table = query.data.split("unsur_table_")[1]
    context.user_data["table"] = table

    if context.user_data.get("is_arabic"):
        keyboard = [
            [InlineKeyboardButton(i18n.t("SHADDA_USE_ONCE", language), callback_data="unsur_shadda_1")],
            [InlineKeyboardButton(i18n.t("SHADDA_USE_TWICE", language), callback_data="unsur_shadda_2")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.message.reply_text(
            i18n.t("UNSUR_PROMPT_SHADDA", language),
            reply_markup=reply_markup
        )
		await query.answer()
        return SHADDA
    else:
        context.user_data["shadda"] = 1
        return await unsur_shadda(update, context)

async def unsur_shadda(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id if query else update.message.from_user.id
    db = Database()
    i18n = I18n()
    language = db.get_user_language(user_id)
    db.set_user_attribute(user_id, "last_interaction", datetime.now())
    db.increment_command_usage("unsur", user_id)

    try:
        if query:
            if not query.data.startswith("unsur_shadda_"):
                logger.debug(f"Ignoring unrelated callback in unsur_shadda: {query.data}")
                return SHADDA
            shadda = int(query.data.split("unsur_shadda_")[1])
            context.user_data["shadda"] = shadda
            await query.answer()

        else:
            shadda = context.user_data.get("shadda", 1)

        input_text = context.user_data["input_text"]
        lang = context.user_data["language"]
        table = context.user_data["table"]

        unsur = ElementClassifier()
        result = unsur.classify_elements(input_text, table, shadda, lang)
        if isinstance(result, str) and result.startswith("Error"):
            await (query.message.reply_text if query else update.message.reply_text)(
                i18n.t("ERROR_GENERAL", language, error=result),
                parse_mode=ParseMode.MARKDOWN
            )
            context.user_data.clear()
            return ConversationHandler.END

        value = result["adet"]
        liste = result["liste"]
        elements = {
            'fire': i18n.t("ELEMENT_FIRE", language),
            'water': i18n.t("ELEMENT_WATER", language),
            'air': i18n.t("ELEMENT_AIR", language),
            'earth': i18n.t("ELEMENT_EARTH", language)
        }
        element = elements.get(table, i18n.t("ELEMENT_UNKNOWN", language))

        response = i18n.t("UNSUR_RESULT", language, input=input_text, liste=liste, value=value, element=element)

        commentary = await get_ai_commentary(response, language)
        if commentary:
            response += "\n\n" + i18n.t("AI_COMMENTARY", language, commentary=commentary)

        keyboard = []
        if value >= 15:
            keyboard.append([InlineKeyboardButton(
                i18n.t("CREATE_MAGIC_SQUARE", language),
                callback_data=f"magic_square_{value}"
            )])
            keyboard.append([InlineKeyboardButton(
                i18n.t("CREATE_INDIAN_MAGIC_SQUARE", language),
                callback_data=f"indian_square_{value}"
            )])
        keyboard.append([InlineKeyboardButton(
            i18n.t("SPELL_NUMBER", language),
            callback_data=f"nutket_{value}_{lang}"
        )])
        if not input_text.replace(" ", "").isdigit():
            keyboard.append([InlineKeyboardButton(
                i18n.t("CALCULATE_ABJAD", language),
                callback_data=f"abjad_text_{input_text}_{lang}"
            )])
        reply_markup = InlineKeyboardMarkup(keyboard)

        await (query.message.reply_text if query else update.message.reply_text)(
            response,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=reply_markup
        )
        context.user_data.clear()
        return ConversationHandler.END

    except Exception as e:
        logger.error(f"Unsur error: {str(e)}")
        await (query.message.reply_text if query else update.message.reply_text)(
            i18n.t("ERROR_GENERAL", language),
            parse_mode=ParseMode.MARKDOWN
        )
        context.user_data.clear()
        return ConversationHandler.END

async def unsur_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    db = Database()
    i18n = I18n()
    language = db.get_user_language(user_id)
    await update.message.reply_text(
        i18n.t("UNSUR_CANCEL", language),
        parse_mode=ParseMode.MARKDOWN
    )
    context.user_data.clear()
    return ConversationHandler.END

def get_unsur_conversation_handler():
    return ConversationHandler(
        entry_points=[CommandHandler("unsur", unsur_start)],
        states={
            INPUT: [MessageHandler(filters.TEXT & ~filters.COMMAND, unsur_input)],
            LANGUAGE: [CallbackQueryHandler(unsur_language, pattern=r"^unsur_lang_")],
            TABLE: [CallbackQueryHandler(unsur_table, pattern=r"^unsur_table_")],
            SHADDA: [CallbackQueryHandler(unsur_shadda, pattern=r"^unsur_shadda_")],
        },
        fallbacks=[CommandHandler("cancel", unsur_cancel)],
        per_message=False,
        allow_reentry=False
    )