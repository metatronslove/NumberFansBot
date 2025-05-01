from telegram import Update
from telegram.ext import CallbackContext
from telegram.constants import ParseMode
from ...database import Database
from ...i18n import I18n
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

async def help_group_chat_handle(update: Update, context: CallbackContext):
	user = update.message.from_user
	await register_user_if_not_exists(update, context, user)
	user_id = user.id
	db = Database()
	i18n = I18n()
	language = db.get_user_language(user_id)
	db.set_user_attribute(user_id, "last_interaction", datetime.now())

	# Increment command usage
	db.increment_command_usage("help_group_chat", user_id)

	try:
		await update.message.reply_video(
			video=open("Static/help_group_chat.mp4", "rb"),
			caption=i18n.t("HELP_GROUP_CHAT_USAGE", language),
			parse_mode=ParseMode.HTML
		)
	except Exception as e:
		await update.message.reply_text(
			i18n.t("ERROR_GENERAL", language, error="Failed to send help video"),
			parse_mode=ParseMode.HTML
		)