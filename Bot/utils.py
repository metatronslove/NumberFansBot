import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

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