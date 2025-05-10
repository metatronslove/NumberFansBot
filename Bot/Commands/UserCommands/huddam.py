import logging
import requests
import re
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
from Bot.Abjad import Abjad
from Bot.utils import register_user_if_not_exists, get_warning_description, get_ai_commentary, timeout, handle_credits, send_long_message, uptodate_query
from datetime import datetime

logger = logging.getLogger(__name__)

ENTITY_TYPE, LANGUAGE, MULTIPLIAR = range(3)

async def huddam_start(update: Update, context: ContextTypes.DEFAULT_TYPE, number: int = None):
	logger.info(f"Starting /huddam for user {update.effective_user.id}")
	try:
		# Determine if this is a message or callback query
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
		db.increment_command_usage("huddam", user_id)

		args = context.args
		if number is None:
			if not args or not args[0].isdigit():
				await send_long_message(
					i18n.t("HUDDAM_USAGE", language),
					parse_mode=ParseMode.MARKDOWN,
					update=update,
					query_message=query_message
				)
				return ConversationHandler.END
			number = int(args[0])
		context.user_data["huddam_number"] = number

		keyboard = [
			[InlineKeyboardButton(i18n.t("HUDDAM_HIGH", language), callback_data="huddam_entity_ulvi"),
			InlineKeyboardButton(i18n.t("HUDDAM_LOW", language), callback_data="huddam_entity_sufli")],
			[InlineKeyboardButton(i18n.t("HUDDAM_BAD", language), callback_data="huddam_entity_ser"),
			InlineKeyboardButton(i18n.t("CANCEL_BUTTON", language), callback_data="end_conversation")],
		]
		reply_markup = InlineKeyboardMarkup(keyboard)
		await send_long_message(
			i18n.t("HUDDAM_PROMPT_ENTITY_TYPE", language),
			reply_markup=reply_markup,
			update=update,
			query_message=query_message
		)
		return ENTITY_TYPE
	except Exception as e:
		logger.error(f"Error in huddam_start: {str(e)}")
		await send_long_message(
			i18n.t("ERROR_GENERAL", language, error=str(e)),
			parse_mode=ParseMode.MARKDOWN,
			update=update,
			query_message=query_message
		)
		return ConversationHandler.END

async def huddam_entity_type(update: Update, context: ContextTypes.DEFAULT_TYPE)	:
	logger.debug(f"Processing huddam_entity_type for user {update.effective_user.id}")
	try:
		update, context, query, user, query_message = await uptodate_query(update, context)
		if not query_message:
			return
		await query.answer()
		user_id = user.id
		db = Database()
		i18n = I18n()
		language = db.get_user_language(user_id)

		if query.data == "end_conversation":
			return await huddam_cancel(update, context)

		if not query.data.startswith("huddam_entity_"):
			logger.debug(f"Ignoring unrelated callback in huddam_entity_type: {query.data}")
			return ENTITY_TYPE
		entity_type = query.data[len("huddam_entity_"):]
		context.user_data["entity_type"] = entity_type

		keyboard = [
			[InlineKeyboardButton(i18n.t("ALPHABET_ORDER_ABJADI", language), callback_data="huddam_lang_0-4"),
			InlineKeyboardButton(i18n.t("ALPHABET_ORDER_MAGHRIBI", language), callback_data="huddam_lang_6-10")],
			[InlineKeyboardButton(i18n.t("ALPHABET_ORDER_QURANIC", language), callback_data="huddam_lang_11-15"),
			InlineKeyboardButton(i18n.t("ALPHABET_ORDER_HIJA", language), callback_data="huddam_lang_16-20")],
			[InlineKeyboardButton(i18n.t("ALPHABET_ORDER_MAGHRIBI_HIJA", language), callback_data="huddam_lang_21-25"),
			InlineKeyboardButton(i18n.t("ALPHABET_ORDER_IKLEELS", language), callback_data="huddam_lang_26-30")],
			[InlineKeyboardButton(i18n.t("ALPHABET_ORDER_SHAMSE_ABJADI", language), callback_data="huddam_lang_31-35"),
			InlineKeyboardButton(i18n.t("ALPHABET_ORDER_HEBREW", language), callback_data="huddam_lang_HE")],
			[InlineKeyboardButton(i18n.t("ALPHABET_ORDER_TURKISH", language), callback_data="huddam_lang_TR"),
			InlineKeyboardButton(i18n.t("ALPHABET_ORDER_ENGLISH", language), callback_data="huddam_lang_EN")],
			[InlineKeyboardButton(i18n.t("ALPHABET_ORDER_LATIN", language), callback_data="huddam_lang_LA"),
			InlineKeyboardButton(i18n.t("CANCEL_BUTTON", language), callback_data="end_conversation")],
		]
		reply_markup = InlineKeyboardMarkup(keyboard)
		await send_long_message(
			i18n.t("HUDDAM_PROMPT_LANGUAGE", language),
			reply_markup=reply_markup,
			update=update,
			query_message=query_message
		)
		return LANGUAGE
	except Exception as e:
		logger.error(f"Error in huddam_entity_type: {str(e)}")
		await send_long_message(
			i18n.t("ERROR_GENERAL", language, error=str(e)),
			parse_mode=ParseMode.MARKDOWN,
			update=update,
			query_message=query_message
		)
		return ConversationHandler.END

