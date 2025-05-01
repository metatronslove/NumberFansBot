import requests
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CallbackContext
from telegram.constants import ParseMode
from ...database import Database
from ...i18n import I18n
from ...transliteration import Transliteration
from ...config import config
from datetime import datetime
import urllib.parse

async def register_user_if_not_exists(update: Update, context: CallbackContext, user):
	db = Database()
	if not db.check_if_user_exists(user.id):
		db.add_new_user(
			user_id=user.id,
			chat_id=update.message.chat_id,
			username=user.username or "",
			first_name=user.first_name or "",
			last_name=user.last_name or "",
		)

async def get_ai_commentary(response: str, lang: str) -> str:
	i18n = I18n()
	prompt = i18n.t("AI_PROMPT", lang, response=response)
	try:
		headers = {"Authorization": f"Bearer {config.ai_access_token}"}
		payload = {
			"inputs": prompt,
			"parameters": {"max_length": 200, "temperature": 0.7}
		}
		response = requests.post(
			config.ai_model_url,
			headers=headers,
			json=payload
		)
		if response.status_code == 200:
			return response.json()[0]["generated_text"].split("[/INST]")[-1].strip()
		else:
			return ""
	except Exception:
		return ""

async def name_handle(update: Update, context: CallbackContext):
	user = update.message.from_user
	await register_user_if_not_exists(update, context, user)
	user_id = user.id
	db = Database()
	i18n = I18n()
	language = db.get_user_language(user_id)
	db.set_user_attribute(user_id, "last_interaction", datetime.now())

	# Increment command usage
	db.increment_command_usage("name", user_id)

	args = context.args
	if len(args) < 1:
		await update.message.reply_text(
			i18n.t("NAME_USAGE", language),
			parse_mode=ParseMode.HTML
		)
		return

	prefix = " ".join(args[:-1]) if len(args) > 1 else args[0]
	target_lang = args[-1].lower() if len(args) >= 1 else "english"

	transliteration = Transliteration(db, i18n)
	valid_languages = transliteration.valid_languages

	if target_lang not in valid_languages:
		await update.message.reply_text(
			i18n.t("ERROR_INVALID_INPUT", language, error=f"Invalid language. Use: {', '.join(valid_languages)}"),
			parse_mode=ParseMode.HTML
		)
		return

	try:
		source_lang = transliteration.guess_source_lang(prefix)
		result = transliteration.transliterate(prefix, target_lang, source_lang)
		name = result["primary"]
		response = i18n.t("NAME_RESULT", language, prefix=prefix, type="modern", method="simple", name=name)

		# Add AI commentary
		commentary = await get_ai_commentary(response, language)
		if commentary:
			response += "\n\n" + i18n.t("AI_COMMENTARY", language, commentary=commentary)

		# Add buttons for alternative languages
		encoded_prefix = urllib.parse.quote(prefix)
		buttons = [
			[InlineKeyboardButton(
				f"Lang: {lang.capitalize()}",
				callback_data=f"name_alt_{encoded_prefix}_{lang}_{urllib.parse.quote(name)}"
			)] for lang in valid_languages if lang != target_lang
		]
		reply_markup = InlineKeyboardMarkup(buttons) if buttons else None

		await update.message.reply_text(
			response,
			parse_mode=ParseMode.MARKDOWN,
			reply_markup=reply_markup
		)
	except Exception as e:
		await update.message.reply_text(
			i18n.t("ERROR_INVALID_INPUT", language, error=str(e)),
			parse_mode=ParseMode.HTML
		)