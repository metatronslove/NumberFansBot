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
            """CREATE TABLE IF NOT EXISTS users (
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
            	is_admin BOOLEAN DEFAULT FALSE,
            	password VARCHAR(255),
            	created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            	last_interaction DATETIME DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS groups (
                group_id BIGINT PRIMARY KEY,
                group_name VARCHAR(255),
                type VARCHAR(50),          -- e.g., "group", "supergroup", "channel"
                is_public BOOLEAN,         -- True if public, False if private
                member_count INT,          -- Number of members
                creator_id BIGINT,         -- ID of the founder
                admins JSON,               -- List of admin IDs as JSON
                is_blacklisted BOOLEAN DEFAULT FALSE,
                added_at DATETIME
            );
            CREATE TABLE IF NOT EXISTS transliterations (
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
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
            CREATE TABLE IF NOT EXISTS transliteration_cache (
            	cache_id VARCHAR(8) PRIMARY KEY,
            	user_id BIGINT NOT NULL,
            	source_lang VARCHAR(10) NOT NULL,
            	target_lang VARCHAR(10) NOT NULL,
            	source_name TEXT NOT NULL,
            	alternatives JSON NOT NULL,
            	created_at DOUBLE NOT NULL,
            	INDEX idx_created_at (created_at)
            );
            CREATE TABLE IF NOT EXISTS command_usage (
            	id BIGINT AUTO_INCREMENT PRIMARY KEY,
            	user_id BIGINT NOT NULL,
            	last_used DATETIME,
            	last_user_id BIGINT,
            	command VARCHAR(255) NOT NULL,
            	count INT DEFAULT 1,
            	UNIQUE INDEX idx_user_command (user_id, command)
            );
            CREATE TABLE IF NOT EXISTS inline_usage (
                id INT AUTO_INCREMENT PRIMARY KEY,
                user_id BIGINT,
                chat_id BIGINT,
                query TEXT,
                timestamp DATETIME
            );
            CREATE TABLE IF NOT EXISTS user_settings (
            	id BIGINT AUTO_INCREMENT PRIMARY KEY,
            	user_id BIGINT NOT NULL,
            	setting_key VARCHAR(255) NOT NULL,
            	setting_value TEXT,
            	UNIQUE INDEX idx_user_setting (user_id, setting_key)
            );
            CREATE TABLE IF NOT EXISTS orders (
            	id BIGINT AUTO_INCREMENT PRIMARY KEY,
            	user_id BIGINT NOT NULL,
            	amount INT NOT NULL,
            	currency VARCHAR(10) NOT NULL,
            	payload TEXT,
            	credits_added INT DEFAULT 0,
            	created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS user_activity (
            	id BIGINT AUTO_INCREMENT PRIMARY KEY,
            	user_id BIGINT NOT NULL,
            	action VARCHAR(255) NOT NULL,
            	details JSON,
            	timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            );
            -- TTL-like behavior for transliteration_cache
            DELIMITER //
            CREATE EVENT IF NOT EXISTS clean_transliteration_cache
            ON SCHEDULE EVERY 1 HOUR
            DO
            BEGIN
            	DELETE FROM transliteration_cache WHERE created_at < UNIX_TIMESTAMP() - 3600;
            END //
            DELIMITER ;
			"""
        ]
        for query in queries:
            try:
                self.cursor.execute(query)
                self.conn.commit()
            except mysql.connector.Error as e:
                logger.error(f"Schema update error: {str(e)}")

    def get_users_paginated(self, page: int, per_page: int, search: str = "") -> tuple:
        offset = (page - 1) * per_page
        query = """
        SELECT user_id, username, is_admin, is_beta_tester, is_blacklisted, is_teskilat, credits, created_at, last_interaction, chat_id
        FROM users
        WHERE username LIKE %s
        ORDER BY user_id
        LIMIT %s OFFSET %s
        """
        self.cursor.execute(query, (f"%{search}%", per_page, offset))
        users = self.cursor.fetchall()
        count_query = "SELECT COUNT(*) as total FROM users WHERE username LIKE %s"
        self.cursor.execute(count_query, (f"%{search}%",))
        total = self.cursor.fetchone()['total']
        total_pages = (total + per_page - 1) // per_page
        return users, total_pages

    def get_groups_paginated(self, page: int, per_page: int, search: str = "") -> tuple:
        offset = (page - 1) * per_page
        query = """
        SELECT g.*, u.username as last_inline_username, iu.query as last_inline_query, iu.timestamp as last_inline_timestamp
        FROM groups g
        LEFT JOIN (
            SELECT chat_id, MAX(timestamp) as max_timestamp
            FROM inline_usage
            GROUP BY chat_id
        ) latest ON g.group_id = latest.chat_id
        LEFT JOIN inline_usage iu ON latest.chat_id = iu.chat_id AND latest.max_timestamp = iu.timestamp
        LEFT JOIN users u ON iu.user_id = u.user_id
        WHERE g.group_name LIKE %s
        ORDER BY g.group_id
        LIMIT %s OFFSET %s
        """
        self.cursor.execute(query, (f"%{search}%", per_page, offset))
        groups = self.cursor.fetchall()
        count_query = "SELECT COUNT(*) as total FROM groups WHERE group_name LIKE %s"
        self.cursor.execute(count_query, (f"%{search}%",))
        total = self.cursor.fetchone()['total']
        total_pages = (total + per_page - 1) // per_page
        return groups, total_pages

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

	def toggle_group_blacklist(self, group_id: int) -> bool:
		query = "UPDATE groups SET is_blacklisted = NOT is_blacklisted WHERE group_id = %s"
		self.cursor.execute(query, (group_id,))
		self.conn.commit()
		return True

	def is_group_blacklisted(self, group_id: int) -> bool:
		query = "SELECT is_blacklisted FROM groups WHERE group_id = %s"
		self.cursor.execute(query, (group_id,))
		result = self.cursor.fetchone()
		return result['is_blacklisted'] if result else False

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

	def toggle_beta_tester(self, user_id: int) -> bool:
		try:
			query = """
			UPDATE users
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

	def increment_command_usage(self, command: str, user_id: int, chat_id: int = None):
		query = """
		INSERT INTO command_usage (user_id, last_used, last_user_id, command, count, chat_id)
		VALUES (%s, %s, %s, %s, 1, %s)
		ON DUPLICATE KEY UPDATE count = count + 1, last_user_id = %s, last_used = %s, chat_id = %s
		"""
		now = datetime.now()
		self.cursor.execute(query, (user_id, now, user_id, command, chat_id, user_id, now, chat_id))
		self.conn.commit()

	def get_command_usage(self):
		query = """
		SELECT
			cu.command,
			SUM(cu.count) as total_count,
			latest.last_user_id,
			latest.last_used,
			latest.chat_id
		FROM command_usage cu
		INNER JOIN (
			SELECT
				command,
				last_user_id,
				last_used,
				chat_id,
				ROW_NUMBER() OVER (PARTITION BY command ORDER BY last_used DESC) as rn
			FROM command_usage
		) latest ON cu.command = latest.command AND latest.rn = 1
		GROUP BY cu.command, latest.last_user_id, latest.last_used, latest.chat_id
		ORDER BY total_count DESC
		"""
		self.cursor.execute(query)
		return [
			{
				'command': row['command'],
				'count': row['total_count'],
				'last_user_id': row['last_user_id'],
				'last_used': row['last_used'],
				'chat_id': row['chat_id']
			}
			for row in self.cursor.fetchall()
		]

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

    def add_group(self, group_id: int, group_name: str, added_at: datetime):
        query = """
        INSERT INTO groups (group_id, group_name, added_at)
        VALUES (%s, %s, %s)
        ON DUPLICATE KEY UPDATE group_name = %s
        """
        self.cursor.execute(query, (group_id, group_name, added_at, group_name))
        self.conn.commit()

    def update_group_details(self, group_id: int, details: dict):
        if not details:
            return
        set_clause = ", ".join([f"{key} = %s" for key in details.keys()])
        values = list(details.values())
        values.append(group_id)
        query = f"UPDATE groups SET {set_clause} WHERE group_id = %s"
        self.cursor.execute(query, values)
        self.conn.commit()

	def get_groups(self):
		query = """
		SELECT g.*, u.username as last_inline_username, iu.query as last_inline_query, iu.timestamp as last_inline_timestamp
		FROM groups g
		LEFT JOIN (
			SELECT chat_id, MAX(timestamp) as max_timestamp
			FROM inline_usage
			GROUP BY chat_id
		) latest ON g.group_id = latest.chat_id
		LEFT JOIN inline_usage iu ON latest.chat_id = iu.chat_id AND latest.max_timestamp = iu.timestamp
		LEFT JOIN users u ON iu.user_id = u.user_id
		"""
		self.cursor.execute(query)
		return self.cursor.fetchall()

	def __del__(self):
		self.cursor.close()
		self.conn.close()