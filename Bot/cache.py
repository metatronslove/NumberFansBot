from pymongo import MongoClient, IndexModel, ASCENDING
from .config import config
import hashlib
import time

class Cache:
	def __init__(self):
		self.client = MongoClient(config.mongodb_uri)
		self.db = self.client.get_database()
		self.cache_collection = self.db.transliteration_cache
		# Create TTL index to expire entries after 1 hour
		self.cache_collection.create_indexes([
			IndexModel([("created_at", ASCENDING)], expireAfterSeconds=3600)
		])

	def store_alternatives(self, user_id: int, source_lang: str, target_lang: str, text: str, alternatives: list) -> str:
		"""Store alternatives and return a cache ID."""
		# Generate a unique cache ID based on user_id, text, and timestamp
		cache_id = hashlib.md5(f"{user_id}:{text}:{time.time()}".encode()).hexdigest()[:8]  # 8-char hash
		cache_data = {
			"cache_id": cache_id,
			"user_id": user_id,
			"source_lang": source_lang,
			"target_lang": target_lang,
			"source_name": text,
			"alternatives": alternatives,
			"created_at": time.time()
		}
		self.cache_collection.insert_one(cache_data)
		return cache_id

	def get_alternatives(self, cache_id: str) -> dict:
		"""Retrieve alternatives by cache ID."""
		return self.cache_collection.find_one({"cache_id": cache_id}) or {}