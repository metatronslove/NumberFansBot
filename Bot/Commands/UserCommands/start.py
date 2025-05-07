import logging
import re
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
# import asyncio
from Bot.Abjad import Abjad
from Bot.utils import register_user_if_not_exists, get_warning_description, get_ai_commentary, timeout
from urllib.parse import urlparse
from pathlib import Path
from datetime import datetime
import os
from .language import language_handle

logger = logging.getLogger(__name__)

async def start_handle(update: Update, context: CallbackContext)	:
	user = update.message.from_user
	user_language = user.language_code.split('-')[0] if user.language_code else 'en'
	await register_user_if_not_exists(update, context, user, language=user_language)
	user_id = user.id
	db = Database()
	i18n = I18n()

	try:
		if user_language in ['en', 'tr', 'ar', 'he', 'la']:
			language = user_language
			context.args = [language]
			await language_handle(update, context)
		else:
			language = 'en'
			db.set_user_language(user_id, language)

		db.set_user_attribute(user_id, "last_interaction", datetime.now())
		db.increment_command_usage("start", user_id)
		remaining_credits = db.get_user_credits(user_id)

		reply_text = i18n.t("START_MESSAGE", language, remaining_credits=remaining_credits)
		reply_text += "\n" + i18n.t("HELP_MESSAGE", language)
		await update.message.reply_text(reply_text, parse_mode=ParseMode.HTML)
	except Exception as e:
		logger.error(f"StartCommand error: {str(e)}")
		await update.message.reply_text(
			i18n.t("ERROR_GENERAL", language, error=str(e)),
			parse_mode=ParseMode.HTML
		)