import json
import logging
from pathlib import Path
from telegram import Update
from telegram.ext import ContextTypes
from .database import Database

logger = logging.getLogger(__name__)

async def register_user_if_not_exists(update: Update, context: ContextTypes.DEFAULT_TYPE, user: telegram.User) -> None:
	"""
	Register a new user in the database if they don't already exist.

	Args:
		update: The Telegram update object.
		context: The context object for the Telegram bot.
		user: The Telegram user object to register.
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
		)

def get_warning_description(value, language):
	"""
	Check if the value exists in warningNumbers.json and return the description for the given language.
	Args:
		value: The number value to check (int or str).
		language: The active language code (e.g., 'en', 'tr', 'ar', 'he', 'la').
	Returns:
		str: The description in the specified language, or empty string if no match.
	"""
	try:
		config_dir = Path(__file__).parent.parent / 'Config'
		warning_file = config_dir / 'warningNumbers.json'
		with open(warning_file, 'r', encoding='utf-8') as f:
			warnings = json.load(f)

		# Convert value to string for comparison
		value_str = str(value)
		for entry in warnings:
			if entry.get('value') == value_str:
				description_key = f"description_{language}"
				return entry.get(description_key, "")
		return ""
	except Exception as e:
		logger.error(f"Error reading warningNumbers.json: {str(e)}")
		return ""