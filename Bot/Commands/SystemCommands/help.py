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

async def help_handle(update: Update, context: ContextTypes.DEFAULT_TYPE)	:
	update, context, query, user, query_message = await uptodate_query(update, context)
	if not query_message:
		return

	user_language = user.language_code.split('-')[0] if user.language_code else 'en'
	await register_user_if_not_exists(update, context, user, language=user_language)
	user_id = user.id
	db = Database()
	i18n = I18n()
	language = db.get_user_language(user_id)
	# await handle_credits(update, context) because help MUST NOT decrement credits
	db.set_user_attribute(user_id, "last_interaction", datetime.now())
	db.increment_command_usage("help", user_id)

	buttons = [[InlineKeyboardButton(
		i18n.t("HELP_GROUP_CHAT_USAGE", language),
		callback_data="help_group_chat"
	)]]
	reply_markup = InlineKeyboardMarkup(buttons)

	await send_long_message(
		i18n.t("HELP_MESSAGE", language),
		parse_mode=ParseMode.HTML,
		reply_markup=reply_markup,
		update=update,
		query_message=query_message,
		context=context,
		force_new_message=force_new
	)