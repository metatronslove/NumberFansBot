from flask import Flask, request, render_template, redirect, url_for, session, flash
from telegram import Update
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, PreCheckoutQueryHandler, MessageHandler, filters
from .config import Config
from .database import Database
from .i18n import I18n
from .seed_admin import seed_admin  # Import the seeding function
import asyncio
import bcrypt
import logging
import yaml
from pathlib import Path
from datetime import datetime

app = Flask(__name__, template_folder="../Templates/", static_folder="../Assets", static_url_path="/Assets")
config = Config()
app.secret_key = config.flask_secret_key or "your-secret-key"
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Define available languages
AVAILABLE_LANGUAGES = ["en", "tr", "ar", "he", "la"]

# Create a single event loop for async operations
loop = asyncio.new_event_loop()
asyncio.set_event_loop(loop)

# Initialize Telegram application
telegram_app = Application.builder().token(config.telegram_token).build()

# Initialize the application
try:
	loop.run_until_complete(telegram_app.initialize())
	logger.info("Telegram application initialized successfully")
except Exception as e:
	logger.error(f"Failed to initialize Telegram application: {str(e)}")
	loop.close()
	raise

# Register handlers
def register_handlers():
	from .Commands.UserCommands import (
		start, help, language, numerology, convert_numbers, magic_square,
		transliterate, name, cancel, settings, credits
	)
	from .Commands.UserCommands.abjad import get_abjad_conversation_handler
	from .Commands.UserCommands.bastet import get_bastet_conversation_handler
	from .Commands.UserCommands.huddam import get_huddam_conversation_handler
	from .Commands.UserCommands.unsur import get_unsur_conversation_handler
	from .Commands.UserCommands.payment import payment_handle, handle_pre_checkout, handle_successful_payment
	from .Commands.SystemCommands.callback_query import set_language_handle, handle_callback_query

	try:
		telegram_app.add_handler(CallbackQueryHandler(handle_callback_query))
		logger.info("Registered CallbackQueryHandler for handle_callback_query")
	except Exception as e:
		logger.error(f"Failed to register handle_callback_query: {str(e)}")

	try:
		telegram_app.add_handler(CallbackQueryHandler(set_language_handle, pattern=r"lang\|.+"))
		logger.info("Registered CallbackQueryHandler for set_language_handle")
	except Exception as e:
		logger.error(f"Failed to register set_language_handle: {str(e)}")

	try:
		telegram_app.add_handler(CommandHandler("start", start.start_handle))
		logger.info("Registered CommandHandler for /start")
	except Exception as e:
		logger.error(f"Failed to register /start: {str(e)}")

	try:
		telegram_app.add_handler(CommandHandler("help", help.help_handle))
		logger.info("Registered CommandHandler for /help")
	except Exception as e:
		logger.error(f"Failed to register /help: {str(e)}")

	try:
		telegram_app.add_handler(CommandHandler("language", language.language_handle))
		logger.info("Registered CommandHandler for /language")
	except Exception as e:
		logger.error(f"Failed to register /language: {str(e)}")

	try:
		telegram_app.add_handler(CommandHandler("numerology", numerology.numerology_handle))
		logger.info("Registered CommandHandler for /numerology")
	except Exception as e:
		logger.error(f"Failed to register /numerology: {str(e)}")

	try:
		telegram_app.add_handler(CommandHandler("convertnumbers", convert_numbers.convert_numbers_handle))
		logger.info("Registered CommandHandler for /convertnumbers")
	except Exception as e:
		logger.error(f"Failed to register /convertnumbers: {str(e)}")

	try:
		telegram_app.add_handler(CommandHandler("magicsquare", magic_square.magic_square_handle))
		logger.info("Registered CommandHandler for /magicsquare")
	except Exception as e:
		logger.error(f"Failed to register /magicsquare: {str(e)}")

	try:
		telegram_app.add_handler(CommandHandler("transliterate", transliterate.transliterate_handle))
		logger.info("Registered CommandHandler for /transliterate")
	except Exception as e:
		logger.error(f"Failed to register /transliterate: {str(e)}")

	try:
		telegram_app.add_handler(CommandHandler("name", name.name_handle))
		logger.info("Registered CommandHandler for /name")
	except Exception as e:
		logger.error(f"Failed to register /name: {str(e)}")

	try:
		telegram_app.add_handler(CommandHandler("cancel", cancel.cancel_handle))
		logger.info("Registered CommandHandler for /cancel")
	except Exception as e:
		logger.error(f"Failed to register /cancel: {str(e)}")

	try:
		telegram_app.add_handler(CommandHandler("settings", settings.settings_handle))
		logger.info("Registered CommandHandler for /settings")
	except Exception as e:
		logger.error(f"Failed to register /settings: {str(e)}")

	try:
		telegram_app.add_handler(CommandHandler("credits", credits_handle))
		logger.info("Registered CommandHandler for /credits")
	except Exception as e:
		logger.error(f"Failed to register /credits: {str(e)}")

	try:
		telegram_app.add_handler(CommandHandler("payment", payment_handle))
		logger.info("Registered CommandHandler for /payment")
	except Exception as e:
		logger.error(f"Failed to register /payment: {str(e)}")

	try:
		telegram_app.add_handler(PreCheckoutQueryHandler(handle_pre_checkout))
		logger.info("Registered PreCheckoutQueryHandler")
	except Exception as e:
		logger.error(f"Failed to register PreCheckoutQueryHandler: {str(e)}")

	try:
		telegram_app.add_handler(MessageHandler(filters.SUCCESSFUL_PAYMENT, handle_successful_payment))
		logger.info("Registered MessageHandler for successful payment")
	except Exception as e:
		logger.error(f"Failed to register successful payment handler: {str(e)}")

	try:
		telegram_app.add_handler(get_abjad_conversation_handler())
		logger.info("Registered ConversationHandler for /abjad")
	except Exception as e:
		logger.error(f"Failed to register /abjad conversation handler: {str(e)}")

	try:
		telegram_app.add_handler(get_bastet_conversation_handler())
		logger.info("Registered ConversationHandler for /bastet")
	except Exception as e:
		logger.error(f"Failed to register /bastet conversation handler: {str(e)}")

	try:
		telegram_app.add_handler(get_huddam_conversation_handler())
		logger.info("Registered ConversationHandler for /huddam")
	except Exception as e:
		logger.error(f"Failed to register /huddam conversation handler: {str(e)}")

	try:
		telegram_app.add_handler(get_unsur_conversation_handler())
		logger.info("Registered ConversationHandler for /unsur")
	except Exception as e:
		logger.error(f"Failed to register /unsur conversation handler: {str(e)}")

