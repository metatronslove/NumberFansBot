import logging
import os
import re
import bcrypt
import yaml
import requests
import asyncio
import urllib
import importlib
import sys
import json
from flask import Flask, request, render_template, redirect, url_for, session, flash, jsonify
from asgiref.wsgi import WsgiToAsgi
from Bot.config import Config
from Bot.database import Database
from Bot.Helpers.i18n import I18n
from .seed_admin import seed_admin
from pathlib import Path
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
	Application, CommandHandler, MessageHandler, CallbackQueryHandler, PreCheckoutQueryHandler,
	ConversationHandler, filters, ContextTypes, InlineQueryHandler
)
from telegram.constants import ParseMode
from telegram.error import BadRequest

# Initialize Flask app
flask_app = Flask(__name__, template_folder="/code/Templates/", static_folder="/code/Assets", static_url_path="/Assets")
config = Config()
flask_app.secret_key = config.flask_secret_key
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Define available languages
AVAILABLE_LANGUAGES = ["en", "tr", "ar", "he", "la"]

# Initialize Telegram application
telegram_app = Application.builder().token(config.telegram_token).build()

# Flag to ensure initialization happens only once
_initialized = False

async def initialize_telegram_app():
	"""Initialize the Telegram application asynchronously."""
	global _initialized
	if not _initialized:
		try:
			logger.info("Starting Telegram application initialization")
			await telegram_app.initialize()
			logger.info("Telegram application initialized successfully")
			_initialized = True
		except Exception as e:
			logger.error(f"Failed to initialize Telegram application: {str(e)}")
			raise
	else:
		logger.info("Telegram application already initialized")

async def set_webhook_on_startup():
	"""Set the Telegram webhook after initialization."""
	if not config.telegram_token:
		logger.error("TELEGRAM_TOKEN is not set, cannot set webhook")
		return
	webhook_url = f"https://{os.getenv('RENDER_EXTERNAL_HOSTNAME', 'localhost')}/bot{config.telegram_token}"
	try:
		await telegram_app.bot.set_webhook(url=webhook_url)
		logger.info(f"Webhook set successfully to {webhook_url}")
	except Exception as e:
		logger.error(f"Failed to set webhook: {str(e)}")

async def setup_telegram_app():
	"""Schedule or run Telegram initialization and webhook setup."""
	try:
		logger.info("Scheduling Telegram initialization and webhook setup")
		await initialize_telegram_app()
		await set_webhook_on_startup()
	except Exception as e:
		logger.error(f"Initialization or webhook setup error: {str(e)}")
		raise

# Schedule initialization and webhook setup
try:
	loop = asyncio.get_event_loop()
	if loop.is_running():
		logger.info("Event loop is running, scheduling Telegram initialization as a task")
		asyncio.create_task(setup_telegram_app())
	else:
		logger.info("Event loop is not running, running Telegram initialization directly")
		asyncio.run(setup_telegram_app())
except Exception as e:
	logger.error(f"Failed to schedule Telegram initialization: {str(e)}")
	raise

# Register handlers
def register_handlers():
	from .Commands.UserCommands.abjad import get_abjad_conversation_handler
	from .Commands.UserCommands.bastet import get_bastet_conversation_handler
	from .Commands.UserCommands.huddam import get_huddam_conversation_handler
	from .Commands.UserCommands.unsur import get_unsur_conversation_handler
	from .Commands.UserCommands.transliterate import get_transliterate_conversation_handler
	from .Commands.UserCommands import numerology as user_numerology
	from .Commands.UserCommands import convert_numbers as user_convert_numbers
	from .Commands.UserCommands import magic_square as user_magic_square
	from .Commands.UserCommands import nutket as user_nutket
	from .Commands.SystemCommands.payment import (
		payment_handle, handle_pre_checkout, handle_successful_payment
	)
	from .Commands.SystemCommands import (
		start, help, language, cancel, settings, credits, callback_query
	)
	from .Commands.InlineCommands import (
		abjad, bastet, huddam, unsur, nutket, transliterate, numerology,
		magic_square, convert_numbers
	)
	from .Commands.ShopCommands.buy import BuyCommand
	from .Commands.ShopCommands.address import AddressCommand
	from .Commands.ShopCommands.password import PasswordCommand
	from .Commands.ShopCommands.orders import OrdersCommand
	from .Commands.ShopCommands.papara import PaparaCommand
	from .Commands.InlineShopCommands.shop import ShopInlineCommand
	from .Commands.InlineShopCommands.product import ProductInlineCommand
	from .Commands.InlineShopCommands.update import UpdateInlineCommand

	try:
		# Initialize database and reset connection
		db = Database()
		try:
			db.reset_connection()
			logger.info("Database connection reset successfully")
		except Exception as e:
			logger.error(f"Failed to reset database connection: {str(e)}")
			raise

		# Register conversation and command handlers
		telegram_app.add_handler(get_abjad_conversation_handler())
		telegram_app.add_handler(get_bastet_conversation_handler())
		telegram_app.add_handler(get_huddam_conversation_handler())
		telegram_app.add_handler(get_unsur_conversation_handler())
		telegram_app.add_handler(get_transliterate_conversation_handler())
		telegram_app.add_handler(PreCheckoutQueryHandler(handle_pre_checkout))		# Register inline query handlers
		telegram_app.add_handler(InlineQueryHandler(abjad, pattern=r"^/abjad"))
		telegram_app.add_handler(InlineQueryHandler(bastet, pattern=r"^/bastet"))
		telegram_app.add_handler(InlineQueryHandler(huddam, pattern=r"^/huddam"))
		telegram_app.add_handler(InlineQueryHandler(unsur, pattern=r"^/unsur"))
		telegram_app.add_handler(InlineQueryHandler(nutket, pattern=r"^/nutket"))
		telegram_app.add_handler(InlineQueryHandler(transliterate, pattern=r"^/transliterate"))
		telegram_app.add_handler(InlineQueryHandler(numerology, pattern=r"^/numerology"))
		telegram_app.add_handler(InlineQueryHandler(magic_square, pattern=r"^/magicsquare"))
		telegram_app.add_handler(InlineQueryHandler(convert_numbers, pattern=r"^/convertnumbers"))

		# Register inline shop command handlers
		try:
			shop_inline_command = ShopInlineCommand()
			shop_inline_command.register_handlers(telegram_app)
		except Exception as e:
			logger.error(f"Failed to register ShopInlineCommand handlers: {str(e)}")
			raise
		try:
			product_inline_command = ProductInlineCommand()
			product_inline_command.register_handlers(telegram_app)
		except Exception as e:
			logger.error(f"Failed to register ProductInlineCommand handlers: {str(e)}")
			raise
		try:
			update_inline_command = UpdateInlineCommand()
			update_inline_command.register_handlers(telegram_app)
		except Exception as e:
			logger.error(f"Failed to register UpdateInlineCommand handlers: {str(e)}")
			raise

		# Register shop command handlers
		try:
			buy_command = BuyCommand()
			buy_command.register_handlers(telegram_app)
		except Exception as e:
			logger.error(f"Failed to register BuyCommand handlers: {str(e)}")
			raise
		try:
			address_command = AddressCommand()
			address_command.register_handlers(telegram_app)
		except Exception as e:
			logger.error(f"Failed to register AddressCommand handlers: {str(e)}")
			raise
		try:
			password_command = PasswordCommand()
			password_command.register_handlers(telegram_app)
		except Exception as e:
			logger.error(f"Failed to register PasswordCommand handlers: {str(e)}")
			raise
		try:
			orders_command = OrdersCommand()
			orders_command.register_handlers(telegram_app)
		except Exception as e:
			logger.error(f"Failed to register OrdersCommand handlers: {str(e)}")
			raise
		try:
			papara_command = PaparaCommand()
			papara_command.register_handlers(telegram_app)
		except Exception as e:
			logger.error(f"Failed to register PaparaCommand handlers: {str(e)}")
			raise

		telegram_app.add_handler(CommandHandler("numerology", user_numerology.numerology_handle))
		telegram_app.add_handler(CommandHandler("convertnumbers", user_convert_numbers.convert_numbers_handle))
		telegram_app.add_handler(CommandHandler("magicsquare", user_magic_square.magic_square_handle))
		telegram_app.add_handler(CommandHandler("nutket", user_nutket.nutket_handle))
		telegram_app.add_handler(CommandHandler("cancel", cancel.cancel_handle))
		telegram_app.add_handler(MessageHandler(filters.SUCCESSFUL_PAYMENT, handle_successful_payment))
		telegram_app.add_handler(CallbackQueryHandler(callback_query.set_language_handle, pattern=r"lang\|.+"))
		telegram_app.add_handler(CallbackQueryHandler(callback_query.handle_callback_query))
		telegram_app.add_handler(CommandHandler("start", start.start_handle))
		telegram_app.add_handler(CommandHandler("help", help.help_handle))
		telegram_app.add_handler(CommandHandler("language", language.language_handle))
		telegram_app.add_handler(CommandHandler("settings", settings.settings_handle))
		telegram_app.add_handler(CommandHandler("credits", credits.credits_handle))
		telegram_app.add_handler(CommandHandler("payment", payment_handle))
		logger.info("All handlers registered successfully")
	except Exception as e:
		logger.error(f"Critical error in register_handlers: {str(e)}")
		raise
	finally:
		if 'db' in locals():
			db.__del__()  # Ensure database connection is closed
