import mysql.connector
from datetime import datetime
from pathlib import Path
from .config import Config
import bcrypt
import logging
import json
import hashlib
import uuid

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

	def connect(self):
		"""Establish a new database connection."""
		try:
			if self.conn and self.conn.is_connected():
				self.cursor.close()
				self.conn.close()
			self.conn = mysql.connector.connect(
				host=config.mysql_host,
				port=config.mysql_port,
				user=config.mysql_user,
				password=config.mysql_password,
				database=config.mysql_database
			)
			self.cursor = self.conn.cursor(dictionary=True)
			logger.info("Database connection established")
		except mysql.connector.Error as e:
			logger.error(f"Failed to connect to database: {str(e)}")
			raise

	def reset_connection(self):
		"""Reset the database connection."""
		self.connect()

	def ensure_schema(self):
		"""Create database schema if it doesn't exist."""
		queries = [
			"""CREATE TABLE IF NOT EXISTS `users` (
				user_id BIGINT PRIMARY KEY,
				chat_id BIGINT NOT NULL,
				username VARCHAR(255),
				first_name VARCHAR(255),
				last_name VARCHAR(255),
				language_code VARCHAR(10) DEFAULT 'en',
				is_beta_tester BOOLEAN DEFAULT FALSE,
				is_blacklisted BOOLEAN DEFAULT FALSE,
				is_teskilat BOOLEAN DEFAULT FALSE,
				credits INT DEFAULT 0,
				balance DECIMAL(10, 2) DEFAULT 0.00,
				is_admin BOOLEAN DEFAULT FALSE,
				password VARCHAR(255),
				addresses JSON,
				payment_info JSON,
				created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
				last_interaction DATETIME DEFAULT CURRENT_TIMESTAMP
			);""",
			"""CREATE TABLE IF NOT EXISTS `groups` (
				group_id BIGINT PRIMARY KEY,
				group_name VARCHAR(255),
				type VARCHAR(50),
				is_public BOOLEAN,
				member_count INT,
				creator_id BIGINT,
				admins JSON,
				is_blacklisted BOOLEAN DEFAULT FALSE,
				added_at DATETIME
			);""",
			"""CREATE TABLE IF NOT EXISTS `transliterations` (
				id BIGINT AUTO_INCREMENT PRIMARY KEY,
				source_name VARCHAR(255) NOT NULL,
				source_lang VARCHAR(50) NOT NULL,
				target_lang VARCHAR(50) NOT NULL,
				transliterated_name VARCHAR(255) NOT NULL,
				suffix VARCHAR(255),
				score INT DEFAULT 1,
				user_id BIGINT,
				created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
				INDEX idx_transliteration (source_name, source_lang, target_lang, transliterated_name)
			) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;""",
			"""CREATE TABLE IF NOT EXISTS `transliteration_cache` (
				cache_id VARCHAR(8) PRIMARY KEY,
				user_id BIGINT NOT NULL,
				source_lang VARCHAR(10) NOT NULL,
				target_lang VARCHAR(10) NOT NULL,
				source_name TEXT NOT NULL,
				alternatives JSON NOT NULL,
				created_at DOUBLE NOT NULL,
				INDEX idx_created_at (created_at)
			);""",
			"""CREATE TABLE IF NOT EXISTS `command_usage` (
				id BIGINT AUTO_INCREMENT PRIMARY KEY,
				user_id BIGINT NOT NULL,
				chat_id BIGINT NOT NULL,
				last_used DATETIME,
				last_user_id BIGINT,
				command VARCHAR(255) NOT NULL,
				count INT DEFAULT 1,
				UNIQUE INDEX idx_user_command (user_id, command)
			);""",
			"""CREATE TABLE IF NOT EXISTS `inline_usage` (
				id INT AUTO_INCREMENT PRIMARY KEY,
				user_id BIGINT,
				chat_id BIGINT,
				query TEXT,
				timestamp DATETIME
			);""",
			"""CREATE TABLE IF NOT EXISTS `user_settings` (
				id BIGINT AUTO_INCREMENT PRIMARY KEY,
				user_id BIGINT NOT NULL,
				setting_key VARCHAR(255) NOT NULL,
				setting_value TEXT,
				UNIQUE INDEX idx_user_setting (user_id, setting_key)
			);""",
			"""CREATE TABLE IF NOT EXISTS `orders` (
				id BIGINT AUTO_INCREMENT PRIMARY KEY,
				user_id BIGINT NOT NULL,
				product_id BIGINT,
				quantity INT DEFAULT 1,
				total_price DECIMAL(10, 2) NOT NULL,
				status VARCHAR(50) DEFAULT 'pending',
				shipping_address_id VARCHAR(36),
				payment_id VARCHAR(36),
				created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
				updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
				shipped_date DATETIME,
				delivery_date DATETIME,
				cancelled_date DATETIME,
				notes TEXT,
				INDEX idx_user_id (user_id),
				INDEX idx_product_id (product_id),
				INDEX idx_status (status)
			);""",
			"""CREATE TABLE IF NOT EXISTS `products` (
				id BIGINT AUTO_INCREMENT PRIMARY KEY,
				name VARCHAR(255) NOT NULL,
				description TEXT,
				price DECIMAL(10, 2) NOT NULL,
				quantity INT,
				type VARCHAR(50) NOT NULL,
				image_url VARCHAR(255),
				features JSON,
				active BOOLEAN DEFAULT TRUE,
				created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
				updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
				created_by BIGINT,
				INDEX idx_type (type),
				INDEX idx_active (active)
			);""",
			"""CREATE TABLE IF NOT EXISTS `payments` (
				id VARCHAR(36) PRIMARY KEY,
				user_id BIGINT NOT NULL,
				amount DECIMAL(10, 2) NOT NULL,
				payment_method VARCHAR(50) NOT NULL,
				payment_details JSON,
				status VARCHAR(50) DEFAULT 'pending',
				reference VARCHAR(255),
				created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
				updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
				completed_at DATETIME,
				cancelled_at DATETIME,
				order_id BIGINT,
				INDEX idx_user_id (user_id),
				INDEX idx_status (status),
				INDEX idx_reference (reference)
			);""",
			"""CREATE TABLE IF NOT EXISTS `user_activity` (
				id BIGINT AUTO_INCREMENT PRIMARY KEY,
				user_id BIGINT NOT NULL,
				action VARCHAR(255) NOT NULL,
				details JSON,
				timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
			);""",
			"""CREATE EVENT IF NOT EXISTS `clean_transliteration_cache`
			ON SCHEDULE EVERY 1 HOUR
			DO
			DELETE FROM `transliteration_cache` WHERE created_at < UNIX_TIMESTAMP() - 3600;"""
		]
		for query in queries:
			try:
				cursor = self.conn.cursor(dictionary=True)
				cursor.execute(query)
				cursor.fetchall()
				self.conn.commit()
				cursor.close()
			except mysql.connector.Error as e:
				logger.error(f"Schema update error for query: {query[:100]}...: {str(e)}")
				if cursor:
					cursor.close()
				raise

	def get_users_paginated(self, page: int, per_page: int, search: str = "") -> tuple:
		try:
			offset = (page - 1) * per_page
			if search == "":
				users, total = self.get_users()
			else:
				query = """
				SELECT user_id, username, is_admin, is_beta_tester, is_blacklisted, is_teskilat, credits, balance, created_at, last_interaction, chat_id
				FROM `users`
				WHERE username LIKE %s
				ORDER BY user_id
				LIMIT %s OFFSET %s
				"""
				self.cursor.execute(query, (f"%{search}%", per_page, offset))
				users = self.cursor.fetchall()
				count_query = "SELECT COUNT(*) as total FROM `users` WHERE username LIKE %s"
				self.cursor.execute(count_query, (f"%{search}%",))
				total = self.cursor.fetchone()['total']
			total_pages = (total + per_page - 1) // per_page
			return users, total_pages
		finally:
			self.cursor.close()
			self.cursor = self.conn.cursor(dictionary=True)

	def get_groups_paginated(self, page: int, per_page: int, search: str = "") -> tuple:
		try:
			offset = (page - 1) * per_page
			if search == "":
				groups, total = self.get_groups()
			else:
				query = """
				SELECT g.*, u.username as last_inline_username, iu.query as last_inline_query, iu.timestamp as last_inline_timestamp
				FROM `groups` g
				LEFT JOIN (
					SELECT chat_id, MAX(timestamp) as max_timestamp
					FROM `inline_usage`
					GROUP BY chat_id
				) latest ON g.group_id = latest.chat_id
				LEFT JOIN `inline_usage` iu ON latest.chat_id = iu.chat_id AND latest.max_timestamp = iu.timestamp
				LEFT JOIN `users` u ON iu.user_id = u.user_id
				WHERE g.group_name LIKE %s
				ORDER BY g.group_id
				LIMIT %s OFFSET %s
				"""
				self.cursor.execute(query, (f"%{search}%", per_page, offset))
				groups = self.cursor.fetchall()
				count_query = "SELECT COUNT(*) as total FROM `groups` WHERE group_name LIKE %s"
				self.cursor.execute(count_query, (f"%{search}%",))
				total = self.cursor.fetchone()['total']
			total_pages = (total + per_page - 1) // per_page
			return groups, total_pages
		finally:
			self.cursor.close()
			self.cursor = self.conn.cursor(dictionary=True)

	def set_teskilat(self, user_id: int, status: bool = True) -> bool:
		try:
			query = "UPDATE `users` SET is_teskilat = %s WHERE user_id = %s"
			self.cursor.execute(query, (status, user_id))
			self.conn.commit()
			logger.info(f"Set is_teskilat to {status} for user_id {user_id}")
			return True
		except mysql.connector.Error as e:
			logger.error(f"Error setting is_teskilat: {str(e)}")
			return False
		finally:
			self.cursor.close()
			self.cursor = self.conn.cursor(dictionary=True)

	def is_teskilat(self, user_id: int) -> bool:
		try:
			query = "SELECT is_teskilat FROM `users` WHERE user_id = %s"
			self.cursor.execute(query, (user_id,))
			user = self.cursor.fetchone()
			return user['is_teskilat'] if user else False
		finally:
			self.cursor.close()
			self.cursor = self.conn.cursor(dictionary=True)

	def get_users(self) -> list:
		try:
			query = """
			SELECT user_id, username, is_admin, is_beta_tester, is_blacklisted, is_teskilat, credits, balance, created_at, last_interaction, chat_id
			FROM `users`
			"""
			self.cursor.execute(query)
			users = self.cursor.fetchall()
			count_query = "SELECT COUNT(*) as total FROM `users`"
			self.cursor.execute(count_query)
			total = self.cursor.fetchone()['total']
			return users, total
		finally:
			self.cursor.close()
			self.cursor = self.conn.cursor(dictionary=True)

	def is_blacklisted(self, user_id: int) -> bool:
		try:
			query = "SELECT is_blacklisted FROM `users` WHERE user_id = %s"
			self.cursor.execute(query, (user_id,))
			user = self.cursor.fetchone()
			return user['is_blacklisted'] if user else False
		finally:
			self.cursor.close()
			self.cursor = self.conn.cursor(dictionary=True)

	def toggle_blacklist(self, user_id: int) -> bool:
		try:
			query = """
			UPDATE `users`
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
		finally:
			self.cursor.close()
			self.cursor = self.conn.cursor(dictionary=True)

	def toggle_group_blacklist(self, group_id: int) -> bool:
		try:
			query = "UPDATE `groups` SET is_blacklisted = NOT is_blacklisted WHERE group_id = %s"
			self.cursor.execute(query, (group_id,))
			self.conn.commit()
			return True
		finally:
			self.cursor.close()
			self.cursor = self.conn.cursor(dictionary=True)

	def is_group_blacklisted(self, group_id: int) -> bool:
		try:
			query = "SELECT is_blacklisted FROM `groups` WHERE group_id = %s"
			self.cursor.execute(query, (group_id,))
			result = self.cursor.fetchone()
			return result['is_blacklisted'] if result else False
		finally:
			self.cursor.close()
			self.cursor = self.conn.cursor(dictionary=True)

	def get_user_credits(self, user_id: int) -> int:
		try:
			query = "SELECT credits FROM `users` WHERE user_id = %s"
			self.cursor.execute(query, (user_id,))
			user = self.cursor.fetchone()
			return user['credits'] if user else 0
		finally:
			self.cursor.close()
			self.cursor = self.conn.cursor(dictionary=True)

	def get_user_balance(self, user_id: int) -> float:
		try:
			query = "SELECT balance FROM `users` WHERE user_id = %s"
			self.cursor.execute(query, (user_id,))
			user = self.cursor.fetchone()
			return float(user['balance']) if user and user['balance'] is not None else 0.0
		finally:
			self.cursor.close()
			self.cursor = self.conn.cursor(dictionary=True)

	def add_balance(self, user_id: int, amount: float) -> bool:
		try:
			query = "UPDATE `users` SET balance = balance + %s WHERE user_id = %s"
			self.cursor.execute(query, (amount, user_id))
			self.conn.commit()
			logger.info(f"Added {amount} to balance for user_id {user_id}")
			return True
		except mysql.connector.Error as e:
			logger.error(f"Error adding balance: {str(e)}")
			return False
		finally:
			self.cursor.close()
			self.cursor = self.conn.cursor(dictionary=True)

	def subtract_balance(self, user_id: int, amount: float) -> bool:
		try:
			query = "UPDATE `users` SET balance = balance - %s WHERE user_id = %s AND balance >= %s"
			self.cursor.execute(query, (amount, user_id, amount))
			success = self.cursor.rowcount > 0
			self.conn.commit()
			if success:
				logger.info(f"Subtracted {amount} from balance for user_id {user_id}")
			else:
				logger.warning(f"Failed to subtract {amount} from balance for user_id {user_id} - insufficient funds")
			return success
		except mysql.connector.Error as e:
			logger.error(f"Error subtracting balance: {str(e)}")
			return False
		finally:
			self.cursor.close()
			self.cursor = self.conn.cursor(dictionary=True)

	def decrement_credits(self, user_id: int) -> None:
		try:
			query = "UPDATE `users` SET credits = credits - 1 WHERE user_id = %s AND credits > 0"
			self.cursor.execute(query, (user_id,))
			self.conn.commit()
		finally:
			self.cursor.close()
			self.cursor = self.conn.cursor(dictionary=True)

	def is_beta_tester(self, user_id: int) -> bool:
		try:
			query = "SELECT is_beta_tester FROM `users` WHERE user_id = %s"
			self.cursor.execute(query, (user_id,))
			user = self.cursor.fetchone()
			return user['is_beta_tester'] if user else False
		finally:
			self.cursor.close()
			self.cursor = self.conn.cursor(dictionary=True)

	def toggle_beta_tester(self, user_id: int) -> bool:
		try:
			query = """
			UPDATE `users`
			SET is_beta_tester = NOT is_beta_tester
			WHERE user_id = %s
			"""
			self.cursor.execute(query, (user_id,))
			self.conn.commit()
			logger.info(f"Toggled beta tester status for user_id {user_id}")
			return True
		except mysql.connector.Error as e:
			logger.error(f"Error toggling beta tester: {str(e)}")
			return False
		finally:
			self.cursor.close()
			self.cursor = self.conn.cursor(dictionary=True)

	def get_user_language(self, user_id: int) -> str:
		try:
			query = "SELECT language_code FROM `users` WHERE user_id = %s"
			self.cursor.execute(query, (user_id,))
			user = self.cursor.fetchone()
			return user['language_code'] if user else 'en'
		finally:
			self.cursor.close()
			self.cursor = self.conn.cursor(dictionary=True)

	def promote_credits(self, user_id: int, credits: int) -> bool:
		try:
			query = """
			UPDATE `users`
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
		finally:
			self.cursor.close()
			self.cursor = self.conn.cursor(dictionary=True)

	def check_if_user_exists(self, user_id: int) -> bool:
		try:
			query = "SELECT 1 FROM `users` WHERE user_id = %s"
			self.cursor.execute(query, (user_id,))
			return bool(self.cursor.fetchone())
		finally:
			self.cursor.close()
			self.cursor = self.conn.cursor(dictionary=True)

	def add_new_user(self, user_id: int, chat_id: int, username: str, first_name: str, last_name: str, language_code: str = "en", is_beta_tester: bool = False, user_credits: int = 100) -> None:
		try:
			query = """
			INSERT INTO `users` (user_id, chat_id, username, first_name, last_name, language_code, is_beta_tester, credits, balance, created_at, last_interaction)
			VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
			"""
			self.cursor.execute(query, (user_id, chat_id, username, first_name, last_name, language_code, is_beta_tester, user_credits, 0.0, datetime.now(), datetime.now()))
			self.conn.commit()
		finally:
			self.cursor.close()
			self.cursor = self.conn.cursor(dictionary=True)

	def set_user_attribute(self, user_id: int, attribute: str, value) -> None:
		try:
			query = f"UPDATE `users` SET {attribute} = %s WHERE user_id = %s"
			self.cursor.execute(query, (value, user_id))
			self.conn.commit()
		finally:
			self.cursor.close()
			self.cursor = self.conn.cursor(dictionary=True)

	def set_user_language(self, user_id: int, language_code: str) -> None:
		try:
			query = "UPDATE `users` SET language_code = %s WHERE user_id = %s"
			self.cursor.execute(query, (language_code, user_id))
			self.conn.commit()
		finally:
			self.cursor.close()
			self.cursor = self.conn.cursor(dictionary=True)

	def add_credits(self, user_id: int, amount: int):
		try:
			query = "INSERT INTO `users` (user_id, credits) VALUES (%s, %s) ON DUPLICATE KEY UPDATE credits = credits + %s"
			self.cursor.execute(query, (user_id, amount, amount))
			self.conn.commit()
		finally:
			self.cursor.close()
			self.cursor = self.conn.cursor(dictionary=True)

	def increment_command_usage(self, command, user_id, chat_id):
		query = """
		INSERT INTO command_usage (user_id, chat_id, last_used, last_user_id, command, count)
		VALUES (%s, %s, %s, %s, %s, %s)
		ON DUPLICATE KEY UPDATE count = count + 1, last_used = %s, last_user_id = %s
		"""
		try:
			now = datetime.now()
			self.cursor.execute(query, (user_id, chat_id, now, user_id, command, 1, now, user_id))
			self.conn.commit()
		except mysql.connector.Error as err:
			logging.error(f"Error incrementing command usage: {err}")
		finally:
			self.cursor.close()
			self.cursor = self.conn.cursor(dictionary=True)

	def get_command_usage(self):
		try:
			query = """
			SELECT cu.command, SUM(cu.count) as total_count, latest.last_used, latest.last_user_id, latest.chat_id
			FROM `command_usage` cu
			LEFT JOIN (
				SELECT
					command,
					last_used,
					last_user_id,
					chat_id,
					ROW_NUMBER() OVER (PARTITION BY command ORDER BY last_used DESC) as rn
				FROM `command_usage`
			) latest ON cu.command = latest.command AND latest.rn = 1
			GROUP BY cu.command, latest.last_user_id, latest.last_used, latest.chat_id
			ORDER BY total_count DESC
			"""
			self.cursor.execute(query)
			return [
				{
					'command': row['command'],
					'count': row['total_count'],
					'chat_id': row['chat_id'],
					'last_user_id': row['last_user_id'],
					'last_used': row['last_used']
				}
				for row in self.cursor.fetchall()
			]
		finally:
			self.cursor.close()
			self.cursor = self.conn.cursor(dictionary=True)

	def save_order(self, user_id: int, payment) -> bool:
		try:
			query = """
			INSERT INTO `orders` (user_id, amount, currency, payload, created_at)
			VALUES (%s, %s, %s, %s, %s)
			"""
			self.cursor.execute(query, (
				user_id,
				payment.total_amount,
				payment.currency,
				payment.invoice_payload,
				datetime.now()
			))
			self.conn.commit()
			return True
		except Exception as e:
			logger.error(f"Order Save Error: {str(e)}")
			return False
		finally:
			self.cursor.close()
			self.cursor = self.conn.cursor(dictionary=True)

	def log_user_activity(self, user_id: int, action: str, details: dict):
		try:
			query = """
			INSERT INTO `user_activity` (user_id, action, details, timestamp)
			VALUES (%s, %s, %s, %s)
			"""
			self.cursor.execute(query, (user_id, action, json.dumps(details), datetime.now()))
			self.conn.commit()
		except Exception as e:
			logger.error(f"User Activity Log Error: {str(e)}")
		finally:
			self.cursor.close()
			self.cursor = self.conn.cursor(dictionary=True)

	def add_group(self, group_id: int, group_name: str, added_at: datetime):
		try:
			query = """
			INSERT INTO `groups` (group_id, group_name, added_at)
			VALUES (%s, %s, %s)
			ON DUPLICATE KEY UPDATE group_name = %s
			"""
			self.cursor.execute(query, (group_id, group_name, added_at, group_name))
			self.conn.commit()
		finally:
			self.cursor.close()
			self.cursor = self.conn.cursor(dictionary=True)

	def update_group_details(self, group_id: int, details: dict):
		if not details:
			return
		try:
			set_clause = ", ".join([f"{key} = %s" for key in details.keys()])
			values = list(details.values())
			values.append(group_id)
			query = f"UPDATE `groups` SET {set_clause} WHERE group_id = %s"
			self.cursor.execute(query, values)
			self.conn.commit()
		finally:
			self.cursor.close()
			self.cursor = self.conn.cursor(dictionary=True)

	def get_groups(self):
		try:
			query = """
			SELECT g.*, u.username as last_inline_username, iu.query as last_inline_query, iu.timestamp as last_inline_timestamp
			FROM `groups` g
			LEFT JOIN (
				SELECT chat_id, MAX(timestamp) as max_timestamp
				FROM `inline_usage`
				GROUP BY chat_id
			) latest ON g.group_id = latest.chat_id
			LEFT JOIN `inline_usage` iu ON latest.chat_id = iu.chat_id AND latest.max_timestamp = iu.timestamp
			LEFT JOIN `users` u ON iu.user_id = u.user_id
			"""
			self.cursor.execute(query)
			groups = self.cursor.fetchall()
			count_query = "SELECT COUNT(*) as total FROM `groups`"
			self.cursor.execute(count_query)
			total = self.cursor.fetchone()['total']
			return groups, total
		finally:
			self.cursor.close()
			self.cursor = self.conn.cursor(dictionary=True)

	# ==================== USER ADDRESS MANAGEMENT ====================

	def get_user_addresses(self, user_id: int) -> list:
		"""Get all addresses for a user"""
		try:
			query = "SELECT addresses FROM `users` WHERE user_id = %s"
			self.cursor.execute(query, (user_id,))
			result = self.cursor.fetchone()
			if not result or not result['addresses']:
				return []
			try:
				addresses = json.loads(result['addresses'])
				return addresses if isinstance(addresses, list) else []
			except json.JSONDecodeError:
				logger.error(f"Error decoding addresses JSON for user {user_id}")
				return []
		finally:
			self.cursor.close()
			self.cursor = self.conn.cursor(dictionary=True)

	def get_address_by_id(self, user_id: int, address_id: str) -> dict:
		"""Get a specific address by ID for a user"""
		addresses = self.get_user_addresses(user_id)
		for address in addresses:
			if address.get('id') == address_id:
				return address
		return None

	def save_user_address(self, user_id: int, name: str, address: str, city: str, is_default: bool = False) -> str:
		"""Save a new address for a user"""
		addresses = self.get_user_addresses(user_id)
		address_id = str(uuid.uuid4())
		new_address = {
			'id': address_id,
			'name': name,
			'address': address,
			'city': city,
			'is_default': is_default
		}
		if is_default or not addresses:
			for addr in addresses:
				addr['is_default'] = False
			if not addresses:
				new_address['is_default'] = True
		addresses.append(new_address)
		try:
			query = "UPDATE `users` SET addresses = %s WHERE user_id = %s"
			self.cursor.execute(query, (json.dumps(addresses), user_id))
			self.conn.commit()
			return address_id
		finally:
			self.cursor.close()
			self.cursor = self.conn.cursor(dictionary=True)

	def update_user_address(self, user_id: int, address_id: str, name: str = None, address: str = None,
							 city: str = None, is_default: bool = None) -> bool:
		"""Update an existing address for a user"""
		addresses = self.get_user_addresses(user_id)
		updated = False
		for i, addr in enumerate(addresses):
			if addr.get('id') == address_id:
				if name is not None:
					addresses[i]['name'] = name
				if address is not None:
					addresses[i]['address'] = address
				if city is not None:
					addresses[i]['city'] = city
				if is_default:
					for j, other_addr in enumerate(addresses):
						addresses[j]['is_default'] = (j == i)
				updated = True
				break
		if updated:
			try:
				query = "UPDATE `users` SET addresses = %s WHERE user_id = %s"
				self.cursor.execute(query, (json.dumps(addresses), user_id))
				self.conn.commit()
			finally:
				self.cursor.close()
				self.cursor = self.conn.cursor(dictionary=True)
		return updated

	def delete_user_address(self, user_id: int, address_id: str) -> bool:
		"""Delete an address for a user"""
		addresses = self.get_user_addresses(user_id)
		addresses = [addr for addr in addresses if addr.get('id') != address_id]
		if not any(addr.get('is_default') for addr in addresses) and addresses:
			addresses[0]['is_default'] = True
		try:
			query = "UPDATE `users` SET addresses = %s WHERE user_id = %s"
			self.cursor.execute(query, (json.dumps(addresses), user_id))
			self.conn.commit()
			return True
		finally:
			self.cursor.close()
			self.cursor = self.conn.cursor(dictionary=True)

	# ==================== PRODUCT MANAGEMENT ====================

	def get_available_products(self, search_terms: str = "", product_type: str = None,
							active_only: bool = True, limit: int = 100, offset: int = 0,
							user_id: int = None) -> list:
		"""Get list of available products matching search criteria"""
		params = []
		conditions = []
		if active_only:
			conditions.append("active = TRUE")
		if search_terms:
			conditions.append("(name LIKE %s OR description LIKE %s)")
			search_pattern = f"%{search_terms}%"
			params.extend([search_pattern, search_pattern])
		if product_type:
			conditions.append("type = %s")
			params.append(product_type)
		if user_id:	# Add this condition
			conditions.append("created_by = %s")
			params.append(user_id)

		where_clause = " WHERE " + " AND ".join(conditions) if conditions else ""
		query = f"""
		SELECT id, name, description, price, quantity, type, image_url, features, active,
				created_at, updated_at, created_by
		FROM `products`
		{where_clause}
		ORDER BY id DESC
		LIMIT %s OFFSET %s
		"""
		params.extend([limit, offset])
		try:
			self.cursor.execute(query, params)
			products = self.cursor.fetchall()
			for product in products:
				if product['features']:
					try:
						product['features'] = json.loads(product['features'])
					except json.JSONDecodeError:
						product['features'] = []
			return products
		finally:
			self.cursor.close()
			self.cursor = self.conn.cursor(dictionary=True)

	def get_product_by_id(self, product_id: int) -> dict:
		"""Get product details by ID"""
		query = """
		SELECT id, name, description, price, quantity, type, image_url, features, active,
				 created_at, updated_at, created_by
		FROM `products`
		WHERE id = %s
		"""
		try:
			self.cursor.execute(query, (product_id,))
			product = self.cursor.fetchone()
			if product and product['features']:
				try:
					product['features'] = json.loads(product['features'])
				except json.JSONDecodeError:
					product['features'] = []
			return product
		finally:
			self.cursor.close()
			self.cursor = self.conn.cursor(dictionary=True)

	def create_product(self, name: str, price: float, product_type: str, description: str = None,
						quantity: int = None, image_url: str = None, features: list = None,
						active: bool = True, created_by: int = None) -> int:
		"""Create a new product"""
		query = """
		INSERT INTO `products` (name, description, price, quantity, type, image_url, features, active, created_by)
		VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
		"""
		features_json = json.dumps(features) if features else None
		try:
			self.cursor.execute(query, (
				name, description, price, quantity, product_type,
				image_url, features_json, active, created_by
			))
			self.conn.commit()
			return self.cursor.lastrowid
		finally:
			self.cursor.close()
			self.cursor = self.conn.cursor(dictionary=True)

	def update_product(self, product_id: int, name: str = None, price: float = None,
						product_type: str = None, description: str = None, quantity: int = None,
						image_url: str = None, features: list = None, active: bool = None) -> bool:
		"""Update an existing product"""
		set_parts = []
		params = []
		if name is not None:
			set_parts.append("name = %s")
			params.append(name)
		if price is not None:
			set_parts.append("price = %s")
			params.append(price)
		if product_type is not None:
			set_parts.append("type = %s")
			params.append(product_type)
		if description is not None:
			set_parts.append("description = %s")
			params.append(description)
		if quantity is not None:
			set_parts.append("quantity = %s")
			params.append(quantity)
		if image_url is not None:
			set_parts.append("image_url = %s")
			params.append(image_url)
		if features is not None:
			set_parts.append("features = %s")
			params.append(json.dumps(features))
		if active is not None:
			set_parts.append("active = %s")
			params.append(active)
		if not set_parts:
			return False
		params.append(product_id)
		query = f"""
		UPDATE `products`
		SET {", ".join(set_parts)}
		WHERE id = %s
		"""
		try:
			self.cursor.execute(query, params)
			self.conn.commit()
			return self.cursor.rowcount > 0
		finally:
			self.cursor.close()
			self.cursor = self.conn.cursor(dictionary=True)

	def update_product_quantity(self, product_id: int, new_quantity: int) -> bool:
		"""Update product quantity"""
		query = "UPDATE `products` SET quantity = %s WHERE id = %s"
		try:
			self.cursor.execute(query, (new_quantity, product_id))
			self.conn.commit()
			return self.cursor.rowcount > 0
		finally:
			self.cursor.close()
			self.cursor = self.conn.cursor(dictionary=True)

	def toggle_product_active(self, product_id: int) -> bool:
		"""Toggle product active status"""
		query = "UPDATE `products` SET active = NOT active WHERE id = %s"
		try:
			self.cursor.execute(query, (product_id,))
			self.conn.commit()
			return self.cursor.rowcount > 0
		finally:
			self.cursor.close()
			self.cursor = self.conn.cursor(dictionary=True)

	def delete_product(self, product_id: int) -> bool:
		"""Delete a product"""
		query = "DELETE FROM `products` WHERE id = %s"
		try:
			self.cursor.execute(query, (product_id,))
			self.conn.commit()
			return self.cursor.rowcount > 0
		finally:
			self.cursor.close()
			self.cursor = self.conn.cursor(dictionary=True)

	def get_products_count(self, user_id: int = None, active_only: bool = None) -> int:
		"""Get count of products, optionally filtered by user or active status"""
		conditions = []
		params = []
		if user_id is not None:
			conditions.append("created_by = %s")
			params.append(user_id)
		if active_only is not None:
			conditions.append("active = %s")
			params.append(active_only)
		where_clause = " WHERE " + " AND ".join(conditions) if conditions else ""
		query = f"SELECT COUNT(*) as count FROM `products`{where_clause}"
		try:
			self.cursor.execute(query, params)
			result = self.cursor.fetchone()
			return result['count'] if result else 0
		finally:
			self.cursor.close()
			self.cursor = self.conn.cursor(dictionary=True)

	# ==================== ORDER MANAGEMENT ====================

	def create_order(self, user_id: int, product_id: int, quantity: int, address_id: str,
					total_price: float, status: str = 'pending', notes: str = None) -> int:
		"""Create a new order"""
		query = """
		INSERT INTO `orders` (user_id, product_id, quantity, shipping_address_id, total_price, status, notes)
		VALUES (%s, %s, %s, %s, %s, %s, %s)
		"""
		try:
			self.cursor.execute(query, (
				user_id, product_id, quantity, address_id, total_price, status, notes
			))
			self.conn.commit()
			order_id = self.cursor.lastrowid
			self.log_user_activity(
				user_id=user_id,
				action="create_order",
				details={
					"order_id": order_id,
					"product_id": product_id,
					"quantity": quantity,
					"total_price": float(total_price)
				}
			)
			return order_id
		finally:
			self.cursor.close()
			self.cursor = self.conn.cursor(dictionary=True)

	def get_user_orders(self, user_id: int, status: str = None, limit: int = 100, offset: int = 0) -> list:
		"""Get orders for a user, optionally filtered by status"""
		conditions = ["user_id = %s"]
		params = [user_id]
		if status:
			conditions.append("status = %s")
			params.append(status)
		where_clause = " WHERE " + " AND ".join(conditions)
		query = f"""
		SELECT o.*, p.name as product_name, p.type as product_type
		FROM `orders` o
		LEFT JOIN `products` p ON o.product_id = p.id
		{where_clause}
		ORDER BY o.created_at DESC
		LIMIT %s OFFSET %s
		"""
		params.extend([limit, offset])
		try:
			self.cursor.execute(query, params)
			orders = self.cursor.fetchall()
			for order in orders:
				if order['shipping_address_id']:
					address = self.get_address_by_id(user_id, order['shipping_address_id'])
					if address:
						order['shipping_address'] = address
			return orders
		finally:
			self.cursor.close()
			self.cursor = self.conn.cursor(dictionary=True)

	def get_order_by_id(self, user_id: int, order_id: int) -> dict:
		"""Get order details by ID for a specific user"""
		query = """
		SELECT o.*, p.name as product_name, p.type as product_type, p.image_url
		FROM `orders` o
		LEFT JOIN `products` p ON o.product_id = p.id
		WHERE o.id = %s AND o.user_id = %s
		"""
		try:
			self.cursor.execute(query, (order_id, user_id))
			order = self.cursor.fetchone()
			if order and order['shipping_address_id']:
				address = self.get_address_by_id(user_id, order['shipping_address_id'])
				if address:
					order['shipping_address'] = address
			return order
		finally:
			self.cursor.close()
			self.cursor = self.conn.cursor(dictionary=True)

	def update_order_status(self, order_id: int, status: str, user_id: int = None) -> bool:
		"""Update order status"""
		params = [status]
		conditions = ["id = %s"]
		params.append(order_id)
		if user_id is not None:
			conditions.append("user_id = %s")
			params.append(user_id)
		where_clause = " WHERE " + " AND ".join(conditions)
		date_field = None
		if status == 'shipped':
			date_field = "shipped_date = CURRENT_TIMESTAMP"
		elif status == 'delivered':
			date_field = "delivery_date = CURRENT_TIMESTAMP"
		elif status == 'cancelled':
			date_field = "cancelled_date = CURRENT_TIMESTAMP"
		set_clause = "status = %s" + (f", {date_field}" if date_field else "")
		query = f"UPDATE `orders` SET {set_clause} {where_clause}"
		try:
			self.cursor.execute(query, params)
			self.conn.commit()
			return self.cursor.rowcount > 0
		finally:
			self.cursor.close()
			self.cursor = self.conn.cursor(dictionary=True)

	def get_all_orders(self, status: str = None, limit: int = 100, offset: int = 0) -> list:
		"""Get all orders, optionally filtered by status"""
		conditions = []
		params = []
		if status:
			conditions.append("o.status = %s")
			params.append(status)
		where_clause = " WHERE " + " AND ".join(conditions) if conditions else ""
		query = f"""
		SELECT o.*, p.name as product_name, p.type as product_type, u.username as customer_name
		FROM `orders` o
		LEFT JOIN `products` p ON o.product_id = p.id
		LEFT JOIN `users` u ON o.user_id = u.user_id
		{where_clause}
		ORDER BY o.created_at DESC
		LIMIT %s OFFSET %s
		"""
		params.extend([limit, offset])
		try:
			self.cursor.execute(query, params)
			return self.cursor.fetchall()
		finally:
			self.cursor.close()
			self.cursor = self.conn.cursor(dictionary=True)

	def get_order_count(self, status: str = None, user_id: int = None) -> int:
		"""Get count of orders, optionally filtered by status and/or user"""
		conditions = []
		params = []
		if status:
			conditions.append("status = %s")
			params.append(status)
		if user_id:
			conditions.append("user_id = %s")
			params.append(user_id)
		where_clause = " WHERE " + " AND ".join(conditions) if conditions else ""
		query = f"SELECT COUNT(*) as count FROM `orders`{where_clause}"
		try:
			self.cursor.execute(query, params)
			result = self.cursor.fetchone()
			return result['count'] if result else 0
		finally:
			self.cursor.close()
			self.cursor = self.conn.cursor(dictionary=True)

	# ==================== PAYMENT MANAGEMENT ====================

	def create_papara_payment(self, user_id: int, amount: float, order_id: int = None) -> dict:
		"""Create a new Papara payment record"""
		payment_id = str(uuid.uuid4())
		reference = hashlib.md5(f"{payment_id}{datetime.now().timestamp()}".encode()).hexdigest()[:8].upper()

		# Get Papara merchant details from config
		papara_number = config.papara_number
		recipient_name = config.papara_recipient_name

		payment_details = {
			'papara_number': papara_number,
			'recipient_name': recipient_name,
			'reference': reference
		}

		query = """
		INSERT INTO `payments` (id, user_id, amount, payment_method, payment_details, status, reference, order_id)
		VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
		"""
		try:
			self.cursor.execute(query, (
				payment_id, user_id, amount, 'papara', json.dumps(payment_details),
				'pending', reference, order_id
			))
			self.conn.commit()

			return {
				'payment_id': payment_id,
				'amount': amount,
				'papara_number': papara_number,
				'recipient_name': recipient_name,
				'reference': reference
			}
		except mysql.connector.Error as e:
			logger.error(f"Error creating Papara payment: {str(e)}")
			return None
		finally:
			self.cursor.close()
			self.cursor = self.conn.cursor(dictionary=True)

	def check_payment_status(self, user_id: int, reference: str) -> dict:
		"""Check status of a payment by reference"""
		query = """
		SELECT p.id as payment_id, p.amount, p.status, p.payment_details, p.order_id, p.completed_at
		FROM `payments` p
		WHERE p.user_id = %s AND p.reference = %s
		"""
		try:
			self.cursor.execute(query, (user_id, reference))
			payment = self.cursor.fetchone()
			if not payment:
				return None

			result = {
				'payment_id': payment['payment_id'],
				'amount': float(payment['amount']),
				'status': payment['status']
			}

			if payment['payment_details']:
				try:
					details = json.loads(payment['payment_details'])
					result.update(details)
				except json.JSONDecodeError:
					pass

			return result
		finally:
			self.cursor.close()
			self.cursor = self.conn.cursor(dictionary=True)

	def update_payment_status(self, payment_id: str, status: str) -> bool:
		"""Update payment status"""
		query = """
		UPDATE `payments`
		SET status = %s,
			completed_at = %s,
			cancelled_at = %s
		WHERE id = %s
		"""
		completed_at = datetime.now() if status == 'verified' else None
		cancelled_at = datetime.now() if status == 'cancelled' else None

		try:
			self.cursor.execute(query, (status, completed_at, cancelled_at, payment_id))
			self.conn.commit()

			# If payment is verified, add the amount to user's balance
			if status == 'verified':
				payment_query = "SELECT user_id, amount FROM `payments` WHERE id = %s"
				self.cursor.execute(payment_query, (payment_id,))
				payment = self.cursor.fetchone()

				if payment:
					self.add_balance(payment['user_id'], float(payment['amount']))

			return self.cursor.rowcount > 0
		except mysql.connector.Error as e:
			logger.error(f"Error updating payment status: {str(e)}")
			return False
		finally:
			self.cursor.close()
			self.cursor = self.conn.cursor(dictionary=True)

	def get_user_payments(self, user_id: int, status: str = None, limit: int = 100, offset: int = 0) -> list:
		"""Get payments for a user, optionally filtered by status"""
		conditions = ["user_id = %s"]
		params = [user_id]
		if status:
			conditions.append("status = %s")
			params.append(status)
		where_clause = " WHERE " + " AND ".join(conditions)
		query = f"""
		SELECT id, amount, payment_method, payment_details, status, reference, created_at, completed_at, cancelled_at, order_id
		FROM `payments`
		{where_clause}
		ORDER BY created_at DESC
		LIMIT %s OFFSET %s
		"""
		params.extend([limit, offset])
		try:
			self.cursor.execute(query, params)
			payments = self.cursor.fetchall()
			for payment in payments:
				if payment['payment_details']:
					try:
						payment['payment_details'] = json.loads(payment['payment_details'])
					except json.JSONDecodeError:
						payment['payment_details'] = {}
			return payments
		finally:
			self.cursor.close()
			self.cursor = self.conn.cursor(dictionary=True)

	def get_payment_by_id(self, payment_id: str) -> dict:
		"""Get payment details by ID"""
		query = """
		SELECT id, user_id, amount, payment_method, payment_details, status, reference, created_at, completed_at, cancelled_at, order_id
		FROM `payments`
		WHERE id = %s
		"""
		try:
			self.cursor.execute(query, (payment_id,))
			payment = self.cursor.fetchone()
			if payment and payment['payment_details']:
				try:
					payment['payment_details'] = json.loads(payment['payment_details'])
				except json.JSONDecodeError:
					payment['payment_details'] = {}
			return payment
		finally:
			self.cursor.close()
			self.cursor = self.conn.cursor(dictionary=True)

	def get_available_payment_methods(self) -> list:
		"""Get list of available payment methods"""
		return [
			{
				"id": "papara",
				"name": "Papara",
				"description": "Pay with Papara",
				"enabled": True,
				"icon": "papara_icon.png"
			}
		]

	def update_user_password(self, user_id: int, new_password: str) -> bool:
		"""Update user's password"""
		hashed_password = self._hash_password(new_password)
		try:
			query = "UPDATE `users` SET password = %s WHERE user_id = %s"
			self.cursor.execute(query, (hashed_password, user_id))
			self.conn.commit()
			return self.cursor.rowcount > 0
		finally:
			self.cursor.close()
			self.cursor = self.conn.cursor(dictionary=True)

	def verify_papara_payment(self, reference: str, amount: float = None) -> bool:
		"""Verify a Papara payment (would be called by webhook or email checker)"""
		payment = self.get_payment_by_reference(reference)
		if not payment:
			return False
		if amount is not None and float(payment['amount']) != float(amount):
			logger.warning(f"Payment amount mismatch: expected {payment['amount']}, got {amount}")
			return False
		return self.process_completed_payment(payment['id'])

	def verify_password(self, user_id: int, password: str) -> bool:
		"""Verify user's password"""
		try:
			query = "SELECT password FROM `users` WHERE user_id = %s"
			self.cursor.execute(query, (user_id,))
			user = self.cursor.fetchone()
			if not user or not user['password']:
				return False
			hashed_password = self._hash_password(password)
			return user['password'] == hashed_password
		finally:
			self.cursor.close()
			self.cursor = self.conn.cursor(dictionary=True)

	def user_has_password(self, user_id: int) -> bool:
		"""Check if user has a password set"""
		try:
			query = "SELECT password FROM `users` WHERE user_id = %s"
			self.cursor.execute(query, (user_id,))
			user = self.cursor.fetchone()
			return user and user['password'] is not None
		finally:
			self.cursor.close()
			self.cursor = self.conn.cursor(dictionary=True)

	def process_completed_payment(self, payment_id: str) -> bool:
		"""Process a completed payment - add credits to user and update related order if any"""
		query = """
		SELECT user_id, amount, status, credits_added, order_id
		FROM `payments`
		WHERE id = %s
		"""
		try:
			self.cursor.execute(query, (payment_id,))
			payment = self.cursor.fetchone()
			if not payment or payment['status'] == 'completed':
				return False
			self.conn.start_transaction()
			try:
				credits_to_add = int(float(payment['amount']))
				self.add_credits(payment['user_id'], credits_to_add)
				self.update_payment_status(payment_id, 'completed', credits_to_add)
				if payment['order_id']:
					self.update_order_status(payment['order_id'], 'processing')
				self.log_user_activity(
					user_id=payment['user_id'],
					action="payment_completed",
					details={
						"payment_id": payment_id,
						"amount": float(payment['amount']),
						"credits_added": credits_to_add,
						"order_id": payment['order_id']
					}
				)
				self.conn.commit()
				return True
			except Exception as e:
				self.conn.rollback()
				logger.error(f"Error processing payment {payment_id}: {str(e)}")
				return False
		finally:
			self.cursor.close()
			self.cursor = self.conn.cursor(dictionary=True)

	def is_shop_admin(self, user_id: int) -> bool:
		"""Check if user is a shop admin"""
		try:
			query = "SELECT is_admin FROM `users` WHERE user_id = %s"
			self.cursor.execute(query, (user_id,))
			user = self.cursor.fetchone()
			return user and user['is_admin']
		finally:
			self.cursor.close()
			self.cursor = self.conn.cursor(dictionary=True)

	def create_payment_record(self, user_id: int, amount: float, payment_method: str,
							 payment_details: dict, reference: str = None, order_id: int = None) -> str:
		"""Create a new payment record"""
		payment_id = str(uuid.uuid4())
		query = """
		INSERT INTO `payments` (id, user_id, amount, payment_method, payment_details, reference, order_id)
		VALUES (%s, %s, %s, %s, %s, %s, %s)
		"""
		try:
			self.cursor.execute(query, (
				payment_id, user_id, amount, payment_method,
				json.dumps(payment_details), reference, order_id
			))
			self.conn.commit()
			self.log_user_activity(
				user_id=user_id,
				action="create_payment",
				details={
					"payment_id": payment_id,
					"amount": float(amount),
					"payment_method": payment_method,
					"order_id": order_id
				}
			)
			return payment_id
		finally:
			self.cursor.close()
			self.cursor = self.conn.cursor(dictionary=True)

	def execute_query(self, query: str, params: tuple = None, fetch: bool = True) -> list:
		"""Helper method to execute queries safely."""
		cursor = None
		try:
			cursor = self.conn.cursor(dictionary=True)
			cursor.execute(query, params)
			results = cursor.fetchall() if fetch else []
			self.conn.commit()
			return results
		except mysql.connector.Error as e:
			logger.error(f"Query error: {query[:100]}... with params {params}: {str(e)}")
			raise
		finally:
			if cursor:
				cursor.close()

	def cancel_user_order(self, user_id: int, order_id: int) -> bool:
		"""Cancel a user's order and refund credits if applicable"""
		query = "SELECT status, total_price FROM `orders` WHERE id = %s AND user_id = %s"
		try:
			self.cursor.execute(query, (order_id, user_id))
			order = self.cursor.fetchone()
			if not order:
				return False
			if order['status'] not in ['pending', 'pending_payment']:
				return False
			success = self.update_order_status(order_id, 'cancelled', user_id)
			if success:
				self.add_credits(user_id, float(order['total_price']))
				self.log_user_activity(
					user_id=user_id,
					action="cancel_order",
					details={
						"order_id": order_id,
						"refunded_amount": float(order['total_price'])
					}
				)
			return success
		finally:
			self.cursor.close()
			self.cursor = self.conn.cursor(dictionary=True)

	def _hash_password(self, password: str) -> str:
		"""Hash a password (simplified for demonstration)"""
		return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

	def __del__(self):
		"""Clean up database connection and cursor."""
		try:
			if hasattr(self, 'cursor') and self.cursor is not None:
				self.cursor.close()
			if hasattr(self, 'conn') and self.conn is not None and self.conn.is_connected():
				self.conn.close()
			logger.debug("Database connection closed")
		except Exception as e:
			logger.error(f"Error closing database connection: {str(e)}")