async def huddam_language(update: Update, context: ContextTypes.DEFAULT_TYPE)	:
	logger.debug(f"Processing huddam_language for user {update.effective_user.id}")
	try:
		update, context, query, user, query_message = await uptodate_query(update, context)
		if not query_message:
			return
		await query.answer()
		user_id = user.id
		db = Database()
		i18n = I18n()
		language = db.get_user_language(user_id)

		if query.data == "end_conversation":
			return await huddam_cancel(update, context)

		if not query.data.startswith("huddam_lang_"):
			logger.debug(f"Ignoring unrelated callback in huddam_language: {query.data}")
			return LANGUAGE
		huddam_lang = query.data[len("huddam_lang_"):]
		context.user_data["language"] = huddam_lang

		keyboard = [
			[InlineKeyboardButton(i18n.t("HUDDAM_REGULAR", language), callback_data="huddam_multi_regular"),
			InlineKeyboardButton(i18n.t("HUDDAM_EACHER", language), callback_data="huddam_multi_eacher")],
			[InlineKeyboardButton(i18n.t("CANCEL_BUTTON", language), callback_data="end_conversation")],
		]
		reply_markup = InlineKeyboardMarkup(keyboard)
		await send_long_message(
			i18n.t("HUDDAM_PROMPT_MULTIPLIAR", language),
			reply_markup=reply_markup,
			update=update,
			query_message=query_message
		)
		return MULTIPLIAR
	except Exception as e:
		logger.error(f"Error in huddam_language: {str(e)}")
		await send_long_message(
			i18n.t("ERROR_GENERAL", language, error=str(e)),
			parse_mode=ParseMode.MARKDOWN,
			update=update,
			query_message=query_message
		)
		return ConversationHandler.END

