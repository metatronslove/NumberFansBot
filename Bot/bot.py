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
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, User
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
from .Commands.UserCommands.abjad import get_abjad_conversation_handler
from .Commands.UserCommands.bastet import get_bastet_conversation_handler
from .Commands.UserCommands.huddam import get_huddam_conversation_handler
from .Commands.UserCommands.unsur import get_unsur_conversation_handler
from .Commands.UserCommands.transliterate import get_transliterate_conversation_handler
from .Commands.UserCommands import (
	numerology, convert_numbers, magic_square, nutket
)
from .Commands.SystemCommands.payment import (
	payment_handle, handle_pre_checkout, handle_successful_payment
)
from .Commands.SystemCommands import (
	start, help, language, cancel, settings, credits, callback_query
)

logger = logging.getLogger(__name__)
config = Config()

def run_bot():
	raise NotImplementedError("Bot now runs via webhooks in admin_panel.py")