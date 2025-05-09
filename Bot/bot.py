import logging
import re
import asyncio
import os
import json
import requests
import aiohttp
from Bot.cache import Cache
from Bot.config import Config
from Bot.database import Database
from Bot.i18n import I18n
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, User
from telegram.ext import (
	Application, ExtBot, ConversationHandler, CommandHandler, MessageHandler,
	ContextTypes, CallbackContext, CallbackQueryHandler, filters,
	TypeHandler,
)
from telegram.constants import ParseMode
from telegram.error import BadRequest
from .Abjad import Abjad
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
config = Config()

def run_bot():
	raise NotImplementedError("Bot now runs via webhooks in admin_panel.py")