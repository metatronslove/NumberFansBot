import logging
import os
import re
import asyncio
from pathlib import Path
import json
from Bot.config import Config
from Bot.database import Database
from Bot.Helpers.i18n import I18n
from telegram.ext import Application, CommandHandler

logger = logging.getLogger(__name__)

class MultilingualCommandRegistrar:
	"""
	A utility class to handle multilingual command registration.
	This class reads command aliases from language files and registers
	all translated versions of commands to their respective handlers.
	"""

	def __init__(self):
		self.command_aliases = {}
		self.translations_dir = Path(__file__).parent.parent / 'Locales'
		self.load_command_aliases()

	def load_command_aliases(self):
		"""Load command aliases from all language files."""
		try:
			if not self.translations_dir.exists():
				logger.warning(f"Translations directory not found: {self.translations_dir}")
				return

			# Process each language file
			for lang_file in self.translations_dir.glob('*.json'):
				try:
					with open(lang_file, 'r', encoding='utf-8') as f:
						lang_data = json.load(f)

					if 'COMMAND_ALIASES' in lang_data:
						# For each command, add all its aliases to our mapping
						for cmd, aliases in lang_data['COMMAND_ALIASES'].items():
							if cmd not in self.command_aliases:
								self.command_aliases[cmd] = set()

							# Add all aliases for this command
							for alias in aliases:
								if alias.startswith('/'):
									alias = alias[1:]  # Remove leading slash if present
								self.command_aliases[cmd].add(alias)

				except Exception as e:
					logger.error(f"Error processing language file {lang_file}: {str(e)}")

		except Exception as e:
			logger.error(f"Error loading command aliases: {str(e)}")

	def register_command_handlers(self, app: Application, command_map: dict):
		"""
		Register all command handlers with their aliases.

		Args:
			app: The Telegram Application instance
			command_map: Dictionary mapping command names to their handler functions
		"""
		registered_commands = set()

		for cmd, handler_func in command_map.items():
			# Skip if handler is None
			if handler_func is None:
				continue

			# Get all aliases for this command
			aliases = self.command_aliases.get(cmd, [cmd])

			# Register each alias as a command
			for alias in aliases:
				# Skip if already registered to avoid duplicates
				if alias in registered_commands:
					logger.warning(f"Command alias '{alias}' already registered, skipping.")
					continue

				try:
					app.add_handler(CommandHandler(alias, handler_func))
					registered_commands.add(alias)
					logger.info(f"Registered command alias '{alias}' for handler '{cmd}'")
				except Exception as e:
					logger.error(f"Failed to register command alias '{alias}': {str(e)}")

		return registered_commands

	def get_preferred_command(self, command, language):
		"""
		Get the preferred command name for a specific language.

		Args:
			command: The original command name
			language: The language code

		Returns:
			str: The preferred command name for the specified language
		"""
		try:
			lang_file = self.translations_dir / f'{language}.json'
			if not lang_file.exists():
				return command

			with open(lang_file, 'r', encoding='utf-8') as f:
				lang_data = json.load(f)

			if 'COMMAND_ALIASES' in lang_data and command in lang_data['COMMAND_ALIASES']:
				aliases = lang_data['COMMAND_ALIASES'][command]
				return aliases[0] if aliases else command

		except Exception as e:
			logger.error(f"Error getting preferred command: {str(e)}")

		return command
