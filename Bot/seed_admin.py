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

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def seed_admin():
	config = Config()

	# Database connection configuration with SSL
	db_config = {
		'host': config.mysql_host or 'mysql-numberfansbot-numberfansbot.j.aivencloud.com',
		'port': int(os.environ.get('MYSQL_PORT', 28236)),  # Use env var or default Aiven port
		'user': config.mysql_user or 'avnadmin',
		'password': config.mysql_password or 'real-password',
		'database': config.mysql_database or 'numberfansbot',
		'ssl_ca': os.environ.get('MYSQL_SSL_CA', '/code/ca.pem')  # Path to Aiven CA certificate
	}

	try:
		# Connect to the database
		conn = mysql.connector.connect(**db_config)
		cursor = conn.cursor(dictionary=True)

		# Check if admin user already exists
		username = os.environ.get('ADMIN_USER')
		query = "SELECT * FROM users WHERE username = %s"
		cursor.execute(query, (username,))
		existing_user = cursor.fetchone()

		if existing_user:
			logger.info(f"Admin user '{username}' already exists.")
			return

		# Hash the admin password
		password = os.environ.get('ADMIN_PASS')  # Use env var or default
		hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

		# Insert admin user, including chat_id
		query = """
		INSERT INTO users (user_id, username, password, is_admin, created_at, last_interaction, chat_id)
		VALUES (%s, %s, %s, %s, %s, %s, %s)
		"""
		cursor.execute(query, (user_id, username, hashed_password, True, datetime.now(), datetime.now(), 0))
		conn.commit()

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

if __name__ == '__main__':
	seed_admin()