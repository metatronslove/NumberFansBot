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

async def help_group_chat_handle(update: Update, context: ContextTypes.DEFAULT_TYPE)	:
	user = update.message.from_user
	await register_user_if_not_exists(update, context, user)
	user_id = user.id
	db = Database()
	i18n = I18n()
	language = db.get_user_language(user_id)
	db.set_user_attribute(user_id, "last_interaction", datetime.now())

	# Increment command usage
	db.increment_command_usage("help_group_chat", user_id)

	try:
		await update.message.reply_video(
			video=open("Static/help_group_chat.mp4", "rb"),
			caption=i18n.t("HELP_GROUP_CHAT_USAGE", language),
			parse_mode=ParseMode.HTML
		)
	except Exception as e:
		await update.message.reply_text(
			i18n.t("ERROR_GENERAL", language, error="Failed to send help video"),
			parse_mode=ParseMode.HTML
		)