try:
	register_handlers()
	logger.info("All handlers registered successfully")
except Exception as e:
	logger.error(f"Error in register_handlers: {str(e)}")
	raise

def get_fields():
	config = Config()
	return [
		{"key": "telegram_token", "label": "Telegram Token", "value": config.telegram_token or "", "use_env": config._config.get("telegram_token_use_env", False)},
		{"key": "bot_username", "label": "Bot Username", "value": config.bot_username or "", "use_env": config._config.get("bot_username_use_env", False)},
		{"key": "webhook_url", "label": "Webhook URL", "value": config.webhook_url or "", "use_env": config._config.get("webhook_url_use_env", False)},
		{"key": "mysql_host", "label": "MySQL Host", "value": config.mysql_host or "", "use_env": config._config.get("mysql_host_use_env", False)},
		{"key": "mysql_user", "label": "MySQL User", "value": config.mysql_user or "", "use_env": config._config.get("mysql_user_use_env", False)},
		{"key": "mysql_password", "label": "MySQL Password", "value": config.mysql_password or "", "use_env": config._config.get("mysql_password_use_env", False)},
		{"key": "mysql_database", "label": "MySQL Database", "value": config.mysql_database or "", "use_env": config._config.get("mysql_database_use_env", False)},
		{"key": "github_username", "label": "GitHub Username", "value": config.github_username or "", "use_env": config._config.get("github_username_use_env", False)},
		{"key": "github_token", "label": "GitHub Token", "value": config.github_token or "", "use_env": config._config.get("github_token_use_env", False)},
		{"key": "github_repo", "label": "GitHub Repository", "value": config.github_repo or "", "use_env": config._config.get("github_repo_use_env", False)},
		{"key": "github_pages_url", "label": "GitHub Pages URL", "value": config.github_pages_url or "", "use_env": config._config.get("github_pages_url_use_env", False)},
		{"key": "payment_provider_token", "label": "Payment Provider Token", "value": config.payment_provider_token or "", "use_env": config._config.get("payment_provider_token_use_env", False)},
		{"key": "currency_exchange_token", "label": "Currency Exchange Token", "value": config.currency_exchange_token or "", "use_env": config._config.get("currency_exchange_token_use_env", False)},
		{"key": "huggingface_access_token", "label": "Hugging Face Access Token", "value": config.huggingface_access_token or "", "use_env": config._config.get("huggingface_access_token_use_env", False)},
		{"key": "flask_secret_key", "label": "Flask Secret Key", "value": config.flask_secret_key or "", "use_env": config._config.get("flask_secret_key_use_env", False)},
		{"key": "ai_settings.model_url", "label": "AI Model URL", "value": config.ai_model_url or "", "use_env": config._config.get("ai_settings", {}).get("model_url_use_env", False)},
		{"key": "ai_settings.access_token", "label": "AI Access Token", "value": config.ai_access_token or "", "use_env": config._config.get("ai_settings", {}).get("access_token_use_env", False)}
	]

# File Management Routes
PROJECT_ROOT = Path(__file__).parent.parent  # Root directory of the project

@flask_app.route("/<lang>")
@flask_app.route("/")
def index(lang="en"):
	if "username" not in session:
		return redirect(url_for("login", lang=lang))

	config = Config()
	i18n = I18n()
	if lang not in AVAILABLE_LANGUAGES:
		lang = "en"
	critical_fields = ['telegram_token', 'mysql_host', 'mysql_user', 'mysql_password', 'mysql_database', 'flask_secret_key']
	if not all(getattr(config, field) for field in critical_fields):
		return redirect(url_for("install", lang=lang))

	db = Database()

	# Check if user is admin and redirect to appropriate dashboard
	user_id = session.get("user_id")
	if user_id:
		query = "SELECT is_admin FROM users WHERE user_id = %s"
		db.cursor.execute(query, (user_id,))
		user = db.cursor.fetchone()
		if user and not user['is_admin']:
			return redirect(url_for("user_dashboard", lang=lang))

	# Handle Users tab pagination and search
	users_page = int(request.args.get("users_page", 1))
	users_search = request.args.get("users_search", "")
	users, users_total_pages = db.get_users_paginated(users_page, 50, users_search)
	for user in users:
		badges = []
		if user['is_admin']:
			badges.append('🛡️')
		if user['is_beta_tester']:
			badges.append('🧪')
		if user['is_teskilat']:
			badges.append('🇹🇷')
		if user['credits'] == 0:
			badges.append('⚠️')
		if user['is_blacklisted']:
			badges.append('🚫')
		user['badges'] = ' '.join(badges)

	# Handle Groups tab pagination and search
	groups_page = int(request.args.get("groups_page", 1))
	groups_search = request.args.get("groups_search", "")
	groups, groups_total_pages = db.get_groups_paginated(groups_page, 50, groups_search)

	# Validate and parse github_pages_url
	github_info = {
		"url": config.github_pages_url,
		"username": "",
		"repo": ""
	}

	if not config.github_pages_url:
		flash(i18n.t("CONFIGURE_GITHUB_URL", lang), "warning")
	else:
		try:
			parsed_url = urllib.parse.urlparse(config.github_pages_url)
			if not parsed_url.hostname or not parsed_url.hostname.endswith(".github.io"):
				flash(i18n.t("ERROR_GENERAL", lang, error="URL must be a GitHub Pages URL (e.g., username.github.io)"), "error")
			else:
				path_match = re.match(r"/?([^/]*\.github\.io)?/?([^/]*)/?", parsed_url.path)
				if path_match:
					username = parsed_url.hostname.split(".github.io")[0]
					repo = path_match.group(2) or username + ".github.io"
					github_info["username"] = username
					github_info["repo"] = repo
				else:
					flash(i18n.t("ERROR_GENERAL", lang, error="Invalid GitHub Pages URL format"), "error")
		except Exception as e:
			flash(i18n.t("ERROR_GENERAL", lang, error=str(e)), "error")

	# Get command usage statistics
	command_usage = db.get_command_usage()
	if command_usage:
		max_count = max(usage['count'] for usage in command_usage)
		for usage in command_usage:
			usage['percentage'] = (usage['count'] / max_count * 100) if max_count > 0 else 0

	# Get fields for config tab
	fields = get_fields()

	return render_template(
		"dashboard.html",
		lang=lang,
		i18n=i18n,
		config=config,
		fields=fields,
		users=users,
		users_total_pages=users_total_pages,
		current_page=users_page,
		groups=groups,
		groups_total_pages=groups_total_pages,
		command_usage=command_usage,
		github_info=github_info
	)