try:
	register_handlers()
	logger.info("All handlers registered successfully")
except Exception as e:
	logger.error(f"Error in register_handlers: {str(e)}")
	raise

def get_fields():
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

@app.route("/<lang>")
@app.route("/")
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
    users = db.get_users()
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
    return render_template("dashboard.html", i18n=i18n, lang=lang, users=users, fields=get_fields(), config=config)

@app.route("/<lang>/toggle_blacklist", methods=["POST"])
def toggle_blacklist(lang="en"):
    if "username" not in session:
        return redirect(url_for("login", lang=lang))
    config = Config()
    i18n = I18n()
    if lang not in AVAILABLE_LANGUAGES:
        lang = "en"
    user_id = request.form.get("user_id")
    try:
        db = Database()
        if db.toggle_blacklist(user_id):
            query = "SELECT is_blacklisted FROM users WHERE user_id = %s"
            db.cursor.execute(query, (user_id,))
            user = db.cursor.fetchone()
            status = "blacklisted" if user['is_blacklisted'] else "unblacklisted"
            flash(i18n.t("BLACKLIST_TOGGLED", lang, user_id=user_id, status=status), "success")
        else:
            flash(i18n.t("BLACKLIST_TOGGLE_ERROR", lang), "error")
    except Exception as e:
        logger.error(f"Error toggling blacklist: {str(e)}")
        flash(i18n.t("BLACKLIST_TOGGLE_ERROR", lang), "error")
    return redirect(url_for("index", lang=lang))

