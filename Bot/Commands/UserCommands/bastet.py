import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
	Application, CommandHandler, MessageHandler, CallbackQueryHandler,
	ConversationHandler, filters, ContextTypes
)
from telegram.constants import ParseMode
from ...database import Database
from ...i18n import I18n
from ...admin_panel import config
from ...Abjad import Abjad
from ...utils import register_user_if_not_exists, get_warning_description
from datetime import datetime
import requests
import re

logger = logging.getLogger(__name__)

REPETITION, TABLE, LANGUAGE = range(3)

async def get_ai_commentary(response: str, lang: str) -> str:
	i18n = I18n()
	prompt = i18n.t("AI_PROMPT", lang, response=response)
	try:
		headers = {"Authorization": f"Bearer {config.huggingface_access_token}"}
		payload = {
			"inputs": prompt,
			"parameters": {"max_length": 200, "temperature": 0.7}
		}
		response = requests.post(
			config.ai_model_url,
			headers=headers,
			json=payload
		)
		response.json()[0]["generated_text"] = re.sub(rf"^{re.escape(prompt)}.*?\[/INST\]", "", generated_text, flags=re.DOTALL).strip()
		if response.status_code == 200:
			return response.json()[0]["generated_text"].split("[/INST]")[-1].strip()
		else:
			logger.error(f"AI API error: {response.status_code}")
			return ""
	except Exception as e:
		logger.error(f"AI commentary error: {str(e)}")
		return ""

async def bastet_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
	user = update.message.from_user
	await register_user_if_not_exists(update, context, user)
	user_id = user.id
	db = Database()
	i18n = I18n()
	language = db.get_user_language(user_id)

	args = context.args
	if not args or not args[0].isdigit():
		await update.message.reply_text(
			i18n.t("BASTET_USAGE", language),
			parse_mode=ParseMode.MARKDOWN
		)
		return ConversationHandler.END

	number = int(args[0])
	context.user_data["bastet_number"] = number

	await update.message.reply_text(
		i18n.t("BASTET_PROMPT_REPETITION", language)
	)
	return REPETITION

async def bastet_repetition(update: Update, context: ContextTypes.DEFAULT_TYPE):
	user_id = update.message.from_user.id
	db = Database()
	i18n = I18n()
	language = db.get_user_language(user_id)

	repetition = update.message.text
	if not repetition.isdigit() or int(repetition) < 1:
		await update.message.reply_text(
			i18n.t("ERROR_INVALID_INPUT", language, error="Repetition must be a positive integer")
		)
		return REPETITION

	context.user_data["repetition"] = int(repetition)

	# Prompt for Table (0-35)
	keyboard = [
		[InlineKeyboardButton(i18n.t("ALPHABET_ORDER_ABJADI", language), callback_data="0-4")],
		[InlineKeyboardButton(i18n.t("ALPHABET_ORDER_MAGHRIBI", language), callback_data="6-10")],
		[InlineKeyboardButton(i18n.t("ALPHABET_ORDER_QURANIC", language), callback_data="11-15")],
		[InlineKeyboardButton(i18n.t("ALPHABET_ORDER_HIJA", language), callback_data="16-20")],
		[InlineKeyboardButton(i18n.t("ALPHABET_ORDER_MAGHRIBI_HIJA", language), callback_data="21-25")],
		[InlineKeyboardButton(i18n.t("ALPHABET_ORDER_IKLEELS", language), callback_data="26-30")],
		[InlineKeyboardButton(i18n.t("ALPHABET_ORDER_SHAMSE_ABJADI", language), callback_data="31-35")],
		[InlineKeyboardButton(i18n.t("ALPHABET_ORDER_HEBREW", language), callback_data="HE")],
		[InlineKeyboardButton(i18n.t("ALPHABET_ORDER_TURKISH", language), callback_data="TR")],
		[InlineKeyboardButton(i18n.t("ALPHABET_ORDER_ENGLISH", language), callback_data="EN")],
		[InlineKeyboardButton(i18n.t("ALPHABET_ORDER_LATIN", language), callback_data="LA")]
	]
	reply_markup = InlineKeyboardMarkup(keyboard)
	await update.message.reply_text(
		i18n.t("BASTET_PROMPT_TABLE", language),
		reply_markup=reply_markup
	)
	return TABLE

