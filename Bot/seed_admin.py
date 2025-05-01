from pymongo import MongoClient
import bcrypt
import os
import sys

# Load environment variables
mongodb_uri = os.getenv('MONGODB_URI')
admin_user = os.getenv('ADMIN_USER')  # Default to 'admin' if not set
admin_pass = os.getenv('ADMIN_PASS')  # Default to 'password123' if not set

# Check for required environment variables
missing_vars = []
if not mongodb_uri:
    missing_vars.append('MONGODB_URI')
if not admin_user:
    missing_vars.append('ADMIN_USER')
if not admin_pass:
    missing_vars.append('ADMIN_PASS')

if missing_vars:
    print(f"Error: The following environment variables are not set: {', '.join(missing_vars)}")
    sys.exit(1)

try:
    # Connect to MongoDB
    client = MongoClient(mongodb_uri)
    db = client.get_database()
    user_collection = db.user_collection

    # Check if admin exists
    if user_collection.find_one({"username": admin_user}):
        print(f"Admin user '{admin_user}' already exists")
        client.close()
        sys.exit(0)

    # Create admin user
    hashed_password = bcrypt.hashpw(admin_pass.encode('utf-8'), bcrypt.gensalt())
    user_id = user_collection.insert_one({
        "username": admin_user,
        "password": hashed_password,
        "is_admin": True
    }).inserted_id

    print(f"Admin user '{admin_user}' created with ID: {user_id}")
    client.close()
    sys.exit(0)

except Exception as e:
    print(f"Error creating admin user: {str(e)}")
    client.close()
    sys.exit(1)