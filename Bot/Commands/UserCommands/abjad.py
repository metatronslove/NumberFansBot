import logging
import requests
import re
import aiohttp
import asyncio
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

logger = logging.getLogger(__name__)

ALPHABET_ORDER, ABJAD_TYPE, SHADDA, DETAIL = range(4)

async def get_ai_commentary(response: str, lang: str) -> str:
    i18n = I18n()
    prompt = i18n.t("AI_PROMPT", lang, response=response)
    try:
        headers = {"Authorization": f"Bearer {config.ai_access_token}"}
        payload = {
            "inputs": prompt,
            "parameters": {"max_length": 200, "temperature": 0.7}
        }
        async with aiohttp.ClientSession() as session:
            async with session.post(config.ai_model_url, headers=headers, json=payload) as api_response:
                if api_response.status == 200:
                    data = await api_response.json()
                    generated_text = data[0]["generated_text"]
                    logger.debug(f"Raw generated text: {generated_text}")
                    cleaned_text = re.sub(
                        rf"^{re.escape(prompt)}(?:\s*\[\/INST\])?\s*",
                        "",
                        generated_text,
                        flags=re.DOTALL
                    ).strip()
                    logger.debug(f"Cleaned text: {cleaned_text}")
                    return cleaned_text
                else:
                    logger.error(f"Hugging Face API error: Status code {api_response.status}, Response: {await api_response.text()}")
                    return ""
    except KeyError as e:
        logger.error(f"AI commentary error: Invalid response format, missing key {e}")
        return ""
    except Exception as e:
        logger.error(f"AI commentary error: {str(e)}")
        return ""

async def abjad_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
	user = update.message.from_user
	await register_user_if_not_exists(update, context, user)
	user_id = user.id
	db = Database()
	i18n = I18n()
	language = db.get_user_language(user_id)

	args = context.args
	if not args:
		await update.message.reply_text(
			i18n.t("ABJAD_USAGE", language),
			parse_mode=ParseMode.MARKDOWN
		)
		return ConversationHandler.END

	text = " ".join(args)
	context.user_data["abjad_text"] = text

	is_arabic = bool(re.search(r'[\u0600-\u06FF]', text))
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
		i18n.t("ABJAD_PROMPT_ALPHABET", language),
		reply_markup=reply_markup
	)
	context.user_data["is_arabic"] = is_arabic
	return ALPHABET_ORDER

async def abjad_alphabet_order(update: Update, context: ContextTypes.DEFAULT_TYPE):
	query = update.callback_query
	user_id = query.from_user.id
	db = Database()
	i18n = I18n()
	language = db.get_user_language(user_id)

	alphabet_order = query.data
	context.user_data["alphabet_order"] = alphabet_order

	# Prompt for Abjad Type
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
		i18n.t("ABJAD_PROMPT_TYPE", language),
		reply_markup=reply_markup
	)
	await query.answer()
	return ABJAD_TYPE

async def abjad_type(update: Update, context: ContextTypes.DEFAULT_TYPE):
	query = update.callback_query
	user_id = query.from_user.id
	db = Database()
	i18n = I18n()
	language = db.get_user_language(user_id)

	abjad_type = query.data
	context.user_data["abjad_type"] = abjad_type

	# Prompt for Shadda if Arabic text
	if context.user_data.get("is_arabic"):
		keyboard = [
			[InlineKeyboardButton(i18n.t("SHADDA_USE_ONCE", language), callback_data="1")],
			[InlineKeyboardButton(i18n.t("SHADDA_USE_TWICE", language), callback_data="2")]
		]
		reply_markup = InlineKeyboardMarkup(keyboard)
		await query.message.reply_text(
			i18n.t("ABJAD_PROMPT_SHADDA", language),
			reply_markup=reply_markup
		)
		await query.answer()
		return SHADDA
	else:
		context.user_data["shadda"] = 1
		return await abjad_shadda(update, context)

