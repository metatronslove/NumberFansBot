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
from Bot.transliteration import Transliteration
from Bot.utils import register_user_if_not_exists
from datetime import datetime

async def settings_handle(update: Update, context: ContextTypes.DEFAULT_TYPE):
	user = update.message.from_user
	await register_user_if_not_exists(update, context, user)
	user_id = user.id
	db = Database()
	i18n = I18n()
	language = db.get_user_language(user_id)
	db.set_user_attribute(user_id, "last_interaction", datetime.now())

	# Increment command usage
	db.increment_command_usage("settings", user_id)

	transliteration = Transliteration(db, i18n)
	valid_languages = transliteration.valid_languages

	buttons = [
		[InlineKeyboardButton(f"Lang: {lang.upper()}", callback_data=f"settings_lang_{lang}")]
		for lang in valid_languages
	]
	reply_markup = InlineKeyboardMarkup(buttons)

	await update.message.reply_text(
		i18n.t("SETTINGS_USAGE", language),
		parse_mode=ParseMode.HTML,
		reply_markup=reply_markup
	)