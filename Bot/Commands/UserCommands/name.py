import logging
import aiohttp
import asyncio
import requests
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from telegram.constants import ParseMode
from ...database import Database
from ...i18n import I18n
from ...transliteration import Transliteration
from ...config import Config
from ...utils import register_user_if_not_exists
from datetime import datetime
import urllib.parse
import re

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

async def name_handle(update: Update, context: ContextTypes.DEFAULT_TYPE):
	user = update.message.from_user
	await register_user_if_not_exists(update, context, user)
	user_id = user.id
	db = Database()
	i18n = I18n()
	language = db.get_user_language(user_id)
	db.set_user_attribute(user_id, "last_interaction", datetime.now())

	# Increment command usage
	db.increment_command_usage("name", user_id)

	args = context.args
	if len(args) < 1:
		await update.message.reply_text(
			i18n.t("NAME_USAGE", language),
			parse_mode=ParseMode.HTML
		)
		return

	prefix = " ".join(args[:-1]) if len(args) > 1 else args[0]
	target_lang = args[-1].lower() if len(args) >= 1 else "english"

	transliteration = Transliteration(db, i18n)
	valid_languages = transliteration.valid_languages

	if target_lang not in valid_languages:
		await update.message.reply_text(
			i18n.t("ERROR_INVALID_INPUT", language, error=f"Invalid language. Use: {', '.join(valid_languages)}"),
			parse_mode=ParseMode.HTML
		)
		return

	try:
		source_lang = transliteration.guess_source_lang(prefix)
		result = transliteration.transliterate(prefix, target_lang, source_lang)
		name = result["primary"]
		response = i18n.t("NAME_RESULT", language, prefix=prefix, type="modern", method="simple", name=name)

		# Add AI commentary
		commentary = await get_ai_commentary(response, language)
		if commentary:
			response += "\n\n" + i18n.t("AI_COMMENTARY", language, commentary=commentary)

		# Add buttons for alternative languages
		encoded_prefix = urllib.parse.quote(prefix)
		buttons = [
			[InlineKeyboardButton(
				f"Lang: {lang.capitalize()}",
				callback_data=f"name_alt_{encoded_prefix}_{lang}_{urllib.parse.quote(name)}"
			)] for lang in valid_languages if lang != target_lang
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