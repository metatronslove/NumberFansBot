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
from Bot.Helpers.Transliteration import Transliteration
from Bot.utils import (
	register_user_if_not_exists, get_warning_description, get_ai_commentary,
	timeout, handle_credits, send_long_message, uptodate_query
)
from urllib.parse import urlparse
from pathlib import Path
from datetime import datetime

async def settings_handle(update: Update, context: ContextTypes.DEFAULT_TYPE)	:
	update, context, query, user, query_message = await uptodate_query(update, context)
	if not query_message:
		return

	await register_user_if_not_exists(update, context, user)
	user_id = user.id
	db = Database()
	i18n = I18n()
	language = db.get_user_language(user_id)
	# await handle_credits(update, context) because settings MUST NOT decrement credits
	db.set_user_attribute(user_id, "last_interaction", datetime.now())
	db.increment_command_usage("settings", user_id, query.chat_id)

	transliteration = Transliteration(db, i18n)
	valid_languages = transliteration.valid_languages

	buttons = [
		[InlineKeyboardButton(f"Lang: {lang.upper()}", callback_data=f"settings_lang_{lang}")]
		for lang in valid_languages
	]
	reply_markup = InlineKeyboardMarkup(buttons)

	await send_long_message(
		i18n.t("SETTINGS_USAGE", language),
		parse_mode=ParseMode.HTML,
		reply_markup=reply_markup,
		update=update,
		query_message=query_message,
		context=context,
		force_new_message=True
	)