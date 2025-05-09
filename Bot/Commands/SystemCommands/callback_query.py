import logging
import requests
import re
import aiohttp
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CallbackQueryHandler, ContextTypes
from telegram.constants import ParseMode
from telegram.error import BadRequest
from Bot.database import Database
from Bot.i18n import I18n
from Bot.transliteration import Transliteration
from Bot.Abjad import Abjad
from Bot.Numerology import UnifiedNumerology
from Bot.MagicSquare import MagicSquareGenerator
from Bot.NumberConverter import NumberConverter
from Bot.cache import Cache
from Bot.config import Config
from Bot.utils import register_user_if_not_exists, get_warning_description, get_ai_commentary, timeout, handle_credits
from Bot.Commands.UserCommands.abjad import abjad_start
from Bot.Commands.UserCommands.magic_square import magic_square_handle
from Bot.Commands.UserCommands.numerology import numerology_handle
from Bot.Commands.UserCommands.huddam import huddam_start
from Bot.Commands.UserCommands.nutket import nutket_handle
from Bot.Commands.UserCommands.payment import payment_handle
import urllib.parse

logger = logging.getLogger(__name__)
config = Config()

async def set_language_handle(update: Update, context: ContextTypes.DEFAULT_TYPE)	:
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

async def handle_callback_query(update: Update, context: ContextTypes.DEFAULT_TYPE)	:
	query = update.callback_query
	data = query.data
	user_id = query.from_user.id
	db = Database()
	i18n = I18n()
	transliteration = Transliteration(db, i18n)
	cache = Cache()
	language = db.get_user_language(user_id)

	try:
		await query.answer()
	except BadRequest as e:
		if "Query is too old" in str(e) or "query id is invalid" in str(e):
			logger.info(f"Ignoring old or invalid callback query: {str(e)}")
		else:
			logger.error(f"BadRequest in handle_callback_query: {str(e)}")
			raise

	try:
		if data.startswith("end_conversation_"):
			commandToEnd = data[len("end_conversation_"):]
			if commandToEnd == "abjad":
				return await Bot.Commands.UserCommands.abjad.abjad_cancel(update, context)
			elif commandToEnd == "bastet":
				return await Bot.Commands.UserCommands.bastet.bastet_cancel(update, context)
			elif commandToEnd == "huddam":
				return await Bot.Commands.UserCommands.huddam.huddam_cancel(update, context)
			elif commandToEnd == "unsur":
				return await Bot.Commands.UserCommands.unsur.unsur_cancel(update, context)
		elif data.startswith("name_alt_"):
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
		elif data.startswith("huddam_"):
			number = int(data[len("huddam_"):])
			await huddam_start(update, context, number=number)
		elif data.startswith("magic_square_"):
			row_sum = int(data[len("magic_square_"):])
			await magic_square_handle(update, context, number=row_sum)
		elif data.startswith("indian_square_"):
			row_sum = int(data[len("indian_square_"):])
			magic_square = MagicSquareGenerator()
			square = magic_square.generate_magic_square(3, row_sum, 0, False, "indian")
			response = i18n.t("MAGICSQUARE_RESULT", language, number=row_sum, square=square["box"])
			commentary = await get_ai_commentary(response, language)
			if commentary:
				response += "\n\n" + i18n.t("AI_COMMENTARY", language, commentary=commentary)
			buttons = [
				[
					InlineKeyboardButton(
						i18n.t("CREATE_MAGIC_SQUARE", language),
						callback_data=f"magic_square_{row_sum}",
					)
				],
				[
					InlineKeyboardButton(
						i18n.t("NEXT_SIZE", language),
						callback_data=f"next_size_{row_sum}_{square['size']}_indian",
					)
				],
			]
			reply_markup = InlineKeyboardMarkup(buttons)
			await query.message.reply_text(response, parse_mode=ParseMode.MARKDOWN, reply_markup=reply_markup)
		elif data.startswith("next_size_"):
			parts = data[len("next_size_"):].split("_")
			row_sum, current_n, output_numbering = int(parts[0]), int(parts[1]), parts[2]
			magic_square = MagicSquareGenerator()
			square = magic_square.generate_magic_square(current_n + 1, row_sum, 0, False, output_numbering)
			response = i18n.t("MAGICSQUARE_RESULT", language, number=row_sum, square=square["box"])
			commentary = await get_ai_commentary(response, language)
			if commentary:
				response += "\n\n" + i18n.t("AI_COMMENTARY", language, commentary=commentary)
			if output_numbering == "indian":
				buttons = [
					[
						InlineKeyboardButton(
							i18n.t("CREATE_INDIAN_MAGIC_SQUARE", language),
							callback_data=f"indian_square_{row_sum}",
						)
					]
				]
			else:
				buttons = [
					[
						InlineKeyboardButton(
							i18n.t("CREATE_INDIAN_MAGIC_SQUARE", language),
							callback_data=f"magic_square_{row_sum}",
						)
					]
				]
			buttons.append(
				[
					InlineKeyboardButton(
						i18n.t("NEXT_SIZE", language),
						callback_data=f"next_size_{row_sum}_{square['size']}_{output_numbering}",
					)
				]
			)
			reply_markup = InlineKeyboardMarkup(buttons)
			await query.message.reply_text(response, parse_mode=ParseMode.MARKDOWN, reply_markup=reply_markup)
		elif data.startswith("nutket_"):
			parts = data[len("nutket_"):].split("_")
			if len(parts) != 2:
				await query.message.reply_text(
					i18n.t("ERROR_INVALID_INPUT", language, error="Invalid nutket callback data"),
					parse_mode=ParseMode.HTML
				)
				await query.answer()
				return
			number, nutket_lang = int(parts[0]), parts[1]
			await nutket_handle(update, context, number=number, lang=nutket_lang)
		elif data.startswith("abjad_text_"):
			parts = data[len("abjad_text_"):].rsplit("_", 1)
			if len(parts) != 1:
				await query.message.reply_text(
					i18n.t("ERROR_INVALID_INPUT", language, error="Invalid abjad_text callback data"),
					parse_mode=ParseMode.HTML
				)
				await query.answer()
				return
			text, lang = urllib.parse.unquote(parts[0]), parts[1]
			abjad = Abjad()
			await abjad_start(update, context, text=text)
		elif data.startswith("payment_select_"):
			await payment_handle(update, context)
		elif data.startswith("numerology_"):
			parts = data[len("numerology_"):].split("_", 2)
			alphabet, method, encoded_text = parts[0], parts[1], parts[2]
			text = urllib.parse.unquote(encoded_text)
			await numerology_handle(update, context, alphabet=alphabet, method=method, text=text)
		elif data.startswith("convertnumbers_"):
			parts = data[len("convertnumbers_"):].split("_")
			encoded_text, format_type = parts[0], parts[1]
			text = urllib.parse.unquote(encoded_text)
			format_type = parts[0]
			await convert_numbers_handle(update, context, text=text, alt_format=format_type)
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
					[
						InlineKeyboardButton(
							alt.get("suffix", transliteration.get_suffix(alt["transliterated_name"], text)),
							callback_data=f"name_alt_{cache_id}_{i}",
						)
					]
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
				history_str = "\n".join(
					[
						f"{item['source_name']} -> {item.get('suffix', transliteration.get_suffix(item['transliterated_name'], item['source_name']))} ({item['target_lang']})"
						for item in history
					]
				)
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
	except BadRequest as e:
		logger.error(f"Telegram BadRequest: {str(e)}")
		if "Query is too old" in str(e):
			await query.message.reply_text(
				i18n.t("ERROR_TIMEOUT", language, error="Processing took too long. Please try again."),
				parse_mode=ParseMode.HTML
			)
		else:
			await query.message.reply_text(
				i18n.t("ERROR_GENERAL", language, error=str(e)),
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
def register_handlers(application):
	"""Register callback query handlers."""
	application.add_handler(CallbackQueryHandler(
		handle_callback_query,
		pattern="^(name_alt_|magic_square_|indian_square_|next_size_|nutket_|abjad_details_|abjad_text_.*|payment_select_|numerology_prompt_|numerology_|convertnumbers_|settings_lang_|transliterate_suggest_|transliterate_history_|help_group_chat)"
	))
	application.add_handler(CallbackQueryHandler(
		set_language_handle,
		pattern="^lang\\|"
	))