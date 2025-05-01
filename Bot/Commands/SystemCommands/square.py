import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CallbackContext
from telegram.constants import ParseMode
from ...database import Database
from ...i18n import I18n
from ...config import config
from ...MagicSquare import MagicSquareGenerator
from ...NumberConverter import NumberConverter
from datetime import datetime
import requests

logger = logging.getLogger(__name__)

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
		headers = {"Authorization": f"Bearer {config.huggingface_access_token}"}
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
			logger.error(f"AI API error: {response.status_code}")
			return ""
	except Exception as e:
		logger.error(f"AI commentary error: {str(e)}")
		return ""

async def square_handle(update: Update, context: CallbackContext, row_sum: int = None, current_n: int = 3, use_indian: bool = False):
	user = update.message.from_user if update.message else update.callback_query.from_user
	chat_id = update.message.chat_id if update.message else update.callback_query.message.chat_id
	await register_user_if_not_exists(update, context, user)
	user_id = user.id
	db = Database()
	i18n = I18n()
	language = db.get_user_language(user_id)
	db.set_user_attribute(user_id, "last_interaction", datetime.now())

	db.increment_command_usage("square", user_id)

	try:
		if update.message:  # Direct /square command
			args = context.args
			if not args or not args[0].isdigit():
				await update.message.reply_text(
					i18n.t("SQUARE_USAGE", language),
					parse_mode=ParseMode.MARKDOWN
				)
				return
			row_sum = int(args[0])

		if not row_sum or row_sum < 15:  # Minimum row sum for 3x3 square
			await (update.message.reply_text if update.message else update.callback_query.message.reply_text)(
				i18n.t("ERROR_INVALID_INPUT", language, error="Row sum must be an integer >= 15"),
				parse_mode=ParseMode.MARKDOWN
			)
			return

		generator = MagicSquareGenerator()
		n = current_n
		max_n = 100
		square = None

		# Iterate sizes until a valid square is found
		while n <= max_n:
			temp_square = generator.generate_magic_square(n=n, row_sum=row_sum)
			if not isinstance(temp_square, str) and generator.check_magic_square(temp_square, row_sum):
				square = temp_square
				break
			n += 1

		if square is None:
			await (update.message.reply_text if update.message else update.callback_query.message.reply_text)(
				i18n.t("ERROR_GENERAL", language, error=f"No magic square found for row sum {row_sum}"),
				parse_mode=ParseMode.MARKDOWN
			)
			return

		# Convert to Eastern Arabic numerals if use_indian is True
		converter = NumberConverter()
		display_square = square
		number_format = "arabic"
		if use_indian:
			display_square = [[converter.arabic(str(cell)) for cell in row] for row in square]
			number_format = "indian"

		# Format the square with borders
		formatted_square = generator.box_the_square(
			display_square,
			border_style=0,
			number_format=number_format
		)
		response = i18n.t("SQUARE_RESULT", language, number=n, row_sum=row_sum, square=formatted_square)

		# Get AI commentary
		commentary = await get_ai_commentary(response, language)
		if commentary:
			response += "\n\n" + i18n.t("AI_COMMENTARY", language, commentary=commentary)

		# Add buttons: Eastern Arabic and Next Size
		keyboard = []
		if not use_indian:
			keyboard.append([InlineKeyboardButton(
				i18n.t("EASTERN_ARABIC_NUMBERS", language),
				callback_data=f"indian_square_{row_sum}_{n}"
			)])
		# Check if a next size exists
		next_n = n + 1
		next_square = None
		while next_n <= max_n:
			temp_square = generator.generate_magic_square(n=next_n, row_sum=row_sum)
			if not isinstance(temp_square, str) and generator.check_magic_square(temp_square, row_sum):
				next_square = temp_square
				break
			next_n += 1
		if next_square:
			keyboard.append([InlineKeyboardButton(
				i18n.t("NEXT_SIZE", language),
				callback_data=f"next_size_{row_sum}_{n}"
			)])
		reply_markup = InlineKeyboardMarkup(keyboard) if keyboard else None

		await (update.message.reply_text if update.message else update.callback_query.message.reply_text)(
			response,
			parse_mode=ParseMode.MARKDOWN,
			reply_markup=reply_markup
		)

	except Exception as e:
		logger.error(f"Square error: {str(e)}")
		await (update.message.reply_text if update.message else update.callback_query.message.reply_text)(
			i18n.t("ERROR_GENERAL", language),
			parse_mode=ParseMode.MARKDOWN
		)