@app.route("/<lang>/promote_credits", methods=["POST"])
def promote_credits(lang="en"):
    if "username" not in session:
        return redirect(url_for("login", lang=lang))
    config = Config()
    i18n = I18n()
    if lang not in AVAILABLE_LANGUAGES:
        lang = "en"
    user_id = request.form.get("user_id")
    credits = request.form.get("credits")
    try:
        credits = int(credits)
        if credits <= 0:
            flash(i18n.t("INVALID_CREDITS", lang, error="Credits must be positive"), "error")
            return redirect(url_for("index", lang=lang))
        db = Database()
        if db.promote_credits(user_id, credits):
            flash(i18n.t("CREDITS_PROMOTED", lang, credits=credits, user_id=user_id), "success")
        else:
            flash(i18n.t("CREDITS_PROMOTE_ERROR", lang), "error")
    except ValueError:
        flash(i18n.t("INVALID_CREDITS", lang, error="Invalid credits value"), "error")
    return redirect(url_for("index", lang=lang))

@app.route("/<lang>/install", methods=["GET", "POST"])
def install(lang="en"):
    config = Config()
    i18n = I18n()
    if lang not in AVAILABLE_LANGUAGES:
        lang = "en"
    messages = []
    if request.method == "POST":
        config_data = {
            'mysql': {},
            'ai_settings': {}
        }
        fields = [
            'telegram_token', 'bot_username', 'webhook_url', 'mysql_host', 'mysql_user', 'mysql_password',
            'mysql_database', 'github_username', 'github_token', 'github_repo', 'github_pages_url',
            'payment_provider_token', 'currency_exchange_token', 'huggingface_access_token', 'flask_secret_key'
        ]
        for field in fields:
            value = request.form.get(field)
            config_data[field] = value or ""
            config_data[f"{field}_use_env"] = False
        try:
            config.save_config(config_data)
            # Set environment variables for admin seeding
            os.environ['ADMIN_USER'] = request.form.get("admin_username", "admin")
            os.environ['ADMIN_PASS'] = request.form.get("admin_password", "password123")
            seed_admin()  # Seed the admin user
            flash(i18n.t("INSTALL_SUCCESS", lang), "success")
            return redirect(url_for("index", lang=lang))
        except Exception as e:
            logger.error(f"Install error: {str(e)}")
            messages.append(f"Failed to save configuration or seed admin: {str(e)}")
    return render_template("install.html", i18n=i18n, lang=lang, messages=messages)

@app.route("/<lang>/login", methods=["GET", "POST"])
def login(lang="en"):
	config = Config()
	db = Database()
	i18n = I18n()
	if lang not in AVAILABLE_LANGUAGES:
		lang = "en"
	if request.method == "POST":
		username = request.form.get("username")
		password = request.form.get("password")
		if not username or not password:
			flash(i18n.t("ERROR_INVALID_INPUT", lang, error="Username and password are required"), "error")
			return render_template("login.html", i18n=i18n, lang=lang)
		query = "SELECT * FROM users WHERE username = %s AND is_admin = TRUE"
		db.cursor.execute(query, (username,))
		user = db.cursor.fetchone()
		if user and bcrypt.checkpw(password.encode("utf-8"), user['password'].encode("utf-8")):
			session["username"] = username
			session["user_id"] = str(user["user_id"])
			flash(i18n.t("LOGIN_SUCCESS", lang), "success")
			return redirect(url_for("index", lang=lang))
		else:
			flash(i18n.t("LOGIN_ERROR", lang), "error")
	return render_template("login.html", i18n=i18n, lang=lang)

@app.route("/<lang>/commands")
def commands(lang="en"):
    config = Config()
    db = Database()
    i18n = I18n()
    if lang not in AVAILABLE_LANGUAGES:
        lang = "en"
    command_usage = db.get_command_usage()
    # Process for visualization
    if command_usage:
        max_count = max(usage['count'] for usage in command_usage)
        for usage in command_usage:
            usage['percentage'] = (usage['count'] / max_count * 100) if max_count > 0 else 0
    return render_template("commands.html", i18n=i18n, lang=lang, command_usage=command_usage, config=config)

