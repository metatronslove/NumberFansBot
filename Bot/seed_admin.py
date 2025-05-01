from pymongo import MongoClient
import bcrypt
import os

# Load MongoDB URI from environment
mongodb_uri = os.getenv('MONGODB_URI')
if not mongodb_uri:
	raise ValueError("MONGODB_URI is not set")

# Connect to MongoDB
client = MongoClient(mongodb_uri)
db = client.get_database()
user_collection = db.user_collection

adminuser = os.getenv('ADMIN_USER')

# Check if admin exists
if user_collection.find_one({"username": adminuser}):
	print("Admin user already exists")
	exit()

# Create admin user
password = os.getenv('ADMIN_PASS')  # Change this to a secure password
hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
user_id = user_collection.insert_one({
	"username": adminuser,
	"password": hashed_password,
	"is_admin": True
}).inserted_id

print(f"Admin user created with ID: {user_id}")
client.close()