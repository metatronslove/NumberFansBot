from .database import Database
import hashlib
import time
import json
import logging

logger = logging.getLogger(__name__)

class Cache:
	def __init__(self):
		self.db = Database()

	def store_alternatives(self, user_id: int, source_lang: str, target_lang: str, text: str, alternatives: list) -> str:
		"""Store alternatives and return a cache ID."""
		cache_id = hashlib.md5(f"{user_id}:{text}:{time.time()}".encode()).hexdigest()[:8]
		query = """
		INSERT INTO `transliteration_cache` (cache_id, user_id, source_lang, target_lang, source_name, alternatives, created_at)
		VALUES (%s, %s, %s, %s, %s, %s, %s)
		"""
		try:
			self.db.execute_query(query, (
				cache_id,
				user_id,
				source_lang,
				target_lang,
				text,
				json.dumps(alternatives),
				time.time()
			), fetch=False)
			return cache_id
		except Exception as e:
			logger.error(f"Error storing alternatives for cache_id {cache_id}: {str(e)}")
			raise

	def get_alternatives(self, cache_id: str) -> dict:
		"""Retrieve alternatives by cache ID."""
		query = "SELECT * FROM `transliteration_cache` WHERE cache_id = %s"
		try:
			result = self.db.execute_query(query, (cache_id,))
			if result:
				result[0]['alternatives'] = json.loads(result[0]['alternatives'])
				return result[0]
			return {}
		except Exception as e:
			logger.error(f"Error retrieving alternatives for cache_id {cache_id}: {str(e)}")
			return {}

	def __del__(self):
		"""Clean up database connection."""
		try:
			if hasattr(self, 'db'):
				self.db.__del__()
			logger.debug("Cache database connection closed")
		except Exception as e:
			logger.error(f"Error closing cache database connection: {str(e)}")