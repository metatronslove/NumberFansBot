import logging
import os
import re
import asyncio
import json
from pathlib import Path
from Bot.config import Config
from Bot.database import Database
from Bot.Helpers.i18n import I18n
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
	Application, ExtBot, ConversationHandler, CommandHandler, MessageHandler,
	ContextTypes, CallbackContext, CallbackQueryHandler, filters,
	TypeHandler,
)
from telegram.constants import ParseMode
from telegram.error import BadRequest
from Bot.utils import (
	register_user_if_not_exists, get_warning_description, get_ai_commentary,
	timeout, handle_credits, send_long_message, uptodate_query
)
from urllib.parse import urlparse
from pathlib import Path
from datetime import datetime

async def help_handle(update: Update, context: ContextTypes.DEFAULT_TYPE):
	update, context, query, user, query_message = await uptodate_query(update, context)
	if not query_message:
		return

	user_language = user.language_code.split('-')[0] if user.language_code else 'en'
	await register_user_if_not_exists(update, context, user, language=user_language)
	user_id = user.id
	db = Database()
	i18n = I18n()
	language = db.get_user_language(user_id)
	# await handle_credits(update, context) because help MUST NOT decrement credits
	db.set_user_attribute(user_id, "last_interaction", datetime.now())
	db.increment_command_usage("help", user_id, query.chat_id)

	# Get the command that triggered this help request
	command_used = query.text.split()[0].lower() if hasattr(query, 'text') and query.text else "/help"

	# Load command aliases to determine which language-specific help to show
	command_aliases = load_command_aliases()
	original_command = get_original_command(command_used[1:], command_aliases)  # Remove leading slash

	buttons = [[InlineKeyboardButton(
		i18n.t("HELP_GROUP_CHAT_USAGE", language),
		callback_data="help_group_chat"
	)]]
	reply_markup = InlineKeyboardMarkup(buttons)

	await send_long_message(
		i18n.t("HELP_MESSAGE", language),
		parse_mode=ParseMode.HTML,
		reply_markup=reply_markup,
		update=update,
		query_message=query_message,
		context=context,
		force_new_message=True
	)

def load_command_aliases():
	"""Load command aliases from all language files."""
	command_aliases = {}
	try:
		# Path to language files directory
		lang_dir = Path(__file__).parent.parent / 'Translations'

		if not lang_dir.exists():
			return command_aliases

		# Process each language file
		for lang_file in lang_dir.glob('*.json'):
			try:
				with open(lang_file, 'r', encoding='utf-8') as f:
					lang_data = json.load(f)

				if 'COMMAND_ALIASES' in lang_data:
					# For each command, add all its aliases to our mapping
					for cmd, aliases in lang_data['COMMAND_ALIASES'].items():
						if cmd not in command_aliases:
							command_aliases[cmd] = []

						# Add all aliases for this command
						for alias in aliases:
							if alias not in command_aliases[cmd]:
								command_aliases[cmd].append(alias)

			except Exception as e:
				pass

	except Exception as e:
		pass

	return command_aliases

def get_original_command(alias, command_aliases):
	"""Find the original command for a given alias."""
	for cmd, aliases in command_aliases.items():
		if alias in aliases:
			return cmd
	return alias  # Return the alias itself if no mapping found
