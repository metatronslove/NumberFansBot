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

REPETITION, TABLE, LANGUAGE = range(3)

async def bastet_start(update: Update, context: ContextTypes.DEFAULT_TYPE)	:
	logger.info(f"Starting /bastet for user {update.effective_user.id}")
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
		db.increment_command_usage("bastet", user_id)

		args = context.args
		if len(args) == 1:
			if not args[0].isdigit():
				await send_long_message(
					i18n.t("BASTET_USAGE", language),
					parse_mode=ParseMode.MARKDOWN,
					update=update,
					query_message=query_message,
					context=context
				)
				return ConversationHandler.END

			number = int(args[0])
			context.user_data["bastet_number"] = number

			await send_long_message(
				i18n.t("BASTET_PROMPT_REPETITION", language),
				force_new_message=force_new
			)
			return REPETITION
		elif len(args) == 2:
			if not args[0].isdigit() or not args[1].isdigit():
				await send_long_message(
					i18n.t("BASTET_USAGE", language),
					parse_mode=ParseMode.MARKDOWN,
					update=update,
					query_message=query_message,
					context=context
				)
				return ConversationHandler.END

			number = int(args[0])
			context.user_data["bastet_number"] = number
			repetition = int(args[1])
			context.user_data["repetition"] = int(repetition)
			return TABLE
		elif not args:
			await send_long_message(
				i18n.t("BASTET_USAGE", language),
				parse_mode=ParseMode.MARKDOWN,
				update=update,
				query_message=query_message,
				context=context
			)
			return ConversationHandler.END
	except Exception as e:
		logger.error(f"Error in bastet_start: {str(e)}")
		await send_long_message(
			i18n.t("ERROR_GENERAL", language, error=str(e)),
			parse_mode=ParseMode.MARKDOWN,
			update=update,
			query_message=query_message,
			context=context
		)
		return ConversationHandler.END

async def bastet_repetition(update: Update, context: ContextTypes.DEFAULT_TYPE)	:
	logger.debug(f"Processing bastet_repetition for user {update.effective_user.id}")
	try:
		user_id = update.message.from_user.id
		db = Database()
		i18n = I18n()
		language = db.get_user_language(user_id)

		repetition = update.message.text.strip()
		if not repetition.isdigit() or int(repetition) < 1 or int(repetition) > 1000:  # Add upper limit
			await send_long_message(
				i18n.t("ERROR_INVALID_INPUT", language, error="Repetition must be a positive integer between 1 and 1000"),
				parse_mode=ParseMode.HTML,
				update=update,
				query_message=query_message,
				context=context
			)
			return REPETITION

		context.user_data["repetition"] = int(repetition)

		keyboard = [
			[InlineKeyboardButton(i18n.t("ALPHABET_ORDER_ABJADI", language), callback_data="bastet_table_0-4"),
			InlineKeyboardButton(i18n.t("ALPHABET_ORDER_MAGHRIBI", language), callback_data="bastet_table_6-10")],
			[InlineKeyboardButton(i18n.t("ALPHABET_ORDER_QURANIC", language), callback_data="bastet_table_11-15"),
			InlineKeyboardButton(i18n.t("ALPHABET_ORDER_HIJA", language), callback_data="bastet_table_16-20")],
			[InlineKeyboardButton(i18n.t("ALPHABET_ORDER_MAGHRIBI_HIJA", language), callback_data="bastet_table_21-25"),
			InlineKeyboardButton(i18n.t("ALPHABET_ORDER_IKLEELS", language), callback_data="bastet_table_26-30")],
			[InlineKeyboardButton(i18n.t("ALPHABET_ORDER_SHAMSE_ABJADI", language), callback_data="bastet_table_31-35"),
			InlineKeyboardButton(i18n.t("ALPHABET_ORDER_HEBREW", language), callback_data="bastet_table_HE")],
			[InlineKeyboardButton(i18n.t("ALPHABET_ORDER_TURKISH", language), callback_data="bastet_table_TR"),
			InlineKeyboardButton(i18n.t("ALPHABET_ORDER_ENGLISH", language), callback_data="bastet_table_EN")],
			[InlineKeyboardButton(i18n.t("ALPHABET_ORDER_LATIN", language), callback_data="bastet_table_LA"),
			InlineKeyboardButton(i18n.t("CANCEL_BUTTON", language), callback_data="end_conversation")],
		]
		reply_markup = InlineKeyboardMarkup(keyboard)
		await send_long_message(
			i18n.t("BASTET_PROMPT_TABLE", language),
			reply_markup=reply_markup,
			update=update,
			query_message=query_message,
			context=context
		)
		return TABLE
	except Exception as e:
		logger.error(f"Error in bastet_repetition: {str(e)}")
		await send_long_message(
			i18n.t("ERROR_GENERAL", language, error=str(e)),
			parse_mode=ParseMode.MARKDOWN,
			update=update,
			query_message=query_message,
			context=context
		)
		return ConversationHandler.END

