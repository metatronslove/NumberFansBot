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
from Bot.MagicSquare import MagicSquareGenerator
from Bot.utils import register_user_if_not_exists, get_warning_description, get_ai_commentary, timeout, handle_credits
from urllib.parse import urlparse
from pathlib import Path
from datetime import datetime

logger = logging.getLogger(__name__)

async def magic_square_handle(update: Update, context: ContextTypes.DEFAULT_TYPE, number: int = None):
	user = update.message.from_user
	await register_user_if_not_exists(update, context, user)
	user_id = user.id
	db = Database()
	i18n = I18n()
	language = db.get_user_language(user_id)
	handle_credits(update, context)
	db.set_user_attribute(user_id, "last_interaction", datetime.now())
	db.increment_command_usage("magicsquare", user_id)

	args = context.args
	if not args and number is None:
		await update.message.reply_text(
			i18n.t("MAGICSQUARE_USAGE", language),
			parse_mode=ParseMode.HTML
		)
	return

	if number is None:
		row_sum = int(args[0])

	try:
		if row_sum < 15:
			await update.message.reply_text(
				i18n.t("ERROR_INVALID_INPUT", language, error="Row sum must be at least 15"),
				parse_mode=ParseMode.HTML
			)
			return
		magic_square = MagicSquareGenerator()
		square = magic_square.generate_magic_square(3, row_sum, 0, False, 'arabic')
		response = i18n.t("MAGICSQUARE_RESULT", language, number=row_sum, square=square["box"])

		commentary = await get_ai_commentary(response, language)
		if commentary:
			response += "\n\n" + i18n.t("AI_COMMENTARY", language, commentary=commentary)

		buttons = [
			[InlineKeyboardButton(
				i18n.t("CREATE_INDIAN_MAGIC_SQUARE", language),
				callback_data=f"indian_square_{row_sum}"
			)],
			[InlineKeyboardButton(
				i18n.t("NEXT_SIZE", language),
				callback_data=f"next_size_{row_sum}_{square['size']}_arabic"
			)]
		]
		reply_markup = InlineKeyboardMarkup(buttons)
		await update.message.reply_text(
			response,
			parse_mode=ParseMode.MARKDOWN,
			reply_markup=reply_markup
		)
	except ValueError:
		await update.message.reply_text(
			i18n.t("ERROR_INVALID_INPUT", language, error="Invalid row sum"),
			parse_mode=ParseMode.HTML
		)
	except Exception as e:
		await update.message.reply_text(
			i18n.t("ERROR_GENERAL", language, error=str(e)),
			parse_mode=ParseMode.HTML
		)