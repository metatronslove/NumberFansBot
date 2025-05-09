import logging
import os
import re
import asyncio
import urllib
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
from Bot.utils import register_user_if_not_exists, get_warning_description, get_ai_commentary, timeout, handle_credits
from pathlib import Path
from datetime import datetime

async def convert_numbers_handle(update: Update, context: ContextTypes.DEFAULT_TYPE, text: str = None, alt_format: str = None):
	db = Database()
	i18n = I18n()

	# Determine if this is a message or callback query
	if update.message:
		query = update.message
		user = query.from_user
		chat = query.chat
		query_message = query
	elif update.callback_query:
		query = update.callback_query
		user = query.from_user
		chat = query.message.chat
		query_message = query.message
	else:
		logging.error("Invalid update type received")
		return

	await register_user_if_not_exists(update, context, user)
	user_id = user.id
	language = db.get_user_language(user_id)
	await handle_credits(update, context)
	db.set_user_attribute(user_id, "last_interaction", datetime.now())
	db.increment_command_usage("convertnumbers", user_id)

	# If text is not provided (e.g., from message args)
	if text is None:
		args = context.args
		if not args:
			await chat.send_message(
				i18n.t("CONVERTNUMBERS_USAGE", language),
				parse_mode=ParseMode.HTML
			)
			return
		text = " ".join(args[:-1]) if len(args) >= 2 else ""
		alt_format = args[-1].lower() if len(args) > 1 else "indian"

	try:
		converter = NumberConverter()
		available_formats = ["arabic", "indian"]

		if alt_format not in available_formats:
			await chat.send_message(
				i18n.t("ERROR_INVALID_INPUT", language, error=f"Invalid format. Use: {', '.join(available_formats)}"),
				parse_mode=ParseMode.HTML
			)
			return

		result = converter.indian(str(text)) if alt_format == "indian" else converter.arabic(str(text))
		response = i18n.t("CONVERTNUMBERS_RESULT", language, result=result)

		# Add buttons for alternative format
		alt_format_button = "indian" if alt_format == "arabic" else "arabic"
		encoded_text = urllib.parse.quote(text)
		buttons = [[InlineKeyboardButton(
			i18n.t("INDIAN_NUMBERS", language) if alt_format == "arabic" else i18n.t("ARABIC_NUMBERS", language),
			callback_data=f"convertnumbers_{encoded_text}_{alt_format_button}"
		)]]
		reply_markup = InlineKeyboardMarkup(buttons)

		# Send response to the appropriate chat
		if update.callback_query:
			await update.callback_query.message.edit_text(
				response,
				parse_mode=ParseMode.MARKDOWN,
				reply_markup=reply_markup
			)
		else:
			await chat.send_message(
				response,
				parse_mode=ParseMode.MARKDOWN,
				reply_markup=reply_markup
			)

	except ValueError:
		await chat.send_message(
			i18n.t("ERROR_INVALID_INPUT", language, error="Invalid number"),
			parse_mode=ParseMode.HTML
		)
	except Exception as e:
		await chat.send_message(
			i18n.t("ERROR_GENERAL", language, error=str(e)),
			parse_mode=ParseMode.HTML
		)