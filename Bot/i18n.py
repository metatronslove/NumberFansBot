import json
from pathlib import Path
import logging
from typing import Any

logger = logging.getLogger(__name__)

class I18n:
	def __init__(self):
		self.locale_path = Path(__file__).parent.parent / "Locales"
		self.translations = {}
		self.available_languages = self._load_available_languages()

	def _load_available_languages(self) -> list:
		languages = []
		for file in self.locale_path.glob("*.json"):
			lang = file.stem
			languages.append(lang)
		return sorted(languages)

	def get_available_languages(self) -> list:
		return self.available_languages

	def _load_translations(self, lang: str) -> dict:
		if lang in self.translations:
			return self.translations[lang]

		file_path = self.locale_path / f"{lang}.json"
		if not file_path.exists():
			file_path = self.locale_path / "en.json"

		try:
			with open(file_path, "r", encoding="utf-8") as f:
				translations = json.load(f)
			self.translations[lang] = translations
			return translations
		except Exception as e:
			logger.error(f"Failed to load translations for {lang}: {str(e)}")
			self.translations[lang] = {}
			return {}

	def t(self, key: str, lang: str, **params) -> str:
		translations = self._load_translations(lang)
		keys = key.split(".")
		value = translations

		for k in keys:
			if not isinstance(value, dict) or k not in value:
				return key
			value = value[k]

		if not isinstance(value, str):
			return key

		try:
			return value.format(**params)
		except KeyError:
			return value