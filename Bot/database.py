from pymongo import MongoClient
from datetime import datetime
from pathlib import Path
from .config import Config
import logging

logger = logging.getLogger(__name__)
config = Config()

class Database:
	def __init__(self):
		self.client = MongoClient(config.mongodb_uri)
		self.db = self.client['numberfansbot']
		self.user_collection = self.db['users']
		self.command_usage = self.db['command_usage']
		self.command_usage_collection = self.db.command_usage
		self.user_settings_collection = self.db.user_settings
		self.orders_collection = self.db.orders
		self.user_activity_collection = self.db.user_activity
		self.transliteration_collection = self.db.transliteration
		self.blacklist_collection = self.db.blacklist

	def check_if_user_exists(self, user_id: int) -> bool:
		return self.user_collection.count_documents({"_id": user_id}) > 0

	def add_new_user(self, user_id: int, chat_id: int, username: str, first_name: str, last_name: str):
		self.user_collection.insert_one({
			"_id": user_id,
			"chat_id": chat_id,
			"username": username,
			"first_name": first_name,
			"last_name": last_name,
			"language": "en",
			"credits": 100,  # Initial promotion credits
			"is_beta_tester": False,
			"last_interaction": datetime.now(),
			"created_at": datetime.now()
		})

	def set_user_attribute(self, user_id: int, attribute: str, value):
		self.user_collection.update_one(
			{"_id": user_id},
			{"$set": {attribute: value}},
			upsert=True
		)

	def get_user_language(self, user_id: int) -> str:
		settings = self.user_settings_collection.find_one({"user_id": user_id})
		return settings.get("language", "en") if settings else "en"

	def set_user_language(self, user_id: int, language: str):
		self.user_settings_collection.update_one(
			{"user_id": user_id},
			{"$set": {"language": language}},
			upsert=True
		)

	def get_user_credits(self, user_id: int) -> int:
		user = self.user_collection.find_one({"_id": user_id})
		return user.get("credits", 0) if user else 0

	def decrement_credits(self, user_id: int) -> bool:
		result = self.user_collection.update_one(
			{"_id": user_id, "credits": {"$gt": 0}, "is_beta_tester": False},
			{"$inc": {"credits": -1}}
		)
		return result.modified_count > 0

	def add_credits(self, user_id: int, amount: int):
		self.user_collection.update_one(
			{"_id": user_id},
			{"$inc": {"credits": amount}},
			upsert=True
		)

	def is_beta_tester(self, user_id: int) -> bool:
		user = self.user_collection.find_one({"_id": user_id})
		return user.get("is_beta_tester", False) if user else False

	def set_beta_tester(self, user_id: int, is_beta_tester: bool):
		self.user_collection.update_one(
			{"_id": user_id},
			{"$set": {"is_beta_tester": is_beta_tester}},
			upsert=True
		)

	def is_blacklisted(self, user_id: int) -> bool:
		return self.blacklist_collection.count_documents({"user_id": user_id}) > 0

	def add_to_blacklist(self, user_id: int):
		self.blacklist_collection.update_one(
			{"user_id": user_id},
			{"$set": {"user_id": user_id, "added_at": datetime.now()}},
			upsert=True
		)

	def remove_from_blacklist(self, user_id: int):
		self.blacklist_collection.delete_one({"user_id": user_id})

	def increment_command_usage(self, command: str, user_id: int):
		self.command_usage_collection.update_one(
			{"command": command},
			{
				"$inc": {"count": 1},
				"$set": {
					"last_used": datetime.now(),
					"last_user_id": user_id
				},
				"$push": {
					"usage_history": {
						"user_id": user_id,
						"timestamp": datetime.now()
					}
				}
			},
			upsert=True
		)

	def get_command_usage(self) -> list:
		return list(self.command_usage_collection.find().sort("count", -1))

	def save_order(self, user_id: int, payment) -> bool:
		try:
			self.orders_collection.insert_one({
				"user_id": user_id,
				"amount": payment.total_amount,
				"currency": payment.currency,
				"payload": payment.invoice_payload,
				"credits_added": payment.credits_added if hasattr(payment, 'credits_added') else 0,
				"created_at": datetime.now()
			})
			return True
		except Exception as e:
			logger.error(f"Order Save Error: {str(e)}")
			return False

	def log_user_activity(self, user_id: int, action: str, details: dict):
		try:
			self.user_activity_collection.insert_one({
				"user_id": user_id,
				"action": action,
				"details": details,
				"timestamp": datetime.now()
			})
		except Exception as e:
			logger.error(f"User Activity Log Error: {str(e)}")

	def __del__(self):
		self.client.close()