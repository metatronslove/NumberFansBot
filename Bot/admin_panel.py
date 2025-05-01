from flask import Flask, request, render_template, redirect, url_for, session, flash
from telegram import Update
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, PreCheckoutQueryHandler, MessageHandler, filters
from .config import Config
from .database import Database
from .i18n import I18n
from .Commands.UserCommands import (
    start, help, language, numerology, convert_numbers, magic_square,
    transliterate, name, cancel, settings
)
from .Commands.UserCommands.abjad import get_abjad_conversation_handler
from .Commands.UserCommands.bastet import get_bastet_conversation_handler
from .Commands.UserCommands.huddam import get_huddam_conversation_handler
from .Commands.UserCommands.unsur import get_unsur_conversation_handler
from .Commands.UserCommands.nutket import nutket_handle
from .Commands.UserCommands.payment import payment_handle, handle_pre_checkout, handle_successful_payment
from .Commands.SystemCommands.callback_query import set_language_handle, handle_callback_query
import asyncio
import logging
import yaml

# Instantiate config before using it
config = Config()

app = Flask(__name__)
app.secret_key = config.flask_secret_key or 'your-secret-key'
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize Telegram application
telegram_app = Application.builder().token(config.telegram_token).build()

# Register handlers
def register_handlers():
    telegram_app.add_handler(CommandHandler("start", start.start_handle))
    telegram_app.add_handler(CommandHandler("help", help.help_handle))
    telegram_app.add_handler(CommandHandler("language", language.language_handle))
    telegram_app.add_handler(CommandHandler("numerology", numerology.numerology_handle))
    telegram_app.add_handler(CommandHandler("convertnumbers", convert_numbers.convert_numbers_handle))
    telegram_app.add_handler(CommandHandler("magicsquare", magic_square.magic_square_handle))
    telegram_app.add_handler(CommandHandler("transliterate", transliterate.transliterate_handle))
    telegram_app.add_handler(CommandHandler("name", name.name_handle))
    telegram_app.add_handler(CommandHandler("cancel", cancel.cancel_handle))
    telegram_app.add_handler(CommandHandler("settings", settings.settings_handle))
    telegram_app.add_handler(CommandHandler("payment", payment_handle))
    telegram_app.add_handler(get_abjad_conversation_handler())
    telegram_app.add_handler(get_bastet_conversation_handler())
    telegram_app.add_handler(get_huddam_conversation_handler())
    telegram_app.add_handler(get_unsur_conversation_handler())
    telegram_app.add_handler(CallbackQueryHandler(set_language_handle, pattern=r"lang\|.+"))
    telegram_app.add_handler(CallbackQueryHandler(handle_callback_query))
    telegram_app.add_handler(PreCheckoutQueryHandler(handle_pre_checkout))
    telegram_app.add_handler(MessageHandler(filters.SUCCESSFUL_PAYMENT, handle_successful_payment))

register_handlers()

def get_fields():
    return [
        {"key": "telegram_token", "label": "Telegram Token", "value": config.telegram_token or "", "use_env": True},
        {"key": "bot_username", "label": "Bot Username", "value": config.bot_username or "", "use_env": True},
        {"key": "webhook_url", "label": "Webhook URL", "value": config.webhook_url or "", "use_env": True},
        {"key": "mongodb_uri", "label": "MongoDB URI", "value": config.mongodb_uri or "", "use_env": True},
        {"key": "github_username", "label": "GitHub Username", "value": config.github_username or "", "use_env": True},
        {"key": "github_token", "label": "GitHub Token", "value": config.github_token or "", "use_env": True},
        {"key": "github_repo", "label": "GitHub Repository", "value": config.github_repo or "", "use_env": True},
        {"key": "github_pages_url", "label": "GitHub Pages URL", "value": config.github_pages_url or "", "use_env": True},
        {"key": "payment_provider_token", "label": "Payment Provider Token", "value": config.payment_provider_token or "", "use_env": True},
        {"key": "currency_exchange_token", "label": "Currency Exchange Token", "value": config.currency_exchange_token or "", "use_env": True},
        {"key": "huggingface_access_token", "label": "Hugging Face Access Token", "value": config.huggingface_access_token or "", "use_env": True},
        {"key": "flask_secret_key", "label": "Flask Secret Key", "value": config.flask_secret_key or "", "use_env": True},
        {"key": "ai_settings.model_url", "label": "AI Model URL", "value": config.ai_model_url or "", "use_env": True},
        {"key": "ai_settings.access_token", "label": "AI Access Token", "value": config.ai_access_token or "", "use_env": True}
    ]

