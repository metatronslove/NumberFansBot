import logging
import requests
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from telegram.constants import ParseMode
from ...database import Database
from ...i18n import I18n
from ...transliteration import Transliteration
from ...Abjad import Abjad
from ...Numerology import UnifiedNumerology
from ...MagicSquare import MagicSquareGenerator
from ...NumberConverter import NumberConverter
from ...cache import Cache
from ...config import config
from ..UserCommands.nutket import nutket_handle
from ..UserCommands.payment import handle_payment_callback
import urllib.parse
import re

logger = logging.getLogger(__name__)

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
		response.json()[0]["generated_text"] = re.sub(rf"^{re.escape(prompt)}.*?\[/INST\]", "", generated_text, flags=re.DOTALL).strip()
		if response.status_code == 200:
			return response.json()[0]["generated_text"].split("[/INST]")[-1].strip()
		else:
			logger.error(f"Hugging Face API error: {response.status_code}")
			return ""
	except Exception as e:
		logger.error(f"Hugging Face commentary error: {str(e)}")
		return ""

async def set_language_handle(update: Update, context: ContextTypes.DEFAULT_TYPE):
	query = update.callback_query
	await query.answer()
	user_id = query.from_user.id
	db = Database()
	i18n = I18n()
	language = db.get_user_language(user_id)

	new_language = query.data.split("|")[1]
	transliteration = Transliteration(db, i18n)
	if new_language in transliteration.valid_languages:
		db.set_user_language(user_id, new_language)
		await query.edit_message_text(
			i18n.t("LANGUAGE_CHANGED", new_language, selected_lang=new_language.upper()),
			parse_mode=ParseMode.HTML
		)
	else:
		await query.edit_message_text(
			i18n.t("ERROR_INVALID_INPUT", language, error="Invalid language"),
			parse_mode=ParseMode.HTML
		)

