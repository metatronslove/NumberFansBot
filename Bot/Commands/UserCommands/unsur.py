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
from Bot.element_classifier import ElementClassifier
from Bot.utils import register_user_if_not_exists, get_ai_commentary
from datetime import datetime

logger = logging.getLogger(__name__)

INPUT, LANGUAGE, TABLE, SHADDA = range(4)

async def unsur_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
	logger.info(f"Starting /unsur for user {update.effective_user.id}")
	try:
		user = update.message.from_user
		await register_user_if_not_exists(update, context, user)
		user_id = user.id
		db = Database()
		i18n = I18n()
		language = db.get_user_language(user_id)

		await update.message.reply_text(
			i18n.t("UNSUR_PROMPT_INPUT", language),
			parse_mode=ParseMode.MARKDOWN
		)
		return INPUT
	except Exception as e:
		logger.error(f"Error in unsur_start: {str(e)}")
		await update.message.reply_text(
			i18n.t("ERROR_GENERAL", language, error=str(e)),
			parse_mode=ParseMode.MARKDOWN
		)
		return ConversationHandler.END

async def unsur_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
	logger.debug(f"Processing unsur_input for user {update.effective_user.id}")
	try:
		user_id = update.message.from_user.id
		db = Database()
		i18n = I18n()
		language = db.get_user_language(user_id)

		input_text = update.message.text.strip()
		if not input_text:
			await update.message.reply_text(
				i18n.t("ERROR_INVALID_INPUT", language, error="Input is required"),
				parse_mode=ParseMode.MARKDOWN
			)
			return INPUT

		context.user_data["input_text"] = input_text
		is_arabic = bool(re.search(r'[\u0600-\u06FF]', input_text))
		context.user_data["is_arabic"] = is_arabic

		keyboard = [
			[InlineKeyboardButton(i18n.t("ALPHABET_ORDER_TURKISH", language), callback_data="unsur_lang_TURKCE")],
			[InlineKeyboardButton(i18n.t("ALPHABET_ORDER_ARABI", language), callback_data="unsur_lang_ARABI")],
			[InlineKeyboardButton(i18n.t("ALPHABET_ORDER_BUNI", language), callback_data="unsur_lang_BUNI")],
			[InlineKeyboardButton(i18n.t("ALPHABET_ORDER_HUSEYNI", language), callback_data="unsur_lang_HUSEYNI")],
			[InlineKeyboardButton(i18n.t("ALPHABET_ORDER_HEBREW", language), callback_data="unsur_lang_HEBREW")],
			[InlineKeyboardButton(i18n.t("ALPHABET_ORDER_ENGLISH", language), callback_data="unsur_lang_ENGLISH")],
			[InlineKeyboardButton(i18n.t("ALPHABET_ORDER_LATIN", language), callback_data="unsur_lang_LATIN")],
			[InlineKeyboardButton(i18n.t("ALPHABET_ORDER_DEFAULT", language), callback_data="unsur_lang_DEFAULT")]
		]
		reply_markup = InlineKeyboardMarkup(keyboard)
		await update.message.reply_text(
			i18n.t("UNSUR_PROMPT_LANGUAGE", language),
			reply_markup=reply_markup
		)
		return LANGUAGE
	except Exception as e:
		logger.error(f"Error in unsur_input: {str(e)}")
		await update.message.reply_text(
			i18n.t("ERROR_GENERAL", language, error=str(e)),
			parse_mode=ParseMode.MARKDOWN
		)
		return ConversationHandler.END

