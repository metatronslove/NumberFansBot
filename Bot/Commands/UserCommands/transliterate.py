import logging
import urllib
import json
from datetime import datetime
from pathlib import Path
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
	Application, ConversationHandler, CommandHandler, MessageHandler,
	ContextTypes, CallbackQueryHandler, filters
)
from telegram.constants import ParseMode
from telegram.error import BadRequest
from Bot.config import Config
from Bot.database import Database
from Bot.Helpers.i18n import I18n
from Bot.Helpers.Transliteration import Transliteration
from Bot.utils import register_user_if_not_exists, get_ai_commentary, timeout, handle_credits, send_long_message, uptodate_query
from Bot.cache import Cache
from Bot.Commands.UserCommands.abjad import abjad_start

logger = logging.getLogger(__name__)

# Conversation states
TEXT, SOURCE_LANG, TARGET_LANG, SUGGESTIONS, HISTORY = range(5)

async def transliterate_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
	"""Start the /transliterate command conversation."""
	update, context, query, user, query_message = await uptodate_query(update, context)
	if not query_message:
		return ConversationHandler.END

	logger.info(f"Starting /transliterate for user {user.id if user else 'unknown'}")
	try:
		if user:
			await register_user_if_not_exists(update, context, user)
		user_id = user.id if user else 0
		db = Database()
		i18n = I18n()
		language = db.get_user_language(user_id) if user_id else "en"
		await handle_credits(update, context)
		if user_id:
			db.set_user_attribute(user_id, "last_interaction", datetime.now())
			db.increment_command_usage("transliterate", user_id, query.chat_id)

		args = context.args
		if args:
			context.user_data["transliterate_text"] = " ".join(args)
			return await select_source_lang(update, context)

		await send_long_message(
			message=i18n.t("TRANSLITERATION_PROMPT_TEXT", language),
			parse_mode=ParseMode.HTML,
			update=update,
			query_message=query_message,
			context=context,
			force_new_message=True
		)
		return TEXT
	except Exception as e:
		logger.error(f"Error in transliterate_start: {str(e)}")
		await send_long_message(
			message=i18n.t("ERROR_GENERAL", language, error=str(e)),
			parse_mode=ParseMode.HTML,
			update=update,
			query_message=query_message,
			context=context
		)
		return ConversationHandler.END

async def transliterate_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
	"""Handle the text input for transliteration."""
	update, context, query, user, query_message = await uptodate_query(update, context)
	if not query_message:
		return ConversationHandler.END

	try:
		user_id = user.id if user else 0
		db = Database()
		i18n = I18n()
		language = db.get_user_language(user_id) if user_id else "en"

		text = query.text.strip()
		if not text:
			await send_long_message(
				message=i18n.t("ERROR_INVALID_INPUT", language, error="Text cannot be empty"),
				parse_mode=ParseMode.HTML,
				update=update,
				query_message=query_message,
				context=context
			)
			return TEXT

		context.user_data["transliterate_text"] = text
		return await select_source_lang(update, context)
	except Exception as e:
		logger.error(f"Error in transliterate_text: {str(e)}")
		await send_long_message(
			message=i18n.t("ERROR_GENERAL", language, error=str(e)),
			parse_mode=ParseMode.HTML,
			update=update,
			query_message=query_message,
			context=context
		)
		return ConversationHandler.END

async def select_source_lang(update: Update, context: ContextTypes.DEFAULT_TYPE):
	"""Prompt user to select the source language."""
	update, context, query, user, query_message = await uptodate_query(update, context)
	if not query_message:
		return ConversationHandler.END

	try:
		user_id = user.id if user else 0
		db = Database()
		i18n = I18n()
		language = db.get_user_language(user_id) if user_id else "en"
		transliteration = Transliteration(db, i18n)
		valid_languages = transliteration.valid_languages

		# Create buttons for languages and guess option
		keyboard = [
			[
				InlineKeyboardButton(i18n.t("LANGUAGE_NAME_AR", language), callback_data="source_lang_arabic"),
				InlineKeyboardButton(i18n.t("LANGUAGE_NAME_EN", language), callback_data="source_lang_english")
			],
			[
				InlineKeyboardButton(i18n.t("LANGUAGE_NAME_TR", language), callback_data="source_lang_turkish"),
				InlineKeyboardButton(i18n.t("LANGUAGE_NAME_HE", language), callback_data="source_lang_hebrew")
			],
			[
				InlineKeyboardButton(i18n.t("LANGUAGE_NAME_LA", language), callback_data="source_lang_latin"),
				InlineKeyboardButton(i18n.t("GUESS_LANGUAGE", language), callback_data="source_lang_guess")
			],
			[InlineKeyboardButton(i18n.t("CANCEL_BUTTON", language), callback_data="end_conversation")]
		]
		reply_markup = InlineKeyboardMarkup(keyboard)

		await send_long_message(
			message=i18n.t("TRANSLITERATION_PROMPT_SOURCE_LANG", language),
			parse_mode=ParseMode.HTML,
			reply_markup=reply_markup,
			update=update,
			query_message=query_message,
			context=context
		)
		return SOURCE_LANG
	except Exception as e:
		logger.error(f"Error in select_source_lang: {str(e)}")
		await send_long_message(
			message=i18n.t("ERROR_GENERAL", language, error=str(e)),
			parse_mode=ParseMode.HTML,
			update=update,
			query_message=query_message,
			context=context
		)
		return ConversationHandler.END