async def bastet_table(update: Update, context: ContextTypes.DEFAULT_TYPE)	:
	logger.debug(f"Processing bastet_table for user {update.effective_user.id}")
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
			return await bastet_cancel(update, context)

		if not query.data.startswith("bastet_table_"):
			logger.debug(f"Ignoring unrelated callback in bastet_table: {query.data}")
			return TABLE
		table = query.data.split("bastet_table_")[1]
		context.user_data["table"] = table

		keyboard = [
			[InlineKeyboardButton(i18n.t("ABJAD_TYPE_ASGHAR", language), callback_data="bastet_lang_-1"),
			InlineKeyboardButton(i18n.t("ABJAD_TYPE_SAGHIR", language), callback_data="bastet_lang_0")],
			[InlineKeyboardButton(i18n.t("ABJAD_TYPE_KEBEER", language), callback_data="bastet_lang_+1"),
			InlineKeyboardButton(i18n.t("ABJAD_TYPE_AKBAR", language), callback_data="bastet_lang_+2")],
			[InlineKeyboardButton(i18n.t("ABJAD_TYPE_SAGHIR_PLUS_QUANTITY", language), callback_data="bastet_lang_+3"),
			InlineKeyboardButton(i18n.t("ABJAD_TYPE_LETTER_QUANTITY", language), callback_data="bastet_lang_5")],
			[InlineKeyboardButton(i18n.t("CANCEL_BUTTON", language), callback_data="end_conversation")],
		]
		reply_markup = InlineKeyboardMarkup(keyboard)
		await send_long_message(
			i18n.t("BASTET_PROMPT_LANGUAGE", language),
			reply_markup=reply_markup,
			update=update,
			query_message=query_message,
			context=context
		)
		return LANGUAGE
	except Exception as e:
		logger.error(f"Error in bastet_table: {str(e)}")
		await send_long_message(
			i18n.t("ERROR_GENERAL", language, error=str(e)),
			parse_mode=ParseMode.MARKDOWN,
			update=update,
			query_message=query_message,
			context=context
		)
		return ConversationHandler.END

async def bastet_language(update: Update, context: ContextTypes.DEFAULT_TYPE)	:
	logger.info(f"Processing bastet_language for user {update.effective_user.id}")
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
			return await bastet_cancel(update, context)

		if not query.data.startswith("bastet_lang_"):
			logger.debug(f"Ignoring callback: {query.data}")
			return LANGUAGE
		abjad_type = query.data[len("bastet_lang_"):]

		number = context.user_data["bastet_number"]
		repetition = context.user_data["repetition"]
		table = context.user_data["table"]

		alphabet_map = {
			"0-4": ("arabic", 1), "6-10": ("arabic", 7), "11-15": ("arabic", 12),
			"16-20": ("arabic", 17), "21-25": ("arabic", 22), "26-30": ("arabic", 27),
			"31-35": ("arabic", 32), "HE": ("hebrew", 1), "TR": ("turkish", 1),
			"EN": ("english", 1), "LA": ("latin", 1)
		}
		alphabeta, tablebase = alphabet_map[table]
		tablebase += {"-1": -1, "0": 0, "+1": 1, "+2": 2, "+3": 3, "5": 5}[abjad_type]

		abjad = Abjad()
		result = abjad.bastet(number, int(repetition), tablebase, 1, alphabeta.upper(), 0)
		if isinstance(result, str) and result.startswith("Error"):
			await send_long_message(i18n.t("ERROR_GENERAL", language, error=result), parse_mode="HTML")
			return ConversationHandler.END

		response = i18n.t("BASTET_RESULT", language, number=number, repetition=repetition, table=tablebase, value=result)

		warning_desc = get_warning_description(result, language)
		if warning_desc:
			response += "\n\n" + i18n.t("WARNING_NUMBER", language, value=result, description=warning_desc)

		commentary = await get_ai_commentary(response, language)
		if commentary:
			response += "\n\n" + i18n.t("AI_COMMENTARY", language, commentary=commentary)

		keyboard = [
			[InlineKeyboardButton(i18n.t("CREATE_MAGIC_SQUARE", language), callback_data=f"magic_square_{number}"),
			InlineKeyboardButton(i18n.t("SPELL_NUMBER", language), callback_data=f"nutket_{number}_{alphabeta}")],
			[InlineKeyboardButton(i18n.t("GENERATE_ENTITY", language), callback_data=f"huddam_cb_{number}"),
			InlineKeyboardButton(i18n.t("CANCEL_BUTTON", language), callback_data="end_conversation_bastet")],
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
		logger.error(f"Error in bastet_language: {str(e)}")
		await send_long_message(i18n.t("ERROR_GENERAL", language, error=str(e)), parse_mode="HTML")
		return ConversationHandler.END

async def bastet_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE)	:
	logger.info(f"Cancelling /bastet for user {update.effective_user.id}")
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
			i18n.t("BASTET_CANCEL", language),
			parse_mode=ParseMode.MARKDOWN,
			update=update,
			query_message=query_message,
			context=context
		)
		context.user_data.clear()
		return ConversationHandler.END
	except Exception as e:
		logger.error(f"Error in bastet_cancel: {str(e)}")
		await send_long_message(
			i18n.t("ERROR_GENERAL", language, error=str(e)),
			parse_mode=ParseMode.MARKDOWN,
			update=update,
			query_message=query_message,
			context=context
		)
		return ConversationHandler.END

def get_bastet_conversation_handler():
	try:
		handler = ConversationHandler(
			entry_points=[CommandHandler("bastet", bastet_start)],
			states={
				REPETITION: [MessageHandler(filters.Text() & ~filters.COMMAND, bastet_repetition)],
				TABLE: [CallbackQueryHandler(bastet_table)],
				LANGUAGE: [CallbackQueryHandler(bastet_language)],
			},
			fallbacks=[CommandHandler("cancel", bastet_cancel), MessageHandler(filters.Regex(r'^/.*'), timeout)],
		)
		logger.info("Bastet conversation handler initialized successfully")
		return handler
	except Exception as e:
		logger.error(f"Failed to initialize bastet conversation handler: {str(e)}")
		raise