async def bastet_table(update: Update, context: ContextTypes.DEFAULT_TYPE):
	query = update.callback_query
	user_id = query.from_user.id
	db = Database()
	i18n = I18n()
	language = db.get_user_language(user_id)

	table = query.data
	context.user_data["table"] = table

	# Prompt for Language
	keyboard = [
		[InlineKeyboardButton(i18n.t("ABJAD_TYPE_ASGHAR", language), callback_data="-1")],
		[InlineKeyboardButton(i18n.t("ABJAD_TYPE_SAGHIR", language), callback_data="0")],
		[InlineKeyboardButton(i18n.t("ABJAD_TYPE_KEBEER", language), callback_data="+1")],
		[InlineKeyboardButton(i18n.t("ABJAD_TYPE_AKBAR", language), callback_data="+2")],
		[InlineKeyboardButton(i18n.t("ABJAD_TYPE_SAGHIR_PLUS_QUANTITY", language), callback_data="+3")],
		[InlineKeyboardButton(i18n.t("ABJAD_TYPE_LETTER_QUANTITY", language), callback_data="5")]
	]
	reply_markup = InlineKeyboardMarkup(keyboard)
	await query.message.reply_text(
		i18n.t("BASTET_PROMPT_LANGUAGE", language),
		reply_markup=reply_markup
	)
	await query.answer()
	return LANGUAGE

async def bastet_language(update: Update, context: ContextTypes.DEFAULT_TYPE):
	query = update.callback_query
	user_id = query.from_user.id
	db = Database()
	i18n = I18n()
	language = db.get_user_language(user_id)
	db.set_user_attribute(user_id, "last_interaction", datetime.now())
	db.increment_command_usage("bastet", user_id)

	try:
		lang = query.data
		context.user_data["language"] = lang

		number = context.user_data["bastet_number"]
		repetition = context.user_data["repetition"]
		table = context.user_data["table"]
		alphabet_order = table
		abjad_type = lang

		if alphabet_order == '0-4':
			alphabeta = "arabic"
			tablebase = 1
		elif alphabet_order == '6-10':
			alphabeta = "arabic"
			tablebase = 7
		elif alphabet_order == '11-15':
			alphabeta = "arabic"
			tablebase = 12
		elif alphabet_order == '16-20':
			alphabeta = "arabic"
			tablebase = 17
		elif alphabet_order == '21-25':
			alphabeta = "arabic"
			tablebase = 22
		elif alphabet_order == '26-30':
			alphabeta = "arabic"
			tablebase = 27
		elif alphabet_order == '31-35':
			alphabeta = "arabic"
			tablebase = 32
		elif alphabet_order == 'HE':
			alphabeta = "hebrew"
			tablebase = 1
		elif alphabet_order == 'TR':
			alphabeta = "turkish"
			tablebase = 1
		elif alphabet_order == 'EN':
			alphabeta = "english"
			tablebase = 1
		elif alphabet_order == 'LA':
			alphabeta = "latin"
			tablebase = 1

		if abjad_type == '-1':
			tablebase -= 1
		elif abjad_type == '0':
			tablebase = tablebase
		elif abjad_type == '+1':
			tablebase += 1
		elif abjad_type == '+2':
			tablebase += 2
		elif abjad_type == '+3':
			tablebase += 3
		elif abjad_type == '5':
			tablebase = 5

		abjad = Abjad()
		value = number
		result = int(abjad.bastet(
			value,
			int(repetition),
			tablebase,
			1,
			alphabeta,
			0
		))

		if isinstance(result, str) and str(result).startswith("Error"):
			await query.message.reply_text(
				i18n.t("ERROR_GENERAL", language, error=value),
				parse_mode=ParseMode.MARKDOWN
			)
			await query.answer()
			return ConversationHandler.END

		response = i18n.t("BASTET_RESULT", language, number=number, repetition=repetition, table=tablebase, value=result)

		# Check warningNumbers.json
		warning_desc = get_warning_description(value, language)
		if warning_desc:
			response += "\n\n" + i18n.t("WARNING_NUMBER", language, value=value, description=warning_desc)

		# Get AI commentary
		commentary = await get_ai_commentary(response, language)
		if commentary:
			response += "\n\n" + i18n.t("AI_COMMENTARY", language, commentary=commentary)

		# Add buttons
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
		reply_markup = InlineKeyboardMarkup(keyboard)

		await query.message.reply_text(
			response,
			parse_mode=ParseMode.MARKDOWN,
			reply_markup=reply_markup
		)
		await query.answer()
		return ConversationHandler.END

	except Exception as e:
		logger.error(f"Bastet error: {str(e)}")
		await query.message.reply_text(
			i18n.t("ERROR_GENERAL", language),
			parse_mode=ParseMode.MARKDOWN
		)
		await query.answer()
		return ConversationHandler.END

async def bastet_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
	user_id = update.message.from_user.id
	db = Database()
	i18n = I18n()
	language = db.get_user_language(user_id)
	await update.message.reply_text(
		i18n.t("BASTET_CANCEL", language),
		parse_mode=ParseMode.MARKDOWN
	)
	return ConversationHandler.END

def get_bastet_conversation_handler():
	return ConversationHandler(
		entry_points=[CommandHandler("bastet", bastet_start)],
		states={
			REPETITION: [MessageHandler(filters.TEXT & ~filters.COMMAND, bastet_repetition)],
			TABLE: [CallbackQueryHandler(bastet_table)],
			LANGUAGE: [CallbackQueryHandler(bastet_language)],
		},
		fallbacks=[CommandHandler("cancel", bastet_cancel)],
		per_message=False
	)