@flask_app.route("/<lang>/login", methods=["GET", "POST"])
@flask_app.route("/login", methods=["GET", "POST"])
def login(lang="en"):
	if lang not in AVAILABLE_LANGUAGES:
		lang = "en"

	i18n = I18n()

	if request.method == "POST":
		username = request.form.get("username")
		password = request.form.get("password")

		if not username or not password:
			flash(i18n.t("LOGIN_EMPTY_FIELDS", lang), "error")
			return render_template("login.html", lang=lang, i18n=i18n)

		db = Database()
		query = "SELECT * FROM users WHERE username = %s"
		db.cursor.execute(query, (username,))
		user = db.cursor.fetchone()

		if not user:
			flash(i18n.t("LOGIN_INVALID_CREDENTIALS", lang), "error")
			return render_template("login.html", lang=lang, i18n=i18n)

		if not user.get("password"):
			flash(i18n.t("LOGIN_NO_PASSWORD", lang), "error")
			return render_template("login.html", lang=lang, i18n=i18n)

		try:
			if user and bcrypt.checkpw(password.encode("utf-8"), user["password"].encode("utf-8")):
				session["username"] = username
				session["user_id"] = user["user_id"]

				# Redirect based on user role
				if user["is_admin"]:
					return redirect(url_for("index", lang=lang))
				else:
					return redirect(url_for("user_dashboard", lang=lang))
			else:
				flash(i18n.t("LOGIN_INVALID_CREDENTIALS", lang), "error")
		except Exception as e:
			flash(i18n.t("ERROR_GENERAL", lang, error=str(e)), "error")

	return render_template("login.html", lang=lang, i18n=i18n)

@flask_app.route("/<lang>/user-dashboard")
@flask_app.route("/user-dashboard")
def user_dashboard(lang="en"):
	if "username" not in session:
		return redirect(url_for("login", lang=lang))

	if lang not in AVAILABLE_LANGUAGES:
		lang = "en"

	i18n = I18n()
	db = Database()

	user_id = session.get("user_id")
	if not user_id:
		return redirect(url_for("login", lang=lang))

	# Get user information
	user = db.get_user_by_id(user_id)
	if not user:
		session.clear()
		return redirect(url_for("login", lang=lang))

	# Check if user is admin and redirect if necessary
	if user.get("is_admin"):
		return redirect(url_for("index", lang=lang))

	# Get user's orders
	orders = db.get_user_orders(user_id)
	orders_count = len(orders)

	# Get available products
	products = db.get_available_products(user_id=user_id)
	products_count = len(products)

	# Get user's payment history
	payments = db.get_user_payments(user_id)

	# Get user's addresses
	addresses = db.get_user_addresses(user_id)

	return render_template(
		"user-dashboard.html",
		lang=lang,
		i18n=i18n,
		user=user,
		orders=orders,
		orders_count=orders_count,
		products=products,
		products_count=products_count,
		payments=payments,
		addresses=addresses
	)

@flask_app.route("/<lang>/logout")
@flask_app.route("/logout")
def logout(lang="en"):
	session.clear()
	if lang not in AVAILABLE_LANGUAGES:
		lang = "en"
	i18n = I18n()
	flash(i18n.t("LOGOUT_SUCCESS", lang), "success")
	return redirect(url_for("login", lang=lang))

# Dosya İçeriği Görüntüleme
@flask_app.route("/<lang>/files/view", methods=["GET"])
def view_file(lang="en"):
	if "username" not in session:
		return jsonify({"error": "Unauthorized access"}), 401

	file_path = request.args.get("path")
	if not file_path or not is_safe_path(file_path):
		return jsonify({"error": "Invalid file path"}), 400

	try:
		full_path = PROJECT_ROOT / file_path
		if not full_path.is_file():
			return jsonify({"error": "Not a file"}), 400

		with open(full_path, "r", encoding="utf-8") as f:
			content = f.read()

		return jsonify({
			"content": content,
			"path": file_path,
			"name": full_path.name
		})
	except Exception as e:
		logger.error(f"Error reading file: {str(e)}")
		return jsonify({"error": f"Failed to read file: {str(e)}"}), 500

# Dosya Düzenleme
@flask_app.route("/<lang>/files/edit", methods=["POST"])
def edit_file(lang="en"):
	if "username" not in session:
		return jsonify({"error": "Unauthorized access"}), 401

	file_path = request.form.get("path")
	content = request.form.get("content")

	if not file_path or not is_safe_path(file_path) or content is None:
		return jsonify({"error": "Invalid parameters"}), 400

	try:
		full_path = PROJECT_ROOT / file_path
		if not full_path.is_file():
			return jsonify({"error": "Not a file"}), 400

		with open(full_path, "w", encoding="utf-8") as f:
			f.write(content)

		return jsonify({"success": True, "message": "File saved successfully"})
	except Exception as e:
		logger.error(f"Error saving file: {str(e)}")
		return jsonify({"error": f"Failed to save file: {str(e)}"}), 500

# Yeni Dosya Oluşturma
@flask_app.route("/<lang>/files/create", methods=["POST"])
def create_file(lang="en"):
	if "username" not in session:
		return jsonify({"error": "Unauthorized access"}), 401
	if lang not in AVAILABLE_LANGUAGES:
		lang = "en"
	data = request.get_json()
	file_path = data.get("path")
	if not file_path or not is_safe_path(file_path):
		return jsonify({"error": "Invalid or unsafe file path"}), 400
	try:
		file = PROJECT_ROOT / file_path
		if file.exists():
			return jsonify({"error": "File already exists"}), 400
		file.parent.mkdir(parents=True, exist_ok=True)
		with open(file, "w", encoding="utf-8") as f:
			f.write("")
		logger.info(f"File created successfully: {file_path}")
		return jsonify({"message": "File created successfully"})
	except Exception as e:
		logger.error(f"Error creating file {file_path}: {str(e)}")
		return jsonify({"error": f"Failed to create file: {str(e)}"}), 500

# Dosya Silme
@flask_app.route("/<lang>/files/delete", methods=["POST"])
def delete_file(lang="en"):
	if "username" not in session:
		return jsonify({"error": "Unauthorized access"}), 401
	if lang not in AVAILABLE_LANGUAGES:
		lang = "en"
	data = request.get_json()
	file_path = data.get("path")
	if not file_path or not is_safe_path(file_path):
		return jsonify({"error": "Invalid or unsafe file path"}), 400
	try:
		path = PROJECT_ROOT / file_path
		if not path.exists():
			return jsonify({"error": "File or directory does not exist"}), 404
		if path.is_file():
			path.unlink()
			logger.info(f"File deleted successfully: {file_path}")
			return jsonify({"message": "File deleted successfully"})
		else:
			path.rmdir()
			logger.info(f"Directory deleted successfully: {file_path}")
			return jsonify({"message": "Directory deleted successfully"})
	except Exception as e:
		logger.error(f"Error deleting {file_path}: {str(e)}")
		return jsonify({"error": f"Failed to delete: {str(e)}"}), 500

# Dizin Oluşturma
@flask_app.route("/<lang>/files/create_directory", methods=["POST"])
def create_directory(lang="en"):
	if "username" not in session:
		return jsonify({"error": "Unauthorized access"}), 401

	dir_path = request.form.get("path")

	if not dir_path or not is_safe_path(dir_path):
		return jsonify({"error": "Invalid directory path"}), 400

	try:
		full_path = PROJECT_ROOT / dir_path
		if full_path.exists():
			return jsonify({"error": "Directory already exists"}), 400

		full_path.mkdir(parents=True, exist_ok=True)

		return jsonify({
			"success": True,
			"message": "Directory created successfully",
			"path": dir_path,
			"name": full_path.name
		})
	except Exception as e:
		logger.error(f"Error creating directory: {str(e)}")
		return jsonify({"error": f"Failed to create directory: {str(e)}"}), 500