async def select_target_lang(update: Update, context: ContextTypes.DEFAULT_TYPE):
	"""Prompt user to select the target language."""
	update, context, query, user, query_message = await uptodate_query(update, context)
	if not query_message:
		return ConversationHandler.END

	try:
		if update.callback_query:
			await query.answer()
		user_id = user.id if user else 0
		db = Database()
		i18n = I18n()
		language = db.get_user_language(user_id) if user_id else "en"
		transliteration = Transliteration(db, i18n)
		valid_languages = transliteration.valid_languages

		if query.data == "end_conversation":
			return await transliterate_cancel(update, context)

		if not query.data.startswith("source_lang_"):
			logger.debug(f"Ignoring unrelated callback in select_source_lang: {query.data}")
			return SOURCE_LANG

		source_lang = query.data[len("source_lang_"):]
		if source_lang == "guess":
			text = context.user_data["transliterate_text"]
			source_lang = transliteration.guess_source_lang(text)
		context.user_data["source_lang"] = source_lang

		# Create buttons for target languages (excluding source language)
		keyboard = [
			[
				InlineKeyboardButton(i18n.t("LANGUAGE_NAME_AR", language), callback_data="target_lang_arabic")
				if source_lang != "arabic" else None,
				InlineKeyboardButton(i18n.t("LANGUAGE_NAME_EN", language), callback_data="target_lang_english")
				if source_lang != "english" else None
			],
			[
				InlineKeyboardButton(i18n.t("LANGUAGE_NAME_TR", language), callback_data="target_lang_turkish")
				if source_lang != "turkish" else None,
				InlineKeyboardButton(i18n.t("LANGUAGE_NAME_HE", language), callback_data="target_lang_hebrew")
				if source_lang != "hebrew" else None
			],
			[
				InlineKeyboardButton(i18n.t("LANGUAGE_NAME_LA", language), callback_data="target_lang_latin")
				if source_lang != "latin" else None
			],
			[InlineKeyboardButton(i18n.t("CANCEL_BUTTON", language), callback_data="end_conversation")]
		]
		# Remove None values and empty rows
		keyboard = [[btn for btn in row if btn] for row in keyboard if any(row)]
		reply_markup = InlineKeyboardMarkup(keyboard)

		await send_long_message(
			message=i18n.t("TRANSLITERATION_PROMPT_TARGET_LANG", language),
			parse_mode=ParseMode.HTML,
			reply_markup=reply_markup,
			update=update,
			query_message=query_message,
			context=context
		)
		return TARGET_LANG
	except Exception as e:
		logger.error(f"Error in select_target_lang: {str(e)}")
		await send_long_message(
			message=i18n.t("ERROR_GENERAL", language, error=str(e)),
			parse_mode=ParseMode.HTML,
			update=update,
			query_message=query_message,
			context=context
		)
		return ConversationHandler.END

