import requests
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CallbackContext
from telegram.constants import ParseMode
from ...database import Database
from ...i18n import I18n
from ...MagicSquare import MagicSquareGenerator
from ...config import config
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

async def get_ai_commentary(response: str, lang: str) -> str:
	i18n = I18n()
	prompt = i18n.t("AI_PROMPT", lang, response=response)
	try:
		headers = {"Authorization": f"Bearer {config.ai_access_token}"}
		payload = {
			"inputs": prompt,
			"parameters": {"max_length": 200, "temperature": 0.7}
		}
		response = requests.post(
			config.ai_model_url,
			headers=headers,
			json=payload
		)
		if response.status_code == 200:
			return response.json()[0]["generated_text"].split("[/INST]")[-1].strip()
		else:
			return ""
	except Exception:
		return ""

async def magic_square_handle(update: Update, context: CallbackContext):
	user = update.message.from_user
	await register_user_if_not_exists(update, context, user)
	user_id = user.id
	db = Database()
	i18n = I18n()
	language = db.get_user_language(user_id)
	db.set_user_attribute(user_id, "last_interaction", datetime.now())

	# Increment command usage
	db.increment_command_usage("magicsquare", user_id)

	args = context.args
	if len(args) < 1:
		await update.message.reply_text(
			i18n.t("MAGICSQUARE_USAGE", language),
			parse_mode=ParseMode.HTML
		)
		return

	try:
		row_sum = int(args[0])
		if row_sum < 15:  # Minimum for 3x3 magic square
			await update.message.reply_text(
				i18n.t("ERROR_INVALID_INPUT", language, error="Row sum must be at least 15"),
				parse_mode=ParseMode.HTML
			)
			return

		magic_square = MagicSquareGenerator()
		square = magic_square.generate(row_sum, n=3)
		square_str = "\n".join(["  ".join(map(str, row)) for row in square])
		response = i18n.t("MAGICSQUARE_RESULT", language, number=row_sum, square=square_str)

		# Add AI commentary
		commentary = await get_ai_commentary(response, language)
		if commentary:
			response += "\n\n" + i18n.t("AI_COMMENTARY", language, commentary=commentary)

		# Add button for next size
		buttons = [[InlineKeyboardButton(
			i18n.t("NEXT_SIZE", language),
			callback_data=f"next_size_{row_sum}_3"
		)]]
		reply_markup = InlineKeyboardMarkup(buttons)

		await update.message.reply_text(
			response,
			parse_mode=ParseMode.MARKDOWN,
			reply_markup=reply_markup
		)
	except ValueError:
		await update.message.reply_text(
			i18n.t("ERROR_INVALID_INPUT", language, error="Invalid row sum"),
			parse_mode=ParseMode.HTML
		)
	except Exception as e:
		await update.message.reply_text(
			i18n.t("ERROR_GENERAL", language, error=str(e)),
			parse_mode=ParseMode.HTML
		)