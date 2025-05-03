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
from ...Numerology import UnifiedNumerology
from ...MagicSquare import MagicSquareGenerator
from ...config import config
from ...utils import register_user_if_not_exists
from datetime import datetime
import urllib.parse

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

async def numerology_square_handle(update: Update, context: ContextTypes.DEFAULT_TYPE):
	user = update.message.from_user
	await register_user_if_not_exists(update, context, user)
	user_id = user.id
	db = Database()
	i18n = I18n()
	language = db.get_user_language(user_id)
	db.set_user_attribute(user_id, "last_interaction", datetime.now())

	db.increment_command_usage("numerologysquare", user_id)

	args = context.args
	if len(args) < 1:
		await update.message.reply_text(
			i18n.t("NUMEROLOGYSQUARE_USAGE", language),
			parse_mode=ParseMode.HTML
		)
		return

	alphabet_index = len(args)
	numerology = UnifiedNumerology()
	for i, arg in enumerate(args):
		if arg.lower() in numerology.get_available_alphabets():
			alphabet_index = i
			break

	text = " ".join(args[:alphabet_index]) if alphabet_index > 0 else args[0]
	alphabet = args[alphabet_index].lower() if alphabet_index < len(args) else "turkish"
	method = "normal"

	if alphabet not in numerology.get_available_alphabets():
		await update.message.reply_text(
			i18n.t("ERROR_INVALID_INPUT", language, error="Invalid alphabet"),
			parse_mode=ParseMode.HTML
		)
		return

	try:
		result = numerology.numerolog(text, alphabet=alphabet, method=method, detail=False)
		if isinstance(result, dict) and "error" in result:
			raise ValueError(result["error"])

		magic_square = MagicSquareGenerator()
		square = magic_square.generate(result)
		square_str = "\n".join(["  ".join(map(str, row)) for row in square])

		response = i18n.t("NUMEROLOGYSQUARE_RESULT", language, text=text, alphabet=alphabet, square=square_str)

		commentary = await get_ai_commentary(response, language)
		if commentary:
			response += "\n\n" + i18n.t("AI_COMMENTARY", language, commentary=commentary)

		encoded_text = urllib.parse.quote(text)
		buttons = [
			[InlineKeyboardButton(f"Alphabet: {a}", callback_data=f"numerologysquare_{encoded_text}_{a}")]
			for a in numerology.get_available_alphabets() if a != alphabet
		]
		reply_markup = InlineKeyboardMarkup(buttons) if buttons else None

		await update.message.reply_text(
			response,
			parse_mode=ParseMode.MARKDOWN,
			reply_markup=reply_markup
		)
	except Exception as e:
		await update.message.reply_text(
			i18n.t("ERROR_INVALID_INPUT", language, error=str(e)),
			parse_mode=ParseMode.HTML
		)