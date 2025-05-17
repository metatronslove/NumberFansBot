import logging
import re
import asyncio
import os
import json
import requests
import aiohttp
import urllib
from Bot.cache import Cache
from Bot.config import Config
from Bot.database import Database
from Bot.Helpers.i18n import I18n
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, User, Message
from telegram.ext import (
	Application, ExtBot, ConversationHandler, CommandHandler, MessageHandler,
	ContextTypes, CallbackContext, CallbackQueryHandler, filters,
	TypeHandler,
)
from telegram.constants import ParseMode
from telegram.error import BadRequest
from .Helpers.Abjad import Abjad
from pathlib import Path
from datetime import datetime

logger = logging.getLogger(__name__)
config = Config()

async def uptodate_query(update: Update = None, context: ContextTypes.DEFAULT_TYPE = None):
	"""
	Process the update object to extract query, user, and query_message.

	Args:
		update: The Telegram update object.
		context: Telegram context object (optional, defaults to ContextTypes.DEFAULT_TYPE).

	Returns:
		tuple: (update, context, query, user, query_message) or (None, None, None, None, None) if invalid update.
	"""
	if not update:
		logger.error("No update provided")
		return None, None, None, None, None

	context = context or ContextTypes.DEFAULT_TYPE()

	# Determine if this is a message, callback query, channel post, or edited channel post
	if update.message:
		query = update.message
		user = query.from_user
		query_message = query
	elif update.callback_query:
		query = update.callback_query
		user = query.from_user
		query_message = query.message
	elif update.channel_post:
		query = update.channel_post
		user = None
		query_message = query
	elif update.edited_channel_post:
		query = update.edited_channel_post
		user = None
		query_message = query
	else:
		logger.error("Invalid update type received")
		return None, None, None, None, None

	return update, context, query, user, query_message

async def send_long_message(
	message: str,
	parse_mode: str = None,
	reply_markup=None,
	update: Update = None,
	query_message: Message = None,
	context: ContextTypes.DEFAULT_TYPE = None,
	force_new_message: bool = False
) -> None:
	"""
	Splits long messages into chunks of 4096 characters or less and sends them sequentially.
	Supports editing existing messages for callback queries if possible.

	Args:
		message: The message text to send.
		parse_mode: The parse mode for the message (e.g., ParseMode.MARKDOWN, ParseMode.HTML).
		reply_markup: Inline keyboard or other markup (optional).
		update: The Telegram update object (optional, used to derive chat, context, or user info).
		query_message: The Message object to send or edit (e.g., update.message or update.callback_query.message).
		context: Telegram context object (optional, for error reporting).
	"""
	MAX_MESSAGE_LENGTH = 4096
	messages = []

	# Derive chat_id and context
	chat_id = None
	if query_message:
		chat_id = query_message.chat_id
	elif update:
		if update.message:
			chat_id = update.message.chat_id
			query_message = query_message or update.message
		elif update.callback_query:
			chat_id = update.callback_query.message.chat_id
			query_message = query_message or update.callback_query.message
		elif update.channel_post:
			chat_id = update.channel_post.chat_id
			query_message = query_message or update.channel_post
		elif update.edited_channel_post:
			chat_id = update.edited_channel_post.chat_id
			query_message = query_message or update.edited_channel_post
		else:
			logger.error("Invalid update type received")
			return
	else:
		logger.error("No valid chat derived from update or query_message")
		return

	if not chat_id:
		logger.error("No valid chat_id provided or derived")
		return

	context = context or ContextTypes.DEFAULT_TYPE()

	# Split the message into chunks of 4096 characters or less
	while message:
		if len(message) <= MAX_MESSAGE_LENGTH:
			messages.append(message)
			break
		# Find the nearest newline or space to split
		split_index = message.rfind('\n', 0, MAX_MESSAGE_LENGTH)
		if split_index == -1:
			split_index = message.rfind(' ', 0, MAX_MESSAGE_LENGTH)
		if split_index == -1:
			split_index = MAX_MESSAGE_LENGTH
		messages.append(message[:split_index])
		message = message[split_index:].lstrip()

	# Send or edit messages
	for i, msg in enumerate(messages):
		markup = reply_markup if i == len(messages) - 1 else None
		try:
			# If this is a callback query and the first chunk, try editing the existing message
			if not force_new_message and i == 0 and update and update.callback_query and query_message:
				try:
					await query_message.edit_text(
						text=msg,
						parse_mode=parse_mode,
						reply_markup=markup
					)
					continue  # Skip sending a new message for this chunk
				except BadRequest as e:
					if "Message is too long" not in str(e):
						logger.warning(f"Failed to edit message: {e}")
						# Continue to send as new message if edit fails for other reasons
			# Send as a new message using context.bot
			await context.bot.send_message(
				chat_id=chat_id,
				text=msg,
				parse_mode=parse_mode,
				reply_markup=markup
			)
		except BadRequest as e:
			logger.error(f"Error sending message chunk: {e}")
			db = Database()
			i18n = I18n()
			user_id = update.effective_user.id if update and update.effective_user else 0
			language = db.get_user_language(user_id) if user_id else "en"
			# Send error message using context.bot, avoid recursion
			try:
				await context.bot.send_message(
					chat_id=chat_id,
					text=i18n.t("ERROR_GENERAL", language, error=str(e)),
					parse_mode=ParseMode.HTML
				)
			except Exception as send_error:
				logger.error(f"Failed to send error message: {send_error}")

