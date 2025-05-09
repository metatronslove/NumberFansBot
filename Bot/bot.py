import logging
import re
import asyncio
import os
from Bot.config import Config
from Bot.database import Database
from Bot.i18n import I18n
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
	Application, ExtBot, ConversationHandler, CommandHandler, MessageHandler,
	ContextTypes, CallbackContext, CallbackQueryHandler, filters,
	TypeHandler,
)
from telegram.constants import ParseMode
from telegram.error import BadRequest
from Bot.Abjad import Abjad
from Bot.utils import register_user_if_not_exists, get_warning_description, get_ai_commentary, timeout, handle_credits
from urllib.parse import urlparse
from pathlib import Path
from datetime import datetime
from .Commands.UserCommands import (
	start, help, language, numerology, convert_numbers, magic_square,
	transliterate, name, cancel, settings, credits
)
from .Commands.UserCommands.abjad import get_abjad_conversation_handler
from .Commands.UserCommands.bastet import get_bastet_conversation_handler
from .Commands.UserCommands.huddam import get_huddam_conversation_handler
from .Commands.UserCommands.unsur import get_unsur_conversation_handler
from .Commands.UserCommands.nutket import nutket_handle
from .Commands.UserCommands.payment import payment_handle, get_payment_handlers
from .Commands.SystemCommands.callback_query import set_language_handle, handle_callback_query

logger = logging.getLogger(__name__)

async def check_credits(update, context):
	if not update.message:
		return True  # Allow callback queries
	user_id = update.message.from_user.id
	command = update.message.text.split()[0].lower() if update.message.text else ""
	db = Database()
	i18n = I18n()
	language = db.get_user_language(user_id)

	# Skip credit check for essential commands
	if command in ["/start", "/help", "/payment", "/credits"]:
		return True

	# Check blacklist
	if db.is_blacklisted(user_id):
		await update.message.reply_text(
			i18n.t("USER_BLACKLISTED", language),
			parse_mode=filters.ParseMode.HTML
		)
		return False

	# Check credits
	credits = db.get_user_credits(user_id)
	if credits <= 0 and not db.is_beta_tester(user_id) and not db.is_teskilat(user_id):
		await update.message.reply_text(
			i18n.t("NO_CREDITS", language),
			parse_mode=filters.ParseMode.HTML
		)
		return False

	# Decrement credits if not beta tester
	if not db.is_beta_tester(user_id) or not db.is_teskilat(user_id):
		db.decrement_credits(user_id)

	return True

def run_bot():
	raise NotImplementedError("Bot now runs via webhooks in admin_panel.py")