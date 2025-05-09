import logging
import requests
import re
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
from Bot.Abjad import Abjad
from Bot.bot import register_user_if_not_exists, get_warning_description, get_ai_commentary, timeout, handle_credits
from urllib.parse import urlparse
from datetime import datetime

logger = logging.getLogger(__name__)

async def nutket_handle(update: Update, context: ContextTypes.DEFAULT_TYPE, number: int = None, lang: str = None):
	user = update.message.from_user if update.message else update.callback_query.from_user
	chat_id = update.message.chat_id if update.message else update.callback_query.message.chat_id
	await register_user_if_not_exists(update, context, user)
	user_id = user.id
	db = Database()
	i18n = I18n()
	language = lang or db.get_user_language(user_id)
	await handle_credits(update, context)
	db.set_user_attribute(user_id, "last_interaction", datetime.now())
	db.increment_command_usage("nutket", user_id)

	try:
		if update.message:
			args = context.args
			if not args or not args[0].isdigit():
				await update.message.reply_text(
					i18n.t("NUTKET_USAGE", language),
					parse_mode=ParseMode.MARKDOWN
				)
				return
			number = int(args[0])
			lang = args[-1].lower() if len(args) > 1 and args[-1].lower() in ["arabic", "hebrew", "turkish", "english", "latin"] else language

		if not number:
			await (update.message.reply_text if update.message else update.callback_query.message.reply_text)(
				i18n.t("ERROR_INVALID_INPUT", language, error="Number is required"),
				parse_mode=ParseMode.MARKDOWN
			)
			return

		lang_map = {
			"ar": "ARABIC",
			"he": "HEBREW",
			"tr": "TURKISH",
			"en": "ENGLISH",
			"la": "LATIN"
		}
		abjad_lang = lang_map.get(lang.upper(), "ENGLISH")
		abjad = Abjad()
		spelled = abjad.nutket(number, abjad_lang)

		if spelled.startswith("Error"):
			await (update.message.reply_text if update.message else update.callback_query.message.reply_text)(
				i18n.t("ERROR_GENERAL", language, error=spelled),
				parse_mode=ParseMode.MARKDOWN
			)
			return

		response = i18n.t("NUTKET_RESULT", language, number=number, lang=lang, spelled=spelled)

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
			callback_data=f"abjad_text_{spelled}_{lang}"
		)])
		reply_markup = InlineKeyboardMarkup(keyboard)

		await (update.message.reply_text if update.message else update.callback_query.message.reply_text)(
			response,
			parse_mode=ParseMode.MARKDOWN,
			reply_markup=reply_markup
		)
		if update.callback_query:
			await update.callback_query.answer()

	except Exception as e:
		logger.error(f"Nutket error: {str(e)}")
		await (update.message.reply_text if update.message else update.callback_query.message.reply_text)(
			i18n.t("ERROR_GENERAL", language, error=str(e)),
			parse_mode=ParseMode.MARKDOWN
		)
		if update.callback_query:
			await update.callback_query.answer()