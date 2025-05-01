from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CallbackContext
from telegram.constants import ParseMode
from ...database import Database
from ...i18n import I18n
from ...transliteration import Transliteration
from datetime import datetime

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

async def suggest_transliteration_handle(update: Update, context: CallbackContext):
	user = update.message.from_user
	await register_user_if_not_exists(update, context, user)
	user_id = user.id
	db = Database()
	i18n = I18n()
	language = db.get_user_language(user_id)
	db.set_user_attribute(user_id, "last_interaction", datetime.now())

	# Increment command usage
	db.increment_command_usage("suggest_transliteration", user_id)

	args = context.args
	if len(args) < 1:
		await update.message.reply_text(
			i18n.t("SUGGEST_TRANSLITERATION_USAGE", language),
			parse_mode=ParseMode.HTML
		)
		return

	text = " ".join(args[:-2]) if len(args) > 2 else args[0]
	source_lang = args[-2].lower() if len(args) >= 2 else None
	target_lang = args[-1].lower() if len(args) >= 1 else "english"

	transliteration = Transliteration(db, i18n)
	valid_languages = transliteration.valid_languages

	if target_lang not in valid_languages:
		await update.message.reply_text(
			i18n.t("ERROR_INVALID_INPUT", language, error=f"Invalid target language. Use: {', '.join(valid_languages)}"),
			parse_mode=ParseMode.HTML
		)
		return

	try:
		source_lang = source_lang or transliteration.guess_source_lang(text)
		suggestions = transliteration.suggest_transliterations(text, source_lang, target_lang)
		results = ", ".join(suggestions)
		response = i18n.t("SUGGEST_TRANSLITERATION_RESULT", language, text=text, source_lang=source_lang, target_lang=target_lang, results=results)

		# Add buttons for selecting a suggestion
		buttons = [
			[InlineKeyboardButton(s, callback_data=f"name_alt_{text}_{target_lang}_{s}")]
			for s in suggestions
		]
		reply_markup = InlineKeyboardMarkup(buttons) if buttons else None

		await update.message.reply_text(
			response,
			parse_mode=ParseMode.MARKDOWN,
			reply_markup=reply_markup
		)
	except Exception as e:
		await update.message.reply_text(
			i18n.t("ERROR_INVALID_INPUT", language, error=str(e)),
			parse_mode=ParseMode.HTML
		)