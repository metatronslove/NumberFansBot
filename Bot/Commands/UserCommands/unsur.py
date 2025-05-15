import logging
import requests
import re
import urllib
from datetime import datetime
from Bot.config import Config
from Bot.database import Database
from Bot.Helpers.i18n import I18n
from Bot.Helpers.Abjad import Abjad
from Bot.Helpers.ElementClassifier import ElementClassifier
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

LANGUAGE, TABLE, SHADDA = range(3)

async def unsur_start(update: Update, context: ContextTypes.DEFAULT_TYPE)	:
	logger.info(f"Starting /unsur for user {update.effective_user.id}")
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
		db.increment_command_usage("unsur", user_id)

		args = context.args
		input_text = " ".join(args)
		context.user_data["abjad_text"] = input_text
		is_arabic = bool(re.search(r"[\u0600-\u06FF]", input_text))
		context.user_data["is_arabic"] = is_arabic
		if not input_text:
			await send_long_message(
				message=i18n.t("UNSUR_USAGE", language),
				parse_mode=ParseMode.MARKDOWN,
				update=update,
				query_message=query_message,
				context=context
			)
			return ConversationHandler.END

		context.user_data["input_text"] = input_text
		is_arabic = bool(re.search(r'[\u0600-\u06FF]', input_text))
		context.user_data["is_arabic"] = is_arabic

		keyboard = [
			[InlineKeyboardButton(i18n.t("ALPHABET_ORDER_TURKISH", language), callback_data="unsur_lang_TURKCE"),
			InlineKeyboardButton(i18n.t("ALPHABET_ORDER_ARABI", language), callback_data="unsur_lang_ARABI")],
			[InlineKeyboardButton(i18n.t("ALPHABET_ORDER_BUNI", language), callback_data="unsur_lang_BUNI"),
			InlineKeyboardButton(i18n.t("ALPHABET_ORDER_HUSEYNI", language), callback_data="unsur_lang_HUSEYNI")],
			[InlineKeyboardButton(i18n.t("ALPHABET_ORDER_HEBREW", language), callback_data="unsur_lang_HEBREW"),
			InlineKeyboardButton(i18n.t("ALPHABET_ORDER_ENGLISH", language), callback_data="unsur_lang_ENGLISH")],
			[InlineKeyboardButton(i18n.t("ALPHABET_ORDER_LATIN", language), callback_data="unsur_lang_LATIN"),
			InlineKeyboardButton(i18n.t("ALPHABET_ORDER_DEFAULT", language), callback_data="unsur_lang_DEFAULT")],
			[InlineKeyboardButton(i18n.t("CANCEL_BUTTON", language), callback_data="end_conversation")],
		]
		reply_markup = InlineKeyboardMarkup(keyboard)
		await send_long_message(
			i18n.t("UNSUR_PROMPT_LANGUAGE", language),
			reply_markup=reply_markup,
			update=update,
			query_message=query_message,
			context=context,
			force_new_message=force_new
		)
		return LANGUAGE
	except Exception as e:
		logger.error(f"Error in unsur_input: {str(e)}")
		await send_long_message(
			i18n.t("ERROR_GENERAL", language, error=str(e)),
			parse_mode=ParseMode.MARKDOWN,
			update=update,
			query_message=query_message,
			context=context
		)
		return ConversationHandler.END

async def unsur_shadda(update: Update, context: ContextTypes.DEFAULT_TYPE)	:
	logger.info(f"Processing unsur_shadda for user {update.effective_user.id}")
	try:
		update, context, query, user, query_message = await uptodate_query(update, context)
		if not query_message:
			return
		await query.answer()
		user_id = user.id
		db = Database()
		i18n = I18n()
		language = db.get_user_language(user_id)

		if not query.data.startswith("unsur_shadda_"):
			logger.debug(f"Ignoring callback: {query.data}")
			return SHADDA
		context.user_data["shadda"] = int(query.data[len("unsur_shadda_"):]) or 1

		keyboard = [
			[InlineKeyboardButton(i18n.t("TURKISH", language), callback_data="unsur_lang_turkish"),
			InlineKeyboardButton(i18n.t("ARABIC", language), callback_data="unsur_lang_arabic")],
			[InlineKeyboardButton(i18n.t("BUNI", language), callback_data="unsur_lang_buni"),
			InlineKeyboardButton(i18n.t("HUSEYNI", language), callback_data="unsur_lang_huseyni")],
			[InlineKeyboardButton(i18n.t("HEBREW", language), callback_data="unsur_lang_hebrew"),
			InlineKeyboardButton(i18n.t("ENGLISH", language), callback_data="unsur_lang_english")],
			[InlineKeyboardButton(i18n.t("LATIN", language), callback_data="unsur_lang_latin"),
			InlineKeyboardButton(i18n.t("CANCEL_BUTTON", language), callback_data="end_conversation")],
		]
		await send_long_message(
			i18n.t("UNSUR_PROMPT_LANGUAGE", language),
			reply_markup=InlineKeyboardMarkup(keyboard),
			parse_mode="HTML"
		)
		return LANGUAGE
	except Exception as e:
		logger.error(f"Error in unsur_shadda: {str(e)}")
		await send_long_message(i18n.t("ERROR_GENERAL", language, error=str(e)), parse_mode="HTML")
		return ConversationHandler.END

