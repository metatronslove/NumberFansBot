import logging
import urllib.parse
from Bot.config import Config  # Updated import
from Bot.database import Database
from Bot.i18n import I18n
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
	Application, CommandHandler, MessageHandler, CallbackQueryHandler,
	ConversationHandler, filters, ContextTypes
)
from telegram.constants import ParseMode
from telegram.error import BadRequest
from Bot.Numerology import UnifiedNumerology
from Bot.utils import register_user_if_not_exists, get_warning_description, get_ai_commentary
from datetime import datetime

logger = logging.getLogger(__name__)

async def numerology_handle(update: Update, context: ContextTypes.DEFAULT_TYPE):
	user = update.message.from_user
	await register_user_if_not_exists(update, context, user)
	user_id = user.id
	db = Database()
	i18n = I18n()
	language = db.get_user_language(user_id)
	db.set_user_attribute(user_id, "last_interaction", datetime.now())

	db.increment_command_usage("numerology", user_id)

	args = context.args
	if not args:
		await update.message.reply_text(
			i18n.t("NUMEROLOGY_USAGE", language),
			parse_mode=ParseMode.HTML
		)
		return

	text = " ".join(args)
	encoded_text = urllib.parse.quote(text)
	numerology = UnifiedNumerology()
	available_alphabets = ["turkish", "arabic_abjadi", "arabic_hija", "hebrew", "latin"]

	if len(args) < 2 or args[-1].lower() not in numerology.get_available_alphabets():
		buttons = [
			[InlineKeyboardButton(
				i18n.t(f"LANGUAGE_NAME_{lang.upper()}", language),
				callback_data=f"numerology_prompt_{encoded_text}_normal_{lang}"
			)] for lang in available_alphabets
		]
		reply_markup = InlineKeyboardMarkup(buttons)
		await update.message.reply_text(
			i18n.t("NUMEROLOGY_PROMPT_ALPHABET", language),
			parse_mode=ParseMode.HTML,
			reply_markup=reply_markup
		)
		return

	try:
		alphabet = args[-1].lower()
		method = args[-2].lower() if len(args) >= 2 and args[-2].lower() in numerology.get_available_methods() else "normal"
		text = " ".join(args[:-2]) if len(args) >= 2 else text

		if alphabet not in available_alphabets:
			await update.message.reply_text(
				i18n.t("ERROR_INVALID_INPUT", language, error=f"Invalid alphabet. Use: {', '.join(available_alphabets)}"),
				parse_mode=ParseMode.HTML
			)
			return

		result = numerology.numerolog(text, alphabet=alphabet, method=method, detail=False)
		if isinstance(result, dict) and "error" in result:
			await update.message.reply_text(
				i18n.t("ERROR_INVALID_INPUT", language, error=result["error"]),
				parse_mode=ParseMode.HTML
			)
			return

		response = i18n.t("NUMEROLOGY_RESULT", language, text=text, alphabet=alphabet, method=method, value=result)

		warning_desc = get_warning_description(result, language)
		if warning_desc:
			response += "\n\n" + i18n.t("WARNING_NUMBER", language, value=result, description=warning_desc)

		commentary = await get_ai_commentary(response, language)
		if commentary:
			response += "\n\n" + i18n.t("AI_COMMENTARY", language, commentary=commentary)

		buttons = [
			[InlineKeyboardButton(
				f"Method: {m.capitalize()}",
				callback_data=f"numerology_{encoded_text}_{alphabet}_{m}"
			)] for m in numerology.get_available_methods() if m != method
		]
		if result >= 15:
			buttons.append([InlineKeyboardButton(
				i18n.t("CREATE_MAGIC_SQUARE", language),
				callback_data=f"magic_square_{result}"
			)])
		reply_markup = InlineKeyboardMarkup(buttons) if buttons else None

		await update.message.reply_text(
			response,
			parse_mode=ParseMode.MARKDOWN,
			reply_markup=reply_markup
		)
	except Exception as e:
		await update.message.reply_text(
			i18n.t("ERROR_GENERAL", language, error=str(e)),
			parse_mode=ParseMode.HTML
		)