async def timeout(update: Update, context: ContextTypes.DEFAULT_TYPE, lang: str = "en"):
	update, context, query, user, query_message = await uptodate_query(update, context)
	if not query_message:
		return

	user_id = user.id if user else 0
	db = Database()
	i18n = I18n()
	lang = db.get_user_language(user_id) if user_id else "en"
	await send_long_message(
		message=i18n.t("TIMEOUT_RETRY", lang),
		parse_mode=ParseMode.HTML,
		update=update,
		query_message=query_message,
		context=context
	)
	context.user_data.clear()
	return ConversationHandler.END

async def get_ai_commentary(response: str, lang: str) -> str:
	i18n = I18n()
	prompt = i18n.t("AI_PROMPT", lang, response=response)
	try:
		headers = {"Authorization": f"Bearer {config.ai_access_token}"}
		payload = {
			"inputs": prompt,
			"parameters": {"max_length": 69, "temperature": 0.8}
		}
		async with aiohttp.ClientSession() as session:
			async with session.post(config.ai_model_url, headers=headers, json=payload) as api_response:
				if api_response.status == 200:
					data = await api_response.json()
					generated_text = data[0]["generated_text"]
					logger.debug(f"Raw generated text: {generated_text}")
					cleaned_text = re.sub(
						rf"^{re.escape(prompt)}(?:\s*\[\/INST\])?\s*",
						"",
						generated_text,
						flags=re.DOTALL
					).strip()
					logger.debug(f"Cleaned text: {cleaned_text}")
					return cleaned_text
				else:
					logger.error(f"Hugging Face API error: Status code {api_response.status}, Response: {await api_response.text()}")
					return ""
	except KeyError as e:
		logger.error(f"AI commentary error: Invalid response format, missing key {e}")
		return ""
	except Exception as e:
		logger.error(f"AI commentary error: {str(e)}")
		return ""

async def register_user_if_not_exists(update: Update, context: ContextTypes.DEFAULT_TYPE, user: User, language: str | None = None) -> None:
	"""
	Register a new user in the database if they don't already exist.

	Args:
		update: The Telegram update object.
		context: The context object for the Telegram bot.
		user: The Telegram user object to register.
		language: The language code to set for the user (optional, defaults to 'en').
	"""
	if not user or not hasattr(user, 'id'):
		return  # Silently skip if user is invalid

	db = Database()
	if not db.check_if_user_exists(user.id):
		db.add_new_user(
			user_id=user.id,
			chat_id=update.message.chat_id if update.message else update.channel_post.chat_id if update.channel_post else 0,
			username=user.username or "",
			first_name=user.first_name or "",
			last_name=user.last_name or "",
			language_code=language or "en",
			is_beta_tester=False,
			user_credits=100
		)

async def chat_member_update(update: Update, context: ContextTypes.DEFAULT_TYPE):
	if update.my_chat_member:
		chat = update.my_chat_member.chat
		new_status = update.my_chat_member.new_chat_member.status
		if chat.type in ["group", "supergroup", "channel"]:
			db = Database()  # Your database class
			db.add_group(chat.id, chat.title, datetime.now())

			# Fetch detailed chat info
			full_chat = await context.bot.get_chat(chat.id)
			is_public = bool(full_chat.username)
			member_count = getattr(full_chat, 'member_count', None)

			creator_id = None
			admins = []
			if new_status in ["administrator", "creator"]:
				admin_list = await context.bot.get_chat_administrators(chat.id)
				for admin in admin_list:
					if admin.status == "creator":
						creator_id = admin.user.id
					admins.append(admin.user.id)

			# Update database
			db.update_group_details(chat.id, {
				'type': chat.type,
				'is_public': is_public,
				'member_count': member_count,
				'creator_id': creator_id,
				'admins': json.dumps(admins) if admins else None
			})

