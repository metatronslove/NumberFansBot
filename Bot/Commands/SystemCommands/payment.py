import os
import logging
import re
from Bot.config import Config
from Bot.database import Database
from Bot.Helpers.i18n import I18n
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, LabeledPrice
from telegram.ext import (
	Application, ExtBot, ConversationHandler, CommandHandler, MessageHandler,
	ContextTypes, CallbackContext, CallbackQueryHandler, filters,
	TypeHandler, PreCheckoutQueryHandler
)
from telegram.constants import ParseMode
from telegram.error import BadRequest
import asyncio
from Bot.utils import (
	register_user_if_not_exists, get_warning_description, get_ai_commentary,
	timeout, handle_credits, send_long_message, uptodate_query
)
from urllib.parse import urlparse
from pathlib import Path
from datetime import datetime
from .language import language_handle

logger = logging.getLogger(__name__)

async def payment_handle(update: Update, context: ContextTypes.DEFAULT_TYPE)	:
	update, context, query, user, query_message = await uptodate_query(update, context)
	if not query_message:
		return

	await register_user_if_not_exists(update, context, user)
	user_id = user.id
	db = Database()
	config = Config()
	i18n = I18n()
	language = db.get_user_language(user_id)
	# await handle_credits(update, context) because payment MUST NOT decrement credits
	db.set_user_attribute(user_id, "last_interaction", datetime.now())
	db.increment_command_usage("payment", user_id, query.chat_id)

	# Check blacklist
	if db.is_blacklisted(user_id):
		await send_long_message(
			i18n.t("PAYMENT_BLACKLISTED", language),
			parse_mode=ParseMode.HTML,
			update=update,
			query_message=query_message,
			context=context,
			force_new_message=True
		)
		return

	# Check for Easter egg phrase
	easter_egg_phrase = config.teskilat_creditentials	 # Hardcoded for security
	args = context.args
	if args and " ".join(args).lower() == easter_egg_phrase.lower():
		if db.is_teskilat(user_id):
			reply_text = i18n.t("TESKILAT_ALREADY_ACTIVE", language)
		else:
			if db.set_teskilat(user_id, True):
				reply_text = i18n.t("TESKILAT_ACTIVATED", language)
			else:
				reply_text = i18n.t("TESKILAT_ACTIVATION_FAILED", language)
		await send_long_message(reply_text, parse_mode=ParseMode.HTML, update=update, query_message=query_message,	context=context)
		return

	# Existing payment logic (placeholder, replace with actual implementation)
	reply_text = i18n.t("PAYMENT_INSTRUCTIONS", language)
	await send_long_message(reply_text, parse_mode=ParseMode.HTML, update=update, query_message=query_message,	context=context)

	# Check if payment provider token is set
	if not Config().payment_provider_token:
		await send_long_message(
			i18n.t("PAYMENT_MISSING_PROVIDER_TOKEN", language),
			parse_mode=ParseMode.HTML,
			update=update,
			query_message=query_message,
			context=context,
			force_new_message=True
		)
		return

	# Check if user is a beta tester
	if db.is_beta_tester(user_id):
		await send_long_message(
			i18n.t("PAYMENT_BETA_TESTER", language),
			parse_mode=ParseMode.HTML,
			update=update,
			query_message=query_message,
			context=context,
			force_new_message=True
		)
		return

	# Offer credit purchase
	keyboard = [[InlineKeyboardButton(
		i18n.t("PAYMENT_PRODUCTS_CREDIT_PRODUCT_NAME", language),
		callback_data="payment_select_credit_500"
	)]]
	reply_markup = InlineKeyboardMarkup(keyboard)

	await send_long_message(
		i18n.t("PAYMENT_SELECT_PRODUCT", language),
		parse_mode=ParseMode.HTML,
		reply_markup=reply_markup,
		update=update,
		query_message=query_message,
		context=context,
		force_new_message=True
	)

async def handle_payment_callback(update: Update, context: ContextTypes.DEFAULT_TYPE)	:
	update, context, query, user, query_message = await uptodate_query(update, context)
	if not query_message:
		return

	user_id = user.id
	db = Database()
	i18n = I18n()
	language = db.get_user_language(user_id)

	await query.answer()

	if query.data == "payment_select_credit_500":
		if db.is_blacklisted(user_id):
			await send_long_message(
				i18n.t("PAYMENT_BLACKLISTED", language),
				parse_mode=ParseMode.HTML,
				update=update,
				query_message=query_message,
				context=context,
				force_new_message=True
			)
			return

		if not Config().payment_provider_token:
			await send_long_message(
				i18n.t("PAYMENT_MISSING_PROVIDER_TOKEN", language),
				parse_mode=ParseMode.HTML,
				update=update,
				query_message=query_message,
				context=context,
				force_new_message=True
			)
			return

		try:
			await send_long_message(
				i18n.t("PAYMENT_INVOICE_TITLE", language),
				parse_mode=ParseMode.HTML,
				update=update,
				query_message=query_message,
				context=context,
				force_new_message=True
			)

			await context.bot.send_invoice(
				chat_id=query.message.chat_id,
				title=i18n.t("PAYMENT_PRODUCTS_CREDIT_PRODUCT_NAME", language),
				description=i18n.t("PAYMENT_PRODUCTS_CREDIT_PRODUCT_DESCRIPTION", language),
				payload="credit_500",
				provider_token=Config().payment_provider_token,
				currency="USD",
				prices=[LabeledPrice("500 Credits", 200)],	# $2.00
				start_parameter="credit-purchase"
			)
		except Exception as e:
			logger.error(f"Payment invoice error: {str(e)}")
			await send_long_message(
				i18n.t("PAYMENT_FAILED", language),
				parse_mode=ParseMode.HTML,
				update=update,
				query_message=query_message,
				context=context
			)

async def handle_pre_checkout(update: Update, context: ContextTypes.DEFAULT_TYPE)	:
	query = update.pre_checkout_query
	user_id = user.id
	db = Database()
	i18n = I18n()
	language = db.get_user_language(user_id)

	if db.is_blacklisted(user_id):
		await query.answer(ok=False, error_message=i18n.t("PAYMENT_BLACKLISTED", language))
		return

	try:
		await query.answer(ok=True)
	except Exception as e:
		logger.error(f"Pre-checkout error: {str(e)}")
		await query.answer(ok=False, error_message=i18n.t("PAYMENT_FAILED", language))

async def handle_successful_payment(update: Update, context: ContextTypes.DEFAULT_TYPE)	:
	user_id = update.message.from_user.id
	payment = update.message.successful_payment
	db = Database()
	i18n = I18n()
	language = db.get_user_language(user_id)

	if payment.invoice_payload == "credit_500":
		db.add_credits(user_id, 500)
		payment.credits_added = 500
		db.save_order(user_id, payment)
		db.log_user_activity(user_id, "purchase_credits", {"amount": 500, "cost": 2.00, "currency": "USD"})

		await send_long_message(
			i18n.t("PAYMENT_THANK_YOU", language, product="500 Credits", amount="2.00", currency="USD"),
			parse_mode=ParseMode.HTML,
			update=update,
			query_message=query_message,
			context=context,
			force_new_message=True
		)
	else:
		await send_long_message(
			i18n.t("PAYMENT_FAILED", language),
			parse_mode=ParseMode.HTML,
			update=update,
			query_message=query_message,
			context=context,
			force_new_message=True
		)

def get_payment_handlers():
	return [
		PreCheckoutQueryHandler(handle_pre_checkout),
		MessageHandler(filters.SUCCESSFUL_PAYMENT, handle_successful_payment)
	]