import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CallbackContext
from telegram.constants import ParseMode
from ...database import Database
from ...i18n import I18n
from datetime import datetime
from .language import language_handle
from ...config import Config

# Set up logging
logger = logging.getLogger(__name__)
config = Config()

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

async def start_handle(update: Update, context: CallbackContext):
	user = update.message.from_user
	await register_user_if_not_exists(update, context, user)
	user_id = user.id
	db = Database()
	i18n = I18n()

	# Store user in database if not exists
	if not db.user_collection.find_one({"telegram_id": user.id}):
		db.user_collection.insert_one({
			"telegram_id": user.id,
			"username": user.username,
			"first_name": user.first_name,
			"last_name": user.last_name,
			"language_code": lang,
			"is_beta_tester": False
		})

	# Get user's Telegram language code and normalize it
	user_language = user.language_code.split('-')[0] if user.language_code else 'en'
	available_languages = ['en', 'tr', 'ar', 'he', 'la']

	# Set language: use user's Telegram language if supported, else default to 'en'
	try:
		if user_language in available_languages:
			language = user_language
			# Simulate /language command by calling language_handle
			context.args = [language]
			await language_handle(update, context)
		else:
			language = 'en'
			db.set_user_attribute(user_id, "language", language)

		# Update last interaction
		db.set_user_attribute(user_id, "last_interaction", datetime.now())

		# Increment command usage
		db.increment_command_usage("start", user_id)

		# Send welcome message in the selected language
		reply_text = i18n.t("START_MESSAGE", language)
		reply_text += "\n" + i18n.t("HELP_MESSAGE", language)
		await update.message.reply_text(reply_text, parse_mode=ParseMode.HTML)
	except Exception as e:
		logger.error(f"StartCommand error: {str(e)}")
		await update.message.reply_text(
			i18n.t("ERROR_GENERAL", language, error=str(e)),
			parse_mode=ParseMode.HTML
		)