# Düzeltilmiş Install Fonksiyonu
@flask_app.route("/<lang>/install", methods=["GET", "POST"])
@flask_app.route("/install", methods=["GET", "POST"])
def install(lang="en"):
	if lang not in AVAILABLE_LANGUAGES:
		lang = "en"

	i18n = I18n()
	config = Config()

	if request.method == "POST":
		# Update configuration
		telegram_token = config.telegram_token or request.form.get("telegram_token")
		mysql_host = config.mysql_host or request.form.get("mysql_host")
		mysql_user = config.mysql_user or request.form.get("mysql_user")
		mysql_port = config.mysql_port or request.form.get("mysql_port", "3306")  # Default port
		mysql_password = config.mysql_password or request.form.get("mysql_password")
		mysql_database = config.mysql_database or request.form.get("mysql_database")
		bot_username = request.form.get("bot_username")
		webhook_url = request.form.get("webhook_url")
		github_username = request.form.get("github_username")
		github_token = request.form.get("github_token")
		github_repo = request.form.get("github_repo")
		github_pages_url = request.form.get("github_pages_url")
		payment_provider_token = request.form.get("payment_provider_token")
		currency_exchange_token = request.form.get("currency_exchange_token")
		huggingface_access_token = request.form.get("huggingface_access_token")
		admin_username = request.form.get("admin_username")
		admin_password = request.form.get("admin_password")

		# Validate required fields
		if not all([telegram_token, mysql_host, mysql_user, mysql_database, admin_username, admin_password]):
			flash(i18n.t("INSTALL_MISSING_FIELDS", lang), "error")
			return render_template("install.html", lang=lang, i18n=i18n)

		# Update config.yaml
		config_data = {
			"telegram_token": telegram_token,
			"bot_username": bot_username,
			"webhook_url": webhook_url,
			"mysql_host": mysql_host,
			"mysql_user": mysql_user,
			"mysql_port": mysql_port,
			"mysql_password": mysql_password,
			"mysql_database": mysql_database,
			"github_username": github_username,
			"github_token": github_token,
			"github_repo": github_repo,
			"github_pages_url": github_pages_url,
			"payment_provider_token": payment_provider_token,
			"currency_exchange_token": currency_exchange_token,
			"huggingface_access_token": huggingface_access_token,
			"flask_secret_key": os.urandom(24).hex()
		}

		try:
			config_path = os.path.join(os.path.dirname(__file__), "config.yaml")
			with open(config_path, "w") as f:
				yaml.dump(config_data, f)

			# Reload configuration
			config = Config()

			# Initialize database
			db = Database()

			# Create admin user
			success = seed_admin(db, admin_username, admin_password)
			if success:
				flash(i18n.t("INSTALL_SUCCESS", lang), "success")
				return redirect(url_for("login", lang=lang))
			else:
				flash(i18n.t("INSTALL_ADMIN_ERROR", lang), "error")
		except Exception as e:
			flash(i18n.t("ERROR_GENERAL", lang, error=str(e)), "error")

	return render_template("install.html", lang=lang, i18n=i18n)

# Tamamlanmamış file_tree fonksiyonunun düzeltilmiş versiyonu
@flask_app.route("/<lang>/file_tree", methods=["GET"])
def file_tree(lang="en"):
	if "username" not in session:
		return jsonify({"error": "Unauthorized access"}), 401

	try:
		def build_file_tree(path, prefix=""):
			tree = []
			for item in sorted(path.iterdir()):
				if item.name.startswith(".") or item.name == "__pycache__":
					continue
				relative_path = str(item.relative_to(PROJECT_ROOT))
				if item.is_dir():
					tree.append({
						"name": item.name,
						"path": relative_path,
						"type": "directory",
						"children": build_file_tree(item, prefix + "  ")
					})
				else:
					tree.append({
						"name": item.name,
						"path": relative_path,
						"type": "file"
					})
			return tree

		file_tree = build_file_tree(PROJECT_ROOT)
		return jsonify({"files": file_tree})
	except Exception as e:
		logger.error(f"Error building file tree: {str(e)}")
		return jsonify({"error": f"Failed to build file tree: {str(e)}"}), 500

@flask_app.route("/<lang>/save_config", methods=["POST"])
def save_config_route(lang="en"):
	if "username" not in session:
		return redirect(url_for("login", lang=lang))

	if lang not in AVAILABLE_LANGUAGES:
		lang = "en"

	i18n = I18n()

	try:
		config_data = {}
		ai_settings = {}

		for field in get_fields():
			key = field["key"]
			if key.startswith("ai_settings."):
				ai_key = key.split(".", 1)[1]
				value = request.form.get(key, "")
				use_env = request.form.get(f"{key}_use_env") == "on"
				ai_settings[ai_key] = value
				ai_settings[f"{ai_key}_use_env"] = use_env
			else:
				value = request.form.get(key, "")
				use_env = request.form.get(f"{key}_use_env") == "on"
				config_data[key] = value
				config_data[f"{key}_use_env"] = use_env

		config_data["ai_settings"] = ai_settings

		config_path = os.path.join(os.path.dirname(__file__), "config.yaml")
		with open(config_path, "w") as f:
			yaml.dump(config_data, f)

		flash(i18n.t("CONFIG_SAVED", lang), "success")
	except Exception as e:
		flash(i18n.t("ERROR_GENERAL", lang, error=str(e)), "error")

	return redirect(url_for("index", lang=lang))

@flask_app.route("/<lang>/add_model", methods=["POST"])
def add_model(lang="en"):
	if "username" not in session:
		return redirect(url_for("login", lang=lang))

	if lang not in AVAILABLE_LANGUAGES:
		lang = "en"

	i18n = I18n()

	try:
		model_name = request.form.get("model_name")
		model_url = request.form.get("model_url")
		access_token_env = request.form.get("access_token_env")

		if not all([model_name, model_url, access_token_env]):
			flash(i18n.t("MODEL_MISSING_FIELDS", lang), "error")
			return redirect(url_for("index", lang=lang))

		config = Config()

		if not hasattr(config, "_config"):
			config._config = {}

		if "models" not in config._config:
			config._config["models"] = {}

		config._config["models"][model_name] = {
			"name": model_name,
			"url": model_url,
			"access_token_env": access_token_env
		}

		config_path = os.path.join(os.path.dirname(__file__), "config.yaml")
		with open(config_path, "w") as f:
			yaml.dump(config._config, f)

		flash(i18n.t("MODEL_ADDED", lang), "success")
	except Exception as e:
		flash(i18n.t("ERROR_GENERAL", lang, error=str(e)), "error")

	return redirect(url_for("index", lang=lang))

@flask_app.route("/<lang>/delete_model", methods=["POST"])
def delete_model(lang="en"):
	if "username" not in session:
		return redirect(url_for("login", lang=lang))

	if lang not in AVAILABLE_LANGUAGES:
		lang = "en"

	i18n = I18n()

	try:
		model_name = request.form.get("model_name")

		if not model_name:
			flash(i18n.t("MODEL_NAME_REQUIRED", lang), "error")
			return redirect(url_for("index", lang=lang))

		config = Config()

		if not hasattr(config, "_config") or "models" not in config._config:
			flash(i18n.t("NO_MODELS_FOUND", lang), "error")
			return redirect(url_for("index", lang=lang))

		if model_name in config._config["models"]:
			del config._config["models"][model_name]

			config_path = os.path.join(os.path.dirname(__file__), "config.yaml")
			with open(config_path, "w") as f:
				yaml.dump(config._config, f)

			flash(i18n.t("MODEL_DELETED", lang), "success")
		else:
			flash(i18n.t("MODEL_NOT_FOUND", lang), "error")
	except Exception as e:
		flash(i18n.t("ERROR_GENERAL", lang, error=str(e)), "error")

	return redirect(url_for("index", lang=lang))

@flask_app.route("/<lang>/users")
def get_users(lang="en"):
	if "username" not in session:
		return redirect(url_for("login", lang=lang))

	if lang not in AVAILABLE_LANGUAGES:
		lang = "en"

	i18n = I18n()
	db = Database()

	page = int(request.args.get("page", 1))
	search = request.args.get("search", "")

	users, total_pages = db.get_users_paginated(page, 50, search)

	for user in users:
		badges = []
		if user['is_admin']:
			badges.append('🛡️')
		if user['is_beta_tester']:
			badges.append('🧪')
		if user['is_teskilat']:
			badges.append('🇹🇷')
		if user['credits'] == 0:
			badges.append('⚠️')
		if user['is_blacklisted']:
			badges.append('🚫')
		user['badges'] = ' '.join(badges)

	return render_template(
		"users_partial.html",
		lang=lang,
		i18n=i18n,
		users=users,
		users_total_pages=total_pages,
		current_page=page
	)

@flask_app.route("/<lang>/groups")
def get_groups(lang="en"):
	if "username" not in session:
		return redirect(url_for("login", lang=lang))

	if lang not in AVAILABLE_LANGUAGES:
		lang = "en"

	i18n = I18n()
	db = Database()

	page = int(request.args.get("page", 1))
	search = request.args.get("search", "")

	groups, total_pages = db.get_groups_paginated(page, 50, search)

	return render_template(
		"groups_partial.html",
		lang=lang,
		i18n=i18n,
		groups=groups,
		groups_total_pages=total_pages,
		current_page=page
	)

