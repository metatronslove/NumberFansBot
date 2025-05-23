import logging
import requests
import re
import urllib
from datetime import datetime
from Bot.config import Config
from Bot.database import Database
from Bot.Helpers.i18n import I18n
from Bot.Helpers.Abjad import Abjad
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

logger = logging.getLogger(__name__)

async def nutket_handle(update: Update, context: ContextTypes.DEFAULT_TYPE, number: int = None, nutket_lang: str = None):
	update, context, query, user, query_message = await uptodate_query(update, context)
	if not query_message:
		return

	await register_user_if_not_exists(update, context, user)
	user_id = user.id
	db = Database()
	i18n = I18n()
	language = db.get_user_language(user_id)
	await handle_credits(update, context)
	db.set_user_attribute(user_id, "last_interaction", datetime.now())
	db.increment_command_usage("nutket", user_id, query.chat_id)

	try:
		if update.message:
			args = context.args
			if not args or not args[0].isdigit():
				await send_long_message(
					i18n.t("NUTKET_USAGE", language),
					parse_mode=ParseMode.MARKDOWN,
					update=update,
					query_message=query_message,
					context=context
				)
				return
			number = int(args[0])
			nutket_lang = args[-1].lower() if len(args) > 1 and args[-1].lower() in ["arabic", "hebrew", "turkish", "english", "latin"] else language

		if not number:
			await send_long_message(
				i18n.t("ERROR_INVALID_INPUT", language, error="Number is required"),
				parse_mode=ParseMode.MARKDOWN,
				update=update,
				query_message=query_message,
				context=context
			)
			return

		lang_map = {
			"ar": "ARABIC",
			"he": "HEBREW",
			"tr": "TURKISH",
			"en": "ENGLISH",
			"la": "LATIN"
		}
		abjad_lang = lang_map.get(nutket_lang.upper(), "ENGLISH")
		abjad = Abjad()
		spelled = abjad.nutket(number, abjad_lang)

		if spelled.startswith("Error"):
			await send_long_message(
				i18n.t("ERROR_GENERAL", language, error=spelled),
				parse_mode=ParseMode.MARKDOWN,
				update=update,
				query_message=query_message,
				context=context
			)
			return

		response = i18n.t("NUTKET_RESULT", language, number=number, nutket_lang=nutket_lang, spelled=spelled)

		commentary = await get_ai_commentary(response, language)
		if commentary:
			response += "\n\n" + i18n.t("AI_COMMENTARY", language, commentary=commentary)

		keyboard = []
		if number >= 15:
			keyboard.append([InlineKeyboardButton(
				i18n.t("CREATE_MAGIC_SQUARE", language),
				callback_data=f"magic_square_{number}"
			)])
		keyboard.append([InlineKeyboardButton(
			i18n.t("CALCULATE_ABJAD", language),
			callback_data=f"abjad_text_{spelled}"
		)])
		reply_markup = InlineKeyboardMarkup(keyboard)

		await send_long_message(
			response,
			parse_mode=ParseMode.MARKDOWN,
			reply_markup=reply_markup,
			update=update,
			query_message=query_message,
			context=context
		)
		if update.callback_query:
			await update.callback_query.answer()

	except Exception as e:
		logger.error(f"Nutket error: {str(e)}")
		await send_long_message(
			i18n.t("ERROR_GENERAL", language, error=str(e)),
			parse_mode=ParseMode.MARKDOWN,
			update=update,
			query_message=query_message,
			context=context
		)
		if update.callback_query:
			await update.callback_query.answer()