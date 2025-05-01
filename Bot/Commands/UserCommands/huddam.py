import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
	Application, CommandHandler, MessageHandler, CallbackQueryHandler,
	ConversationHandler, filters, CallbackContext
)
from telegram.constants import ParseMode
from ...database import Database
from ...i18n import I18n
from ...config import config
from ...Abjad import Abjad
from datetime import datetime
import requests

logger = logging.getLogger(__name__)

# Conversation states
ENTITY_TYPE, LANGUAGE = range(2)

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

async def huddam_start(update: Update, context: CallbackContext):
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

	# Prompt for Entity Type
	keyboard = [
		[InlineKeyboardButton("Ulvi", callback_data="ulvi")],
		[InlineKeyboardButton("Sufli", callback_data="sufli")]
	]
	reply_markup = InlineKeyboardMarkup(keyboard)
	await update.message.reply_text(
		i18n.t("HUDDAM_PROMPT_ENTITY_TYPE", language),
		reply_markup=reply_markup
	)
	return ENTITY_TYPE

async def huddam_entity_type(update: Update, context: CallbackContext):
	query = update.callback_query
	user_id = query.from_user.id
	db = Database()
	i18n = I18n()
	language = db.get_user_language(user_id)

	entity_type = query.data
	context.user_data["entity_type"] = entity_type

	# Prompt for Language
	keyboard = [
		[InlineKeyboardButton(lang.capitalize(), callback_data=lang)]
		for lang in ["arabic", "hebrew", "turkish", "english", "latin"]
	]
	reply_markup = InlineKeyboardMarkup(keyboard)
	await query.message.reply_text(
		i18n.t("HUDDAM_PROMPT_LANGUAGE", language),
		reply_markup=reply_markup
	)
	await query.answer()
	return LANGUAGE

async def huddam_language(update: Update, context: CallbackContext):
	query = update.callback_query
	user_id = query.from_user.id
	db = Database()
	i18n = I18n()
	language = db.get_user_language(user_id)
	db.set_user_attribute(user_id, "last_interaction", datetime.now())
	db.increment_command_usage("huddam", user_id)

	try:
		lang = query.data
		context.user_data["language"] = lang

		number = context.user_data["huddam_number"]
		entity_type = context.user_data["entity_type"]

		abjad = Abjad()
		result = abjad.huddam(number, type=entity_type, lang=lang)

		if isinstance(result, str) and result.startswith("Error"):
			await query.message.reply_text(
				i18n.t("ERROR_GENERAL", language, error=result),
				parse_mode=ParseMode.MARKDOWN
			)
			await query.answer()
			return ConversationHandler.END

		# Assume result is a dict with name and value
		name = result.get("name", result) if isinstance(result, dict) else result
		value = result.get("value", number) if isinstance(result, dict) else number

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

async def huddam_cancel(update: Update, context: CallbackContext):
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
		},
		fallbacks=[CommandHandler("cancel", huddam_cancel)],
	)