async def huddam_multipliar(update: Update, context: ContextTypes.DEFAULT_TYPE)	:
	logger.info(f"Processing huddam_multipliar for user {update.effective_user.id}")
	try:
		update, context, query, user, query_message = await uptodate_query(update, context)
		if not query_message:
			return
		await query.answer()
		user_id = user.id
		db = Database()
		i18n = I18n()
		language = db.get_user_language(user_id)

		if query.data == "end_conversation":
			return await huddam_cancel(update, context)

		if not query.data.startswith("huddam_multi_"):
			logger.debug(f"Ignoring callback: {query.data}")
			return MULTIPLIAR
		context.user_data["multipliar"] = query.data[len("huddam_multi_"):]

		huddam_lang = context.user_data["language"]
		number = context.user_data["huddam_number"]
		entity_type = context.user_data["entity_type"]

		alphabet_map = {
			"0-4": ("arabic", 1, "LANGUAGE_NAME_AR"), "6-10": ("arabic", 7, "LANGUAGE_NAME_AR"), "11-15": ("arabic", 12, "LANGUAGE_NAME_AR"),
			"16-20": ("arabic", 17, "LANGUAGE_NAME_AR"), "21-25": ("arabic", 22, "LANGUAGE_NAME_AR"), "26-30": ("arabic", 27, "LANGUAGE_NAME_AR"),
			"31-35": ("arabic", 32, "LANGUAGE_NAME_AR"), "HE": ("hebrew", 1, "LANGUAGE_NAME_HE"), "TR": ("turkish", 1, "LANGUAGE_NAME_TR"),
			"EN": ("english", 1, "LANGUAGE_NAME_EN"), "LA": ("latin", 1, "LANGUAGE_NAME_LA")
		}
		alphabeta, method, huddam_lang_text = alphabet_map[huddam_lang]

		abjad = Abjad()
		result = abjad.generate_name(number, entity_type, method, alphabeta, context.user_data["multipliar"])
		if isinstance(result, str) and result.startswith("Error"):
			await send_long_message(i18n.t("ERROR_GENERAL", language, error=result), parse_mode="HTML")
			return ConversationHandler.END

		response = i18n.t("HUDDAM_RESULT", language, number=number, type=entity_type, huddam_lang=i18n.t(huddam_lang_text, language), name=result)
		keyboard = [
			[InlineKeyboardButton(i18n.t("CREATE_MAGIC_SQUARE", language), callback_data=f"magic_square_{number}"),
			InlineKeyboardButton(i18n.t("SPELL_NUMBER", language), callback_data=f"nutket_{number}_{alphabeta}")],
			[InlineKeyboardButton(i18n.t("CALCULATE_ABJAD", language), callback_data=f"abjad_text_{result}"),
			InlineKeyboardButton(i18n.t("CANCEL_BUTTON", language), callback_data="end_conversation_huddam")],
		]
		await send_long_message(
			response,
			parse_mode=ParseMode.HTML,
			reply_markup=InlineKeyboardMarkup(keyboard),
			update=update,
			query_message=query_message
		)
		context.user_data.clear()
		return ConversationHandler.END
	except Exception as e:
		logger.error(f"Error in huddam_multipliar: {str(e)}")
		await send_long_message(i18n.t("ERROR_GENERAL", language, error=str(e)), parse_mode="HTML")
		return ConversationHandler.END

async def huddam_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE)	:
	logger.info(f"Cancelling /huddam for user {update.effective_user.id}")
	try:
		update, context, query, user, query_message = await uptodate_query(update, context)
		if not query_message:
			return
		await query.answer()
		user_id = user.id
		db = Database()
		i18n = I18n()
		language = db.get_user_language(user_id)
		await send_long_message(
			i18n.t("HUDDAM_CANCEL", language),
			parse_mode=ParseMode.MARKDOWN,
			update=update,
			query_message=query_message
		)
		context.user_data.clear()
		return ConversationHandler.END
	except Exception as e:
		logger.error(f"Error in huddam_cancel: {str(e)}")
		await send_long_message(
			i18n.t("ERROR_GENERAL", language, error=str(e)),
			parse_mode=ParseMode.MARKDOWN,
			update=update,
			query_message=query_message
		)
		return ConversationHandler.END

def get_huddam_conversation_handler():
	try:
		handler = ConversationHandler(
			entry_points=[CommandHandler("huddam", huddam_start)],
			states={
				ENTITY_TYPE: [CallbackQueryHandler(huddam_entity_type)],
				LANGUAGE: [CallbackQueryHandler(huddam_language)],
				MULTIPLIAR: [CallbackQueryHandler(huddam_multipliar)],
			},
			fallbacks=[CommandHandler("cancel", huddam_cancel), MessageHandler(filters.Regex(r'^/.*'), timeout)],
		)
		logger.info("Huddam conversation handler initialized successfully")
		return handler
	except Exception as e:
		logger.error(f"Failed to initialize huddam conversation handler: {str(e)}")
		raise