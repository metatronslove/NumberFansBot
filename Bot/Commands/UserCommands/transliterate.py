from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from telegram.constants import ParseMode
from ...database import Database
from ...i18n import I18n
from ...transliteration import Transliteration
from ...utils import register_user_if_not_exists
from datetime import datetime
import urllib.parse
import logging

logger = logging.getLogger(__name__)

async def transliterate_handle(update: Update, context: ContextTypes.DEFAULT_TYPE):
	user = update.message.from_user
	await register_user_if_not_exists(update, context, user)
	user_id = user.id
	db = Database()
	i18n = I18n()
	language = db.get_user_language(user_id)
	db.set_user_attribute(user_id, "last_interaction", datetime.now())

	db.increment_command_usage("transliterate", user_id)

	args = context.args
	if len(args) < 3:
		await update.message.reply_text(
			i18n.t("TRANSLITERATION_USAGE", language, source_lang="source_lang", target_lang="target_lang", text="text"),
			parse_mode=ParseMode.HTML
		)
		return

	source_lang = args[0].lower()
	target_lang = args[1].lower()
	text = " ".join(args[2:])

	try:
		transliteration = Transliteration(db, i18n)
	except Exception as e:
		logger.error(f"Failed to initialize Transliteration: {str(e)}")
		await update.message.reply_text(
			i18n.t("ERROR_GENERAL", language, error="Failed to initialize transliteration system"),
			parse_mode=ParseMode.HTML
		)
		return

	valid_languages = transliteration.valid_languages

	if source_lang not in valid_languages or target_lang not in valid_languages:
		await update.message.reply_text(
			i18n.t("LANGUAGE_INVALID", language, languages=", ".join(valid_languages)),
			parse_mode=ParseMode.HTML
		)
		return

	try:
		if language == 'en':
			output_lang = "english"
		elif language == 'tr':
			output_lang = "turkish"
		elif language == 'ar':
			output_lang = "arabic"
		elif language == 'he':
			output_lang = "hebrew"
		elif language == 'la':
			output_lang = "latin"
		result = transliteration.transliterate(text, target_lang, source_lang)
		primary = result["primary"]
		suffix = transliteration.get_suffix(primary, text)
		response = transliteration.format_response(suffix, target_lang, output_lang, language)

		transliteration.store_transliteration(text, source_lang, target_lang, primary, user_id=user_id)

		encoded_text = urllib.parse.quote(text)
		buttons = [
			[
				InlineKeyboardButton(
					i18n.t("SELECT_ALTERNATIVE", language),
					callback_data=f"transliterate_suggest_{source_lang}_{target_lang}_{encoded_text}"
				)
			],
			[
				InlineKeyboardButton(
					i18n.t("TRANSLITERATION_HISTORY_USAGE", language),
					callback_data=f"transliterate_history_{user_id}"
				)
			],
		]
		reply_markup = InlineKeyboardMarkup(buttons)

		await update.message.reply_text(
			response,
			parse_mode=ParseMode.HTML,
			reply_markup=reply_markup
		)
	except Exception as e:
		logger.error(f"Transliteration error for user {user_id}: {str(e)}")
		await update.message.reply_text(
			i18n.t("ERROR_INVALID_INPUT", language, error=str(e)),
			parse_mode=ParseMode.HTML
		)