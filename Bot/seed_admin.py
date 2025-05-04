import mysql.connector
import bcrypt
import os
import sys
from .config import Config

config = Config()

# Load environment variables
admin_user = os.getenv('ADMIN_USER', 'admin')
admin_pass = os.getenv('ADMIN_PASS', 'password123')

# Check for required environment variables
missing_vars = []
if not config.mysql_host:
    missing_vars.append('MYSQL_HOST')
if not config.mysql_user:
    missing_vars.append('MYSQL_USER')
if not config.mysql_password:
    missing_vars.append('MYSQL_PASSWORD')
if not config.mysql_database:
    missing_vars.append('MYSQL_DATABASE')
if not admin_user:
    missing_vars.append('ADMIN_USER')
if not admin_pass:
    missing_vars.append('ADMIN_PASS')

if missing_vars:
    print(f"Error: The following environment variables are not set: {', '.join(missing_vars)}")
    sys.exit(1)

try:
    # Connect to MySQL
    conn = mysql.connector.connect(
        host=config.mysql_host.split(':')[0],
        port=int(config.mysql_host.split(':')[1]) if ':' in config.mysql_host else 3306,
        user=config.mysql_user,
        password=config.mysql_password,
        database=config.mysql_database
    )
    cursor = conn.cursor(dictionary=True)

    # Check if admin exists
    query = "SELECT 1 FROM users WHERE username = %s AND is_admin = TRUE"
    cursor.execute(query, (admin_user,))
    if cursor.fetchone():
        print(f"Admin user '{admin_user}' already exists")
        cursor.close()
        conn.close()
        sys.exit(0)

    # Create admin user
    hashed_password = bcrypt.hashpw(admin_pass.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    query = """
    INSERT INTO users (user_id, username, password, is_admin, created_at, last_interaction)
    VALUES (%s, %s, %s, %s, NOW(), NOW())
    """
    cursor.execute(query, (0, admin_user, hashed_password, True))
    conn.commit()

    print(f"Admin user '{admin_user}' created successfully")
    cursor.close()
    conn.close()
    sys.exit(0)

except Exception as e:
    print(f"Error creating admin user: {str(e)}")
    cursor.close()
    conn.close()
    sys.exit(1)