async def unsur_language(update: Update, context: ContextTypes.DEFAULT_TYPE):
	logger.debug(f"Processing unsur_language for user {update.effective_user.id}")
	try:
		query = update.callback_query
		await query.answer()
		user_id = query.from_user.id
		db = Database()
		i18n = I18n()
		language = db.get_user_language(user_id)

		if not query.data.startswith("unsur_lang_"):
			logger.debug(f"Ignoring unrelated callback in unsur_language: {query.data}")
			return LANGUAGE
		lang = query.data.split("unsur_lang_")[1]
		context.user_data["language"] = lang

		keyboard = [
			[InlineKeyboardButton(i18n.t("ELEMENT_FIRE", language), callback_data="unsur_table_fire")],
			[InlineKeyboardButton(i18n.t("ELEMENT_WATER", language), callback_data="unsur_table_water")],
			[InlineKeyboardButton(i18n.t("ELEMENT_AIR", language), callback_data="unsur_table_air")],
			[InlineKeyboardButton(i18n.t("ELEMENT_EARTH", language), callback_data="unsur_table_earth")]
		]
		reply_markup = InlineKeyboardMarkup(keyboard)
		await query.message.reply_text(
			i18n.t("UNSUR_PROMPT_TABLE", language),
			reply_markup=reply_markup
		)
		return TABLE
	except Exception as e:
		logger.error(f"Error in unsur_language: {str(e)}")
		await query.message.reply_text(
			i18n.t("ERROR_GENERAL", language, error=str(e)),
			parse_mode=ParseMode.MARKDOWN
		)
		return ConversationHandler.END

async def unsur_table(update: Update, context: ContextTypes.DEFAULT_TYPE):
	logger.debug(f"Processing unsur_table for user {update.effective_user.id}")
	try:
		query = update.callback_query
		await query.answer()
		user_id = query.from_user.id
		db = Database()
		i18n = I18n()
		language = db.get_user_language(user_id)

		if not query.data.startswith("unsur_table_"):
			logger.debug(f"Ignoring unrelated callback in unsur_table: {query.data}")
			return TABLE
		table = query.data.split("unsur_table_")[1]
		context.user_data["table"] = table

		if context.user_data.get("is_arabic"):
			keyboard = [
				[InlineKeyboardButton(i18n.t("SHADDA_USE_ONCE", language), callback_data="unsur_shadda_1")],
				[InlineKeyboardButton(i18n.t("SHADDA_USE_TWICE", language), callback_data="unsur_shadda_2")]
			]
			reply_markup = InlineKeyboardMarkup(keyboard)
			await query.message.reply_text(
				i18n.t("UNSUR_PROMPT_SHADDA", language),
				reply_markup=reply_markup
			)
			return SHADDA
		else:
			context.user_data["shadda"] = 1
			return await unsur_shadda(update, context)
	except Exception as e:
		logger.error(f"Error in unsur_table: {str(e)}")
		await query.message.reply_text(
			i18n.t("ERROR_GENERAL", language, error=str(e)),
			parse_mode=ParseMode.MARKDOWN
		)
		return ConversationHandler.END

