import logging
import os
import re
import asyncio
import urllib
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
from Bot.NumberConverter import NumberConverter
from Bot.utils import (
	register_user_if_not_exists, get_warning_description, get_ai_commentary,
	timeout, handle_credits, send_long_message, uptodate_query
)
from pathlib import Path
from datetime import datetime

async def convert_numbers_handle(update: Update, context: ContextTypes.DEFAULT_TYPE, text: str = None, alt_format: str = None):
	db = Database()
	i18n = I18n()

	update, context, query, user, query_message = await uptodate_query(update, context)
	if not query_message:
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
			await send_long_message(
				i18n.t("CONVERTNUMBERS_USAGE", language),
				parse_mode=ParseMode.HTML,
				update=update,
				query_message=query_message,
				context=context
			)
			return
		if len(args) > 1:
			if args[-1].lower() == "arabic":
				if len(args) >= 2:
					text = " ".join(args[:-1])
				else:
					text = ""
				alt_format = "arabic"
			elif args[-1].lower() == "indian":
				if len(args) >= 2:
					text = " ".join(args[:-1])
				else:
					text = ""
				alt_format = "indian"
			else:
				if len(args) >= 2:
					text = " ".join(args)
				else:
					text = ""
				alt_format = "invert"

	try:
		converter = NumberConverter()
		available_formats = ["arabic", "indian", "invert"]

		if alt_format not in available_formats:
			await send_long_message(
				i18n.t("ERROR_INVALID_INPUT", language, error=f"Invalid format. Use: {', '.join(available_formats)}"),
				parse_mode=ParseMode.HTML,
				update=update,
				query_message=query_message,
				context=context
			)
			return

		if alt_format == "invert":
			result = converter.invert(str(text))
		elif alt_format == "arabic":
			result = converter.arabic(str(text))
		elif alt_format == "indian":
			result = converter.indian(str(text))
		response = i18n.t("CONVERTNUMBERS_RESULT", language, result=result)

		# Add buttons for alternative format
		buttons = [];
		encoded_text = urllib.parse.quote(text)
		if alt_format in ["invert", "arabic"]:
			buttons.append([InlineKeyboardButton(
				i18n.t("INDIAN_NUMBERS", language),
				callback_data=f"convertnumbers_{encoded_text}_indian"
			)])
		if alt_format in ["invert", "indian"]:
			buttons.append([InlineKeyboardButton(
				i18n.t("ARABIC_NUMBERS", language),
				callback_data=f"convertnumbers_{encoded_text}_arabic"
			)])
		reply_markup = InlineKeyboardMarkup(buttons)

		# Send response to the appropriate chat
		if update.callback_query:
			await update.callback_query.message.edit_text(
				response,
				parse_mode=ParseMode.MARKDOWN,
				reply_markup=reply_markup,
				update=update,
				query_message=query_message,
				context=context
			)
		else:
			await send_long_message(
				response,
				parse_mode=ParseMode.MARKDOWN,
				reply_markup=reply_markup,
				update=update,
				query_message=query_message,
				context=context,
				force_new_message=force_new
			)

	except ValueError:
		await send_long_message(
			i18n.t("ERROR_INVALID_INPUT", language, error="Invalid number"),
			parse_mode=ParseMode.HTML,
			update=update,
			query_message=query_message,
			context=context
		)
	except Exception as e:
		await send_long_message(
			i18n.t("ERROR_GENERAL", language, error=str(e)),
			parse_mode=ParseMode.HTML,
			update=update,
			query_message=query_message,
			context=context
		)