@flask_app.route("/<lang>/promote_credits", methods=["POST"])
def promote_credits(lang="en"):
	if "username" not in session:
		return redirect(url_for("login", lang=lang))

	if lang not in AVAILABLE_LANGUAGES:
		lang = "en"

	i18n = I18n()
	db = Database()

	user_id = request.form.get("user_id")
	credits = request.form.get("credits")

	if not user_id or not credits:
		flash(i18n.t("MISSING_FIELDS", lang), "error")
		return redirect(url_for("index", lang=lang))

	try:
		user_id = int(user_id)
		credits = int(credits)

		if credits <= 0:
			flash(i18n.t("INVALID_CREDITS", lang), "error")
			return redirect(url_for("index", lang=lang))

		success = db.add_credits(user_id, credits)

		if success:
			flash(i18n.t("CREDITS_ADDED", lang), "success")
		else:
			flash(i18n.t("USER_NOT_FOUND", lang), "error")
	except ValueError:
		flash(i18n.t("INVALID_INPUT", lang), "error")
	except Exception as e:
		flash(i18n.t("ERROR_GENERAL", lang, error=str(e)), "error")

	return redirect(url_for("index", lang=lang))

@flask_app.route("/<lang>/toggle_blacklist", methods=["POST"])
def toggle_blacklist(lang="en"):
	if "username" not in session:
		return redirect(url_for("login", lang=lang))

	if lang not in AVAILABLE_LANGUAGES:
		lang = "en"

	i18n = I18n()
	db = Database()

	user_id = request.form.get("user_id")

	if not user_id:
		flash(i18n.t("MISSING_FIELDS", lang), "error")
		return redirect(url_for("index", lang=lang))

	try:
		user_id = int(user_id)

		success, is_blacklisted = db.toggle_blacklist(user_id)

		if success:
			if is_blacklisted:
				flash(i18n.t("USER_BLACKLISTED", lang), "success")
			else:
				flash(i18n.t("USER_UNBLACKLISTED", lang), "success")
		else:
			flash(i18n.t("USER_NOT_FOUND", lang), "error")
	except ValueError:
		flash(i18n.t("INVALID_INPUT", lang), "error")
	except Exception as e:
		flash(i18n.t("ERROR_GENERAL", lang, error=str(e)), "error")

	return redirect(url_for("index", lang=lang))

@flask_app.route("/<lang>/toggle_beta_tester", methods=["POST"])
def toggle_beta_tester(lang="en"):
	if "username" not in session:
		return redirect(url_for("login", lang=lang))

	if lang not in AVAILABLE_LANGUAGES:
		lang = "en"

	i18n = I18n()
	db = Database()

	user_id = request.form.get("user_id")

	if not user_id:
		flash(i18n.t("MISSING_FIELDS", lang), "error")
		return redirect(url_for("index", lang=lang))

	try:
		user_id = int(user_id)

		success, is_beta_tester = db.toggle_beta_tester(user_id)

		if success:
			if is_beta_tester:
				flash(i18n.t("BETA_ACCESS_GRANTED", lang), "success")
			else:
				flash(i18n.t("BETA_ACCESS_REVOKED", lang), "success")
		else:
			flash(i18n.t("USER_NOT_FOUND", lang), "error")
	except ValueError:
		flash(i18n.t("INVALID_INPUT", lang), "error")
	except Exception as e:
		flash(i18n.t("ERROR_GENERAL", lang, error=str(e)), "error")

	return redirect(url_for("index", lang=lang))

@flask_app.route("/<lang>/toggle_group_blacklist", methods=["POST"])
def toggle_group_blacklist(lang="en"):
	if "username" not in session:
		return redirect(url_for("login", lang=lang))

	if lang not in AVAILABLE_LANGUAGES:
		lang = "en"

	i18n = I18n()
	db = Database()

	group_id = request.form.get("group_id")

	if not group_id:
		flash(i18n.t("MISSING_FIELDS", lang), "error")
		return redirect(url_for("index", lang=lang))

	try:
		group_id = int(group_id)

		success, is_blacklisted = db.toggle_group_blacklist(group_id)

		if success:
			if is_blacklisted:
				flash(i18n.t("GROUP_BLACKLISTED", lang), "success")
			else:
				flash(i18n.t("GROUP_UNBLACKLISTED", lang), "success")
		else:
			flash(i18n.t("GROUP_NOT_FOUND", lang), "error")
	except ValueError:
		flash(i18n.t("INVALID_INPUT", lang), "error")
	except Exception as e:
		flash(i18n.t("ERROR_GENERAL", lang, error=str(e)), "error")

	return redirect(url_for("index", lang=lang))

@flask_app.route("/<lang>/github_traffic", methods=["GET"])
def github_traffic(lang="en"):
	if "username" not in session:
		return jsonify({"error": "Unauthorized"})

	if lang not in AVAILABLE_LANGUAGES:
		lang = "en"

	config = Config()

	if not config.github_token or not config.github_username or not config.github_repo:
		return jsonify({"error": "GitHub configuration incomplete"})

	time_range = request.args.get("time_range", "30d")
	per_page = int(request.args.get("per_page", 25))
	page = int(request.args.get("page", 1))

	days = {
		"1d": 1,
		"7d": 7,
		"30d": 30,
		"90d": 90,
		"180d": 180,
		"365d": 365,
		"all": 0
	}.get(time_range, 30)

	try:
		headers = {
			"Authorization": f"token {config.github_token}",
			"Accept": "application/vnd.github.v3+json"
		}

		# Get repository info
		repo_url = f"https://api.github.com/repos/{config.github_username}/{config.github_repo}"
		repo_response = requests.get(repo_url, headers=headers)
		repo_data = repo_response.json()

		# Get traffic data
		traffic_url = f"{repo_url}/traffic/views"
		traffic_response = requests.get(traffic_url, headers=headers)
		traffic_data = traffic_response.json()

		# Get clones data
		clones_url = f"{repo_url}/traffic/clones"
		clones_response = requests.get(clones_url, headers=headers)
		clones_data = clones_response.json()

		# Get referrers data
		referrers_url = f"{repo_url}/traffic/popular/referrers"
		referrers_response = requests.get(referrers_url, headers=headers)
		referrers_data = referrers_response.json()

		# Get popular content
		content_url = f"{repo_url}/traffic/popular/paths"
		content_response = requests.get(content_url, headers=headers)
		content_data = content_response.json()

		# Get commits
		commits_url = f"{repo_url}/commits"
		commits_params = {"per_page": per_page, "page": page}
		commits_response = requests.get(commits_url, headers=headers, params=commits_params)
		commits_data = commits_response.json()

		# Get total commits count for pagination
		commits_count_response = requests.get(f"{repo_url}/contributors", headers=headers)
		commits_count_data = commits_count_response.json()
		total_commits = sum(contributor.get("contributions", 0) for contributor in commits_count_data if isinstance(contributor, dict))

		return jsonify({
			"repo": repo_data,
			"traffic": traffic_data,
			"clones": clones_data,
			"referrers": referrers_data,
			"popular_content": content_data,
			"commits": commits_data,
			"total_commits": total_commits,
			"total_pages": (total_commits + per_page - 1) // per_page
		})
	except Exception as e:
		return jsonify({"error": str(e)})

def is_safe_path(path):
	"""Ensure the path is within the project root to prevent directory traversal."""
	try:
		resolved_path = (PROJECT_ROOT / path).resolve()
		return PROJECT_ROOT in resolved_path.parents or resolved_path == PROJECT_ROOT
	except Exception:
		return False

@flask_app.route("/<lang>/files/list", methods=["GET"])
def list_files(lang="en"):
	if "username" not in session:
		return jsonify({"error": "Unauthorized access"}), 401
	if lang not in AVAILABLE_LANGUAGES:
		lang = "en"
	try:
		def build_file_tree(path, prefix=""):
			tree = []
			for item in sorted(path.iterdir()):
				if item.name.startswith(".") or item.name == "__pycache__":
					continue
				relative_path = str(item.relative_to(PROJECT_ROOT))
				if item.is_dir():
					tree.append({
						"name": item.name,
						"path": relative_path,
						"type": "directory",
						"children": build_file_tree(item, prefix + "  ")
					})
				else:
					tree.append({
						"name": item.name,
						"path": relative_path,
						"type": "file"
					})
			return tree
		file_tree = build_file_tree(PROJECT_ROOT)
		return jsonify({"files": file_tree})
	except Exception as e:
		logger.error(f"Error listing files: {str(e)}")
		return jsonify({"error": f"Failed to list files: {str(e)}"}), 500

