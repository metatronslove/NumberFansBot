from telegram import Update
from telegram.ext import CallbackContext
from telegram.constants import ParseMode
from ...admin_panel import config
from ...database import Database
from ...i18n import I18n
from datetime import datetime

config = config

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

async def language_handle(update: Update, context: CallbackContext):
	user = update.message.from_user
	await register_user_if_not_exists(update, context, user)
	user_id = user.id
	db = Database()
	i18n = I18n()
	telegram_lang = user.language_code or "en"
	current_lang = db.get_user_language(user_id) or telegram_lang

	if current_lang not in config.available_languages:
		current_lang = "en"

	# Increment command usage
	db.increment_command_usage("language", user_id)

	try:
		args = context.args
		lang_code = args[0].lower() if args else ""

		if not lang_code:
			await show_language_selection(update, current_lang)
			return

		if lang_code not in config.available_languages:
			await update.message.reply_text(
				i18n.t("LANGUAGE_INVALID", current_lang, languages=", ".join(config.available_languages)),
				parse_mode=ParseMode.MARKDOWN
			)
			return

		db.set_user_language(user_id, lang_code)
		db.set_user_attribute(user_id, "last_interaction", datetime.now())

		await update.message.reply_text(
			i18n.t("LANGUAGE_CHANGED", lang_code, selected_lang=lang_code.upper()),
			parse_mode=ParseMode.MARKDOWN
		)

	except Exception as e:
		logger.error(f"LanguageCommand error: {str(e)}")
		await update.message.reply_text(
			i18n.t("LANGUAGE_ERROR_GENERAL", current_lang),
			parse_mode=ParseMode.MARKDOWN
		)