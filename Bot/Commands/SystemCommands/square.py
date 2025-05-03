import logging
import requests
import re
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from telegram.constants import ParseMode
from ...database import Database
from ...i18n import I18n
from ...config import config
from ...MagicSquare import MagicSquareGenerator
from ...NumberConverter import NumberConverter
from ...utils import register_user_if_not_exists
from datetime import datetime

logger = logging.getLogger(__name__)

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
		response = re.sub(rf"^{re.escape(prompt)}.*?\[/INST\]", "", response, flags=re.DOTALL).strip()
		if response.status_code == 200:
			return response.json()[0]["generated_text"].split("[/INST]")[-1].strip()
		else:
			logger.error(f"AI API error: {response.status_code}")
			return ""
	except Exception as e:
		logger.error(f"AI commentary error: {str(e)}")
		return ""

async def square_handle(update: Update, context: ContextTypes.DEFAULT_TYPE, row_sum: int = None, current_n: int = 3, use_indian: bool = False):
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

		square = generator.generate_magic_square(n, row_sum, 0, False, 'arabic')
		indian = generator.generate_magic_square(n, row_sum, 0, False, 'indian')

		if square is None:
			await (update.message.reply_text if update.message else update.callback_query.message.reply_text)(
				i18n.t("ERROR_GENERAL", language, error=f"No magic square found for row sum {row_sum}"),
				parse_mode=ParseMode.MARKDOWN
			)
			return

		display_square = square
		number_format = "arabic"
		if use_indian:
			display_square = indian
			number_format = "indian"

		response = i18n.t("SQUARE_RESULT", language, number=n, row_sum=row_sum, square=display_square)

		commentary = await get_ai_commentary(response, language)
		if commentary:
			response += "\n\n" + i18n.t("AI_COMMENTARY", language, commentary=commentary)

		keyboard = []
		if not use_indian:
			keyboard.append([InlineKeyboardButton(
				i18n.t("EASTERN_ARABIC_NUMBERS", language),
				callback_data=f"indian_square_{row_sum}_{n}"
			)])
		next_n = n + 1
		next_square = None
		while next_n <= max_n:
			square = generator.generate_magic_square(next_n, row_sum, 0, False, 'arabic')
			indian = generator.generate_magic_square(next_n, row_sum, 0, False, 'indian')
			if not isinstance(square, str):
				next_square = square
				if use_indian:
					next_square = indian
				break
			next_n += 1
		if next_square:
			keyboard.append([InlineKeyboardButton(
				i18n.t("NEXT_SIZE", language),
				callback_data=f"next_size_{row_sum}_{next_n}"
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