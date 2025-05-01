from telegram import Update
from telegram.ext import ContextTypes
from telegram.constants import ParseMode
from ...database import Database
from ...i18n import I18n
from ...utils import register_user_if_not_exists
from datetime import datetime

async def cancel_handle(update: Update, context: ContextTypes.DEFAULT_TYPE):
	user = update.message.from_user
	await register_user_if_not_exists(update, context, user)
	user_id = user.id
	db = Database()
	i18n = I18n()
	language = db.get_user_language(user_id)
	db.set_user_attribute(user_id, "last_interaction", datetime.now())

	# Increment command usage
	db.increment_command_usage("cancel", user_id)

	# Clear conversation state
	context.user_data.clear()

	await update.message.reply_text(
		i18n.t("CANCEL_RESULT", language),
		parse_mode=ParseMode.HTML
	)