import logging
import os
import re
import asyncio
from urllib.parse import urlparse
from pathlib import Path
from datetime import datetime
from Bot.config import Config
from Bot.database import Database
from Bot.Helpers.i18n import I18n
from Bot.Helpers.Numerology import UnifiedNumerology
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

def get_method_name(method, language, i18n):
	if method == 'normal':
		return i18n.t("LOGARITHMIC", language)
	elif method == 'inverse':
		return i18n.t("INVERSE_LOGARITHMIC", language)
	elif method == 'base36':
		return i18n.t("BASE_36", language)
	elif method == 'base36_inverse':
		return i18n.t("INVERSE_BASE_36", language)
	elif method == 'base100':
		return i18n.t("BASE_100", language)
	elif method == 'base100_inverse':
		return i18n.t("INVERSE_BASE_100", language)

def get_alphabet_name(alphabet, language, i18n):
	if alphabet == 'arabic_abjadi':
		return i18n.t("ALPHABET_ORDER_ABJADI", language)
	elif alphabet == 'arabic_maghribi':
		return i18n.t("ALPHABET_ORDER_MAGHRIBI", language)
	elif alphabet == 'arabic_hija':
		return i18n.t("ALPHABET_ORDER_HIJA", language)
	elif alphabet == 'arabic_maghribi_hija':
		return i18n.t("ALPHABET_ORDER_MAGHRIBI_HIJA", language)
	elif alphabet == 'hebrew':
		return i18n.t("ALPHABET_ORDER_HEBREW", language)
	elif alphabet == 'english':
		return i18n.t("ALPHABET_ORDER_ENGLISH", language)
	elif alphabet == 'latin':
		return i18n.t("ALPHABET_ORDER_LATIN", language)
	elif alphabet == 'turkish':
		return i18n.t("ALPHABET_ORDER_TURKISH", language)
	elif alphabet == 'ottoman':
		return i18n.t("ALPHABET_ORDER_OTTOMAN", language)

async def numerology_handle(update: Update, context: ContextTypes.DEFAULT_TYPE, alphabet: str = None, method: str = None, text: str = None):
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
	db.increment_command_usage("numerology", user_id, query.chat_id)

	numerology = UnifiedNumerology()
	available_alphabets = ['arabic_abjadi', 'arabic_maghribi', 'arabic_hija', 'arabic_maghribi_hija', 'hebrew', 'english', 'latin', 'turkish', 'ottoman']
	if alphabet is None or alphabet not in numerology.get_available_alphabets():
		args = context.args
		if not args:
			await send_long_message(
				i18n.t("NUMEROLOGY_USAGE", language),
				parse_mode=ParseMode.HTML,
				update=update,
				query_message=query_message,
				context=context
			)
			return
		if text is None:
			text = " ".join(args)
		if len(args) < 2 or args[-1].lower() not in numerology.get_available_alphabets():
			buttons = [
				[InlineKeyboardButton(
					get_alphabet_name(alphabet, language, i18n),
					callback_data=f"numerology_{alphabet}_normal_{encoded_text}"
				)] for alphabet in available_alphabets
			]
			reply_markup = InlineKeyboardMarkup(buttons)
			await send_long_message(
				i18n.t("NUMEROLOGY_PROMPT_ALPHABET", language),
				parse_mode=ParseMode.HTML,
				reply_markup=reply_markup,
				update=update,
				query_message=query_message,
				context=context,
				force_new_message=force_new
			)
			return
		alphabet = args[-1].lower()
	if method is None or method not in numerology.get_available_methods():
		method = args[-2].lower() if len(args) >= 2 and args[-2].lower() in numerology.get_available_methods() else "normal"
	if text is None:
		text = " ".join(args[:-2]) if len(args) >= 2 else text
	encoded_text = urllib.parse.quote(text)
	try:
		if alphabet not in available_alphabets:
			await send_long_message(
				i18n.t("ERROR_INVALID_INPUT", language, error=f"Invalid alphabet. Use: {', '.join(available_alphabets)}"),
				parse_mode=ParseMode.HTML,
				update=update,
				query_message=query_message,
				context=context
			)
			return

		result = numerology.numerolog(text, alphabet=alphabet, method=method, detail=False)
		if isinstance(result, dict) and "error" in result:
			await send_long_message(
				i18n.t("ERROR_INVALID_INPUT", language, error=result["error"]),
				parse_mode=ParseMode.HTML,
				update=update,
				query_message=query_message,
				context=context
			)
			return

		response = i18n.t("NUMEROLOGY_RESULT", language, text=text, alphabet=alphabet, method=method, value=result)

		warning_desc = get_warning_description(result, language)
		if warning_desc:
			response += "\n\n" + i18n.t("WARNING_NUMBER", language, value=result, description=warning_desc)

		commentary = await get_ai_commentary(response, language)
		if commentary:
			response += "\n\n" + i18n.t("AI_COMMENTARY", language, commentary=commentary)

		buttons = [
			[InlineKeyboardButton(
				f"{get_method_name(m, language, i18n)}",
				callback_data=f"numerology_{alphabet}_{m}_{encoded_text}"
			)] for m in numerology.get_available_methods() if m != method
		]
		keyboard = [
			[InlineKeyboardButton(i18n.t("CREATE_MAGIC_SQUARE", language), callback_data=f"magic_square_{value}"),
			InlineKeyboardButton(i18n.t("SPELL_NUMBER", language), callback_data=f"nutket_{value}_{alphabeta}")],
			[InlineKeyboardButton(i18n.t("GENERATE_ENTITY", language), callback_data=f"huddam_cb_{value}"),
			InlineKeyboardButton(i18n.t("CANCEL_BUTTON", language), callback_data="end_conversation_abjad")]
		]
		buttons.append(keyboard)
		reply_markup = InlineKeyboardMarkup(buttons) if buttons else None

		await send_long_message(
			response,
			parse_mode=ParseMode.MARKDOWN,
			reply_markup=reply_markup,
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