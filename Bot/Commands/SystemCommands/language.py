import logging
import os
import re
import asyncio
from Bot.config import Config
from Bot.database import Database
from Bot.Helpers.i18n import I18n
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
	Application, ExtBot, ConversationHandler, CommandHandler, MessageHandler,
	ContextTypes, CallbackContext, CallbackQueryHandler, filters,
	TypeHandler,
)
from telegram.constants import ParseMode
from telegram.error import BadRequest
from Bot.utils import (
	register_user_if_not_exists, get_warning_description, get_ai_commentary,
	timeout, handle_credits, send_long_message, uptodate_query
)
from urllib.parse import urlparse
from pathlib import Path
from datetime import datetime

async def language_handle(update: Update, context: ContextTypes.DEFAULT_TYPE, lang_code: str = None):
	update, context, query, user, query_message = await uptodate_query(update, context)
	if not query_message:
		return

	await register_user_if_not_exists(update, context, user)
	user_id = user.id
	config = Config()
	db = Database()
	i18n = I18n()
	telegram_lang = user.language_code or "en"
	current_lang = db.get_user_language(user_id) or telegram_lang

	if current_lang not in config.available_languages:
		current_lang = "en"

	# await handle_credits(update, context) because language MUST NOT decrement credits
	db.set_user_attribute(user_id, "last_interaction", datetime.now())
	db.increment_command_usage("language", user_id, query.chat_id)

	try:
		args = context.args
		lang_code = args[0].lower() if args else ""

		if not lang_code:
			return

		if lang_code not in config.available_languages:
			await send_long_message(
				i18n.t("LANGUAGE_INVALID", current_lang, languages=", ".join(config.available_languages)),
				parse_mode=ParseMode.MARKDOWN,
				update=update,
				query_message=query_message,
				context=context,
				force_new_message=force_new
			)
			return

		db.set_user_language(user_id, lang_code)
		db.set_user_attribute(user_id, "last_interaction", datetime.now())

		await send_long_message(
			i18n.t("LANGUAGE_CHANGED", lang_code, selected_lang=lang_code.upper()),
			parse_mode=ParseMode.MARKDOWN,
			update=update,
			query_message=query_message,
			context=context,
			force_new_message=force_new
		)

	except Exception as e:
		logger.error(f"LanguageCommand error: {str(e)}")
		await send_long_message(
			i18n.t("LANGUAGE_ERROR_GENERAL", current_lang),
			parse_mode=ParseMode.MARKDOWN,
			update=update,
			query_message=query_message,
			context=context
		)