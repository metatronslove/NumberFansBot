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
from ...element_classifier import ElementClassifier
from ...utils import register_user_if_not_exists
from datetime import datetime
import requests
import re

logger = logging.getLogger(__name__)

INPUT, LANGUAGE, TABLE, SHADDA = range(4)

async def get_ai_commentary(response: str, lang: str) -> str:
    i18n = I18n()
    prompt = i18n.t("AI_PROMPT", lang, response=response)
    try:
        headers = {"Authorization": f"Bearer {config.huggingface_access_token}"}
        payload = {
            "inputs": prompt,
            "parameters": {"max_length": 200, "temperature": 0.7}
        }
        api_response = requests.post(
            config.ai_model_url,
            headers=headers,
            json=payload
        )
        if api_response.status_code == 200:
            generated_text = api_response.json()[0]["generated_text"]
            logger.debug(f"Raw generated text: {generated_text}")
            # Strip the prompt, optionally followed by [/INST], and any leading/trailing whitespace
            cleaned_text = re.sub(
                rf"^{re.escape(prompt)}(?:\s*\[\/INST\])?\s*",
                "",
                generated_text,
                flags=re.DOTALL
            ).strip()
            logger.debug(f"Cleaned text: {cleaned_text}")
            return cleaned_text
        else:
            logger.error(f"AI API error: Status code {api_response.status_code}, Response: {api_response.text}")
            return ""
    except KeyError as e:
        logger.error(f"AI commentary error: Invalid response format, missing key {e}")
        return ""
    except Exception as e:
        logger.error(f"AI commentary error: {str(e)}")
        return ""

async def unsur_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
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

async def unsur_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
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
		[InlineKeyboardButton(i18n.t("ALPHABET_ORDER_TURKISH", language), callback_data="TURKCE")],
		[InlineKeyboardButton(i18n.t("ALPHABET_ORDER_ARABI", language), callback_data="ARABI")],
		[InlineKeyboardButton(i18n.t("ALPHABET_ORDER_BUNI", language), callback_data="BUNI")],
		[InlineKeyboardButton(i18n.t("ALPHABET_ORDER_HUSEYNI", language), callback_data="HUSEYNI")],
		[InlineKeyboardButton(i18n.t("ALPHABET_ORDER_HEBREW", language), callback_data="HEBREW")],
		[InlineKeyboardButton(i18n.t("ALPHABET_ORDER_ENGLISH", language), callback_data="ENGLISH")],
		[InlineKeyboardButton(i18n.t("ALPHABET_ORDER_LATIN", language), callback_data="LATIN")],
		[InlineKeyboardButton(i18n.t("ALPHABET_ORDER_DEFAULT", language), callback_data="DEFAULT")]
	]
	reply_markup = InlineKeyboardMarkup(keyboard)
	await update.message.reply_text(
		i18n.t("UNSUR_PROMPT_LANGUAGE", language),
		reply_markup=reply_markup
	)
	return LANGUAGE

async def unsur_language(update: Update, context: ContextTypes.DEFAULT_TYPE):
	query = update.callback_query
	user_id = query.from_user.id
	db = Database()
	i18n = I18n()
	language = db.get_user_language(user_id)

	lang = query.data
	context.user_data["language"] = lang

	# List or Quantity
	keyboard = [
		[InlineKeyboardButton(i18n.t("ELEMENT_FIRE", language), callback_data="fire")],
		[InlineKeyboardButton(i18n.t("ELEMENT_WATER", language), callback_data="water")],
		[InlineKeyboardButton(i18n.t("ELEMENT_AIR", language), callback_data="air")],
		[InlineKeyboardButton(i18n.t("ELEMENT_EARTH", language), callback_data="earth")]
	]
	reply_markup = InlineKeyboardMarkup(keyboard)
	await query.message.reply_text(
		i18n.t("UNSUR_PROMPT_TABLE", language),
		reply_markup=reply_markup
	)
	await query.answer()
	return TABLE

async def unsur_table(update: Update, context: ContextTypes.DEFAULT_TYPE):
	query = update.callback_query
	user_id = query.from_user.id
	db = Database()
	i18n = I18n()
	language = db.get_user_language(user_id)

	table = query.data
	context.user_data["table"] = table

	# Prompt for Shadda if Arabic input
	if context.user_data.get("is_arabic"):
		keyboard = [
			[InlineKeyboardButton(i18n.t("SHADDA_USE_ONCE", language), callback_data="1")],
			[InlineKeyboardButton(i18n.t("SHADDA_USE_TWICE", language), callback_data="2")]
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

async def unsur_shadda(update: Update, context: ContextTypes.DEFAULT_TYPE):
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

		unsur = ElementClassifier()
		result = unsur.classify_elements(input_text, table, shadda, lang)
		if isinstance(result, str) and result.startswith("Error"):
			await (query.message.reply_text if query else update.message.reply_text)(
				i18n.t("ERROR_GENERAL", language, error=result),
				parse_mode=ParseMode.MARKDOWN
			)
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

async def unsur_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
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
		per_message=False
	)