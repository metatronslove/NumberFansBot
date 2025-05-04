import mysql.connector
import bcrypt
from Bot.config import Config
from datetime import datetime
import logging
import sys
import os

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def seed_admin():
    config = Config()

    # Database connection configuration with SSL
    db_config = {
        'host': config.mysql_host or 'mysql-numberfansbot-numberfansbot.j.aivencloud.com',
        'port': config.mysql_port or 28236,
        'user': config.mysql_user or 'avnadmin',
        'password': config.mysql_password or 'real-password',
        'database': config.mysql_database or 'numberfansbot',
        'ssl_ca': '/path/to/ca.pem'  # Path to Aiven CA certificate
    }

    try:
        # Connect to the database
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor(dictionary=True)

        # Check if admin user already exists
        username = 'admin'
        query = "SELECT * FROM users WHERE username = %s"
        cursor.execute(query, (username,))
        existing_user = cursor.fetchone()

        if existing_user:
            logger.info(f"Admin user '{username}' already exists.")
            return

        # Hash the admin password
        password = 'password123'  # Default password; change in production
        hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

        # Insert admin user
        query = """
        INSERT INTO users (user_id, username, password, is_admin, created_at, last_interaction)
        VALUES (%s, %s, %s, %s, %s, %s)
        """
        cursor.execute(query, (0, username, hashed_password, True, datetime.now(), datetime.now()))
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
    # Ensure the parent directory is in sys.path
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    seed_admin()