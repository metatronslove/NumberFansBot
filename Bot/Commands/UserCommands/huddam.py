import logging
import re
from Bot.config import Config
from Bot.database import Database
from Bot.i18n import I18n
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
	Application, CommandHandler, MessageHandler, CallbackQueryHandler,
	ConversationHandler, filters, ContextTypes
)
from telegram.constants import ParseMode
from telegram.error import BadRequest
import asyncio
from Bot.Abjad import Abjad
from Bot.utils import register_user_if_not_exists, get_warning_description, get_ai_commentary
from urllib.parse import urlparse
from pathlib import Path
from datetime import datetime
import os

logger = logging.getLogger(__name__)

ENTITY_TYPE, LANGUAGE, MULTIPLIAR = range(3)

async def huddam_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
	logger.info(f"Starting /huddam for user {update.effective_user.id}")
	try:
		user = update.message.from_user
		await register_user_if_not_exists(update, context, user)
		user_id = user.id
		db = Database()
		i18n = I18n()
		language = db.get_user_language(user_id)

		args = context.args
		if not args or not args[0].isdigit():
			await update.message.reply_text(
				i18n.t("HUDDAM_USAGE", language),
				parse_mode=ParseMode.MARKDOWN
			)
			return ConversationHandler.END

		number = int(args[0])
		context.user_data["huddam_number"] = number

		keyboard = [
			[InlineKeyboardButton(i18n.t("HUDDAM_HIGH", language), callback_data="huddam_entity_ulvi")],
			[InlineKeyboardButton(i18n.t("HUDDAM_LOW", language), callback_data="huddam_entity_sufli")],
			[InlineKeyboardButton(i18n.t("HUDDAM_BAD", language), callback_data="huddam_entity_ser")],
		]
		reply_markup = InlineKeyboardMarkup(keyboard)
		await update.message.reply_text(
			i18n.t("HUDDAM_PROMPT_ENTITY_TYPE", language),
			reply_markup=reply_markup
		)
		return ENTITY_TYPE
	except Exception as e:
		logger.error(f"Error in huddam_start: {str(e)}")
		await update.message.reply_text(
			i18n.t("ERROR_GENERAL", language, error=str(e)),
			parse_mode=ParseMode.MARKDOWN
		)
		return ConversationHandler.END

async def huddam_entity_type(update: Update, context: ContextTypes.DEFAULT_TYPE):
	logger.debug(f"Processing huddam_entity_type for user {update.effective_user.id}")
	try:
		query = update.callback_query
		await query.answer()
		user_id = query.from_user.id
		db = Database()
		i18n = I18n()
		language = db.get_user_language(user_id)

		if not query.data.startswith("huddam_entity_"):
			logger.debug(f"Ignoring unrelated callback in huddam_entity_type: {query.data}")
			return ENTITY_TYPE
		entity_type = query.data.split("huddam_entity_")[1]
		context.user_data["entity_type"] = entity_type

		keyboard = [
			[InlineKeyboardButton(i18n.t("ALPHABET_ORDER_ABJADI", language), callback_data="huddam_lang_0-4")],
			[InlineKeyboardButton(i18n.t("ALPHABET_ORDER_MAGHRIBI", language), callback_data="huddam_lang_6-10")],
			[InlineKeyboardButton(i18n.t("ALPHABET_ORDER_QURANIC", language), callback_data="huddam_lang_11-15")],
			[InlineKeyboardButton(i18n.t("ALPHABET_ORDER_HIJA", language), callback_data="huddam_lang_16-20")],
			[InlineKeyboardButton(i18n.t("ALPHABET_ORDER_MAGHRIBI_HIJA", language), callback_data="huddam_lang_21-25")],
			[InlineKeyboardButton(i18n.t("ALPHABET_ORDER_IKLEELS", language), callback_data="huddam_lang_26-30")],
			[InlineKeyboardButton(i18n.t("ALPHABET_ORDER_SHAMSE_ABJADI", language), callback_data="huddam_lang_31-35")],
			[InlineKeyboardButton(i18n.t("ALPHABET_ORDER_HEBREW", language), callback_data="huddam_lang_HE")],
			[InlineKeyboardButton(i18n.t("ALPHABET_ORDER_TURKISH", language), callback_data="huddam_lang_TR")],
			[InlineKeyboardButton(i18n.t("ALPHABET_ORDER_ENGLISH", language), callback_data="huddam_lang_EN")],
			[InlineKeyboardButton(i18n.t("ALPHABET_ORDER_LATIN", language), callback_data="huddam_lang_LA")],
		]
		reply_markup = InlineKeyboardMarkup(keyboard)
		await query.message.reply_text(
			i18n.t("HUDDAM_PROMPT_LANGUAGE", language),
			reply_markup=reply_markup
		)
		return LANGUAGE
	except Exception as e:
		logger.error(f"Error in huddam_entity_type: {str(e)}")
		await query.message.reply_text(
			i18n.t("ERROR_GENERAL", language, error=str(e)),
			parse_mode=ParseMode.MARKDOWN
		)
		return ConversationHandler.END

