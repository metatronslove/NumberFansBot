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
from Bot.utils import register_user_if_not_exists, get_warning_description, get_ai_commentary, timeout
from urllib.parse import urlparse
from pathlib import Path
from datetime import datetime
from Bot.transliteration import Transliteration
from Bot.cache import Cache  # Added import

logger = logging.getLogger(__name__)

async def suggest_transliteration_handle(update: Update, context: ContextTypes.DEFAULT_TYPE)	:
	user = update.message.from_user
	await register_user_if_not_exists(update, context, user)
	user_id = user.id
	db = Database()
	i18n = I18n()
	language = db.get_user_language(user_id)
	db.set_user_attribute(user_id, "last_interaction", datetime.now())

	db.increment_command_usage("suggest_transliteration", user_id)

	args = context.args
	if len(args) < 1:
		await update.message.reply_text(
			i18n.t("SUGGEST_TRANSLITERATION_USAGE", language),
			parse_mode=ParseMode.HTML
		)
		return

	text = " ".join(args[:-2]) if len(args) > 2 else args[0]
	source_lang = args[-2].lower() if len(args) >= 2 else None
	target_lang = args[-1].lower() if len(args) >= 1 else "english"

	transliteration = Transliteration(db, i18n)
	valid_languages = transliteration.valid_languages

	if target_lang not in valid_languages:
		await update.message.reply_text(
			i18n.t("ERROR_INVALID_INPUT", language, error=f"Invalid target language. Use: {', '.join(valid_languages)}"),
			parse_mode=ParseMode.HTML
		)
		return

	try:
		source_lang = source_lang or transliteration.guess_source_lang(text)
		if source_lang not in valid_languages:
			await update.message.reply_text(
				i18n.t("ERROR_INVALID_INPUT", language, error=f"Invalid source language: {source_lang}"),
				parse_mode=ParseMode.HTML
			)
			return

		suggestions = transliteration.suggest_transliterations(text, source_lang, target_lang)
		if not suggestions:
			await update.message.reply_text(
				i18n.t("SUGGEST_TRANSLITERATION_RESULT", language, text=text, source_lang=source_lang, target_lang=target_lang, results="No suggestions available"),
				parse_mode=ParseMode.HTML
			)
			return

		# Store suggestions in cache
		cache = Cache()
		alternatives = [{"transliterated_name": s, "suffix": transliteration.get_suffix(s, text)} for s in suggestions]
		cache_id = cache.store_alternatives(user_id, source_lang, target_lang, text, alternatives)

		results = ", ".join(transliteration.get_suffix(s, text) for s in suggestions)
		response = i18n.t("SUGGEST_TRANSLITERATION_RESULT", language, text=text, source_lang=source_lang, target_lang=target_lang, results=results)

		buttons = [
			[InlineKeyboardButton(transliteration.get_suffix(s, text), callback_data=f"name_alt_{cache_id}_{i}")]
			for i, s in enumerate(suggestions)
		]
		reply_markup = InlineKeyboardMarkup(buttons) if buttons else None

		await update.message.reply_text(
			response,
			parse_mode=ParseMode.MARKDOWN,
			reply_markup=reply_markup
		)
	except Exception as e:
		logger.error(f"Suggest transliteration error: {str(e)}")
		await update.message.reply_text(
			i18n.t("ERROR_INVALID_INPUT", language, error=str(e)),
			parse_mode=ParseMode.HTML
		)