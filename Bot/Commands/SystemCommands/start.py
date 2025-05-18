import logging
import re
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
import asyncio
from Bot.utils import (
	register_user_if_not_exists, get_warning_description, get_ai_commentary,
	timeout, handle_credits, send_long_message, uptodate_query
)
from urllib.parse import urlparse
from pathlib import Path
from datetime import datetime
import os
from .language import language_handle

logger = logging.getLogger(__name__)

async def start_handle(update: Update, context: ContextTypes.DEFAULT_TYPE)	:
	update, context, query, user, query_message = await uptodate_query(update, context)
	if not query_message:
		return

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
		db.increment_command_usage("start", user_id, query.chat_id)
		remaining_credits = db.get_user_credits(user_id)

		reply_text = i18n.t("START_MESSAGE", language, remaining_credits=remaining_credits)
		reply_text += "\n" + i18n.t("HELP_MESSAGE", language)
		await send_long_message(reply_text, parse_mode=ParseMode.HTML, update=update, query_message=query_message,	context=context, force_new_message=True)
	except Exception as e:
		logger.error(f"StartCommand error: {str(e)}")
		await send_long_message(
			i18n.t("ERROR_GENERAL", language, error=str(e)),
			parse_mode=ParseMode.HTML,
			update=update,
			query_message=query_message,
			context=context
		)