async def handle_callback_query(update: Update, context: ContextTypes.DEFAULT_TYPE):
	query = update.callback_query
	data = query.data
	user_id = query.from_user.id
	db = Database()
	i18n = I18n()
	transliteration = Transliteration(db, i18n)
	cache = Cache()
	language = db.get_user_language(user_id)

	if not (data.startswith("payment_select_") or data == "help_group_chat"):
		if db.is_blacklisted(user_id):
			await query.message.reply_text(
				i18n.t("USER_BLACKLISTED", language),
				parse_mode=ParseMode.HTML
			)
			await query.answer()
			return
		if not db.is_beta_tester(user_id) and db.get_user_credits(user_id) <= 0:
			await query.message.reply_text(
				i18n.t("NO_CREDITS", language),
				parse_mode=ParseMode.HTML
			)
			await query.answer()
			return
		if not db.is_beta_tester(user_id):
			db.decrement_credits(user_id)

	try:
		if data.startswith("name_alt_"):
			parts = data.split("_")
			if len(parts) != 3:
				await query.message.reply_text(
					i18n.t("ERROR_INVALID_INPUT", language, error="Invalid callback data"),
					parse_mode=ParseMode.HTML
				)
				await query.answer()
				return
			cache_id = parts[1]
			alt_index = int(parts[2])
			cache_data = cache.get_alternatives(cache_id)
			if not cache_data or alt_index >= len(cache_data.get("alternatives", [])):
				await query.message.reply_text(
					i18n.t("ERROR_INVALID_INPUT", language, error="Invalid or expired cache data"),
					parse_mode=ParseMode.HTML
				)
				await query.answer()
				return
			original_name = cache_data["source_name"]
			target_lang = cache_data["target_lang"]
			source_lang = cache_data["source_lang"]
			transliterated_name = cache_data["alternatives"][alt_index]["transliterated_name"]
			suffix = cache_data["alternatives"][alt_index].get("suffix", transliteration.get_suffix(transliterated_name, original_name))
			try:
				transliteration.store_transliteration(original_name, source_lang, target_lang, transliterated_name, user_id=user_id)
				response = transliteration.format_response(suffix, target_lang, language, language)
				await query.message.reply_text(response, parse_mode=ParseMode.HTML)
			except Exception as e:
				await query.message.reply_text(
					i18n.t("ERROR_INVALID_INPUT", language, error=str(e)),
					parse_mode=ParseMode.HTML
				)
		elif data.startswith("magic_square_"):
			row_sum = int(data[len("magic_square_"):])
			magic_square = MagicSquareGenerator()
			square = magic_square.generate_magic_square(3, row_sum, 0, False, 'arabic')
			response = i18n.t("MAGICSQUARE_RESULT", language, number=row_sum, square=square)
			commentary = await get_ai_commentary(response, language)
			if commentary:
				response = "\n\n" + i18n.t("AI_COMMENTARY", language, commentary=commentary)
			buttons = [[InlineKeyboardButton(
				i18n.t("NEXT_SIZE", language),
				callback_data=f"next_size_{row_sum}_{square['size']}_arabic"
			)]]
			reply_markup = InlineKeyboardMarkup(buttons)
			await query.message.reply_text(response, parse_mode=ParseMode.MARKDOWN,	reply_markup=reply_markup)
		elif data.startswith("indian_square_"):
			row_sum = int(data[len("magic_square_"):])
			magic_square = MagicSquareGenerator()
			square = magic_square.generate_magic_square(3, row_sum, 0, False, 'indian')
			response = i18n.t("MAGICSQUARE_RESULT", language, number=row_sum, square=square["box"])
			commentary = await get_ai_commentary(response, language)
			if commentary:
				response = "\n\n" + i18n.t("AI_COMMENTARY", language, commentary=commentary)
			buttons = [[InlineKeyboardButton(
				i18n.t("NEXT_SIZE", language),
				callback_data=f"next_size_{row_sum}_{square['size']}_indian"
			)]]
			reply_markup = InlineKeyboardMarkup(buttons)
			await query.message.reply_text(response, parse_mode=ParseMode.MARKDOWN,	reply_markup=reply_markup)
		elif data.startswith("next_size_"):
			parts = data[len("next_size_"):].split("_")
			row_sum, current_n, output_numbering = int(parts[0]), int(parts[1]), str(parts[3])
			magic_square = MagicSquareGenerator()
			square = magic_square.generate_magic_square(current_n + 1, row_sum, 0, False, output_numbering)
			response = i18n.t("MAGICSQUARE_RESULT", language, number=row_sum, square=square["box"])
			commentary = await get_ai_commentary(response, language)
			if commentary:
				response = "\n\n" + i18n.t("AI_COMMENTARY", language, commentary=commentary)
			buttons = [[InlineKeyboardButton(
				i18n.t("NEXT_SIZE", language),
				callback_data=f"next_size_{row_sum}_{square['size']}_{output_numbering}"
			)]]
			reply_markup = InlineKeyboardMarkup(buttons)
			await query.message.reply_text(response, parse_mode=ParseMode.MARKDOWN,	reply_markup=reply_markup)
		elif data.startswith("nutket_"):
			parts = data[len("nutket_"):].split("_")
			number, lang = int(parts[0]), parts[1]
			await nutket_handle(update, context, number=number, lang=lang)
		elif data.startswith("abjad_details_"):
			details = context.user_data.get("abjad_result", {}).get("details", "")
			if details:
				await query.message.reply_text(
					i18n.t("ABJAD_DETAILS", language, details=details),
					parse_mode=ParseMode.HTML
				)
			else:
				await query.message.reply_text(
					i18n.t("ERROR_GENERAL", language, error="No details available"),
					parse_mode=ParseMode.HTML
				)
		elif data.startswith("abjad_text_"):
			parts = data[len("abjad_text_"):].rsplit("_", 1)
			text, lang = parts[0], parts[1]
			abjad = Abjad()
			result = abjad.abjad(text, tablo=1, shadda=1, detail=0, lang=lang)
			if isinstance(result, str) and result.startswith("Error"):
				await query.message.reply_text(
					i18n.t("ERROR_GENERAL", language, error=result),
					parse_mode=ParseMode.HTML
				)
			else:
				value = result["sum"] if isinstance(result, dict) else result
				response = i18n.t("ABJAD_RESULT", language, text=text, value=value)
				commentary = await get_ai_commentary(response, language)
				if commentary:
					response += "\n\n" + i18n.t("AI_COMMENTARY", language, commentary=commentary)
				keyboard = []
				if value >= 15:
					keyboard.append([InlineKeyboardButton(
						i18n.t("CREATE_MAGIC_SQUARE", language),
						callback_data=f"magic_square_{value}"
					)])
				keyboard.append([InlineKeyboardButton(
					i18n.t("SPELL_NUMBER", language),
					callback_data=f"nutket_{value}_{lang}"
				)])
				reply_markup = InlineKeyboardMarkup(keyboard)
				await query.message.reply_text(
					response,
					parse_mode=ParseMode.HTML,
					reply_markup=reply_markup
				)
		elif data.startswith("payment_select_"):
			await handle_payment_callback(update, context)
		elif data.startswith("numerology_prompt_"):
			parts = data[len("numerology_prompt_"):].split("_", 2)
			encoded_text, method, alphabet = parts[0], parts[1], parts[2]
			text = urllib.parse.unquote(encoded_text)
			numerology = UnifiedNumerology()
			result = numerology.numerolog(text, alphabet=alphabet, method=method, detail=False)
			response = i18n.t("NUMEROLOGY_RESULT", language, text=text, alphabet=alphabet, method=method, value=result)
			commentary = await get_ai_commentary(response, language)
			if commentary:
				response += "\n\n" + i18n.t("AI_COMMENTARY", language, commentary=commentary)
			buttons = [
				[InlineKeyboardButton(f"Method: {m.capitalize()}", callback_data=f"numerology_{encoded_text}_{alphabet}_{m}")]
				for m in numerology.get_available_methods() if m != method
			]
			if result >= 15:
				buttons.append([InlineKeyboardButton(
					i18n.t("CREATE_MAGIC_SQUARE", language),
					callback_data=f"magic_square_{result}"
				)])
			reply_markup = InlineKeyboardMarkup(buttons) if buttons else None
			await query.message.reply_text(response, parse_mode=ParseMode.HTML, reply_markup=reply_markup)
		elif data.startswith("numerology_"):
			parts = data[len("numerology_"):].split("_", 2)
			encoded_text, alphabet, method = parts[0], parts[1], parts[2]
			text = urllib.parse.unquote(encoded_text)
			numerology = UnifiedNumerology()
			result = numerology.numerolog(text, alphabet=alphabet, method=method, detail=False)
			response = i18n.t("NUMEROLOGY_RESULT", language, text=text, alphabet=alphabet, method=method, value=result)
			commentary = await get_ai_commentary(response, language)
			if commentary:
				response += "\n\n" + i18n.t("AI_COMMENTARY", language, commentary=commentary)
			buttons = [
				[InlineKeyboardButton(f"Method: {m.capitalize()}", callback_data=f"numerology_{encoded_text}_{alphabet}_{m}")]
				for m in numerology.get_available_methods() if m != method
			]
			if result >= 15:
				buttons.append([InlineKeyboardButton(
					i18n.t("CREATE_MAGIC_SQUARE", language),
					callback_data=f"magic_square_{result}"
				)])
			reply_markup = InlineKeyboardMarkup(buttons) if buttons else None
			await query.message.reply_text(response, parse_mode=ParseMode.HTML, reply_markup=reply_markup)
		elif data.startswith("convertnumbers_"):
			parts = data[len("convertnumbers_"):].split("_")
			number, format_type = int(parts[0]), parts[1]
			converter = NumberConverter()
			available_formats = ["arabic", "indian"]
			if format_type not in available_formats:
				await query.message.reply_text(
					i18n.t("ERROR_INVALID_INPUT", language, error="Invalid format"),
					parse_mode=ParseMode.HTML
				)
			else:
				result = converter.arabic(str(number)) if format_type == "arabic" else converter.indian(str(number))
				response = i18n.t("CONVERTNUMBERS_RESULT", language, number=number, format=format_type, result=result)
				alt_format = "indian" if format_type == "arabic" else "arabic"
				buttons = [[InlineKeyboardButton(
					f"Format: {alt_format.capitalize()}",
					callback_data=f"convertnumbers_{number}_{alt_format}"
				)]]
				reply_markup = InlineKeyboardMarkup(buttons)
				await query.message.reply_text(response, parse_mode=ParseMode.HTML, reply_markup=reply_markup)
		elif data.startswith("settings_lang_"):
			new_language = data[len("settings_lang_"):]
			if new_language in transliteration.valid_languages:
				db.set_user_language(user_id, new_language)
				await query.message.reply_text(
					i18n.t("LANGUAGE_CHANGED", language, selected_lang=new_language.upper()),
					parse_mode=ParseMode.HTML
				)
			else:
				await query.message.reply_text(
					i18n.t("ERROR_INVALID_INPUT", language, error="Invalid language"),
					parse_mode=ParseMode.HTML
				)
		elif data.startswith("transliterate_suggest_"):
			parts = data[len("transliterate_suggest_"):].split("_", 2)
			source_lang, target_lang, encoded_text = parts[0], parts[1], parts[2]
			text = urllib.parse.unquote(encoded_text)
			alternatives = transliteration.get_transliteration_alternatives(text, source_lang, target_lang)
			if not alternatives:
				await query.message.reply_text(
					i18n.t("SUGGEST_TRANSLITERATION_RESULT", language, text=text, source_lang=source_lang, target_lang=target_lang, results="No suggestions available"),
					parse_mode=ParseMode.HTML
				)
			else:
				# Store alternatives in cache
				cache_id = cache.store_alternatives(user_id, source_lang, target_lang, text, alternatives)
				results = ", ".join(alt.get("suffix", transliteration.get_suffix(alt["transliterated_name"], text)) for alt in alternatives)
				response = i18n.t("SUGGEST_TRANSLITERATION_RESULT", language, text=text, source_lang=source_lang, target_lang=target_lang, results=results)
				buttons = [
					[InlineKeyboardButton(
						alt.get("suffix", transliteration.get_suffix(alt["transliterated_name"], text)),
						callback_data=f"name_alt_{cache_id}_{i}"
					)]
					for i, alt in enumerate(alternatives)
				]
				reply_markup = InlineKeyboardMarkup(buttons) if buttons else None
				await query.message.reply_text(response, parse_mode=ParseMode.HTML, reply_markup=reply_markup)
		elif data.startswith("transliterate_history_"):
			user_id = int(data[len("transliterate_history_"):])
			history = db.transliteration_collection.find({"user_id": user_id})
			history = list(history)
			if not history:
				await query.message.reply_text(
					i18n.t("TRANSLITERATION_HISTORY_RESULT", language, history="No transliteration history found"),
					parse_mode=ParseMode.HTML
				)
			else:
				history_str = "\n".join([f"{item['source_name']} -> {item.get('suffix', transliteration.get_suffix(item['transliterated_name'], item['source_name']))} ({item['target_lang']})" for item in history])
				response = i18n.t("TRANSLITERATION_HISTORY_RESULT", language, history=history_str)
				await query.message.reply_text(response, parse_mode=ParseMode.HTML)
		elif data == "help_group_chat":
			try:
				await query.message.reply_video(
					video=open("Static/help_group_chat.mp4", "rb"),
					caption=i18n.t("HELP_GROUP_CHAT_USAGE", language),
					parse_mode=ParseMode.HTML
				)
			except Exception as e:
				await query.message.reply_text(
					i18n.t("ERROR_GENERAL", language, error="Failed to send help video"),
					parse_mode=ParseMode.HTML
				)
		await query.answer()
	except Exception as e:
		logger.error(f"Callback error: {str(e)}")
		await query.message.reply_text(
			i18n.t("ERROR_GENERAL", language, error="An error occurred while processing the callback"),
			parse_mode=ParseMode.HTML
		)
		await query.answer()