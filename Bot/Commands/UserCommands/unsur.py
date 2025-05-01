import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
	Application, CommandHandler, MessageHandler, CallbackQueryHandler,
	ConversationHandler, filters
)
from telegram.constants import ParseMode
from ...database import Database
from ...i18n import I18n
from ...config import config
from ...Abjad import Abjad
from datetime import datetime
import requests
import re

logger = logging.getLogger(__name__)

# Conversation states
INPUT, LANGUAGE, TABLE, SHADDA = range(4)

async def register_user_if_not_exists(update: Update, context: CallbackContext, user):
	db = Database()
	if not db.check_if_user_exists(user.id):
		db.add_new_user(
			user_id=user.id,
			chat_id=update.message.chat_id,
			username=user.username or "",
			first_name=user.first_name or "",
			last_name=user.last_name or "",
		)

async def get_ai_commentary(response: str, lang: str) -> str:
	i18n = I18n()
	prompt = i18n.t("AI_PROMPT", lang, response=response)
	try:
		headers = {"Authorization": f"Bearer {config.ai_access_token}"}
		payload = {
			"inputs": prompt,
			"parameters": {"max_length": 200, "temperature": 0.7}
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

async def unsur_start(update: Update, context: CallbackContext):
	user = update.message.from_user
	await register_user_if_not_exists(update, context, user)
	user_id = user.id
	db = Database()
	i18n = I18n()
	language = db.get_user_language(user_id)

	# Prompt for Input
	await update.message.reply_text(
		i18n.t("UNSUR_PROMPT_INPUT", language),
		parse_mode=ParseMode.MARKDOWN
	)
	return INPUT

async def unsur_input(update: Update, context: CallbackContext):
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
	# Check if input is Arabic (U+0600–U+06FF)
	is_arabic = bool(re.search(r'[\u0600-\u06FF]', input_text))
	context.user_data["is_arabic"] = is_arabic

	# Prompt for Language
	keyboard = [
		[InlineKeyboardButton(lang.capitalize(), callback_data=lang)]
		for lang in ["arabic", "hebrew", "turkish", "english", "latin"]
	]
	reply_markup = InlineKeyboardMarkup(keyboard)
	await update.message.reply_text(
		i18n.t("UNSUR_PROMPT_LANGUAGE", language),
		reply_markup=reply_markup
	)
	return LANGUAGE

async def unsur_language(update: Update, context: CallbackContext):
	query = update.callback_query
	user_id = query.from_user.id
	db = Database()
	i18n = I18n()
	language = db.get_user_language(user_id)

	lang = query.data
	context.user_data["language"] = lang

	# Prompt for Table (0-35)
	keyboard = [
		[InlineKeyboardButton(str(i), callback_data=str(i)) for i in range(j, min(j + 6, 36))]
		for j in range(0, 36, 6)
	]
	reply_markup = InlineKeyboardMarkup(keyboard)
	await query.message.reply_text(
		i18n.t("UNSUR_PROMPT_TABLE", language),
		reply_markup=reply_markup
	)
	await query.answer()
	return TABLE

async def unsur_table(update: Update, context: CallbackContext):
	query = update.callback_query
	user_id = query.from_user.id
	db = Database()
	i18n = I18n()
	language = db.get_user_language(user_id)

	table = int(query.data)
	context.user_data["table"] = table

	# Prompt for Shadda if Arabic input
	if context.user_data.get("is_arabic"):
		keyboard = [
			[InlineKeyboardButton("1 (Include)", callback_data="1")],
			[InlineKeyboardButton("2 (Exclude)", callback_data="2")]
		]
		reply_markup = InlineKeyboardMarkup(keyboard)
		await query.message.reply_text(
			i18n.t("UNSUR_PROMPT_SHADDA", language),
			reply_markup=reply_markup
		)
		await query.answer()
		return SHADDA
	else:
		context.user_data["shadda"] = 1  # Default
		return await unsur_shadda(update, context)

async def unsur_shadda(update: Update, context: CallbackContext):
	query = update.callback_query
	user_id = query.from_user.id
	db = Database()
	i18n = I18n()
	language = db.get_user_language(user_id)
	db.set_user_attribute(user_id, "last_interaction", datetime.now())
	db.increment_command_usage("unsur", user_id)

	try:
		if query:  # From callback
			shadda = int(query.data)
			context.user_data["shadda"] = shadda
			await query.answer()
		else:
			shadda = context.user_data.get("shadda", 1)

		input_text = context.user_data["input_text"]
		lang = context.user_data["language"]
		table = context.user_data["table"]

		abjad = Abjad()
		if input_text.replace(" ", "").isdigit():
			value = int(input_text.replace(" ", ""))
			output_text = input_text  # Numeric input returns number as text
		else:
			result = abjad.abjad(input_text, tablo=table, shadda=shadda, detail=0, lang=lang)
			if isinstance(result, str) and result.startswith("Error"):
				await (query.message.reply_text if query else update.message.reply_text)(
					i18n.t("ERROR_GENERAL", language, error=result),
					parse_mode=ParseMode.MARKDOWN
				)
				return ConversationHandler.END
			value = result["sum"] if isinstance(result, dict) else result
			output_text = input_text  # Text input returns input text

		# Map to element (fire=0, water=1, air=2, earth=3)
		element_index = value % 4
		elements = {
			0: i18n.t("ELEMENT_FIRE", language),
			1: i18n.t("ELEMENT_WATER", language),
			2: i18n.t("ELEMENT_AIR", language),
			3: i18n.t("ELEMENT_EARTH", language)
		}
		element = elements.get(element_index, i18n.t("ELEMENT_UNKNOWN", language))

		response = i18n.t("UNSUR_RESULT", language, input=input_text, value=value, element=element)

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
			i18n.t("SPELL_NUMBER", language),
			callback_data=f"nutket_{value}_{lang}"
		)])
		if not input_text.replace(" ", "").isdigit():  # Add Calculate Abjad for text input
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
		return ConversationHandler.END

	except Exception as e:
		logger.error(f"Unsur error: {str(e)}")
		await (query.message.reply_text if query else update.message.reply_text)(
			i18n.t("ERROR_GENERAL", language),
			parse_mode=ParseMode.MARKDOWN
		)
		return ConversationHandler.END

async def unsur_cancel(update: Update, context: CallbackContext):
	user_id = update.message.from_user.id
	db = Database()
	i18n = I18n()
	language = db.get_user_language(user_id)
	await update.message.reply_text(
		i18n.t("UNSUR_CANCEL", language),
		parse_mode=ParseMode.MARKDOWN
	)
	return ConversationHandler.END

def get_unsur_conversation_handler():
	return ConversationHandler(
		entry_points=[CommandHandler("unsur", unsur_start)],
		states={
			INPUT: [MessageHandler(filters.TEXT & ~filters.COMMAND, unsur_input)],
			LANGUAGE: [CallbackQueryHandler(unsur_language)],
			TABLE: [CallbackQueryHandler(unsur_table)],
			SHADDA: [CallbackQueryHandler(unsur_shadda)],
		},
		fallbacks=[CommandHandler("cancel", unsur_cancel)],
	)