async def chosen_inline_result(update: Update, context: ContextTypes.DEFAULT_TYPE):
	result = update.chosen_inline_result
	if result.inline_message_id:  # Only store if sent to a chat
		if 'inline_usages' not in context.bot_data:
			context.bot_data['inline_usages'] = {}
		context.bot_data['inline_usages'][result.inline_message_id] = {
			'user_id': result.from_user.id,
			'query': result.query
		}

async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
	message = update.message
	if message.inline_message_id:
		inline_message_id = message.inline_message_id
		chat_id = message.chat.id
		db = Database()
		if 'inline_usages' in context.bot_data and inline_message_id in context.bot_data['inline_usages']:
			usage = context.bot_data['inline_usages'].pop(inline_message_id)
			db.log_inline_usage(usage['user_id'], chat_id, usage['query'])
			if db.is_group_blacklisted(chat_id):
				await context.bot.edit_message_text(
					inline_message_id=inline_message_id,
					text="This bot is not allowed in this group."
				)

def log_inline_usage(self, user_id: int, chat_id: int, query: str):
	query = "INSERT INTO inline_usage (user_id, chat_id, query, timestamp) VALUES (%s, %s, %s, %s)"
	self.cursor.execute(query, (user_id, chat_id, query, datetime.now()))
	self.conn.commit()

async def get_warning_description(value, language):
	"""
	Check if the value exists in warningNumbers.json and return the description for the given language.
	Args:
		value: The number value to check (int or str).
		language: The active language code (e.g., 'en', 'tr', 'ar', 'he', 'la').
	Returns:
		str: The description in the specified language, or empty string if no match.
	"""
	try:
		config_dir = Path(__file__).parent / 'Config'
		warning_file = config_dir / 'warningNumbers.json'
		with open(warning_file, 'r', encoding='utf-8') as f:
			warnings = json.load(f)

		value_str = str(value)
		for entry in warnings:
			if entry.get('value') == value_str:
				description_key = f"description_{language}"
				return entry.get(description_key, "")
		return ""
	except Exception as e:
		logger.error(f"Error reading warningNumbers.json: {str(e)}")
		return ""

async def handle_credits(update: Update, context: ContextTypes.DEFAULT_TYPE):
	# Credit check
	update, context, query, user, query_message = await uptodate_query(update, context)
	if not query_message:
		return ConversationHandler.END

	if not await check_credits(update, context):
		db = Database()
		i18n = I18n()
		user_id = user.id if user else 0
		language = db.get_user_language(user_id) if user_id else "en"
		await send_long_message(
			message=i18n.t("NO_CREDITS", language),
			parse_mode=ParseMode.HTML,
			update=update,
			query_message=query_message,
			context=context
		)
		return ConversationHandler.END
	return

async def check_credits(update, context):
	update, context, query, user, query_message = await uptodate_query(update, context)
	if not query_message or not user:
		return True  # Allow callback queries or channel posts

	user_id = user.id
	command = query.text.split()[0].lower() if hasattr(query, 'text') and query.text else ""
	db = Database()
	i18n = I18n()
	language = db.get_user_language(user_id)

	# Skip credit check for essential commands
	if command in ["/start", "/help", "/payment", "/credits"]:
		return True

	# Check blacklist
	if db.is_blacklisted(user_id):
		await send_long_message(
			message=i18n.t("USER_BLACKLISTED", language),
			parse_mode=ParseMode.HTML,
			update=update,
			query_message=query_message,
			context=context
		)
		return False

	# Check credits
	credits = db.get_user_credits(user_id)
	if credits <= 0:
		if not db.is_beta_tester(user_id):
			if not db.is_teskilat(user_id):
				await send_long_message(
					message=i18n.t("NO_CREDITS", language),
					parse_mode=ParseMode.HTML,
					update=update,
					query_message=query_message,
					context=context
				)
				return False

	# Decrement credits if not beta tester
	if not db.is_beta_tester(user_id):
		if not db.is_teskilat(user_id):
			db.decrement_credits(user_id)

	return True

def run_bot():
	raise NotImplementedError("Bot now runs via webhooks in admin_panel.py")