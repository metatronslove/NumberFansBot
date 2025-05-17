import sys
import os
import mysql.connector
import bcrypt
from datetime import datetime
import logging

# Add the project root directory to sys.path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if project_root not in sys.path:
	sys.path.insert(0, project_root)

from Bot.config import Config
from Bot.database import Database

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def seed_admin():
	config = Config()
	db = Database()

	# Database connection configuration with SSL
	# db_config = {
	# 	'host': config.mysql_host or 'mysql-numberfansbot-numberfansbot.j.aivencloud.com',
	# 	'port': config.mysql_port or 28236,
	# 	'user': config.mysql_user or 'avnadmin',
	# 	'password': config.mysql_password or 'real-password',
	# 	'database': config.mysql_database or 'numberfansbot',
	# 	'ssl_ca': os.environ.get('MYSQL_SSL_CA', '/code/ca.pem')  # Path to Aiven CA certificate
	# }

	try:
		# Check if admin user already exists
		username = os.environ.get('ADMIN_USER')
		query = "SELECT * FROM users WHERE username = %s"
		existing_user = db.execute_query(query, (username))

		if existing_user:
			logger.info(f"Admin user '{username}' already exists.")
			return

		# Hash the admin password
		password = os.environ.get('ADMIN_PASS')  # Use env var or default
		hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

		# Insert admin user, including chat_id
		query = """
		INSERT INTO users (user_id, chat_id, username, first_name, last_name, language_code, is_beta_tester, credits, is_admin, password, created_at, last_interaction)
		VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
		"""
		db.execute_query(query, (0, 0, username, 'Abdil Murat', 'ÜNALAN', 'tr', True, 100, True, hashed_password, datetime.now(), datetime.now()))

		logger.info(f"Admin user '{username}' created successfully.")

	except mysql.connector.Error as e:
		logger.error(f"Database error: {str(e)}")
		sys.exit(1)
	except Exception as e:
		logger.error(f"Error seeding admin user: {str(e)}")
		sys.exit(1)
	finally:
		if 'cursor' in locals():
			cursor.close()
		if 'conn' in locals() and conn.is_connected():
			conn.close()