@app.route('/<lang>')
@app.route('/')
def index(lang='en'):
    if 'username' not in session:
        return redirect(url_for('login', lang=lang))
    db = Database()
    i18n = I18n()
    if lang not in config.available_languages:
        lang = 'en'
    users = list(db.user_collection.find())
    return render_template('dashboard.html', i18n=i18n, lang=lang, users=users, fields=get_fields(), config=config)

@app.route('/<lang>/login', methods=['GET', 'POST'])
def login(lang='en'):
    db = Database()
    i18n = I18n()
    if lang not in config.available_languages:
        lang = 'en'
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = db.user_collection.find_one({"username": username, "password": password})
        if user:
            session['username'] = username
            session['user_id'] = str(user['_id'])
            flash(i18n.t("LOGIN_SUCCESS", lang), 'success')
            return redirect(url_for('index', lang=lang))
        else:
            flash(i18n.t("LOGIN_ERROR", lang), 'error')
    return render_template('login.html', i18n=i18n, lang=lang)

@app.route('/<lang>/logout')
def logout(lang='en'):
    session.pop('username', None)
    session.pop('user_id', None)
    db = Database()
    i18n = I18n()
    if lang not in config.available_languages:
        lang = 'en'
    flash(i18n.t("LOGOUT_SUCCESS", lang), 'success')
    return redirect(url_for('login', lang=lang))

@app.route('/<lang>/save_config', methods=['POST'])
def save_config_route(lang='en'):
    db = Database()
    i18n = I18n()
    if lang not in config.available_languages:
        lang = 'en'
    config_data = {
        'ai_settings': {}
    }
    for field in get_fields():
        key = field['key']
        value = request.form.get(key)
        use_env = request.form.get(f"{key}_use_env") == 'on'
        if key.startswith('ai_settings.'):
            subkey = key.split('.')[1]
            config_data['ai_settings'][subkey] = value if not use_env else ''
            config_data['ai_settings'][f"{subkey}_use_env"] = use_env
        else:
            config_data[key] = value if not use_env else ''
            config_data[f"{key}_use_env"] = use_env
    try:
        with open('Config/config.yml', 'w') as f:
            yaml.dump(config_data, f)
        flash(i18n.t("CONFIG_SAVED", lang), 'success')
    except Exception as e:
        logger.error(f"Config save error: {str(e)}")
        flash(i18n.t("ERROR_GENERAL", lang, error="Failed to save config"), 'error')
    users = list(db.user_collection.find())
    return render_template('dashboard.html', i18n=i18n, lang=lang, users=users, fields=get_fields(), config=config)

@app.route('/<lang>/add_model', methods=['POST'])
def add_model(lang='en'):
    if 'username' not in session:
        flash(i18n.t("LOGIN_ERROR", lang), 'error')
        return redirect(url_for('login', lang=lang))
    db = Database()
    i18n = I18n()
    if lang not in config.available_languages:
        lang = 'en'
    model_name = request.form.get('model_name')
    model_url = request.form.get('model_url')
    access_token_env = request.form.get('access_token_env')
    if not all([model_name, model_url, access_token_env]):
        flash(i18n.t("ERROR_INVALID_INPUT", lang, error="All model fields are required"), 'error')
    else:
        try:
            with open('Config/models.yml', 'r') as f:
                models_data = yaml.safe_load(f) or {'models': []}
            models_data['models'].append({
                'name': model_name,
                'url': model_url,
                'access_token_env': access_token_env
            })
            with open('Config/models.yml', 'w') as f:
                yaml.dump(models_data, f)
            # Note: config.models is not defined in config.py; this may need adjustment
            flash("Model added successfully", 'success')
        except Exception as e:
            logger.error(f"Add model error: {str(e)}")
            flash(i18n.t("ERROR_GENERAL", lang, error="Failed to add model"), 'error')
    users = list(db.user_collection.find())
    return render_template('dashboard.html', i18n=i18n, lang=lang, users=users, fields=get_fields(), config=config)

