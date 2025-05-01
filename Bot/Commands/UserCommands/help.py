from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CallbackContext
from telegram.constants import ParseMode
from ...database import Database
from ...i18n import I18n
from datetime import datetime
from ...config import Config

async def register_user_if_not_exists(update: Update, context: CallbackContext, user, language):
	config = Config()
	db = Database()
	# Store user in database if not exists
	if not db.user_collection.find_one({"telegram_id": user.id}):
		db.user_collection.insert_one({
			"telegram_id": user.id,
			"username": user.username,
			"first_name": user.first_name,
			"last_name": user.last_name,
			"language_code": language,
			"is_beta_tester": False
		})

async def help_handle(update: Update, context: CallbackContext):
	config = Config()
	user = update.message.from_user

	# Get user's Telegram language code and normalize it
	user_language = user.language_code.split('-')[0] if user.language_code else 'en'
	available_languages = ['en', 'tr', 'ar', 'he', 'la']
	await register_user_if_not_exists(update, context, user, user_language)
	user_id = user.id
	db = Database()
	i18n = I18n()
	language = db.get_user_language(user_id)
	db.set_user_attribute(user_id, "last_interaction", datetime.now())

	# Increment command usage
	db.increment_command_usage("help", user_id)

	# Add button for group chat help
	buttons = [[InlineKeyboardButton(
		i18n.t("HELP_GROUP_CHAT_USAGE", language),
		callback_data="help_group_chat"
	)]]
	reply_markup = InlineKeyboardMarkup(buttons)

	await update.message.reply_text(
		i18n.t("HELP_MESSAGE", language),
		parse_mode=ParseMode.HTML,
		reply_markup=reply_markup
	)