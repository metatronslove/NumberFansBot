import requests
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CallbackContext
from telegram.constants import ParseMode
from ...database import Database
from ...i18n import I18n
from ...Numerology import UnifiedNumerology
from ...MagicSquare import MagicSquareGenerator
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

async def numerology_square_handle(update: Update, context: CallbackContext):
	user = update.message.from_user
	await register_user_if_not_exists(update, context, user)
	user_id = user.id
	db = Database()
	i18n = I18n()
	language = db.get_user_language(user_id)
	db.set_user_attribute(user_id, "last_interaction", datetime.now())

	# Increment command usage
	db.increment_command_usage("numerologysquare", user_id)

	args = context.args
	if len(args) < 1:
		await update.message.reply_text(
			i18n.t("NUMEROLOGYSQUARE_USAGE", language),
			parse_mode=ParseMode.HTML
		)
		return

	# Join arguments until alphabet is detected
	alphabet_index = len(args)
	numerology = UnifiedNumerology()
	for i, arg in enumerate(args):
		if arg.lower() in numerology.get_available_alphabets():
			alphabet_index = i
			break

	text = " ".join(args[:alphabet_index]) if alphabet_index > 0 else args[0]
	alphabet = args[alphabet_index].lower() if alphabet_index < len(args) else "turkish"
	method = "normal"  # Fixed to normal for simplicity, as magic square doesn't need method variation

	if alphabet not in numerology.get_available_alphabets():
		await update.message.reply_text(
			i18n.t("ERROR_INVALID_INPUT", language, error="Invalid alphabet"),
			parse_mode=ParseMode.HTML
		)
		return

	try:
		# Calculate numerology value
		result = numerology.numerolog(text, alphabet=alphabet, method=method, detail=False)
		if isinstance(result, dict) and "error" in result:
			raise ValueError(result["error"])

		# Generate magic square
		magic_square = MagicSquareGenerator()
		square = magic_square.generate(result)  # Assumes MagicSquare can handle the numerology value
		square_str = "\n".join(["  ".join(map(str, row)) for row in square])

		response = i18n.t("NUMEROLOGYSQUARE_RESULT", language, text=text, alphabet=alphabet, square=square_str)

		# Add AI commentary
		commentary = await get_ai_commentary(response, language)
		if commentary:
			response += "\n\n" + i18n.t("AI_COMMENTARY", language, commentary=commentary)

		# Add buttons for alternative alphabets
		encoded_text = urllib.parse.quote(text)
		buttons = [
			[InlineKeyboardButton(f"Alphabet: {a}", callback_data=f"numerologysquare_{encoded_text}_{a}")]
			for a in numerology.get_available_alphabets() if a != alphabet
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