async def show_suggestions(update: Update, context: ContextTypes.DEFAULT_TYPE):
	"""Show transliteration suggestions and store results."""
	update, context, query, user, query_message = await uptodate_query(update, context)
	if not query_message:
		return ConversationHandler.END

	try:
		if update.callback_query:
			await query.answer()
		user_id = user.id if user else 0
		db = Database()
		i18n = I18n()
		language = db.get_user_language(user_id) if user_id else "en"
		transliteration = Transliteration(db, i18n)

		if query.data == "end_conversation":
			return await transliterate_cancel(update, context)

		if not query.data.startswith("target_lang_"):
			logger.debug(f"Ignoring unrelated callback in show_suggestions: {query.data}")
			return TARGET_LANG

		target_lang = query.data[len("target_lang_"):]
		context.user_data["target_lang"] = target_lang
		text = context.user_data["transliterate_text"]
		source_lang = context.user_data["source_lang"]

		# Perform transliteration
		result = transliteration.transliterate(text, target_lang, source_lang)
		primary = result["primary"]
		alternatives = result["alternatives"][:4]  # Limit to 4 alternatives to avoid clutter
		suggestions = [primary] + alternatives

		# Store primary transliteration
		transliteration.store_transliteration(text, source_lang, target_lang, primary, user_id=user_id)

		# Store suggestions in cache
		cache = Cache()
		cache_alternatives = [{"transliterated_name": s, "suffix": transliteration.get_suffix(s, text)} for s in suggestions]
		cache_id = cache.store_alternatives(user_id, source_lang, target_lang, text, cache_alternatives)

		# Format response
		output_lang = {
			'en': 'english', 'tr': 'turkish', 'ar': 'arabic',
			'he': 'hebrew', 'la': 'latin'
		}.get(language, 'english')
		response = transliteration.format_response(primary, target_lang, output_lang, language)

		# AI commentary
		commentary = await get_ai_commentary(response, language)
		if commentary:
			response += "\n\n" + i18n.t("AI_COMMENTARY", language, commentary=commentary)

		# Create buttons for suggestions
		keyboard = [
			[InlineKeyboardButton(
				transliteration.get_suffix(s, text),
				callback_data=f"suggestion_{cache_id}_{i}"
			)] for i, s in enumerate(suggestions)
		]
		keyboard.append([
			InlineKeyboardButton(
				i18n.t("TRANSLITERATION_HISTORY_USAGE", language),
				callback_data="show_history"
			),
			InlineKeyboardButton(
				i18n.t("CALCULATE_ABJAD", language),
				callback_data=f"abjad_text_{urllib.parse.quote(primary)}"
			)
		])
		keyboard.append([
			InlineKeyboardButton(
				i18n.t("CANCEL_BUTTON", language),
				callback_data="end_conversation"
			)
		])
		reply_markup = InlineKeyboardMarkup(keyboard)

		await send_long_message(
			message=response,
			parse_mode=ParseMode.HTML,
			reply_markup=reply_markup,
			update=update,
			query_message=query_message,
			context=context
		)
		return SUGGESTIONS
	except Exception as e:
		logger.error(f"Error in show_suggestions: {str(e)}")
		await send_long_message(
			message=i18n.t("ERROR_INVALID_INPUT", language, error=str(e)),
			parse_mode=ParseMode.HTML,
			update=update,
			query_message=query_message,
			context=context
		)
		return ConversationHandler.END

async def handle_suggestion(update: Update, context: ContextTypes.DEFAULT_TYPE):
	"""Handle selection of a transliteration suggestion."""
	update, context, query, user, query_message = await uptodate_query(update, context)
	if not query_message:
		return ConversationHandler.END

	try:
		if update.callback_query:
			await query.answer()
		user_id = user.id if user else 0
		db = Database()
		i18n = I18n()
		language = db.get_user_language(user_id) if user_id else "en"
		transliteration = Transliteration(db, i18n)

		if query.data == "end_conversation":
			return await transliterate_cancel(update, context)

		if query.data == "show_history":
			return await show_history(update, context)

		if query.data.startswith("abjad_text_"):
			text = urllib.parse.unquote(query.data[len("abjad_text_"):])
			return await abjad_start(update, context, text=text)

		if not query.data.startswith("suggestion_"):
			logger.debug(f"Ignoring unrelated callback in handle_suggestion: {query.data}")
			return SUGGESTIONS

		cache_id, index = query.data[len("suggestion_"):].split("_")
		index = int(index)
		cache = Cache()
		cache_data = cache.get_alternatives(cache_id)
		if not cache_data:
			await send_long_message(
				message=i18n.t("ERROR_GENERAL", language, error="Cache expired or invalid"),
				parse_mode=ParseMode.HTML,
				update=update,
				query_message=query_message,
				context=context
			)
			return ConversationHandler.END

		selected = cache_data["alternatives"][index]["transliterated_name"]
		source_lang = cache_data["source_lang"]
		target_lang = cache_data["target_lang"]
		text = cache_data["source_name"]

		# Update score for selected transliteration
		transliteration.store_transliteration(text, source_lang, target_lang, selected, user_id=user_id)

		output_lang = {
			'en': 'english', 'tr': 'turkish', 'ar': 'arabic',
			'he': 'hebrew', 'la': 'latin'
		}.get(language, 'english')
		response = transliteration.format_response(selected, target_lang, output_lang, language)
		response += "\n\n" + i18n.t("SUGGESTION_SELECTED", language)

		# Offer to continue, view history, or calculate Abjad
		keyboard = [
			[
				InlineKeyboardButton(
					i18n.t("TRANSLITERATE_ANOTHER", language),
					callback_data="transliterate_another"
				),
				InlineKeyboardButton(
					i18n.t("TRANSLITERATION_HISTORY_USAGE", language),
					callback_data="show_history"
				)
			],
			[
				InlineKeyboardButton(
					i18n.t("CALCULATE_ABJAD", language),
					callback_data=f"abjad_text_{urllib.parse.quote(selected)}"
				)
			],
			[InlineKeyboardButton(
				i18n.t("CANCEL_BUTTON", language),
				callback_data="end_conversation"
			)]
		]
		reply_markup = InlineKeyboardMarkup(keyboard)

		# Send new message instead of editing
		await context.bot.send_message(
			chat_id=query_message.chat_id,
			text=response,
			parse_mode=ParseMode.HTML,
			reply_markup=reply_markup
		)
		return SUGGESTIONS
	except Exception as e:
		logger.error(f"Error in handle_suggestion: {str(e)}")
		await send_long_message(
			message=i18n.t("ERROR_GENERAL", language, error=str(e)),
			parse_mode=ParseMode.HTML,
			update=update,
			query_message=query_message,
			context=context
		)
		return ConversationHandler.END

