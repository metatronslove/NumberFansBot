from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CallbackContext
from telegram.constants import ParseMode
from ...database import Database
from ...i18n import I18n
from ...transliteration import Transliteration
from datetime import datetime
import urllib.parse

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

async def transliterate_handle(update: Update, context: CallbackContext):
	user = update.message.from_user
	await register_user_if_not_exists(update, context, user)
	user_id = user.id
	db = Database()
	i18n = I18n()
	language = db.get_user_language(user_id)
	db.set_user_attribute(user_id, "last_interaction", datetime.now())

	# Increment command usage
	db.increment_command_usage("transliterate", user_id)

	args = context.args
	if len(args) < 3:
		await update.message.reply_text(
			i18n.t("TRANSLITERATION_USAGE", language),
			parse_mode=ParseMode.HTML
		)
		return

	source_lang = args[0].lower()
	target_lang = args[1].lower()
	text = " ".join(args[2:])

	transliteration = Transliteration(db, i18n)
	valid_languages = transliteration.valid_languages

	if source_lang not in valid_languages or target_lang not in valid_languages:
		await update.message.reply_text(
			i18n.t("LANGUAGE_INVALID", language, languages=", ".join(valid_languages)),
			parse_mode=ParseMode.HTML
		)
		return

	try:
		result = transliteration.transliterate(text, target_lang, source_lang)
		primary = result["primary"]
		transliteration.store_transliteration(text, source_lang, target_lang, primary, user_id=user_id)

		# Add buttons for suggestions and history
		encoded_text = urllib.parse.quote(text)
		buttons = [
			[InlineKeyboardButton(
				i18n.t("SELECT_ALTERNATIVE", language),
				callback_data=f"transliterate_suggest_{source_lang}_{target_lang}_{encoded_text}"
			)],
			[InlineKeyboardButton(
				i18n.t("TRANSLITERATION_HISTORY_USAGE", language),
				callback_data=f"transliterate_history_{user_id}"
			)]
		]
		reply_markup = InlineKeyboardMarkup(buttons)

		await update.message.reply_text(
			response,
			parse_mode=ParseMode.HTML,
			reply_markup=reply_markup
		)
	except Exception as e:
		await update.message.reply_text(
			i18n.t("ERROR_INVALID_INPUT", language, error=str(e)),
			parse_mode=ParseMode.HTML
		)