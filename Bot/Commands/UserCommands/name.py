import logging
import os
import re
import asyncio
from Bot.config import Config
from Bot.database import Database
from Bot.i18n import I18n
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
	Application, ExtBot, ConversationHandler, CommandHandler, MessageHandler,
	ContextTypes, CallbackContext, CallbackQueryHandler, filters,
	TypeHandler,
)
from telegram.constants import ParseMode
from telegram.error import BadRequest
from Bot.transliteration import Transliteration
from Bot.utils import register_user_if_not_exists, get_warning_description, get_ai_commentary, timeout, handle_credits
from urllib.parse import urlparse
from pathlib import Path
from datetime import datetime

logger = logging.getLogger(__name__)

def get_language_name(lang, language, i18n):
	if lang == 'turkish':
		return i18n.t("LANGUAGE_NAME_TR", language)
	elif lang == 'english':
		return i18n.t("LANGUAGE_NAME_EN", language)
	elif lang == 'latin':
		return i18n.t("LANGUAGE_NAME_LA", language)
	elif lang == 'hebrew':
		return i18n.t("LANGUAGE_NAME_HE", language)
	elif lang == 'arabic':
		return i18n.t("LANGUAGE_NAME_AR", language)

async def name_handle(update: Update, context: ContextTypes.DEFAULT_TYPE, prefix: str = None, target_lang: str = None, name: str = None):
	# Determine if this is a message or callback query
	if update.message:
		query = update.message
		user = query.from_user
		chat = query.chat
	elif update.callback_query:
		query = update.callback_query
		user = query.from_user
		chat = query.message.chat
	else:
		logging.error("Invalid update type received")
		return

	await register_user_if_not_exists(update, context, user)
	user_id = user.id
	db = Database()
	i18n = I18n()
	language = db.get_user_language(user_id)
	await handle_credits(update, context)
	db.set_user_attribute(user_id, "last_interaction", datetime.now())
	db.increment_command_usage("name", user_id)

	if prefix is None:
		args = context.args
		if len(args) < 1:
			await update.message.reply_text(
				i18n.t("NAME_USAGE", language),
				parse_mode=ParseMode.HTML
			)
			return

		prefix = " ".join(args[:-1]) if len(args) > 1 else args[0]
		target_lang = args[-1].lower() if len(args) >= 1 else "english"

		transliteration = Transliteration(db, i18n)
		valid_languages = transliteration.valid_languages

		if target_lang not in valid_languages:
			await update.message.reply_text(
				i18n.t("ERROR_INVALID_INPUT", language, error=f"Invalid language. Use: {', '.join(valid_languages)}"),
				parse_mode=ParseMode.HTML
			)
			return

	try:
		source_lang = transliteration.guess_source_lang(prefix)
		result = transliteration.transliterate(prefix, target_lang, source_lang)
		name = result["primary"]
		response = i18n.t("NAME_RESULT", language, prefix=prefix, type="modern", method="simple", name=name)

		commentary = await get_ai_commentary(response, language)
		if commentary:
			response += "\n\n" + i18n.t("AI_COMMENTARY", language, commentary=commentary)

		encoded_prefix = urllib.parse.quote(prefix)
		buttons = [
			[InlineKeyboardButton(
				f"{get_language_name(lang, language, i18n)}",
				callback_data=f"name_alt_{encoded_prefix}_{lang}_{urllib.parse.quote(name)}"
			)] for lang in valid_languages if lang != target_lang
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