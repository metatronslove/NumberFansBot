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
from Bot.transliteration import Transliteration
from Bot.cache import Cache  # Added import
from Bot.utils import register_user_if_not_exists, get_warning_description, get_ai_commentary
from urllib.parse import urlparse
from pathlib import Path
from datetime import datetime

async def transliteration_history_handle(update: Update, context: ContextTypes.DEFAULT_TYPE):
	user = update.message.from_user
	await register_user_if_not_exists(update, context, user)
	user_id = user.id
	db = Database()
	i18n = I18n()
	language = db.get_user_language(user_id)
	db.set_user_attribute(user_id, "last_interaction", datetime.now())

	db.increment_command_usage("transliteration_history", user_id)

	history = db.get_transliteration_history(user_id)
	if not history:
		await update.message.reply_text(
			i18n.t("TRANSLITERATION_HISTORY_RESULT", language, history="No transliteration history found"),
			parse_mode=ParseMode.HTML
		)
		return

	history_str = "\n".join([f"{item['original']} -> {item['transliterated']} ({item['target_lang']})" for item in history])
	response = i18n.t("TRANSLITERATION_HISTORY_RESULT", language, history=history_str)

	await update.message.reply_text(
		response,
		parse_mode=ParseMode.MARKDOWN
	)