@flask_app.route("/<lang>/files/reload", methods=["POST"])
def reload_file(lang="en"):
	"""Reload a file to apply changes without restarting the server."""
	if "username" not in session:
		return jsonify({"error": "Unauthorized access"}), 401
	if lang not in AVAILABLE_LANGUAGES:
		lang = "en"
	data = request.get_json()
	file_path = data.get("path")
	if not file_path or not is_safe_path(file_path):
		return jsonify({"error": "Invalid or unsafe file path"}), 400
	try:
		path = PROJECT_ROOT / file_path
		# Prevent reloading sensitive files
		restricted_files = ["admin_panel.py", "config.py", ".env"]
		if path.name in restricted_files:
			return jsonify({"error": "Reloading this file is restricted"}), 403
		if not path.exists() or not path.is_file():
			return jsonify({"error": "File does not exist or is not a file"}), 404

		# Initialize I18n for translations
		i18n = I18n()

		# Handle Python files
		if path.suffix.lower() == ".py":
			module_name = str(path.relative_to(PROJECT_ROOT).with_suffix("")).replace(os.sep, ".")
			if module_name.startswith("."):
				return jsonify({"error": "Invalid module path"}), 400
			try:
				if module_name in sys.modules:
					module = sys.modules[module_name]
					importlib.reload(module)
				else:
					module = importlib.import_module(module_name)
				# Reinitialize Telegram handlers if the module affects bot logic
				if module_name.startswith("Bot.") or module_name.startswith("Commands."):
					register_handlers()
				logger.info(f"Reloaded Python module: {module_name}")
				return jsonify({"message": i18n.t("FILE_RELOADED", lang)})
			except ImportError as e:
				logger.error(f"Error reloading module {module_name}: {str(e)}")
				return jsonify({"error": f"Failed to reload module: {str(e)}"}), 500

		# Handle HTML templates
		elif path.suffix.lower() == ".html":
			if flask_app.jinja_env.cache:
				flask_app.jinja_env.cache.clear()
			try:
				# Get absolute path to templates folder
				templates_path = Path(flask_app.template_folder).resolve()
				# Get absolute path to the file
				file_abs_path = path.resolve()

				# Check if file is within templates folder
				if templates_path in file_abs_path.parents or file_abs_path.parent == templates_path:
					# Get relative path from templates folder
					template_name = str(file_abs_path.relative_to(templates_path))
					flask_app.jinja_env.get_template(template_name)  # Trigger reload
					logger.info(f"Reloaded template: {file_path}")
					return jsonify({"message": i18n.t("TEMPLATE_RELOADED", lang)})
				else:
					return jsonify({"error": "Template not in template folder"}), 400
			except Exception as e:
				logger.error(f"Error reloading template {file_path}: {str(e)}")
				return jsonify({"error": f"Failed to reload template: {str(e)}"}), 500

		# Handle Assets templates (Yes I prefer you to create javascripts here)
		elif path.suffix.lower() in [".css", ".webmanifest", ".txt", ".js"]:
			if flask_app.jinja_env.cache:
				flask_app.jinja_env.cache.clear()
			try:
				# Get absolute path to assets folder
				assets_path = Path(flask_app.static_folder).resolve()
				# Get absolute path to the file
				file_abs_path = path.resolve()

				# Check if file is within templates folder
				if assets_path in file_abs_path.parents or file_abs_path.parent == assets_path:
					# Get relative path from templates folder
					logger.info(f"Reloaded template: {file_path}")
					return jsonify({"message": i18n.t("TEMPLATE_RELOADED", lang)})
				else:
					return jsonify({"error": "Template not in assets folder"}), 400
			except Exception as e:
				logger.error(f"Error reloading template {file_path}: {str(e)}")
				return jsonify({"error": f"Failed to reload template: {str(e)}"}), 500

		# Handle JSON locale files
		elif path.suffix.lower() == ".json" and str(path).startswith(str(PROJECT_ROOT / "Locales")):
			try:
				# Clear I18n translations cache and reload
				i18n.translations.clear()
				i18n._load_translations(lang)
				logger.info(f"Reloaded locale file: {file_path}")
				return jsonify({"message": i18n.t("LOCALE_RELOADED", lang)})
			except Exception as e:
				logger.error(f"Error reloading locale {file_path}: {str(e)}")
				return jsonify({"error": f"Failed to reload locale: {str(e)}"}), 500

		# Handle other file types
		else:
			logger.info(f"Reload requested for unsupported file type: {file_path}")
			return jsonify({"message": i18n.t("FILE_RELOAD_UNSUPPORTED", lang)})

	except Exception as e:
		logger.error(f"Error reloading file {file_path}: {str(e)}")
		return jsonify({"error": f"Failed to reload file: {str(e)}"}), 500

@flask_app.route("/<lang>/files/read", methods=["POST"])
def read_file(lang="en"):
	if "username" not in session:
		return jsonify({"error": "Unauthorized access"}), 401
	if lang not in AVAILABLE_LANGUAGES:
		lang = "en"
	data = request.get_json()
	file_path = data.get("path")
	if not file_path or not is_safe_path(file_path):
		return jsonify({"error": "Invalid or unsafe file path"}), 400
	try:
		file = PROJECT_ROOT / file_path
		if not file.exists() or not file.is_file():
			return jsonify({"error": "File does not exist or is not a file"}), 404
		with open(file, "r", encoding="utf-8") as f:
			content = f.read()
		extension = file.suffix.lower()
		mime_types = {
			".py": "python",
			".html": "htmlmixed",
			".js": "javascript",
			".json": "javascript",
			".css": "css",
			".yml": "yaml",
			".md": "markdown",
			".sql": "sql",
			".txt": "text"
		}
		mode = mime_types.get(extension, "text")
		return jsonify({"content": content, "mode": mode})
	except Exception as e:
		logger.error(f"Error reading file {file_path}: {str(e)}")
		return jsonify({"error": f"Failed to read file: {str(e)}"}), 500

@flask_app.route("/<lang>/file_content", methods=["GET"])
def file_content(lang="en"):
	if "username" not in session:
		return jsonify({"error": "Unauthorized"})

	if lang not in AVAILABLE_LANGUAGES:
		lang = "en"

	file_path = request.args.get("path")

	if not file_path:
		return jsonify({"error": "No file path provided"})

	try:
		root_dir = os.path.dirname(os.path.dirname(__file__))
		full_path = os.path.join(root_dir, file_path)

		# Ensure the path is within the project directory
		if not os.path.abspath(full_path).startswith(os.path.abspath(root_dir)):
			return jsonify({"error": "Invalid file path"})

		if not os.path.isfile(full_path):
			return jsonify({"error": "File not found"})

		with open(full_path, "r", encoding="utf-8") as f:
			content = f.read()

		return jsonify({"content": content})
	except Exception as e:
		return jsonify({"error": str(e)})

@flask_app.route("/<lang>/files/save", methods=["POST"])
def save_file(lang="en"):
	if "username" not in session:
		return jsonify({"error": "Unauthorized access"}), 401
	if lang not in AVAILABLE_LANGUAGES:
		lang = "en"
	data = request.get_json()
	file_path = data.get("path")
	content = data.get("content")
	if not file_path or not is_safe_path(file_path):
		return jsonify({"error": "Invalid or unsafe file path"}), 400

	full_path = os.path.join(PROJECT_ROOT, file_path)

	try:
		os.makedirs(os.path.dirname(full_path), exist_ok=True)
		with open(full_path, "w", encoding="utf-8") as f:
			f.write(content)
		logger.info(f"File saved successfully: {file_path}")
		return jsonify({"message": "File saved successfully"})
	except PermissionError:
		logger.error(f"Permission denied when writing file {file_path}")
		return jsonify({"error": "Permission denied when writing file"}), 403
	except Exception as e:
		logger.error(f"Failed to save file {file_path}: {str(e)}")
		return jsonify({"error": f"Failed to save file: {str(e)}"}), 500

