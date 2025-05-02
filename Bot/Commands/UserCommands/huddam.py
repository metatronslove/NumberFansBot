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
from ...utils import register_user_if_not_exists
from datetime import datetime
import requests

logger = logging.getLogger(__name__)

ENTITY_TYPE, MULTIPLIAR, LANGUAGE = range(3)

async def get_ai_commentary(response: str, lang: str) -> str:
	i18n = I18n()
	prompt = i18n.t("AI_PROMPT", lang, response=response)
	try:
		headers = {"Authorization": f"Bearer {config.ai_access_token}"}
		payload = {
			"inputs": prompt,
			"parameters": {"max_length": 200, "temperature": 0.7}
            "return_prompt": False  # Try to exclude prompt in output
		}
		response = requests.post(
			config.ai_model_url,
			headers=headers,
			json=payload
		)
		if response.status_code == 200:
			return response.json()[0]["generated_text"].split("[/INST]")[-1].strip()
		else:
			logger.error(f"AI API error: {response.status_code}")
			return ""
	except Exception as e:
		logger.error(f"AI commentary error: {str(e)}")
		return ""

async def huddam_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
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
		[InlineKeyboardButton("Ulvi", callback_data="ulvi")],
		[InlineKeyboardButton("Sufli", callback_data="sufli")],
		[InlineKeyboardButton("Şer", callback_data="ser")]
	]
	reply_markup = InlineKeyboardMarkup(keyboard)
	await update.message.reply_text(
		i18n.t("HUDDAM_PROMPT_ENTITY_TYPE", language),
		reply_markup=reply_markup
	)
	return ENTITY_TYPE

async def huddam_entity_type(update: Update, context: ContextTypes.DEFAULT_TYPE):
	query = update.callback_query
	user_id = query.from_user.id
	db = Database()
	i18n = I18n()
	language = db.get_user_language(user_id)

	entity_type = query.data
	context.user_data["entity_type"] = entity_type

	# Prompt for Language
	keyboard = [
		[InlineKeyboardButton(lang, callback_data=lang)]
		for lang in ["0-4", "6-10", "11-15", "16-20", "21-25", "26-30", "31-35", "HE", "TR", "EN", "LA"]
	]
	reply_markup = InlineKeyboardMarkup(keyboard)
	await query.message.reply_text(
		i18n.t("HUDDAM_PROMPT_LANGUAGE", language),
		reply_markup=reply_markup
	)
	await query.answer()
	return LANGUAGE

async def huddam_language(update: Update, context: ContextTypes.DEFAULT_TYPE):
	query = update.callback_query
	user_id = query.from_user.id
	db = Database()
	i18n = I18n()
	language = db.get_user_language(user_id)

	lang = query.data
	context.user_data["language"] = lang

	number = context.user_data["huddam_number"]
	entity_type = context.user_data["entity_type"]


	# Prompt for Language
	keyboard = [
		[InlineKeyboardButton("Mode 1", callback_data="regular")],
		[InlineKeyboardButton("Mode 2", callback_data="eacher")]
	]
	reply_markup = InlineKeyboardMarkup(keyboard)
	await query.message.reply_text(
		i18n.t("HUDDAM_PROMPT_MULTIPLIAR", language),
		reply_markup=reply_markup
	)
	await query.answer()
	return MULTIPLIAR

async def huddam_multipliar(update: Update, context: ContextTypes.DEFAULT_TYPE):
	query = update.callback_query
	user_id = query.from_user.id
	db = Database()
	i18n = I18n()
	language = db.get_user_language(user_id)
	db.set_user_attribute(user_id, "last_interaction", datetime.now())
	db.increment_command_usage("huddam", user_id)

	try:
		multipliar = query.data
		context.user_data["multipliar"] = multipliar

		lang = context.user_data["language"]
		number = context.user_data["huddam_number"]
		entity_type = context.user_data["entity_type"]
		alphabet_order = lang

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
		method = tablebase

		abjad = Abjad()
		result = abjad.generate_name(number,
			entity_type,
			method,
			alphabeta,
			multipliar
		)
		if isinstance(result, str) and result.startswith("Error"):
			await query.message.reply_text(
				i18n.t("ERROR_GENERAL", language, error=result),
				parse_mode=ParseMode.MARKDOWN
			)
			await query.answer()
			return ConversationHandler.END

		# Assume result is name
		name = result
		value = number
		response = i18n.t("HUDDAM_RESULT", language, number=number, type=entity_type, lang=lang, name=name)

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
		keyboard.append([InlineKeyboardButton(
			i18n.t("CALCULATE_ABJAD", language),
			callback_data=f"abjad_text_{name}_{lang}"
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
		logger.error(f"Huddam error: {str(e)}")
		await query.message.reply_text(
			i18n.t("ERROR_GENERAL", language),
			parse_mode=ParseMode.MARKDOWN
		)
		await query.answer()
		return ConversationHandler.END

async def huddam_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
	user_id = update.message.from_user.id
	db = Database()
	i18n = I18n()
	language = db.get_user_language(user_id)
	await update.message.reply_text(
		i18n.t("HUDDAM_CANCEL", language),
		parse_mode=ParseMode.MARKDOWN
	)
	return ConversationHandler.END

def get_huddam_conversation_handler():
	return ConversationHandler(
		entry_points=[CommandHandler("huddam", huddam_start)],
		states={
			ENTITY_TYPE: [CallbackQueryHandler(huddam_entity_type)],
			LANGUAGE: [CallbackQueryHandler(huddam_language)],
			MULTIPLIAR: [CallbackQueryHandler(huddam_multipliar)]
		},
		fallbacks=[CommandHandler("cancel", huddam_cancel)],
		per_message=False
	)