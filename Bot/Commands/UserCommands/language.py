import logging
import os
import re
import asyncio
from Bot.config import Config
from Bot.database import Database
from Bot.i18n import I18n
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
	Application, CommandHandler, MessageHandler, CallbackQueryHandler,
	ConversationHandler, filters, ContextTypes
)
from telegram.constants import ParseMode
from telegram.error import BadRequest
from Bot.utils import register_user_if_not_exists, get_warning_description, get_ai_commentary, timeout
from urllib.parse import urlparse
from pathlib import Path
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

	if current_lang not in config.available_languages:
		current_lang = "en"

	db.increment_command_usage("language", user_id)

	try:
		args = context.args
		lang_code = args[0].lower() if args else ""

		if not lang_code:
			return

		if lang_code not in config.available_languages:
			await update.message.reply_text(
				i18n.t("LANGUAGE_INVALID", current_lang, languages=", ".join(config.available_languages)),
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