@flask_app.route("/bot<path:path>", methods=["POST"])
async def telegram_webhook(path):
	if not path.startswith(config.telegram_token):
		return "Invalid token", 403

	try:
		update_data = request.get_json()
		update = Update.de_json(update_data, telegram_app.bot)
		await telegram_app.process_update(update)
		return "OK", 200
	except Exception as e:
		logger.error(f"Error processing update: {str(e)}")
		return "Error", 500

# User dashboard routes for payment and order management
@flask_app.route("/<lang>/create_payment", methods=["POST"])
def create_payment(lang="en"):
	if "username" not in session:
		return redirect(url_for("login", lang=lang))

	if lang not in AVAILABLE_LANGUAGES:
		lang = "en"

	i18n = I18n()
	db = Database()

	user_id = session.get("user_id")
	if not user_id:
		return redirect(url_for("login", lang=lang))

	amount = request.form.get("amount")
	description = request.form.get("description", "")

	try:
		amount = float(amount)
		if amount <= 0:
			flash(i18n.t("INVALID_AMOUNT", lang), "error")
			return redirect(url_for("user_dashboard", lang=lang))

		payment_details = db.create_papara_payment(user_id, amount, description)

		if payment_details:
			flash(i18n.t("PAYMENT_CREATED", lang), "success")
		else:
			flash(i18n.t("PAYMENT_ERROR", lang), "error")
	except ValueError:
		flash(i18n.t("INVALID_AMOUNT", lang), "error")
	except Exception as e:
		flash(i18n.t("ERROR_GENERAL", lang, error=str(e)), "error")

	return redirect(url_for("user_dashboard", lang=lang))

@flask_app.route("/<lang>/view_payment/<int:payment_id>")
def view_payment(lang="en", payment_id=None):
	if "username" not in session:
		return redirect(url_for("login", lang=lang))

	if lang not in AVAILABLE_LANGUAGES:
		lang = "en"

	i18n = I18n()
	db = Database()

	user_id = session.get("user_id")
	if not user_id:
		return redirect(url_for("login", lang=lang))

	payment = db.get_payment_by_id(user_id, payment_id)

	if not payment:
		flash(i18n.t("PAYMENT_NOT_FOUND", lang), "error")
		return redirect(url_for("user_dashboard", lang=lang))

	return render_template(
		"payment_details.html",
		lang=lang,
		i18n=i18n,
		payment=payment
	)

@flask_app.route("/<lang>/check_payment/<int:payment_id>")
def check_payment(lang="en", payment_id=None):
	if "username" not in session:
		return redirect(url_for("login", lang=lang))

	if lang not in AVAILABLE_LANGUAGES:
		lang = "en"

	i18n = I18n()
	db = Database()

	user_id = session.get("user_id")
	if not user_id:
		return redirect(url_for("login", lang=lang))

	payment = db.get_payment_by_id(user_id, payment_id)

	if not payment:
		flash(i18n.t("PAYMENT_NOT_FOUND", lang), "error")
		return redirect(url_for("user_dashboard", lang=lang))

	if payment["status"] == "completed":
		flash(i18n.t("PAYMENT_ALREADY_COMPLETED", lang), "info")
		return redirect(url_for("user_dashboard", lang=lang))

	# Verify payment status
	if db.verify_papara_payment(payment["reference"]):
		flash(i18n.t("PAYMENT_VERIFIED", lang), "success")
	else:
		flash(i18n.t("PAYMENT_PENDING", lang), "info")

	return redirect(url_for("user_dashboard", lang=lang))

@flask_app.route("/<lang>/view_order/<int:order_id>")
def view_order(lang="en", order_id=None):
	if "username" not in session:
		return redirect(url_for("login", lang=lang))

	if lang not in AVAILABLE_LANGUAGES:
		lang = "en"

	i18n = I18n()
	db = Database()

	user_id = session.get("user_id")
	if not user_id:
		return redirect(url_for("login", lang=lang))

	order = db.get_order_by_id(user_id, order_id)

	if not order:
		flash(i18n.t("ORDER_NOT_FOUND", lang), "error")
		return redirect(url_for("user_dashboard", lang=lang))

	return render_template(
		"order_details.html",
		lang=lang,
		i18n=i18n,
		order=order
	)

@flask_app.route("/<lang>/pay_order/<int:order_id>")
def pay_order(lang="en", order_id=None):
	if "username" not in session:
		return redirect(url_for("login", lang=lang))

	if lang not in AVAILABLE_LANGUAGES:
		lang = "en"

	i18n = I18n()
	db = Database()

	user_id = session.get("user_id")
	if not user_id:
		return redirect(url_for("login", lang=lang))

	order = db.get_order_by_id(user_id, order_id)

	if not order:
		flash(i18n.t("ORDER_NOT_FOUND", lang), "error")
		return redirect(url_for("user_dashboard", lang=lang))

	if order["status"] != "pending_payment":
		flash(i18n.t("ORDER_NOT_PENDING_PAYMENT", lang), "error")
		return redirect(url_for("user_dashboard", lang=lang))

	# Check if user has enough credits
	user = db.get_user_by_id(user_id)
	if user["credits"] < order["total_price"]:
		flash(i18n.t("INSUFFICIENT_CREDITS", lang), "error")
		return redirect(url_for("user_dashboard", lang=lang))

	# Process payment
	if db.process_order_payment(user_id, order_id):
		flash(i18n.t("ORDER_PAID", lang), "success")
	else:
		flash(i18n.t("PAYMENT_ERROR", lang), "error")

	return redirect(url_for("user_dashboard", lang=lang))

@flask_app.route("/<lang>/cancel_order/<int:order_id>")
def cancel_order(lang="en", order_id=None):
	if "username" not in session:
		return redirect(url_for("login", lang=lang))

	if lang not in AVAILABLE_LANGUAGES:
		lang = "en"

	i18n = I18n()
	db = Database()

	user_id = session.get("user_id")
	if not user_id:
		return redirect(url_for("login", lang=lang))

	order = db.get_order_by_id(user_id, order_id)

	if not order:
		flash(i18n.t("ORDER_NOT_FOUND", lang), "error")
		return redirect(url_for("user_dashboard", lang=lang))

	if order["status"] not in ["pending", "pending_payment"]:
		flash(i18n.t("ORDER_CANNOT_CANCEL", lang), "error")
		return redirect(url_for("user_dashboard", lang=lang))

	# Cancel order
	if db.cancel_user_order(user_id, order_id):
		flash(i18n.t("ORDER_CANCELLED", lang), "success")
	else:
		flash(i18n.t("CANCEL_ERROR", lang), "error")

	return redirect(url_for("user_dashboard", lang=lang))

@flask_app.route("/<lang>/update_profile", methods=["POST"])
def update_profile(lang="en"):
	if "username" not in session:
		return redirect(url_for("login", lang=lang))

	if lang not in AVAILABLE_LANGUAGES:
		lang = "en"

	i18n = I18n()
	db = Database()

	user_id = session.get("user_id")
	if not user_id:
		return redirect(url_for("login", lang=lang))

	email = request.form.get("email", "")
	papara_email = request.form.get("papara_email", "")
	new_password = request.form.get("new_password", "")
	confirm_password = request.form.get("confirm_password", "")

	# Validate password if provided
	if new_password:
		if new_password != confirm_password:
			flash(i18n.t("PASSWORDS_DONT_MATCH", lang), "error")
			return redirect(url_for("user_dashboard", lang=lang))

		if len(new_password) < 8:
			flash(i18n.t("PASSWORD_TOO_SHORT", lang), "error")
			return redirect(url_for("user_dashboard", lang=lang))

	# Update profile
	success = db.update_user_profile(user_id, email, papara_email, new_password)

	if success:
		flash(i18n.t("PROFILE_UPDATED", lang), "success")
	else:
		flash(i18n.t("UPDATE_ERROR", lang), "error")

	return redirect(url_for("user_dashboard", lang=lang))

