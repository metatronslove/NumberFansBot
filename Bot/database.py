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
            host=config.mysql_host.split(':')[0],
            port=int(config.mysql_host.split(':')[1]) if ':' in config.mysql_host else 3306,
            user=config.mysql_user,
            password=config.mysql_password,
            database=config.mysql_database
        )
        self.cursor = self.conn.cursor(dictionary=True)

    def check_if_user_exists(self, user_id: int) -> bool:
        query = "SELECT 1 FROM users WHERE user_id = %s"
        self.cursor.execute(query, (user_id,))
        return bool(self.cursor.fetchone())

    def add_new_user(self, user_id: int, chat_id: int, username: str, first_name: str, last_name: str, language_code: str = "en", is_beta_tester: bool = False) -> None:
        query = """
        INSERT INTO users (user_id, chat_id, username, first_name, last_name, language_code, is_beta_tester, created_at, last_interaction)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        self.cursor.execute(query, (user_id, chat_id, username, first_name, last_name, language_code, is_beta_tester, datetime.now(), datetime.now()))
        self.conn.commit()

    def set_user_attribute(self, user_id: int, attribute: str, value) -> None:
        query = f"UPDATE users SET {attribute} = %s WHERE user_id = %s"
        self.cursor.execute(query, (value, user_id))
        self.conn.commit()

    def get_user_language(self, user_id: int) -> str:
        query = "SELECT language_code FROM users WHERE user_id = %s"
        self.cursor.execute(query, (user_id,))
        result = self.cursor.fetchone()
        return result['language_code'] if result else "en"

    def set_user_language(self, user_id: int, language_code: str) -> None:
        query = "UPDATE users SET language_code = %s WHERE user_id = %s"
        self.cursor.execute(query, (language_code, user_id))
        self.conn.commit()

    def get_user_credits(self, user_id: int) -> int:
        query = "SELECT credits FROM users WHERE user_id = %s"
        self.cursor.execute(query, (user_id,))
        result = self.cursor.fetchone()
        return result['credits'] if result else 0

    def decrement_credits(self, user_id: int) -> bool:
        query = "UPDATE users SET credits = credits - 1 WHERE user_id = %s AND credits > 0 AND is_beta_tester = FALSE"
        self.cursor.execute(query, (user_id,))
        self.conn.commit()
        return self.cursor.rowcount > 0

    def add_credits(self, user_id: int, amount: int):
        query = "INSERT INTO users (user_id, credits) VALUES (%s, %s) ON DUPLICATE KEY UPDATE credits = credits + %s"
        self.cursor.execute(query, (user_id, amount, amount))
        self.conn.commit()

    def is_beta_tester(self, user_id: int) -> bool:
        query = "SELECT is_beta_tester FROM users WHERE user_id = %s"
        self.cursor.execute(query, (user_id,))
        result = self.cursor.fetchone()
        return result['is_beta_tester'] if result else False

    def set_beta_tester(self, user_id: int, is_beta_tester: bool):
        query = "INSERT INTO users (user_id, is_beta_tester) VALUES (%s, %s) ON DUPLICATE KEY UPDATE is_beta_tester = %s"
        self.cursor.execute(query, (user_id, is_beta_tester, is_beta_tester))
        self.conn.commit()

    def is_blacklisted(self, user_id: int) -> bool:
        query = "SELECT 1 FROM blacklist WHERE user_id = %s"
        self.cursor.execute(query, (user_id,))
        return bool(self.cursor.fetchone())

    def add_to_blacklist(self, user_id: int):
        query = "INSERT INTO blacklist (user_id, added_at) VALUES (%s, %s) ON DUPLICATE KEY UPDATE added_at = %s"
        self.cursor.execute(query, (user_id, datetime.now(), datetime.now()))
        self.conn.commit()

    def remove_from_blacklist(self, user_id: int):
        query = "DELETE FROM blacklist WHERE user_id = %s"
        self.cursor.execute(query, (user_id))
        self.conn.commit()

    def increment_command_usage(self, command: str, user_id: int) -> None:
        query = """
        INSERT INTO command_usage (user_id, command, count)
        VALUES (%s, %s, 1)
        ON DUPLICATE KEY UPDATE count = count + 1
        """
        self.cursor.execute(query, (user_id, command))
        self.conn.commit()

    def get_command_usage(self) -> list:
        query = "SELECT user_id, command, count FROM command_usage ORDER BY count DESC"
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