async def unsur_language(update: Update, context: ContextTypes.DEFAULT_TYPE)	:
	logger.info(f"Processing unsur_language for user {update.effective_user.id}")
	try:
		update, context, query, user, query_message = await uptodate_query(update, context)
		if not query_message:
			return
		await query.answer()
		user_id = user.id
		db = Database()
		i18n = I18n()
		language = db.get_user_language(user_id)

		if not query.data.startswith("unsur_lang_"):
			logger.debug(f"Ignoring callback: {query.data}")
			return LANGUAGE
		context.user_data["language"] = query.data[len("unsur_lang_"):].lower()

		keyboard = [
			[InlineKeyboardButton(i18n.t("ELEMENT_FIRE", language), callback_data="unsur_table_fire"),
			InlineKeyboardButton(i18n.t("ELEMENT_WATER", language), callback_data="unsur_table_water")],
			[InlineKeyboardButton(i18n.t("ELEMENT_AIR", language), callback_data="unsur_table_air"),
			InlineKeyboardButton(i18n.t("ELEMENT_EARTH", language), callback_data="unsur_table_earth")],
			[InlineKeyboardButton(i18n.t("CANCEL_BUTTON", language), callback_data="end_conversation")],
		]
		await send_long_message(
			i18n.t("UNSUR_PROMPT_TABLE", language),
			reply_markup=InlineKeyboardMarkup(keyboard),
			parse_mode="HTML"
		)
		return TABLE
	except Exception as e:
		logger.error(f"Error in unsur_language: {str(e)}")
		await send_long_message(i18n.t("ERROR_GENERAL", language, error=str(e)), parse_mode="HTML")
		return ConversationHandler.END

async def unsur_table(update: Update, context: ContextTypes.DEFAULT_TYPE)	:
	logger.info(f"Processing unsur_table for user {update.effective_user.id}")
	try:
		update, context, query, user, query_message = await uptodate_query(update, context)
		if not query_message:
			return
		await query.answer()
		user_id = user.id
		db = Database()
		i18n = I18n()
		language = db.get_user_language(user_id)

		if not query.data.startswith("unsur_table_"):
			logger.debug(f"Ignoring callback: {query.data}")
			return TABLE
		context.user_data["table"] = query.data[len("unsur_table_"):].lower()

		input_text = context.user_data["input_text"]
		lang = context.user_data["language"]
		table = context.user_data["table"]
		shadda = context.user_data.get("shadda", 1)

		unsur = ElementClassifier()
		result = unsur.classify_elements(input_text, table, shadda, lang)
		if isinstance(result, str) and result.startswith("Error"):
			await send_long_message(i18n.t("ERROR_GENERAL", language, error=result), parse_mode="HTML")
			return ConversationHandler.END

		value = result["adet"]
		liste = result["liste"]
		elements = {
			"fire": i18n.t("ELEMENT_FIRE", language),
			"water": i18n.t("ELEMENT_WATER", language),
			"air": i18n.t("ELEMENT_AIR", language),
			"earth": i18n.t("ELEMENT_EARTH", language)
		}
		element = elements.get(table, i18n.t("ELEMENT_UNKNOWN", language))

		response = i18n.t("UNSUR_RESULT", language, input=input_text, liste=liste, value=value, element=element)
		keyboard = [
			[InlineKeyboardButton(i18n.t("CREATE_MAGIC_SQUARE", language), callback_data=f"magic_square_{value}"),
			InlineKeyboardButton(i18n.t("SPELL_NUMBER", language), callback_data=f"nutket_{value}_{lang}")],
			[InlineKeyboardButton(i18n.t("CALCULATE_ABJAD", language), callback_data=f"abjad_text_{liste}"),
			InlineKeyboardButton(i18n.t("CANCEL_BUTTON", language), callback_data="end_conversation_unsur")]
		]

		await send_long_message(
			response,
			parse_mode=ParseMode.HTML,
			reply_markup=InlineKeyboardMarkup(keyboard),
			update=update,
			query_message=query_message,
			context=context
		)
		context.user_data.clear()
		return ConversationHandler.END
	except Exception as e:
		logger.error(f"Error in unsur_table: {str(e)}")
		await send_long_message(i18n.t("ERROR_GENERAL", language, error=str(e)), parse_mode="HTML")
		return ConversationHandler.END

async def unsur_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE)	:
	logger.info(f"Cancelling /unsur for user {update.effective_user.id}")
	try:
		user_id = query = update.callback_query
		await query.answer()
		user_id = user.id
		db = Database()
		i18n = I18n()
		language = db.get_user_language(user_id)
		await send_long_message(
			i18n.t("UNSUR_CANCEL", language),
			parse_mode=ParseMode.MARKDOWN,
			update=update,
			query_message=query_message,
			context=context
		)
		context.user_data.clear()
		return ConversationHandler.END
	except Exception as e:
		logger.error(f"Error in unsur_cancel: {str(e)}")
		await send_long_message(
			i18n.t("ERROR_GENERAL", language, error=str(e)),
			parse_mode=ParseMode.MARKDOWN,
			update=update,
			query_message=query_message,
			context=context
		)
		return ConversationHandler.END

def get_unsur_conversation_handler():
	try:
		handler = ConversationHandler(
			entry_points=[CommandHandler("unsur", unsur_start)],
			states={
				LANGUAGE: [CallbackQueryHandler(unsur_language)],
				TABLE: [CallbackQueryHandler(unsur_table)],
				SHADDA: [CallbackQueryHandler(unsur_shadda)],
			},
			fallbacks=[CommandHandler("cancel", unsur_cancel), MessageHandler(filters.Regex(r'^/.*'), timeout)],
		)
		logger.info("Unsur conversation handler initialized successfully")
		return handler
	except Exception as e:
		logger.error(f"Failed to initialize unsur conversation handler: {str(e)}")
		raise