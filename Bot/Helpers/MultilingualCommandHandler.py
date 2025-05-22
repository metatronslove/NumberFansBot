import logging
import json
import os
from pathlib import Path
from telegram.ext import CommandHandler, Application

logger = logging.getLogger(__name__)

class MultilingualCommandHandler:
	"""
	A utility class to handle multilingual command registration.
	This class reads command aliases from language files and registers
	all translated versions of commands to their respective handlers.
	"""

	def __init__(self):
		self.command_aliases = {}
		self.load_command_aliases()

	def load_command_aliases(self):
		"""Load command aliases from all language files."""
		try:
			# Path to language files directory
			lang_dir = Path(__file__).parent.parent / 'Locales'

			if not lang_dir.exists():
				logger.warning(f"Language directory not found: {lang_dir}")
				return

			# Process each language file
			for lang_file in lang_dir.glob('*.json'):
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
