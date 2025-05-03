import logging
import aiohttp
import asyncio
import requests
import re
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from telegram.constants import ParseMode
from ...database import Database
from ...i18n import I18n
from ...MagicSquare import MagicSquareGenerator
from ...admin_panel import config
from ...utils import register_user_if_not_exists
from datetime import datetime

logger = logging.getLogger(__name__)

async def get_ai_commentary(response: str, lang: str) -> str:
    i18n = I18n()
    prompt = i18n.t("AI_PROMPT", lang, response=response)
    try:
        headers = {"Authorization": f"Bearer {config.ai_access_token}"}
        payload = {
            "inputs": prompt,
            "parameters": {"max_length": 200, "temperature": 0.7}
        }
        async with aiohttp.ClientSession() as session:
            async with session.post(config.ai_model_url, headers=headers, json=payload) as api_response:
                if api_response.status == 200:
                    data = await api_response.json()
                    generated_text = data[0]["generated_text"]
                    logger.debug(f"Raw generated text: {generated_text}")
                    cleaned_text = re.sub(
                        rf"^{re.escape(prompt)}(?:\s*\[\/INST\])?\s*",
                        "",
                        generated_text,
                        flags=re.DOTALL
                    ).strip()
                    logger.debug(f"Cleaned text: {cleaned_text}")
                    return cleaned_text
                else:
                    logger.error(f"Hugging Face API error: Status code {api_response.status}, Response: {await api_response.text()}")
                    return ""
    except KeyError as e:
        logger.error(f"AI commentary error: Invalid response format, missing key {e}")
        return ""
    except Exception as e:
        logger.error(f"AI commentary error: {str(e)}")
        return ""

async def magic_square_handle(update: Update, context: ContextTypes.DEFAULT_TYPE):
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
		square = magic_square.generate_magic_square(3, row_sum, 0, False, 'arabic')
		response = i18n.t("MAGICSQUARE_RESULT", language, number=row_sum, square=square["box"])
		commentary = await get_ai_commentary(response, language)
		if commentary:
			response = "\n\n" + i18n.t("AI_COMMENTARY", language, commentary=commentary)
		buttons = [
		[InlineKeyboardButton(
				i18n.t("CREATE_INDIAN_MAGIC_SQUARE", language),
				callback_data=f"indian_square_{row_sum}"
			)],
		[InlineKeyboardButton(
			i18n.t("NEXT_SIZE", language),
			callback_data=f"next_size_{row_sum}_{square['size']}_arabic"
		)]]
		reply_markup = InlineKeyboardMarkup(buttons)
		await update.message.reply_text(response, parse_mode=ParseMode.MARKDOWN,	reply_markup=reply_markup)
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