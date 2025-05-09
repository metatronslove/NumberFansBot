import json
import logging
import requests
import re
import aiohttp
import asyncio
from pathlib import Path
from .i18n import I18n
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, User  # Added User import
from telegram.ext import (
	Application, ExtBot, ConversationHandler, CommandHandler, MessageHandler,
	ContextTypes, CallbackContext, CallbackQueryHandler, filters,
	TypeHandler,
)
from telegram.constants import ParseMode
from telegram.error import BadRequest
from .cache import Cache
from .config import Config
from .database import Database
from urllib.parse import urlparse
from datetime import datetime

logger = logging.getLogger(__name__)
config = Config()

async def timeout(update: Update, context: ContextTypes.DEFAULT_TYPE, lang: str = "en"):
	user = update.message.from_user
	user_id = user.id
	config=Config()
	db = Database()
	i18n = I18n()
	lang = db.get_user_language(user_id)
	await update.message.reply_text(i18n.t("TIMEOUT_RETRY", lang), parse_mode="HTML")
	context.user_data.clear()
	return ConversationHandler.END

async def get_ai_commentary(response: str, lang: str) -> str:
	i18n = I18n()
	prompt = i18n.t("AI_PROMPT", lang, response=response)
	try:
		headers = {"Authorization": f"Bearer {config.ai_access_token}"}
		payload = {
			"inputs": prompt,
			"parameters": {"max_length": 144, "temperature": 0.7}
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

async def register_user_if_not_exists(update: Update, context: ContextTypes.DEFAULT_TYPE, user: User, language: str | None = None) -> None:
	"""
	Register a new user in the database if they don't already exist.

	Args:
		update: The Telegram update object.
		context: The context object for the Telegram bot.
		user: The Telegram user object to register.
		language: The language code to set for the user (optional, defaults to 'en').
	"""
	if not user or not hasattr(user, 'id'):
		return  # Silently skip if user is invalid

	db = Database()
	if not db.check_if_user_exists(user.id):
		db.add_new_user(
			user_id=user.id,
			chat_id=update.message.chat_id,
			username=user.username or "",
			first_name=user.first_name or "",
			last_name=user.last_name or "",
			language_code=language or "en",
			is_beta_tester=False,
			user_credits=100
		)

async def get_warning_description(value, language):
	"""
	Check if the value exists in warningNumbers.json and return the description for the given language.
	Args:
		value: The number value to check (int or str).
		language: The active language code (e.g., 'en', 'tr', 'ar', 'he', 'la').
	Returns:
		str: The description in the specified language, or empty string if no match.
	"""
	try:
		config_dir = Path(__file__).parent / 'Config'
		warning_file = config_dir / 'warningNumbers.json'
		with open(warning_file, 'r', encoding='utf-8') as f:
			warnings = json.load(f)

		value_str = str(value)
		for entry in warnings:
			if entry.get('value') == value_str:
				description_key = f"description_{language}"
				return entry.get(description_key, "")
		return ""
	except Exception as e:
		logger.error(f"Error reading warningNumbers.json: {str(e)}")
		return ""

async def await handle_credits(update, context):
	# Credit check
	if not await check_credits(update, context):
		await query.message.reply_text(i18n.t("NO_CREDITS", language), parse_mode="HTML")
		return ConversationHandler.END