async def huddam_language(update: Update, context: ContextTypes.DEFAULT_TYPE):
	logger.debug(f"Processing huddam_language for user {update.effective_user.id}")
	try:
		query = update.callback_query
		await query.answer()
		user_id = query.from_user.id
		db = Database()
		i18n = I18n()
		language = db.get_user_language(user_id)

		if not query.data.startswith("huddam_lang_"):
			logger.debug(f"Ignoring unrelated callback in huddam_language: {query.data}")
			return LANGUAGE
		lang = query.data.split("huddam_lang_")[1]
		context.user_data["language"] = lang

		keyboard = [
			[InlineKeyboardButton(i18n.t("HUDDAM_REGULAR", language), callback_data="huddam_multi_regular")],
			[InlineKeyboardButton(i18n.t("HUDDAM_EACHER", language), callback_data="huddam_multi_eacher")],
		]
		reply_markup = InlineKeyboardMarkup(keyboard)
		await query.message.reply_text(
			i18n.t("HUDDAM_PROMPT_MULTIPLIAR", language),
			reply_markup=reply_markup
		)
		return MULTIPLIAR
	except Exception as e:
		logger.error(f"Error in huddam_language: {str(e)}")
		await query.message.reply_text(
			i18n.t("ERROR_GENERAL", language, error=str(e)),
			parse_mode=ParseMode.MARKDOWN
		)
		return ConversationHandler.END

