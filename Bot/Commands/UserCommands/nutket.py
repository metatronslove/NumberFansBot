import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CallbackContext
from telegram.constants import ParseMode
from ...database import Database
from ...i18n import I18n
from ...config import Config
from ...Abjad import Abjad
from datetime import datetime
import requests

logger = logging.getLogger(__name__)

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
		headers = {"Authorization": f"Bearer {config.huggingface_access_token}"}
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
			logger.error(f"AI API error: {response.status_code}")
			return ""
	except Exception as e:
		logger.error(f"AI commentary error: {str(e)}")
		return ""

async def nutket_handle(update: Update, context: CallbackContext, number: int = None, lang: str = None):
	user = update.message.from_user if update.message else update.callback_query.from_user
	chat_id = update.message.chat_id if update.message else update.callback_query.message.chat_id
	await register_user_if_not_exists(update, context, user)
	user_id = user.id
	db = Database()
	i18n = I18n()
	language = lang or db.get_user_language(user_id)
	db.set_user_attribute(user_id, "last_interaction", datetime.now())

	db.increment_command_usage("nutket", user_id)

	try:
		if update.message:  # Direct /nutket command
			args = context.args
			if not args or not args[0].isdigit():
				await update.message.reply_text(
					i18n.t("NUTKET_USAGE", language),
					parse_mode=ParseMode.MARKDOWN
				)
				return
			number = int(args[0])
			lang = args[-1].lower() if len(args) > 1 and args[-1].lower() in ["arabic", "hebrew", "turkish", "english", "latin"] else language

		if not number:
			await (update.message.reply_text if update.message else update.callback_query.message.reply_text)(
				i18n.t("ERROR_INVALID_INPUT", language, error="Number is required"),
				parse_mode=ParseMode.MARKDOWN
			)
			return

		# Map language codes for Abjad.nutket()
		lang_map = {
			"ar": "ARABIC",
			"he": "HEBREW",
			"tr": "TURKISH",
			"en": "ENGLISH",
			"la": "LATIN"
		}
		abjad_lang = lang_map.get(lang, "ENGLISH")
		abjad = Abjad()
		spelled = abjad.nutket(number, abjad_lang)

		if spelled.startswith("Error"):
			await (update.message.reply_text if update.message else update.callback_query.message.reply_text)(
				i18n.t("ERROR_GENERAL", language, error=spelled),
				parse_mode=ParseMode.MARKDOWN
			)
			return

		response = i18n.t("NUTKET_RESULT", language, number=number, lang=lang, spelled=spelled)

		# Get AI commentary
		commentary = await get_ai_commentary(response, language)
		if commentary:
			response += "\n\n" + i18n.t("AI_COMMENTARY", language, commentary=commentary)

		# Add buttons
		keyboard = []
		if number >= 15:
			keyboard.append([InlineKeyboardButton(
				i18n.t("CREATE_MAGIC_SQUARE", language),
				callback_data=f"magic_square_{number}"
			)])
		keyboard.append([InlineKeyboardButton(
			i18n.t("CALCULATE_ABJAD", language),
			callback_data=f"abjad_text_{spelled}_{lang}"
		)])
		reply_markup = InlineKeyboardMarkup(keyboard)

		await (update.message.reply_text if update.message else update.callback_query.message.reply_text)(
			response,
			parse_mode=ParseMode.MARKDOWN,
			reply_markup=reply_markup
		)
		if update.callback_query:
			await update.callback_query.answer()

	except Exception as e:
		logger.error(f"Nutket error: {str(e)}")
		await (update.message.reply_text if update.message else update.callback_query.message.reply_text)(
			i18n.t("ERROR_GENERAL", language, error=str(e)),
			parse_mode=ParseMode.MARKDOWN
		)
		if update.callback_query:
			await update.callback_query.answer()