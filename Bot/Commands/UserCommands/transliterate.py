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
from Bot.Abjad import Abjad
from Bot.transliteration import Transliteration
from Bot.utils import register_user_if_not_exists, get_warning_description, get_ai_commentary, timeout, handle_credits, send_long_message, uptodate_query
from urllib.parse import urlparse
from pathlib import Path
from datetime import datetime

logger = logging.getLogger(__name__)  # Single logger declaration

async def transliterate_handle(update: Update, context: ContextTypes.DEFAULT_TYPE)	:
	update, context, query, user, query_message = await uptodate_query(update, context)
	if not query_message:
		return

	await register_user_if_not_exists(update, context, user)
	user_id = user.id
	db = Database()
	i18n = I18n()
	language = db.get_user_language(user_id)
	await handle_credits(update, context)
	db.set_user_attribute(user_id, "last_interaction", datetime.now())
	db.increment_command_usage("transliterate", user_id)

	args = context.args
	if len(args) < 3:
		await send_long_message(
			i18n.t("TRANSLITERATION_USAGE", language, source_lang="source_lang", target_lang="target_lang", text="text"),
			parse_mode=ParseMode.HTML,
			update=update,
			query_message=query_message
		)
		return
	source_lang = args[0].lower()
	target_lang = args[1].lower()
	text = " ".join(args[2:])

	try:
		transliteration = Transliteration(db, i18n)
	except Exception as e:
		logger.error(f"Failed to initialize Transliteration: {str(e)}")
		await send_long_message(
			i18n.t("ERROR_GENERAL", language, error="Failed to initialize transliteration system"),
			parse_mode=ParseMode.HTML,
			update=update,
			query_message=query_message
		)
		return

	valid_languages = transliteration.valid_languages

	if source_lang not in valid_languages or target_lang not in valid_languages:
		await send_long_message(
			i18n.t("LANGUAGE_INVALID", language, languages=", ".join(valid_languages)),
			parse_mode=ParseMode.HTML,
			update=update,
			query_message=query_message
		)
		return

	try:
		if language == 'en':
			output_lang = "english"
		elif language == 'tr':
			output_lang = "turkish"
		elif language == 'ar':
			output_lang = "arabic"
		elif language == 'he':
			output_lang = "hebrew"
		elif language == 'la':
			output_lang = "latin"
		result = transliteration.transliterate(text, target_lang, source_lang)
		primary = result["primary"]
		suffix = transliteration.get_suffix(primary, text)
		response = transliteration.format_response(suffix, target_lang, output_lang, language)

		transliteration.store_transliteration(text, source_lang, target_lang, primary, user_id=user_id)

		encoded_text = urllib.parse.quote(text)
		buttons = [
			[
				InlineKeyboardButton(
					i18n.t("SELECT_ALTERNATIVE", language),
					callback_data=f"transliterate_suggest_{source_lang}_{target_lang}_{encoded_text}"
				)
			],
			[
				InlineKeyboardButton(
					i18n.t("TRANSLITERATION_HISTORY_USAGE", language),
					callback_data=f"transliterate_history_{user_id}"
				)
			],
		]
		reply_markup = InlineKeyboardMarkup(buttons)

		await send_long_message(
			response,
			parse_mode=ParseMode.HTML,
			reply_markup=reply_markup,
			update=update,
			query_message=query_message
		)

	except Exception as e:
		logger.error(f"Transliteration error for user {user_id}: {str(e)}")
		await send_long_message(
			i18n.t("ERROR_INVALID_INPUT", language, error=str(e)),
			parse_mode=ParseMode.HTML,
			update=update,
			query_message=query_message
		)