async def huddam_multipliar(update: Update, context: ContextTypes.DEFAULT_TYPE):
	logger.debug(f"Processing huddam_multipliar for user {update.effective_user.id}")
	try:
		query = update.callback_query
		await query.answer()
		user_id = query.from_user.id
		db = Database()
		i18n = I18n()
		language = db.get_user_language(user_id)
		db.set_user_attribute(user_id, "last_interaction", datetime.now())
		db.increment_command_usage("huddam", user_id)

		if not query.data.startswith("huddam_multi_"):
			logger.debug(f"Ignoring unrelated callback in huddam_multipliar: {query.data}")
			return MULTIPLIAR
		multipliar = query.data.split("huddam_multi_")[1]
		context.user_data["multipliar"] = multipliar

		lang = context.user_data["language"]
		number = context.user_data["huddam_number"]
		entity_type = context.user_data["entity_type"]
		alphabet_order = lang

		if alphabet_order == "0-4":
			alphabeta = "arabic"
			tablebase = 1
		elif alphabet_order == "6-10":
			alphabeta = "arabic"
			tablebase = 7
		elif alphabet_order == "11-15":
			alphabeta = "arabic"
			tablebase = 12
		elif alphabet_order == "16-20":
			alphabeta = "arabic"
			tablebase = 17
		elif alphabet_order == "21-25":
			alphabeta = "arabic"
			tablebase = 22
		elif alphabet_order == "26-30":
			alphabeta = "arabic"
			tablebase = 27
		elif alphabet_order == "31-35":
			alphabeta = "arabic"
			tablebase = 32
		elif alphabet_order == "HE":
			alphabeta = "hebrew"
			tablebase = 1
		elif alphabet_order == "TR":
			alphabeta = "turkish"
			tablebase = 1
		elif alphabet_order == "EN":
			alphabeta = "english"
			tablebase = 1
		elif alphabet_order == "LA":
			alphabeta = "latin"
			tablebase = 1
		method = tablebase

		abjad = Abjad()
		logger.debug(f"Calling abjad.generate_name with number={number}, entity_type={entity_type}, method={method}, alphabeta={alphabeta}, multipliar={multipliar}")
		result = abjad.generate_name(number, entity_type, method, alphabeta, multipliar)
		if isinstance(result, str) and result.startswith("Error"):
			logger.error(f"Huddam computation failed: {result}")
			await query.message.reply_text(
				i18n.t("ERROR_GENERAL", language, error=result),
				parse_mode=ParseMode.MARKDOWN
			)
			context.user_data.clear()
			return ConversationHandler.END

		name = result
		value = number
		response = i18n.t("HUDDAM_RESULT", language, number=number, type=entity_type, lang=lang, name=name)

		commentary = await get_ai_commentary(response, language)
		if commentary:
			response += "\n\n" + i18n.t("AI_COMMENTARY", language, commentary=commentary)

		keyboard = []
		if value >= 15:
			keyboard.append(
				[
					InlineKeyboardButton(
						i18n.t("CREATE_MAGIC_SQUARE", language),
						callback_data=f"magic_square_{value}",
					)
				]
			)
			keyboard.append(
				[
					InlineKeyboardButton(
						i18n.t("CREATE_INDIAN_MAGIC_SQUARE", language),
						callback_data=f"indian_square_{value}",
					)
				]
			)
		keyboard.append(
			[
				InlineKeyboardButton(
					i18n.t("SPELL_NUMBER", language),
					callback_data=f"nutket_{value}_{lang}",
				)
			]
		)
		keyboard.append(
			[
				InlineKeyboardButton(
					i18n.t("CALCULATE_ABJAD", language),
					callback_data=f"abjad_text_{name}_{lang}",
				)
			]
		)
		reply_markup = InlineKeyboardMarkup(keyboard)

		await query.message.reply_text(
			response,
			parse_mode=ParseMode.MARKDOWN,
			reply_markup=reply_markup,
		)
		context.user_data.clear()
		return ConversationHandler.END

	except Exception as e:
		logger.error(f"Huddam error: {str(e)}")
		await query.message.reply_text(
			i18n.t("ERROR_GENERAL", language, error=str(e)),
			parse_mode=ParseMode.MARKDOWN
		)
		context.user_data.clear()
		return ConversationHandler.END

async def huddam_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
	logger.info(f"Cancelling /huddam for user {update.effective_user.id}")
	try:
		user_id = update.message.from_user.id
		db = Database()
		i18n = I18n()
		language = db.get_user_language(user_id)
		await update.message.reply_text(
			i18n.t("HUDDAM_CANCEL", language),
			parse_mode=ParseMode.MARKDOWN
		)
		context.user_data.clear()
		return ConversationHandler.END
	except Exception as e:
		logger.error(f"Error in huddam_cancel: {str(e)}")
		await update.message.reply_text(
			i18n.t("ERROR_GENERAL", language, error=str(e)),
			parse_mode=ParseMode.MARKDOWN
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
			fallbacks=[CommandHandler("cancel", huddam_cancel)],
			allow_reentry=True,
			per_message=True
		)
		logger.info("Huddam conversation handler initialized successfully")
		return handler
	except Exception as e:
		logger.error(f"Failed to initialize huddam conversation handler: {str(e)}")
		raise