@app.route("/<lang>/logout")
def logout(lang="en"):
	config = Config()
	session.pop("username", None)
	session.pop("user_id", None)
	db = Database()
	i18n = I18n()
	if lang not in AVAILABLE_LANGUAGES:
		lang = "en"
	flash(i18n.t("LOGOUT_SUCCESS", lang), "success")
	return redirect(url_for("login", lang=lang))

@app.route("/<lang>/save_config", methods=["POST"])
def save_config_route(lang="en"):
	config = Config()
	db = Database()
	i18n = I18n()
	if lang not in AVAILABLE_LANGUAGES:
		lang = "en"
	config_data = {
		'mysql': {},
		'ai_settings': {}
	}
	for field in get_fields():
		key = field["key"]
		value = request.form.get(key)
		use_env = request.form.get(f"{key}_use_env") == "on"
		if key.startswith("ai_settings."):
			subkey = key.split(".")[1]
			config_data["ai_settings"][f"{subkey}_use_env"] = use_env
			config_data["ai_settings"][subkey] = value if not use_env else ""
		elif key.startswith("mysql."):
			subkey = key.split(".")[1]
			config_data["mysql"][f"{subkey}_use_env"] = use_env
			config_data["mysql"][subkey] = value if not use_env else ""
		else:
			config_data[key] = value if not use_env else ""
			config_data[f"{key}_use_env"] = use_env
	try:
		config.save_config(config_data)
		flash(i18n.t("CONFIG_SAVED", lang), "success")
	except Exception as e:
		logger.error(f"Config save error: {str(e)}")
		flash(i18n.t("ERROR_GENERAL", lang, error="Failed to save config"), "error")
	query = "SELECT * FROM users"
	db.cursor.execute(query)
	users = db.cursor.fetchall()
	return render_template("dashboard.html", i18n=i18n, lang=lang, users=users, fields=get_fields(), config=config)

@app.route("/<lang>/add_model", methods=["POST"])
def add_model(lang="en"):
	config = Config()
	if "username" not in session:
		flash(i18n.t("LOGIN_ERROR", lang), "error")
		return redirect(url_for("login", lang=lang))
	db = Database()
	i18n = I18n()
	if lang not in AVAILABLE_LANGUAGES:
		lang = "en"
	model_name = request.form.get("model_name")
	model_url = request.form.get("model_url")
	access_token_env = request.form.get("access_token_env")
	if not all([model_name, model_url, access_token_env]):
		flash(i18n.t("ERROR_INVALID_INPUT", lang, error="All model fields are required"), "error")
	else:
		try:
			models_file = Path("Config/models.yml")
			models_data = {"models": []}
			if models_file.exists():
				with open(models_file, "r") as f:
					models_data = yaml.safe_load(f) or {"models": []}
			models_data["models"].append({
				"name": model_name,
				"url": model_url,
				"access_token_env": access_token_env
			})
			with open(models_file, "w") as f:
				yaml.dump(models_data, f)
			config.models = load_models()
			flash(i18n.t("MODEL_ADDED", lang), "success")
		except Exception as e:
			logger.error(f"Add model error: {str(e)}")
			flash(i18n.t("ERROR_GENERAL", lang, error="Failed to add model"), "error")
	query = "SELECT * FROM users"
	db.cursor.execute(query)
	users = db.cursor.fetchall()
	return render_template("dashboard.html", i18n=i18n, lang=lang, users=users, fields=get_fields(), config=config)