async def show_history(update: Update, context: ContextTypes.DEFAULT_TYPE):
	"""Show the user's transliteration history."""
	update, context, query, user, query_message = await uptodate_query(update, context)
	if not query_message:
		return ConversationHandler.END

	try:
		if update.callback_query:
			await query.answer()
		user_id = user.id if user else 0
		db = Database()
		i18n = I18n()
		language = db.get_user_language(user_id) if user_id else "en"

		history = db.get_transliteration_history(user_id)
		if not history:
			response = i18n.t("TRANSLITERATION_HISTORY_RESULT", language, history="No transliteration history found")
		else:
			history_str = "\n".join([
				f"{item['original']} -> {item['transliterated']} ({item['target_lang']})"
				for item in history[:10]  # Limit to 10 entries
			])
			response = i18n.t("TRANSLITERATION_HISTORY_RESULT", language, history=history_str)

		# Create buttons for history entries with Abjad calculation option
		keyboard = [
			[
				InlineKeyboardButton(
					f"{item['transliterated']} ({item['target_lang']})",
					callback_data=f"history_select_{urllib.parse.quote(item['transliterated'])}"
				)
			] for item in history[:5]  # Limit to 5 buttons to avoid clutter
		]
		keyboard.append([
			InlineKeyboardButton(
				i18n.t("TRANSLITERATE_ANOTHER", language),
				callback_data="transliterate_another"
			)
		])
		keyboard.append([
			InlineKeyboardButton(
				i18n.t("CANCEL_BUTTON", language),
				callback_data="end_conversation"
			)
		])
		reply_markup = InlineKeyboardMarkup(keyboard)

		# Send new message instead of editing
		await context.bot.send_message(
			chat_id=query_message.chat_id,
			text=response,
			parse_mode=ParseMode.MARKDOWN,
			reply_markup=reply_markup
		)
		return HISTORY
	except Exception as e:
		logger.error(f"Error in show_history: {str(e)}")
		await send_long_message(
			message=i18n.t("ERROR_GENERAL", language, error=str(e)),
			parse_mode=ParseMode.MARKDOWN,
			update=update,
			query_message=query_message,
			context=context
		)
		return ConversationHandler.END

