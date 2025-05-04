import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from telegram.constants import ParseMode
from Bot.config import Config  # Updated import
from Bot.database import Database
from Bot.i18n import I18n
from Bot.utils import register_user_if_not_exists
from datetime import datetime
from .language import language_handle

logger = logging.getLogger(__name__)

async def start_handle(update: Update, context: ContextTypes.DEFAULT_TYPE):
	user = update.message.from_user
	user_language = user.language_code.split('-')[0] if user.language_code else 'en'
	await register_user_if_not_exists(update, context, user, language=user_language)
	user_id = user.id
	db = Database()
	i18n = I18n()

	try:
		if user_language in ['en', 'tr', 'ar', 'he', 'la']:
			language = user_language
			context.args = [language]
			await language_handle(update, context)
		else:
			language = 'en'
			db.set_user_attribute(user_id, "language", language)

		db.set_user_attribute(user_id, "last_interaction", datetime.now())
		db.increment_command_usage("start", user_id)

		reply_text = i18n.t("START_MESSAGE", language)
		reply_text += "\n" + i18n.t("HELP_MESSAGE", language)
		await update.message.reply_text(reply_text, parse_mode=ParseMode.HTML)
	except Exception as e:
		logger.error(f"StartCommand error: {str(e)}")
		await update.message.reply_text(
			i18n.t("ERROR_GENERAL", language, error=str(e)),
			parse_mode=ParseMode.HTML
		)