@app.route("/<lang>/delete_model", methods=["POST"])
def delete_model(lang="en"):
	config = Config()
	if "username" not in session:
		flash(i18n.t("LOGIN_ERROR", lang), "error")
		return redirect(url_for("login", lang=lang))
	db = Database()
	i18n = I18n()
	if lang not in AVAILABLE_LANGUAGES:
		lang = "en"
	model_name = request.form.get("model_name")
	try:
		models_file = Path("Config/models.yml")
		models_data = {"models": []}
		if models_file.exists():
			with open(models_file, "r") as f:
				models_data = yaml.safe_load(f) or {"models": []}
		models_data["models"] = [m for m in models_data["models"] if m["name"] != model_name]
		with open(models_file, "w") as f:
			yaml.dump(models_data, f)
		config.models = load_models()
		flash(i18n.t("MODEL_DELETED", lang), "success")
	except Exception as e:
		logger.error(f"Delete model error: {str(e)}")
		flash(i18n.t("ERROR_GENERAL", lang, error="Failed to delete model"), "error")
	query = "SELECT * FROM users"
	db.cursor.execute(query)
	users = db.cursor.fetchall()
	return render_template("dashboard.html", i18n=i18n, lang=lang, users=users, fields=get_fields(), config=config)

@app.route("/<lang>/github_traffic")
def github_traffic(lang="en"):
    config = Config()
    i18n = I18n()
    if lang not in AVAILABLE_LANGUAGES:
        lang = "en"
    if not config.github_pages_url:
        flash(i18n.t("CONFIGURE_GITHUB_URL", lang), "warning")
    return render_template("github_traffic.html", i18n=i18n, lang=lang, config=config)

@app.route("/<lang>/manage_beta_tester", methods=["POST"])
def manage_beta_tester(lang="en"):
	config = Config()
	if "username" not in session:
		flash(i18n.t("LOGIN_ERROR", lang), "error")
		return redirect(url_for("login", lang=lang))
	db = Database()
	i18n = I18n()
	if lang not in AVAILABLE_LANGUAGES:
		lang = "en"
	telegram_id = request.form.get("telegram_id")
	action = request.form.get("action")
	query = "SELECT * FROM users"
	db.cursor.execute(query)
	users = db.cursor.fetchall()
	try:
		telegram_id = int(telegram_id)
		if action == "grant":
			db.set_beta_tester(telegram_id, True)
			flash(i18n.t("BETA_TESTER_GRANTED", lang, telegram_id=telegram_id), "success")
		elif action == "revoke":
			db.set_beta_tester(telegram_id, False)
			flash(i18n.t("BETA_TESTER_REVOKED", lang, telegram_id=telegram_id), "success")
		else:
			flash(i18n.t("ERROR_INVALID_INPUT", lang, error="Invalid action"), "error")
	except ValueError:
		flash(i18n.t("ERROR_INVALID_INPUT", lang, error="Invalid Telegram ID"), "error")
	return render_template("dashboard.html", i18n=i18n, lang=lang, users=users, fields=get_fields(), config=config)

@app.route(f"/bot{config.telegram_token}", methods=["POST"])
def webhook():
	config = Config()
	try:
		update = Update.de_json(request.get_json(), telegram_app.bot)
		loop.run_until_complete(telegram_app.process_update(update))
		return "", 200
	except Exception as e:
		logger.error(f"Webhook error: {str(e)}")
		return "", 500

@app.route("/set_webhook", methods=["GET"])
def set_webhook():
	config = Config()
	if not config.telegram_token:
		logger.error("TELEGRAM_TOKEN is not set")
		return "Failed to set webhook: TELEGRAM_TOKEN is not set", 500

	webhook_url = request.args.get("webhook_url")
	if not webhook_url:
		webhook_url = f"https://{request.host}/bot{config.telegram_token}"

	try:
		result = loop.run_until_complete(telegram_app.bot.set_webhook(url=webhook_url))
		if result:
			logger.info(f"Webhook set successfully to {webhook_url}")
			return f"Webhook set to {webhook_url}", 200
		else:
			logger.error("Failed to set webhook: Telegram API returned False")
			return "Failed to set webhook: Telegram API returned False", 500
	except Exception as e:
		logger.error(f"Set webhook error: {str(e)}")
		return f"Failed to set webhook: {str(e)}", 500