@app.route('/<lang>/delete_model', methods=['POST'])
def delete_model(lang='en'):
    if 'username' not in session:
        flash(i18n.t("LOGIN_ERROR", lang), 'error')
        return redirect(url_for('login', lang=lang))
    db = Database()
    i18n = I18n()
    if lang not in config.available_languages:
        lang = 'en'
    model_name = request.form.get('model_name')
    try:
        with open('Config/models.yml', 'r') as f:
            models_data = yaml.safe_load(f) or {'models': []}
        models_data['models'] = [m for m in models_data['models'] if m['name'] != model_name]
        with open('Config/models.yml', 'w') as f:
            yaml.dump(models_data, f)
        # Note: config.models is not defined in config.py; this may need adjustment
        flash("Model deleted successfully", 'success')
    except Exception as e:
        logger.error(f"Delete model error: {str(e)}")
        flash(i18n.t("ERROR_GENERAL", lang, error="Failed to delete model"), 'error')
    users = list(db.user_collection.find())
    return render_template('dashboard.html', i18n=i18n, lang=lang, users=users, fields=get_fields(), config=config)

@app.route('/<lang>/github_traffic')
def github_traffic(lang='en'):
    db = Database()
    i18n = I18n()
    if lang not in config.available_languages:
        lang = 'en'
    users = list(db.user_collection.find())
    flash(i18n.t("ERROR_GENERAL", lang, error="GitHub traffic not implemented"), 'error')
    return render_template('dashboard.html', i18n=i18n, lang=lang, users=users, fields=get_fields(), config=config)

@app.route('/<lang>/manage_beta_tester', methods=['POST'])
def manage_beta_tester(lang='en'):
    if 'username' not in session:
        flash(i18n.t("LOGIN_ERROR", lang), 'error')
        return redirect(url_for('login', lang=lang))
    db = Database()
    i18n = I18n()
    if lang not in config.available_languages:
        lang = 'en'

    telegram_id = request.form.get('telegram_id')
    action = request.form.get('action')
    users = list(db.user_collection.find())
    try:
        telegram_id = int(telegram_id)
        if action == 'grant':
            db.set_beta_tester(telegram_id, True)
            flash(i18n.t("BETA_TESTER_GRANTED", lang, telegram_id=telegram_id), 'success')
        elif action == 'revoke':
            db.set_beta_tester(telegram_id, False)
            flash(i18n.t("BETA_TESTER_REVOKED", lang, telegram_id=telegram_id), 'success')
        else:
            flash(i18n.t("ERROR_INVALID_INPUT", lang, error="Invalid action"), 'error')
    except ValueError:
        flash(i18n.t("ERROR_INVALID_INPUT", lang, error="Invalid Telegram ID"), 'error')
    return render_template('dashboard.html', i18n=i18n, lang=lang, users=users, fields=get_fields(), config=config)

@app.route(f'/bot{config.telegram_token}', methods=['POST'])
async def webhook():
    try:
        update = Update.de_json(request.get_json(), telegram_app.bot)
        await telegram_app.process_update(update)
        return '', 200
    except Exception as e:
        logger.error(f"Webhook error: {str(e)}")
        return '', 500

@app.route('/set_webhook', methods=['GET'])
async def set_webhook():
    webhook_url = f"https://{request.host}/bot{config.telegram_token}"
    try:
        await telegram_app.bot.set_webhook(url=webhook_url)
        return f"Webhook set to {webhook_url}", 200
    except Exception as e:
        logger.error(f"Set webhook error: {str(e)}")
        return f"Failed to set webhook: {str(e)}", 500