async def unsur_shadda(update: Update, context: ContextTypes.DEFAULT_TYPE):
	logger.debug(f"Processing unsur_shadda for user {update.effective_user.id}")
	try:
		query = update.callback_query
		await query.answer()
		user_id = query.from_user.id if query else update.message.from_user.id
		db = Database()
		i18n = I18n()
		language = db.get_user_language(user_id)
		db.set_user_attribute(user_id, "last_interaction", datetime.now())
		db.increment_command_usage("unsur", user_id)

		if query:
			if not query.data.startswith("unsur_shadda_"):
				logger.debug(f"Ignoring unrelated callback in unsur_shadda: {query.data}")
				return SHADDA
			shadda = int(query.data.split("unsur_shadda_")[1])
			context.user_data["shadda"] = shadda
			await query.answer()
		else:
			shadda = context.user_data.get("shadda", 1)

		input_text = context.user_data["input_text"]
		lang = context.user_data["language"]
		table = context.user_data["table"]

		unsur = ElementClassifier()
		logger.debug(f"Calling unsur.classify_elements with input_text={input_text}, table={table}, shadda={shadda}, lang={lang}")
		result = unsur.classify_elements(input_text, table, shadda, lang)
		if isinstance(result, str) and result.startswith("Error"):
			logger.error(f"Unsur computation failed: {result}")
			await (query.message.reply_text if query else update.message.reply_text)(
				i18n.t("ERROR_GENERAL", language, error=result),
				parse_mode=ParseMode.MARKDOWN
			)
			context.user_data.clear()
			return ConversationHandler.END

		value = result["adet"]
		liste = result["liste"]
		elements = {
			'fire': i18n.t("ELEMENT_FIRE", language),
			'water': i18n.t("ELEMENT_WATER", language),
			'air': i18n.t("ELEMENT_AIR", language),
			'earth': i18n.t("ELEMENT_EARTH", language)
		}
		element = elements.get(table, i18n.t("ELEMENT_UNKNOWN", language))

		response = i18n.t("UNSUR_RESULT", language, input=input_text, liste=liste, value=value, element=element)

		commentary = await get_ai_commentary(response, language)
		if commentary:
			response += "\n\n" + i18n.t("AI_COMMENTARY", language, commentary=commentary)

		keyboard = []
		if value >= 15:
			keyboard.append([InlineKeyboardButton(
				i18n.t("CREATE_MAGIC_SQUARE", language),
				callback_data=f"magic_square_{value}"
			)])
			keyboard.append([InlineKeyboardButton(
				i18n.t("CREATE_INDIAN_MAGIC_SQUARE", language),
				callback_data=f"indian_square_{value}"
			)])
		keyboard.append([InlineKeyboardButton(
			i18n.t("SPELL_NUMBER", language),
			callback_data=f"nutket_{value}_{lang}"
		)])
		if not input_text.replace(" ", "").isdigit():
			keyboard.append([InlineKeyboardButton(
				i18n.t("CALCULATE_ABJAD", language),
				callback_data=f"abjad_text_{input_text}_{lang}"
			)])
		reply_markup = InlineKeyboardMarkup(keyboard)

		await (query.message.reply_text if query else update.message.reply_text)(
			response,
			parse_mode=ParseMode.MARKDOWN,
			reply_markup=reply_markup
		)
		context.user_data.clear()
		return ConversationHandler.END

	except Exception as e:
		logger.error(f"Unsur error: {str(e)}")
		await (query.message.reply_text if query else update.message.reply_text)(
			i18n.t("ERROR_GENERAL", language, error=str(e)),
			parse_mode=ParseMode.MARKDOWN
		)
		context.user_data.clear()
		return ConversationHandler.END

async def unsur_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
	logger.info(f"Cancelling /unsur for user {update.effective_user.id}")
	try:
		user_id = update.message.from_user.id
		db = Database()
		i18n = I18n()
		language = db.get_user_language(user_id)
		await update.message.reply_text(
			i18n.t("UNSUR_CANCEL", language),
			parse_mode=ParseMode.MARKDOWN
		)
		context.user_data.clear()
		return ConversationHandler.END
	except Exception as e:
		logger.error(f"Error in unsur_cancel: {str(e)}")
		await update.message.reply_text(
			i18n.t("ERROR_GENERAL", language, error=str(e)),
			parse_mode=ParseMode.MARKDOWN
		)
		return ConversationHandler.END

def get_unsur_conversation_handler():
	try:
		handler = ConversationHandler(
			entry_points=[CommandHandler("unsur", unsur_start)],
			states={
				INPUT: [MessageHandler(filters.TEXT & ~filters.COMMAND, unsur_input)],
				LANGUAGE: [CallbackQueryHandler(unsur_language)],
				TABLE: [CallbackQueryHandler(unsur_table)],
				SHADDA: [CallbackQueryHandler(unsur_shadda)],
			},
			fallbacks=[CommandHandler("cancel", unsur_cancel)],
			allow_reentry=True
		)
		logger.info("Unsur conversation handler initialized successfully")
		return handler
	except Exception as e:
		logger.error(f"Failed to initialize unsur conversation handler: {str(e)}")
		raise