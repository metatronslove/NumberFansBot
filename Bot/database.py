import mysql.connector
from datetime import datetime
from pathlib import Path
from .config import Config
import logging
import json

logger = logging.getLogger(__name__)
config = Config()

class Database:
	def __init__(self):
		self.conn = mysql.connector.connect(
			host=config.mysql_host,
			port=config.mysql_port,
			user=config.mysql_user,
			password=config.mysql_password,
			database=config.mysql_database
		)
		self.cursor = self.conn.cursor(dictionary=True)
		self.ensure_schema()

	def ensure_schema(self):
		queries = [
			"""
			CREATE TABLE IF NOT EXISTS users (
				user_id BIGINT PRIMARY KEY,
				username VARCHAR(255) UNIQUE,
				password VARCHAR(255),
				is_admin BOOLEAN DEFAULT FALSE,
				is_beta_tester BOOLEAN DEFAULT FALSE,
				is_blacklisted BOOLEAN DEFAULT FALSE,
				is_teskilat BOOLEAN DEFAULT FALSE,
				credits INT DEFAULT 0,
				created_at DATETIME,
				last_interaction DATETIME,
				chat_id BIGINT
			)
			"""
		]
		for query in queries:
			try:
				self.cursor.execute(query)
				self.conn.commit()
			except mysql.connector.Error as e:
				logger.error(f"Schema update error: {str(e)}")

	def set_teskilat(self, user_id: int, status: bool = True) -> bool:
		try:
			query = "UPDATE users SET is_teskilat = %s WHERE user_id = %s"
			self.cursor.execute(query, (status, user_id))
			self.conn.commit()
			logger.info(f"Set is_teskilat to {status} for user_id {user_id}")
			return True
		except mysql.connector.Error as e:
			logger.error(f"Error setting is_teskilat: {str(e)}")
			return False

	def is_teskilat(self, user_id: int) -> bool:
		query = "SELECT is_teskilat FROM users WHERE user_id = %s"
		self.cursor.execute(query, (user_id,))
		user = self.cursor.fetchone()
		return user['is_teskilat'] if user else False

	def get_users(self) -> list:
		query = """
		SELECT user_id, username, is_admin, is_beta_tester, is_blacklisted, is_teskilat, credits, created_at, last_interaction, chat_id
		FROM users
		"""
		self.cursor.execute(query)
		return self.cursor.fetchall()

	def is_blacklisted(self, user_id: int) -> bool:
		query = "SELECT is_blacklisted FROM users WHERE user_id = %s"
		self.cursor.execute(query, (user_id,))
		user = self.cursor.fetchone()
		return user['is_blacklisted'] if user else False

	def toggle_blacklist(self, user_id: int) -> bool:
		try:
			query = """
			UPDATE users
			SET is_blacklisted = NOT is_blacklisted
			WHERE user_id = %s
			"""
			self.cursor.execute(query, (user_id,))
			self.conn.commit()
			logger.info(f"Toggled blacklist status for user_id {user_id}")
			return True
		except mysql.connector.Error as e:
			logger.error(f"Error toggling blacklist: {str(e)}")
			return False

	def get_user_credits(self, user_id: int) -> int:
		query = "SELECT credits FROM users WHERE user_id = %s"
		self.cursor.execute(query, (user_id,))
		user = self.cursor.fetchone()
		return user['credits'] if user else 0

	def decrement_credits(self, user_id: int) -> None:
		query = "UPDATE users SET credits = credits - 1 WHERE user_id = %s AND credits > 0"
		self.cursor.execute(query, (user_id,))
		self.conn.commit()

	def is_beta_tester(self, user_id: int) -> bool:
		query = "SELECT is_beta_tester FROM users WHERE user_id = %s"
		self.cursor.execute(query, (user_id,))
		user = self.cursor.fetchone()
		return user['is_beta_tester'] if user else False

	def get_user_language(self, user_id: int) -> str:
		query = "SELECT language_code FROM users WHERE user_id = %s"
		self.cursor.execute(query, (user_id,))
		user = self.cursor.fetchone()
		return user['language_code'] if user else 'en'

	def promote_credits(self, user_id: int, credits: int) -> bool:
		try:
			query = """
			UPDATE users
			SET credits = credits + %s
			WHERE user_id = %s
			"""
			self.cursor.execute(query, (credits, user_id))
			self.conn.commit()
			logger.info(f"Promoted {credits} credits to user_id {user_id}")
			return True
		except mysql.connector.Error as e:
			logger.error(f"Error promoting credits: {str(e)}")
			return False

	def check_if_user_exists(self, user_id: int) -> bool:
		query = "SELECT 1 FROM users WHERE user_id = %s"
		self.cursor.execute(query, (user_id,))
		return bool(self.cursor.fetchone())

	def add_new_user(self, user_id: int, chat_id: int, username: str, first_name: str, last_name: str, language_code: str = "en", is_beta_tester: bool = False, user_credits: int = 100) -> None:
		query = """
		INSERT INTO users (user_id, chat_id, username, first_name, last_name, language_code, is_beta_tester, credits, created_at, last_interaction)
		VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
		"""
		self.cursor.execute(query, (user_id, chat_id, username, first_name, last_name, language_code, is_beta_tester, user_credits, datetime.now(), datetime.now()))
		self.conn.commit()

	def set_user_attribute(self, user_id: int, attribute: str, value) -> None:
		query = f"UPDATE users SET {attribute} = %s WHERE user_id = %s"
		self.cursor.execute(query, (value, user_id))
		self.conn.commit()


	def set_user_language(self, user_id: int, language_code: str) -> None:
		query = "UPDATE users SET language_code = %s WHERE user_id = %s"
		self.cursor.execute(query, (language_code, user_id))
		self.conn.commit()

	def add_credits(self, user_id: int, amount: int):
		query = "INSERT INTO users (user_id, credits) VALUES (%s, %s) ON DUPLICATE KEY UPDATE credits = credits + %s"
		self.cursor.execute(query, (user_id, amount, amount))
		self.conn.commit()

	def set_beta_tester(self, user_id: int, is_beta_tester: bool):
		query = "INSERT INTO users (user_id, is_beta_tester) VALUES (%s, %s) ON DUPLICATE KEY UPDATE is_beta_tester = %s"
		self.cursor.execute(query, (user_id, is_beta_tester, is_beta_tester))
		self.conn.commit()

	def increment_command_usage(self, command: str, user_id: int) -> None:
		query = """
		INSERT INTO command_usage (user_id, last_used, last_user_id, command, count)
		VALUES (%s, %s, %s, %s, 1)
		ON DUPLICATE KEY UPDATE count = count + 1, last_user_id = %s, last_used = %s
		"""
		now = datetime.now()  # Store datetime.now() to ensure consistency
		self.cursor.execute(query, (user_id, now, user_id, command, user_id, now))
		self.conn.commit()

	def get_command_usage(self) -> list:
		query = "SELECT command, count, last_user_id, last_used FROM command_usage ORDER BY count DESC"
		self.cursor.execute(query)
		return self.cursor.fetchall()

	def save_order(self, user_id: int, payment) -> bool:
		try:
			query = """
			INSERT INTO orders (user_id, amount, currency, payload, credits_added, created_at)
			VALUES (%s, %s, %s, %s, %s, %s)
			"""
			self.cursor.execute(query, (
				user_id,
				payment.total_amount,
				payment.currency,
				payment.invoice_payload,
				getattr(payment, 'credits_added', 0),
				datetime.now()
			))
			self.conn.commit()
			return True
		except Exception as e:
			logger.error(f"Order Save Error: {str(e)}")
			return False

	def log_user_activity(self, user_id: int, action: str, details: dict):
		try:
			query = """
			INSERT INTO user_activity (user_id, action, details, timestamp)
			VALUES (%s, %s, %s, %s)
			"""
			self.cursor.execute(query, (user_id, action, json.dumps(details), datetime.now()))
			self.conn.commit()
		except Exception as e:
			logger.error(f"User Activity Log Error: {str(e)}")

	def __del__(self):
		self.cursor.close()
		self.conn.close()