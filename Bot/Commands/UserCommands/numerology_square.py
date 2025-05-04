import logging
import aiohttp
import asyncio
import requests
import re
from Bot.config import Config  # Updated import
from Bot.database import Database
from Bot.i18n import I18n
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler, CallbackQueryHandler,
    ConversationHandler, filters, ContextTypes
)
from telegram.constants import ParseMode
from telegram.error import BadRequest
from Bot.Numerology import UnifiedNumerology
from Bot.MagicSquare import MagicSquareGenerator
from Bot.utils import register_user_if_not_exists, get_warning_description, get_ai_commentary
from datetime import datetime
import urllib.parse

logger = logging.getLogger(__name__)

async def numerology_square_handle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user
    await register_user_if_not_exists(update, context, user)
    user_id = user.id
    db = Database()
    i18n = I18n()
    language = db.get_user_language(user_id)
    db.set_user_attribute(user_id, "last_interaction", datetime.now())

    db.increment_command_usage("numerologysquare", user_id)

    args = context.args
    if len(args) < 1:
        await update.message.reply_text(
            i18n.t("NUMEROLOGYSQUARE_USAGE", language),
            parse_mode=ParseMode.HTML
        )
        return

    alphabet_index = len(args)
    numerology = UnifiedNumerology()
    for i, arg in enumerate(args):
        if arg.lower() in numerology.get_available_alphabets():
            alphabet_index = i
            break

    text = " ".join(args[:alphabet_index]) if alphabet_index > 0 else args[0]
    alphabet = args[alphabet_index].lower() if alphabet_index < len(args) else "turkish"
    method = "normal"

    if alphabet not in numerology.get_available_alphabets():
        await update.message.reply_text(
            i18n.t("ERROR_INVALID_INPUT", language, error="Invalid alphabet"),
            parse_mode=ParseMode.HTML
        )
        return

    try:
        result = numerology.numerolog(text, alphabet=alphabet, method=method, detail=False)
        if isinstance(result, dict) and "error" in result:
            raise ValueError(result["error"])

        magic_square = MagicSquareGenerator()
        square = magic_square.generate(result)
        square_str = "\n".join(["  ".join(map(str, row)) for row in square])

        response = i18n.t("NUMEROLOGYSQUARE_RESULT", language, text=text, alphabet=alphabet, square=square_str)

        commentary = await get_ai_commentary(response, language)
        if commentary:
            response += "\n\n" + i18n.t("AI_COMMENTARY", language, commentary=commentary)

        encoded_text = urllib.parse.quote(text)
        buttons = [
            [InlineKeyboardButton(f"Alphabet: {a}", callback_data=f"numerologysquare_{encoded_text}_{a}")]
            for a in numerology.get_available_alphabets() if a != alphabet
        ]
        reply_markup = InlineKeyboardMarkup(buttons) if buttons else None

        await update.message.reply_text(
            response,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=reply_markup
        )
    except Exception as e:
        await update.message.reply_text(
            i18n.t("ERROR_INVALID_INPUT", language, error=str(e)),
            parse_mode=ParseMode.HTML
        )