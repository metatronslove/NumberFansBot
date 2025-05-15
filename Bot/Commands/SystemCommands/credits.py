# credits.py
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from telegram.constants import ParseMode
from Bot.config import Config
from Bot.database import Database
from Bot.Helpers.i18n import I18n
from Bot.utils import (
	register_user_if_not_exists, get_warning_description, get_ai_commentary,
	timeout, handle_credits, send_long_message, uptodate_query
)
from datetime import datetime

logger = logging.getLogger(__name__)

async def credits_handle(update: Update, context: ContextTypes.DEFAULT_TYPE)	:
	user_id = update.effective_user.id
	db = Database()
	i18n = I18n()
	language = db.get_user_language(user_id)  # Use database-stored language
	# await handle_credits(update, context) because credits MUST NOT decrement credits
	db.set_user_attribute(user_id, "last_interaction", datetime.now())
	db.increment_command_usage("credits", user_id)

	try:
		query = "SELECT credits FROM users WHERE user_id = %s"
		db.cursor.execute(query, (user_id,))
		user = db.cursor.fetchone()
		remaining_credits = user['credits'] if user else 0
		reply_text = i18n.t("CREDITS_REMAINS", language, remaining_credits=remaining_credits)
		await send_long_message(reply_text, parse_mode=ParseMode.HTML, update=update, query_message=query_message,	context=context, force_new_message=force_new)
	except Exception as e:
		logger.error(f"CreditsCommand error: {str(e)}")
		await send_long_message(
			i18n.t("ERROR_GENERAL", language, error=str(e)),
			parse_mode=ParseMode.HTML,
			update=update,
			query_message=query_message,
			context=context
		)