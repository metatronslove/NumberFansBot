import json
from pathlib import Path
from typing import Dict, List, Optional
import mysql.connector
from .Helpers.i18n import I18n
from Bot.config import Config
from .database import Database
from .Numerology import UnifiedNumerology
import logging

logger = logging.getLogger(__name__)

class Transliteration:
	def __init__(self, db: Database, i18n: I18n):
		self.db = db
		self.i18n = i18n
		self.numerology = UnifiedNumerology()
		self.Transliteration_map: Dict = {}
		self.load_transliteration_map()
		self.valid_languages = ["arabic", "turkish", "english", "hebrew", "latin"]
		self.language_mapping = {"arabic": "arabic_hija"}

	@staticmethod
	def get_suffix(x: str, y: str) -> str:
		"""Extract the suffix of x after removing prefix y."""
		if not x or not y:
			return x
		if x.startswith(y):
			return x[len(y):]
		return x

	def load_transliteration_map(self):
		"""Load transliteration_map.json from Config directory."""
		config = Config()
		map_path = Path("Config") / "transliteration_map.json"
		try:
			with open(map_path, "r", encoding="utf-8") as f:
				self.Transliteration_map = json.load(f)
		except Exception as e:
			logger.error(f"Failed to load transliteration map: {str(e)}")
			raise ValueError(f"Failed to load transliteration map: {str(e)}")

	def guess_source_lang(self, text: str) -> str:
		"""Guess the source language based on the first character."""
		first_char = text[0] if text else ""
		for lang, chars in self.numerology.alphabets.items():
			if first_char in chars:
				return lang if lang != "arabic_hija" else "arabic"
		return "english"  # Default fallback

	def transliterate(self, text: str, target_lang: str, source_lang: Optional[str] = None) -> Dict[str, any]:
		"""
		Transliterate text to target language, returning primary and alternative results.
		Returns: {"primary": str, "alternatives": List[str]}
		"""
		if target_lang not in self.valid_languages:
			raise ValueError(f"Invalid target language: {target_lang}")

		source_lang = source_lang or self.guess_source_lang(text)
		if source_lang not in self.valid_languages:
			raise ValueError(f"Invalid source language: {source_lang}")

		# Check cached transliterations in MySQL
		alternatives = self.get_transliteration_alternatives(text, source_lang, target_lang)
		if alternatives:
			primary = alternatives[0]["transliterated_name"]
			alt_names = [alt["transliterated_name"] for alt in alternatives[1:]]
			return {"primary": primary, "alternatives": alt_names}

		# Map source and target languages to transliteration_map keys
		source_key = f"from_{self.language_mapping.get(source_lang, source_lang)}"
		target_key = self.language_mapping.get(target_lang, target_lang)
		map_data = self.Transliteration_map.get(target_key, {}).get(source_key, {})

		if not map_data:
			raise ValueError(f"No transliteration mapping from {source_lang} to {target_lang}")

		# Generate transliterations
		results = {text: {"score": 0, "used": []}}  # Start with original text
		chars = list(text)  # Split into characters
		for char in chars:
			mappings = map_data.get(char, map_data.get(char.upper(), map_data.get(char.lower(), [char])))
			new_results = {}
			for current, info in results.items():
				for mapped_char in mappings:
					new_str = current + mapped_char
					new_score = info["score"] + (-1 if mapped_char in info["used"] else 1)
					new_results[new_str] = {
						"score": new_score,
						"used": info["used"] + [mapped_char]
					}
			results = new_results

		# Sort by score and filter out original text
		sorted_results = sorted(
			[(k, v) for k, v in results.items() if k != text],
			key=lambda x: x[1]["score"],
			reverse=True
		)
		if not sorted_results:
			raise ValueError(f"No valid transliterations found for '{text}' from {source_lang} to {target_lang}")

		primary = sorted_results[0][0]
		alternatives = [res[0] for res in sorted_results[1:]]  # All alternatives

		# Store transliterations
		for translit in [primary] + alternatives:
			self.store_transliteration(text, source_lang, target_lang, translit)

		return {"primary": primary, "alternatives": alternatives}

	def store_transliteration(self, source_name: str, source_lang: str, target_lang: str, transliterated_name: str, user_id: int = None):
		"""Store transliteration in MySQL, incrementing score if it exists."""
		try:
			suffix = self.get_suffix(transliterated_name, source_name)
			# Check if the transliteration exists
			query = """
				SELECT id, score FROM transliterations
				WHERE source_name = %s AND source_lang = %s AND target_lang = %s AND transliterated_name = %s
			"""
			self.db.cursor.execute(query, (source_name, source_lang, target_lang, transliterated_name))
			result = self.db.cursor.fetchone()

			if result:
				# Update existing record
				transliteration_id, current_score = result
				query = """
					UPDATE transliterations
					SET score = %s, suffix = %s, user_id = %s
					WHERE id = %s
				"""
				self.db.cursor.execute(query, (current_score + 1, suffix, user_id, transliteration_id))
			else:
				# Insert new record
				query = """
					INSERT INTO transliterations (source_name, source_lang, target_lang, transliterated_name, suffix, score, user_id)
					VALUES (%s, %s, %s, %s, %s, %s, %s)
				"""
				self.db.cursor.execute(query, (source_name, source_lang, target_lang, transliterated_name, suffix, 1, user_id))

			self.db.conn.commit()
		except mysql.connector.Error as e:
			logger.error(f"Failed to store transliteration in MySQL: {str(e)}")
			self.db.conn.rollback()
		except Exception as e:
			logger.error(f"Unexpected error storing transliteration: {str(e)}")

	def get_transliteration_alternatives(self, source_name: str, source_lang: str, target_lang: str) -> List[Dict]:
		"""Retrieve cached transliterations from MySQL, sorted by score."""
		try:
			query = """
				SELECT id, source_name, source_lang, target_lang, transliterated_name, suffix, score, user_id
				FROM transliterations
				WHERE source_name = %s AND source_lang = %s AND target_lang = %s
				ORDER BY score DESC, transliterated_name ASC
			"""
			self.db.cursor.execute(query, (source_name, source_lang, target_lang))
			results = self.db.cursor.fetchall()
			return [
				{
					"id": row[0],
					"source_name": row[1],
					"source_lang": row[2],
					"target_lang": row[3],
					"transliterated_name": row[4],
					"suffix": row[5],
					"score": row[6],
					"user_id": row[7]
				} for row in results
			]
		except mysql.connector.Error as e:
			logger.error(f"Failed to retrieve transliteration alternatives from MySQL: {str(e)}")
			return []
		except Exception as e:
			logger.error(f"Unexpected error retrieving transliteration alternatives: {str(e)}")
			return []

	def format_response(self, transliterated_name: str, target_lang: str, output_lang: str, language: str) -> str:
		"""Format transliteration response using i18n."""
		lang_names = {
			"arabic": {
				"turkish": "Arapça",
				"english": "Arabic",
				"latin": "Arabicus",
				"arabic": "عربي",
				"hebrew": "ערבית"
			},
			"english": {
				"turkish": "İngilizce",
				"english": "English",
				"latin": "Anglicus",
				"arabic": "إنجليزي",
				"hebrew": "אנגלית"
			},
			"latin": {
				"turkish": "Latince",
				"english": "Latin",
				"latin": "Latinus",
				"arabic": "لاتيني",
				"hebrew": "לטינית"
			},
			"hebrew": {
				"turkish": "İbranice",
				"english": "Hebrew",
				"latin": "Hebraicus",
				"arabic": "عبري",
				"hebrew": "עברית"
			},
			"turkish": {
				"turkish": "Türkçe",
				"english": "Turkish",
				"latin": "Turcicus",
				"arabic": "تركي",
				"hebrew": "טורקית"
			}
		}
		lang_name = lang_names.get(target_lang, {}).get(output_lang, target_lang)
		return self.i18n.t(
			"TRANSLITERATION_RESPONSE",
			language,
			lang_name=lang_name,
			result=transliterated_name
		)

	def suggest_transliterations(self, text: str, source_lang: str, target_lang: str) -> List[str]:
		"""Generate suggested transliterations for the given text."""
		try:
			result = self.transliterate(text, target_lang, source_lang)
			return [result["primary"]] + result["alternatives"]
		except Exception as e:
			logger.error(f"Failed to suggest transliterations: {str(e)}")
			return []