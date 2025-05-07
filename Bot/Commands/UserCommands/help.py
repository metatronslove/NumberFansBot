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

async def help_handle(update: Update, context: ContextTypes.DEFAULT_TYPE)	:
	user = update.message.from_user
	user_language = user.language_code.split('-')[0] if user.language_code else 'en'
	await register_user_if_not_exists(update, context, user, language=user_language)
	user_id = user.id
	db = Database()
	i18n = I18n()
	language = db.get_user_language(user_id)
	db.set_user_attribute(user_id, "last_interaction", datetime.now())

	db.increment_command_usage("help", user_id)

	buttons = [[InlineKeyboardButton(
		i18n.t("HELP_GROUP_CHAT_USAGE", language),
		callback_data="help_group_chat"
	)]]
	reply_markup = InlineKeyboardMarkup(buttons)

	await update.message.reply_text(
		i18n.t("HELP_MESSAGE", language),
		parse_mode=ParseMode.HTML,
		reply_markup=reply_markup
	)