@flask_app.route("/<lang>/manage_addresses")
def manage_addresses(lang="en"):
	if "username" not in session:
		return redirect(url_for("login", lang=lang))

	if lang not in AVAILABLE_LANGUAGES:
		lang = "en"

	i18n = I18n()
	db = Database()

	user_id = session.get("user_id")
	if not user_id:
		return redirect(url_for("login", lang=lang))

	addresses = db.get_user_addresses(user_id)

	return render_template(
		"manage_addresses.html",
		lang=lang,
		i18n=i18n,
		addresses=addresses
	)

@flask_app.route("/<lang>/add_address", methods=["POST"])
def add_address(lang="en"):
	if "username" not in session:
		return redirect(url_for("login", lang=lang))

	if lang not in AVAILABLE_LANGUAGES:
		lang = "en"

	i18n = I18n()
	db = Database()

	user_id = session.get("user_id")
	if not user_id:
		return redirect(url_for("login", lang=lang))

	name = request.form.get("name", "")
	address = request.form.get("address", "")
	city = request.form.get("city", "")
	is_default = request.form.get("is_default") == "on"

	if not name or not address or not city:
		flash(i18n.t("MISSING_FIELDS", lang), "error")
		return redirect(url_for("manage_addresses", lang=lang))

	# Add address
	success = db.add_user_address(user_id, name, address, city, is_default)

	if success:
		flash(i18n.t("ADDRESS_ADDED", lang), "success")
	else:
		flash(i18n.t("ADD_ERROR", lang), "error")

	return redirect(url_for("manage_addresses", lang=lang))

@flask_app.route("/<lang>/edit_address/<int:address_id>", methods=["POST"])
def edit_address(lang="en", address_id=None):
	if "username" not in session:
		return redirect(url_for("login", lang=lang))

	if lang not in AVAILABLE_LANGUAGES:
		lang = "en"

	i18n = I18n()
	db = Database()

	user_id = session.get("user_id")
	if not user_id:
		return redirect(url_for("login", lang=lang))

	name = request.form.get("name", "")
	address = request.form.get("address", "")
	city = request.form.get("city", "")
	is_default = request.form.get("is_default") == "on"

	if not name or not address or not city:
		flash(i18n.t("MISSING_FIELDS", lang), "error")
		return redirect(url_for("manage_addresses", lang=lang))

	# Update address
	success = db.update_user_address(user_id, address_id, name, address, city, is_default)

	if success:
		flash(i18n.t("ADDRESS_UPDATED", lang), "success")
	else:
		flash(i18n.t("UPDATE_ERROR", lang), "error")

	return redirect(url_for("manage_addresses", lang=lang))

@flask_app.route("/<lang>/delete_address/<int:address_id>")
def delete_address(lang="en", address_id=None):
	if "username" not in session:
		return redirect(url_for("login", lang=lang))

	if lang not in AVAILABLE_LANGUAGES:
		lang = "en"

	i18n = I18n()
	db = Database()

	user_id = session.get("user_id")
	if not user_id:
		return redirect(url_for("login", lang=lang))

	# Delete address
	success = db.delete_user_address(user_id, address_id)

	if success:
		flash(i18n.t("ADDRESS_DELETED", lang), "success")
	else:
		flash(i18n.t("DELETE_ERROR", lang), "error")

	return redirect(url_for("manage_addresses", lang=lang))

@flask_app.route("/<lang>/create_product", methods=["GET", "POST"])
def create_product(lang="en"):
	if "username" not in session:
		return redirect(url_for("login", lang=lang))

	if lang not in AVAILABLE_LANGUAGES:
		lang = "en"

	i18n = I18n()
	db = Database()

	user_id = session.get("user_id")
	if not user_id:
		return redirect(url_for("login", lang=lang))

	if request.method == "POST":
		name = request.form.get("name", "")
		price = request.form.get("price", "")
		type = request.form.get("type", "")
		quantity = request.form.get("quantity", "")
		description = request.form.get("description", "")
		image_url = request.form.get("image_url", "")

		if not name or not price or not type:
			flash(i18n.t("MISSING_FIELDS", lang), "error")
			return render_template(
				"create_product.html",
				lang=lang,
				i18n=i18n
			)

		try:
			price = float(price)
			if price <= 0:
				flash(i18n.t("INVALID_PRICE", lang), "error")
				return render_template(
					"create_product.html",
					lang=lang,
					i18n=i18n
				)

			if quantity:
				quantity = int(quantity)
				if quantity < 0:
					flash(i18n.t("INVALID_QUANTITY", lang), "error")
					return render_template(
						"create_product.html",
						lang=lang,
						i18n=i18n
					)
			else:
				quantity = None

			# Create product
			success = db.create_product(user_id, name, price, type, quantity, description, image_url)

			if success:
				flash(i18n.t("PRODUCT_CREATED", lang), "success")
				return redirect(url_for("user_dashboard", lang=lang))
			else:
				flash(i18n.t("CREATE_ERROR", lang), "error")
		except ValueError:
			flash(i18n.t("INVALID_INPUT", lang), "error")

	return render_template(
		"create_product.html",
		lang=lang,
		i18n=i18n
	)

@flask_app.route("/<lang>/edit_product/<int:product_id>", methods=["GET", "POST"])
def edit_product(lang="en", product_id=None):
	if "username" not in session:
		return redirect(url_for("login", lang=lang))

	if lang not in AVAILABLE_LANGUAGES:
		lang = "en"

	i18n = I18n()
	db = Database()

	user_id = session.get("user_id")
	if not user_id:
		return redirect(url_for("login", lang=lang))

	product = db.get_product_by_id(product_id, user_id)

	if not product:
		flash(i18n.t("PRODUCT_NOT_FOUND", lang), "error")
		return redirect(url_for("user_dashboard", lang=lang))

	if request.method == "POST":
		name = request.form.get("name", "")
		price = request.form.get("price", "")
		type = request.form.get("type", "")
		quantity = request.form.get("quantity", "")
		description = request.form.get("description", "")
		image_url = request.form.get("image_url", "")

		if not name or not price or not type:
			flash(i18n.t("MISSING_FIELDS", lang), "error")
			return render_template(
				"edit_product.html",
				lang=lang,
				i18n=i18n,
				product=product
			)

		try:
			price = float(price)
			if price <= 0:
				flash(i18n.t("INVALID_PRICE", lang), "error")
				return render_template(
					"edit_product.html",
					lang=lang,
					i18n=i18n,
					product=product
				)

			if quantity:
				quantity = int(quantity)
				if quantity < 0:
					flash(i18n.t("INVALID_QUANTITY", lang), "error")
					return render_template(
						"edit_product.html",
						lang=lang,
						i18n=i18n,
						product=product
					)
			else:
				quantity = None

			# Update product
			success = db.update_product(user_id, product_id, name, price, type, quantity, description, image_url)

			if success:
				flash(i18n.t("PRODUCT_UPDATED", lang), "success")
				return redirect(url_for("user_dashboard", lang=lang))
			else:
				flash(i18n.t("UPDATE_ERROR", lang), "error")
		except ValueError:
			flash(i18n.t("INVALID_INPUT", lang), "error")

	return render_template(
		"edit_product.html",
		lang=lang,
		i18n=i18n,
		product=product
	)

@flask_app.route("/<lang>/toggle_product/<int:product_id>")
def toggle_product(lang="en", product_id=None):
	if "username" not in session:
		return redirect(url_for("login", lang=lang))

	if lang not in AVAILABLE_LANGUAGES:
		lang = "en"

	i18n = I18n()
	db = Database()

	user_id = session.get("user_id")
	if not user_id:
		return redirect(url_for("login", lang=lang))

	product = db.get_product_by_id(product_id, user_id)

	if not product:
		flash(i18n.t("PRODUCT_NOT_FOUND", lang), "error")
		return redirect(url_for("user_dashboard", lang=lang))

	# Toggle product active status
	success, is_active = db.toggle_product_active(user_id, product_id)

	if success:
		if is_active:
			flash(i18n.t("PRODUCT_ACTIVATED", lang), "success")
		else:
			flash(i18n.t("PRODUCT_DEACTIVATED", lang), "success")
	else:
		flash(i18n.t("UPDATE_ERROR", lang), "error")

	return redirect(url_for("user_dashboard", lang=lang))

# Create ASGI application
app = WsgiToAsgi(flask_app)