async def handle_history_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
	"""Handle selection of a history entry."""
	update, context, query, user, query_message = await uptodate_query(update, context)
	if not query_message:
		return ConversationHandler.END

	try:
		if update.callback_query:
			await query.answer()
		user_id = user.id if user else 0
		db = Database()
		i18n = I18n()
		language = db.get_user_language(user_id) if user_id else "en"

		if query.data == "end_conversation":
			return await transliterate_cancel(update, context)

		if query.data == "transliterate_another":
			return await transliterate_another(update, context)

		if query.data.startswith("abjad_text_"):
			text = urllib.parse.unquote(query.data[len("abjad_text_"):])
			return await abjad_start(update, context, text=text)

		if not query.data.startswith("history_select_"):
			logger.debug(f"Ignoring unrelated callback in handle_history_selection: {query.data}")
			return HISTORY

		selected = urllib.parse.unquote(query.data[len("history_select_"):])
		response = i18n.t("SUGGESTION_SELECTED", language, result=selected)

		# Offer to calculate Abjad, transliterate another, or cancel
		keyboard = [
			[
				InlineKeyboardButton(
					i18n.t("CALCULATE_ABJAD", language),
					callback_data=f"abjad_text_{urllib.parse.quote(selected)}"
				)
			],
			[
				InlineKeyboardButton(
					i18n.t("TRANSLITERATE_ANOTHER", language),
					callback_data="transliterate_another"
				)
			],
			[InlineKeyboardButton(
				i18n.t("CANCEL_BUTTON", language),
				callback_data="end_conversation"
			)]
		]
		reply_markup = InlineKeyboardMarkup(keyboard)

		# Send new message instead of editing
		await context.bot.send_message(
			chat_id=query_message.chat_id,
			text=response,
			parse_mode=ParseMode.HTML,
			reply_markup=reply_markup
		)
		return HISTORY
	except Exception as e:
		logger.error(f"Error in handle_history_selection: {str(e)}")
		await send_long_message(
			message=i18n.t("ERROR_GENERAL", language, error=str(e)),
			parse_mode=ParseMode.HTML,
			update=update,
			query_message=query_message,
			context=context
		)
		return ConversationHandler.END

async def transliterate_another(update: Update, context: ContextTypes.DEFAULT_TYPE):
	"""Restart the transliteration process."""
	update, context, query, user, query_message = await uptodate_query(update, context)
	if not query_message:
		return ConversationHandler.END

	try:
		if update.callback_query:
			await query.answer()
		user_id = user.id if user else 0
		db = Database()
		i18n = I18n()
		language = db.get_user_language(user_id) if user_id else "en"

		# Clear previous data
		context.user_data.clear()

		await send_long_message(
			message=i18n.t("TRANSLITERATION_PROMPT_TEXT", language),
			parse_mode=ParseMode.HTML,
			update=update,
			query_message=query_message,
			context=context
		)
		return TEXT
	except Exception as e:
		logger.error(f"Error in transliterate_another: {str(e)}")
		await send_long_message(
			message=i18n.t("ERROR_GENERAL", language, error=str(e)),
			parse_mode=ParseMode.HTML,
			update=update,
			query_message=query_message,
			context=context
		)
		return ConversationHandler.END

async def transliterate_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
	"""Cancel the transliteration conversation."""
	update, context, query, user, query_message = await uptodate_query(update, context)
	if not query_message:
		return ConversationHandler.END

	logger.info(f"Cancelling /transliterate for user {user.id if user else 'unknown'}")
	try:
		if update.callback_query:
			await query.answer()
		user_id = user.id if user else 0
		db = Database()
		i18n = I18n()
		language = db.get_user_language(user_id) if user_id else "en"

		await send_long_message(
			message=i18n.t("TRANSLITERATION_CANCEL", language),
			parse_mode=ParseMode.HTML,
			update=update,
			query_message=query_message,
			context=context
		)
		context.user_data.clear()
		return ConversationHandler.END
	except Exception as e:
		logger.error(f"Error in transliterate_cancel: {str(e)}")
		await send_long_message(
			message=i18n.t("ERROR_GENERAL", language, error=str(e)),
			parse_mode=ParseMode.HTML,
			update=update,
			query_message=query_message,
			context=context
		)
		return ConversationHandler.END

def get_transliterate_conversation_handler():
	"""Return the conversation handler for /transliterate."""
	try:
		handler = ConversationHandler(
			entry_points=[CommandHandler("transliterate", transliterate_start)],
			states={
				TEXT: [MessageHandler(filters.Text() & ~filters.COMMAND, transliterate_text)],
				SOURCE_LANG: [CallbackQueryHandler(select_target_lang)],
				TARGET_LANG: [CallbackQueryHandler(show_suggestions)],
				SUGGESTIONS: [CallbackQueryHandler(handle_suggestion)],
				HISTORY: [CallbackQueryHandler(handle_history_selection)]
			},
			fallbacks=[CommandHandler("cancel", transliterate_cancel),
					   MessageHandler(filters.Regex(r'^/.*'), timeout)]
		)
		logger.info("Transliterate conversation handler initialized successfully")
		return handler
	except Exception as e:
		logger.error(f"Failed to initialize transliterate conversation handler: {str(e)}")
		raise