async def abjad_shadda(update: Update, context: ContextTypes.DEFAULT_TYPE):
	query = update.callback_query
	user_id = query.from_user.id
	db = Database()
	i18n = I18n()
	language = db.get_user_language(user_id)

	if query:
		shadda = int(query.data)
		context.user_data["shadda"] = shadda
		await query.answer()
	else:
		shadda = context.user_data.get("shadda", 1)

	# Prompt for Detail
	keyboard = [
		[InlineKeyboardButton(i18n.t("ABJAD-ONLY-RESULT", language), callback_data="0")],
		[InlineKeyboardButton(i18n.t("ABJAD-WITH-DETAILS", language), callback_data="1")]
	]
	reply_markup = InlineKeyboardMarkup(keyboard)
	await (query.message.reply_text if query else update.message.reply_text)(
		i18n.t("ABJAD_PROMPT_DETAIL", language),
		reply_markup=reply_markup
	)
	return DETAIL

async def abjad_detail(update: Update, context: ContextTypes.DEFAULT_TYPE):
	query = update.callback_query
	user_id = query.from_user.id
	db = Database()
	i18n = I18n()
	language = db.get_user_language(user_id)
	db.set_user_attribute(user_id, "last_interaction", datetime.now())
	db.increment_command_usage("abjad", user_id)

	try:
		detail = int(query.data)
		context.user_data["detail"] = detail
		text = context.user_data["abjad_text"]
		alphabet_order = context.user_data["alphabet_order"]
		abjad_type = context.user_data["abjad_type"]
		shadda = context.user_data["shadda"]

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
		result = abjad.abjad(
			text,
			tablebase,
			int(shadda),
			detail,
			alphabeta
		)

		if isinstance(result, str) and result.startswith("Error"):
			await query.message.reply_text(
				i18n.t("ERROR_GENERAL", language, error=result),
				parse_mode=ParseMode.MARKDOWN
			)
			await query.answer()
			return ConversationHandler.END

		value = result["sum"] if isinstance(result, dict) else result
		detail_json = result.get("details", "") if isinstance(result, dict) and detail == 1 else ""
		details = "".join(f"\[{d['char']}={d['value']}]" for d in detail_json) if isinstance(result, dict) and detail == 1 else ""


		response = i18n.t("ABJAD_RESULT", language, text=text, value=value)
		if details:
			response += "\n" + i18n.t("ABJAD_DETAILS", language, details=details)

		# Check warningNumbers.json when detail=0
		if detail == 0:
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
			callback_data=f"nutket_{value}_{alphabeta}"
		)])
		if details:
			keyboard.append([InlineKeyboardButton(
				i18n.t("SHOW_DETAILS", language),
				callback_data=f"abjad_details_{user_id}"
			)])
		reply_markup = InlineKeyboardMarkup(keyboard)

		await query.message.reply_text(
			response,
			parse_mode=ParseMode.MARKDOWN,
			reply_markup=reply_markup
		)
		context.user_data["abjad_result"] = result

		await query.answer()
		return ConversationHandler.END

	except Exception as e:
		logger.error(f"Abjad error: {str(e)}")
		await query.message.reply_text(
			i18n.t("ERROR_GENERAL", language),
			parse_mode=ParseMode.MARKDOWN
		)
		await query.answer()
		return ConversationHandler.END

async def abjad_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
	user_id = update.message.from_user.id
	db = Database()
	i18n = I18n()
	language = db.get_user_language(user_id)
	await update.message.reply_text(
		i18n.t("ABJAD_CANCEL", language),
		parse_mode=ParseMode.MARKDOWN
	)
	return ConversationHandler.END

def get_abjad_conversation_handler():
	return ConversationHandler(
		entry_points=[CommandHandler("abjad", abjad_start)],
		states={
			ALPHABET_ORDER: [CallbackQueryHandler(abjad_alphabet_order)],
			ABJAD_TYPE: [CallbackQueryHandler(abjad_type)],
			SHADDA: [CallbackQueryHandler(abjad_shadda)],
			DETAIL: [CallbackQueryHandler(abjad_detail)],
		},
		fallbacks=[CommandHandler("cancel", abjad_cancel)],
		per_message=False
	)