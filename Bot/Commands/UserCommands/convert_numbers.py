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
from Bot.NumberConverter import NumberConverter
from Bot.utils import register_user_if_not_exists, get_warning_description, get_ai_commentary, timeout
from urllib.parse import urlparse
from pathlib import Path
from datetime import datetime

async def convert_numbers_handle(update: Update, context: ContextTypes.DEFAULT_TYPE)	:
	user = update.message.from_user
	await register_user_if_not_exists(update, context, user)
	user_id = user.id
	db = Database()
	i18n = I18n()
	language = db.get_user_language(user_id)
	db.set_user_attribute(user_id, "last_interaction", datetime.now())

	# Increment command usage
	db.increment_command_usage("convertnumbers", user_id)

	args = context.args
	if len(args) < 1:
		await update.message.reply_text(
			i18n.t("CONVERTNUMBERS_USAGE", language),
			parse_mode=ParseMode.HTML
		)
		return

	try:
		number = int(args[0])
		format_type = args[1].lower() if len(args) > 1 else "indian"
		converter = NumberConverter()
		available_formats = ["arabic", "indian"]

		if format_type not in available_formats:
			await update.message.reply_text(
				i18n.t("ERROR_INVALID_INPUT", language, error=f"Invalid format. Use: {', '.join(available_formats)}"),
				parse_mode=ParseMode.HTML
			)
			return

		result = converter.arabic(str(number)) if format_type == "arabic" else converter.indian(str(number))
		response = i18n.t("CONVERTNUMBERS_RESULT", language, number=number, format=format_type, result=result)

		# Add buttons for alternative format
		alt_format = "indian" if format_type == "arabic" else "arabic"
		buttons = [[InlineKeyboardButton(
			f"Format: {alt_format.capitalize()}",
			callback_data=f"convertnumbers_{number}_{alt_format}"
		)]]
		reply_markup = InlineKeyboardMarkup(buttons)

		await update.message.reply_text(
			response,
			parse_mode=ParseMode.MARKDOWN,
			reply_markup=reply_markup
		)
	except ValueError:
		await update.message.reply_text(
			i18n.t("ERROR_INVALID_INPUT", language, error="Invalid number"),
			parse_mode=ParseMode.HTML
		)
	except Exception as e:
		await update.message.reply_text(
			i18n.t("ERROR_GENERAL", language, error=str(e)),
			parse_mode=ParseMode.HTML
		)