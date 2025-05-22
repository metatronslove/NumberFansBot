import logging
import os
import re
import asyncio
from pathlib import Path
import json
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

logger = logging.getLogger(__name__)

class CommandAliasManager:
	"""
	Manages command aliases across different languages and provides
	functionality to register handlers for all aliases.
	"""

	def __init__(self):
		self.config = Config()
		self.translations_dir = Path(__file__).parent.parent / 'Locales'
		self.command_aliases = {}
		self.reverse_aliases = {}  # Maps aliases back to original commands
		self.load_all_aliases()

	def load_all_aliases(self):
		"""Load all command aliases from all language files."""
		try:
			if not self.translations_dir.exists():
				logger.warning(f"Translations directory not found: {self.translations_dir}")
				os.makedirs(self.translations_dir, exist_ok=True)
				return

			# Process each language file
			for lang_file in self.translations_dir.glob('*.json'):
				language = lang_file.stem
				self.load_language_aliases(language)

		except Exception as e:
			logger.error(f"Error loading all command aliases: {str(e)}")

	def load_language_aliases(self, language):
		"""
		Load command aliases for a specific language.

		Args:
			language: The language code to load aliases for
		"""
		try:
			lang_file = self.translations_dir / f'{language}.json'
			if not lang_file.exists():
				logger.warning(f"Language file not found: {lang_file}")
				return

			with open(lang_file, 'r', encoding='utf-8') as f:
				lang_data = json.load(f)

			if 'COMMAND_ALIASES' in lang_data:
				# Store language-specific aliases
				self.command_aliases[language] = lang_data['COMMAND_ALIASES']

				# Update reverse mapping
				for cmd, aliases in lang_data['COMMAND_ALIASES'].items():
					for alias in aliases:
						if alias.startswith('/'):
							alias = alias[1:]  # Remove leading slash if present
						self.reverse_aliases[alias] = cmd

		except Exception as e:
			logger.error(f"Error loading aliases for language {language}: {str(e)}")

	def get_original_command(self, alias):
		"""
		Get the original command for a given alias.

		Args:
			alias: The command alias to look up

		Returns:
			str: The original command name, or the alias itself if not found
		"""
		if alias.startswith('/'):
			alias = alias[1:]  # Remove leading slash if present
		return self.reverse_aliases.get(alias, alias)

	def get_preferred_alias(self, command, language):
		"""
		Get the preferred alias for a command in the specified language.

		Args:
			command: The original command name
			language: The language code

		Returns:
			str: The preferred alias for the command in the specified language
		"""
		if language in self.command_aliases and command in self.command_aliases[language]:
			aliases = self.command_aliases[language][command]
			return aliases[0] if aliases else command
		return command

	def register_command_handlers(self, app, command_handlers):
		"""
		Register command handlers for all aliases across all languages.

		Args:
			app: The Telegram Application instance
			command_handlers: Dictionary mapping command names to handler functions

		Returns:
			set: Set of all registered command aliases
		"""
		registered = set()

		for cmd, handler in command_handlers.items():
			if handler is None:
				continue

			# Register the original command
			if cmd not in registered:
				app.add_handler(CommandHandler(cmd, handler))
				registered.add(cmd)
				logger.info(f"Registered original command: {cmd}")

			# Register all aliases for this command across all languages
			for language in self.command_aliases:
				if cmd in self.command_aliases[language]:
					for alias in self.command_aliases[language][cmd]:
						if alias.startswith('/'):
							alias = alias[1:]  # Remove leading slash

						if alias != cmd and alias not in registered:
							app.add_handler(CommandHandler(alias, handler))
							registered.add(alias)
							logger.info(f"Registered alias '{alias}' for command '{cmd}' ({language})")

		return registered

# Function to generate dynamic help message based on user's language
def generate_help_message(language):
	"""
	Generate a help message with commands in the user's language.

	Args:
		language: The language code

	Returns:
		str: The help message with commands in the user's language
	"""
	i18n = I18n()
	alias_manager = CommandAliasManager()

	# Define command categories
	conceptual_commands = [
		'abjad', 'huddam', 'unsur', 'nutket', 'transliterate',
		'numerology', 'convertnumbers', 'magicsquare', 'name'
	]

	bot_commands = [
		'credits', 'payment', 'cancel', 'settings',
		'help', 'language', 'start'
	]

	shopping_commands = [
		'buy', 'sell', 'orders', 'address', 'password', 'papara'
	]

	# Get command descriptions
	try:
		lang_file = alias_manager.translations_dir / f'{language}.json'
		if not lang_file.exists():
			lang_file = alias_manager.translations_dir / 'en.json'

		with open(lang_file, 'r', encoding='utf-8') as f:
			lang_data = json.load(f)

		help_message = lang_data.get('HELP_MESSAGE', '')
		command_descriptions = {}

		for line in help_message.split('\n'):
			match = re.match(r'/(\w+)\s*-\s*(.*)', line)
			if match:
				cmd, desc = match.groups()
				command_descriptions[cmd] = desc.strip()
	except Exception as e:
		logger.error(f"Error loading command descriptions: {str(e)}")
		return i18n.t("HELP_MESSAGE", language)  # Fallback to static message

	# Build the dynamic help message
	sections = [
		(i18n.t("CONCEPTUAL_COMMANDS_HEADER", language, fallback="Available conceptual commands"), conceptual_commands),
		(i18n.t("BOT_COMMANDS_HEADER", language, fallback="Bot commands"), bot_commands),
		(i18n.t("SHOPPING_COMMANDS_HEADER", language, fallback="Shopping commands"), shopping_commands)
	]

	help_lines = []

	for section_title, commands in sections:
		if commands:
			help_lines.append(section_title)
			help_lines.append("")

			for cmd in commands:
				# Get the preferred alias for this language
				preferred_alias = alias_manager.get_preferred_alias(cmd, language)

				# Get the description
				description = command_descriptions.get(preferred_alias, '')
				if not description:
					# Try to get description from original command
					description = command_descriptions.get(cmd, '')

				help_lines.append(f"/{preferred_alias} - {description}")

			help_lines.append("")

	# Add footer
	help_lines.append(i18n.t("HELP_FOOTER", language,
							fallback="You can do more calculations using https://ebced.free.nf",
							website="https://ebced.free.nf"))

	return "\n".join(help_lines)

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

	# Determine which command was used to trigger help
	command_used = query.text.split()[0].lower() if hasattr(query, 'text') and query.text else "/help"
	command_used = command_used[1:] if command_used.startswith('/') else command_used

	# Get the original command if this is a translated alias
	alias_manager = CommandAliasManager()
	original_command = alias_manager.get_original_command(command_used)

	# Increment usage for the original command
	db.increment_command_usage(original_command, user_id, query.chat_id)

	# Generate dynamic help message
	help_message = generate_help_message(language)

	buttons = [[InlineKeyboardButton(
		i18n.t("HELP_GROUP_CHAT_USAGE", language),
		callback_data="help_group_chat"
	)]]
	reply_markup = InlineKeyboardMarkup(buttons)

	await send_long_message(
		help_message,
		parse_mode=ParseMode.HTML,
		reply_markup=reply_markup,
		update=update,
		query_message=query_message,
		context=context,
		force_new_message=True
	)
