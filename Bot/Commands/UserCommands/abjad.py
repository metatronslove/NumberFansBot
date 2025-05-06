import logging
import re
from Bot.config import Config
from Bot.database import Database
from Bot.i18n import I18n
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
	Application, CommandHandler, MessageHandler, CallbackQueryHandler,
	ConversationHandler, filters, ContextTypes
)
from telegram.constants import ParseMode
from telegram.error import BadRequest
from Bot.Abjad import Abjad
from Bot.utils import register_user_if_not_exists, get_warning_description, get_ai_commentary
from datetime import datetime

logger = logging.getLogger(__name__)

ALPHABET_ORDER, ABJAD_TYPE, SHADDA, DETAIL = range(4)

async def abjad_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
	logger.info(f"Starting /abjad for user {update.effective_user.id}")
	try:
		user = update.message.from_user
		await register_user_if_not_exists(update, context, user)
		user_id = user.id
		db = Database()
		i18n = I18n()
		language = db.get_user_language(user_id)

		args = context.args
		if not args:
			await update.message.reply_text(
				i18n.t("ABJAD_USAGE", language),
				parse_mode=ParseMode.MARKDOWN
			)
			return ConversationHandler.END

		text = " ".join(args)
		context.user_data["abjad_text"] = text

		is_arabic = bool(re.search(r"[\u0600-\u06FF]", text))
		keyboard = [
			[InlineKeyboardButton(i18n.t("ALPHABET_ORDER_ABJADI", language), callback_data="abjad_alphabet_0-4")],
			[InlineKeyboardButton(i18n.t("ALPHABET_ORDER_MAGHRIBI", language), callback_data="abjad_alphabet_6-10")],
			[InlineKeyboardButton(i18n.t("ALPHABET_ORDER_QURANIC", language), callback_data="abjad_alphabet_11-15")],
			[InlineKeyboardButton(i18n.t("ALPHABET_ORDER_HIJA", language), callback_data="abjad_alphabet_16-20")],
			[InlineKeyboardButton(i18n.t("ALPHABET_ORDER_MAGHRIBI_HIJA", language), callback_data="abjad_alphabet_21-25")],
			[InlineKeyboardButton(i18n.t("ALPHABET_ORDER_IKLEELS", language), callback_data="abjad_alphabet_26-30")],
			[InlineKeyboardButton(i18n.t("ALPHABET_ORDER_SHAMSE_ABJADI", language), callback_data="abjad_alphabet_31-35")],
			[InlineKeyboardButton(i18n.t("ALPHABET_ORDER_HEBREW", language), callback_data="abjad_alphabet_HE")],
			[InlineKeyboardButton(i18n.t("ALPHABET_ORDER_TURKISH", language), callback_data="abjad_alphabet_TR")],
			[InlineKeyboardButton(i18n.t("ALPHABET_ORDER_ENGLISH", language), callback_data="abjad_alphabet_EN")],
			[InlineKeyboardButton(i18n.t("ALPHABET_ORDER_LATIN", language), callback_data="abjad_alphabet_LA")],
		]
		reply_markup = InlineKeyboardMarkup(keyboard)
		await update.message.reply_text(
			i18n.t("ABJAD_PROMPT_ALPHABET", language),
			reply_markup=reply_markup
		)
		context.user_data["is_arabic"] = is_arabic
		return ALPHABET_ORDER
	except Exception as e:
		logger.error(f"Error in abjad_start: {str(e)}")
		await update.message.reply_text(
			i18n.t("ERROR_GENERAL", language, error=str(e)),
			parse_mode=ParseMode.MARKDOWN
		)
		return ConversationHandler.END

async def abjad_alphabet_order(update: Update, context: ContextTypes.DEFAULT_TYPE):
	logger.debug(f"Processing abjad_alphabet_order for user {update.effective_user.id}")
	try:
		query = update.callback_query
		await query.answer()
		user_id = query.from_user.id
		db = Database()
		i18n = I18n()
		language = db.get_user_language(user_id)

		if not query.data.startswith("abjad_alphabet_"):
			logger.debug(f"Ignoring unrelated callback in abjad_alphabet_order: {query.data}")
			return ALPHABET_ORDER
		alphabet_order = query.data.split("abjad_alphabet_")[0]
		context.user_data["alphabet_order"] = alphabet_order

		keyboard = [
			[InlineKeyboardButton(i18n.t("ABJAD_TYPE_ASGHAR", language), callback_data="abjad_type_-1")],
			[InlineKeyboardButton(i18n.t("ABJAD_TYPE_SAGHIR", language), callback_data="abjad_type_0")],
			[InlineKeyboardButton(i18n.t("ABJAD_TYPE_KEBEER", language), callback_data="abjad_type_+1")],
			[InlineKeyboardButton(i18n.t("ABJAD_TYPE_AKBAR", language), callback_data="abjad_type_+2")],
			[InlineKeyboardButton(i18n.t("ABJAD_TYPE_SAGHIR_PLUS_QUANTITY", language), callback_data="abjad_type_+3")],
			[InlineKeyboardButton(i18n.t("ABJAD_TYPE_LETTER_QUANTITY", language), callback_data="abjad_type_5")],
		]
		reply_markup = InlineKeyboardMarkup(keyboard)
		await query.message.reply_text(
			i18n.t("ABJAD_PROMPT_TYPE", language),
			reply_markup=reply_markup
		)
		return ABJAD_TYPE
	except Exception as e:
		logger.error(f"Error in abjad_alphabet_order: {str(e)}")
		await query.message.reply_text(
			i18n.t("ERROR_GENERAL", language, error=str(e)),
			parse_mode=ParseMode.MARKDOWN
		)
		return ConversationHandler.END

async def abjad_type(update: Update, context: ContextTypes.DEFAULT_TYPE):
	logger.debug(f"Processing abjad_type for user {update.effective_user.id}")
	try:
		query = update.callback_query
		await query.answer()
		user_id = query.from_user.id
		db = Database()
		i18n = I18n()
		language = db.get_user_language(user_id)

		if not query.data.startswith("abjad_type_"):
			logger.debug(f"Ignoring unrelated callback in abjad_type: {query.data}")
			return ABJAD_TYPE
		abjad_type = query.data.split("abjad_type_")[0]
		context.user_data["abjad_type"] = abjad_type

		if context.user_data.get("is_arabic"):
			keyboard = [
				[InlineKeyboardButton(i18n.t("SHADDA_USE_ONCE", language), callback_data="abjad_shadda_1")],
				[InlineKeyboardButton(i18n.t("SHADDA_USE_TWICE", language), callback_data="abjad_shadda_2")],
			]
			reply_markup = InlineKeyboardMarkup(keyboard)
			await query.message.reply_text(
				i18n.t("ABJAD_PROMPT_SHADDA", language),
				reply_markup=reply_markup
			)
			return SHADDA
		else:
			context.user_data["shadda"] = 1
			return await abjad_shadda(update, context)
	except Exception as e:
		logger.error(f"Error in abjad_type: {str(e)}")
		await query.message.reply_text(
			i18n.t("ERROR_GENERAL", language, error=str(e)),
			parse_mode=ParseMode.MARKDOWN
		)
		return ConversationHandler.END

async def abjad_shadda(update: Update, context: ContextTypes.DEFAULT_TYPE):
	logger.debug(f"Processing abjad_shadda for user {update.effective_user.id}")
	try:
		query = update.callback_query
		if query:
			await query.answer()
		user_id = query.from_user.id if query else update.message.from_user.id
		db = Database()
		i18n = I18n()
		language = db.get_user_language(user_id)

		if query:
			if not query.data.startswith("abjad_shadda_"):
				logger.debug(f"Ignoring unrelated callback in abjad_shadda: {query.data}")
				return SHADDA
			shadda = int(query.data.split("abjad_shadda_")[0])
			context.user_data["shadda"] = shadda
		else:
			shadda = context.user_data.get("shadda", 1)

		keyboard = [
			[InlineKeyboardButton(i18n.t("ABJAD-ONLY-RESULT", language), callback_data="abjad_detail_0")],
			[InlineKeyboardButton(i18n.t("ABJAD-WITH-DETAILS", language), callback_data="abjad_detail_1")],
		]
		reply_markup = InlineKeyboardMarkup(keyboard)
		await (query.message.reply_text if query else update.message.reply_text)(
			i18n.t("ABJAD_PROMPT_DETAIL", language),
			reply_markup=reply_markup
		)
		return DETAIL
	except Exception as e:
		logger.error(f"Error in abjad_shadda: {str(e)}")
		await (query.message.reply_text if query else update.message.reply_text)(
			i18n.t("ERROR_GENERAL", language, error=str(e)),
			parse_mode=ParseMode.MARKDOWN
		)
		return ConversationHandler.END

async def abjad_detail(update: Update, context: ContextTypes.DEFAULT_TYPE):
	logger.debug(f"Processing abjad_detail for user {update.effective_user.id}")
	try:
		query = update.callback_query
		await query.answer()
		user_id = query.from_user.id
		db = Database()
		i18n = I18n()
		language = db.get_user_language(user_id)
		db.set_user_attribute(user_id, "last_interaction", datetime.now())
		db.increment_command_usage("abjad", user_id)

		if not query.data.startswith("abjad_detail_"):
			logger.debug(f"Ignoring unrelated callback in abjad_detail: {query.data}")
			return ConversationHandler.END
		detail = int(query.data.split("abjad_detail_")[0])
		context.user_data["detail"] = detail
		text = context.user_data["abjad_text"]
		alphabet_order = context.user_data["alphabet_order"]
		abjad_type = context.user_data["abjad_type"]
		shadda = context.user_data["shadda"]

		alphabet_map = {
			"0-4": ("arabic", 1),
			"6-10": ("arabic", 7),
			"11-15": ("arabic", 12),
			"16-20": ("arabic", 17),
			"21-25": ("arabic", 22),
			"26-30": ("arabic", 27),
			"31-35": ("arabic", 32),
			"HE": ("hebrew", 1),
			"TR": ("turkish", 1),
			"EN": ("english", 1),
			"LA": ("latin", 1),
		}
		alphabeta, tablebase = alphabet_map[alphabet_order]

		tablebase_adjustments = {
			"-1": -1,
			"0": 0,
			"+1": 1,
			"+2": 2,
			"+3": 3,
			"5": 5,
		}
		tablebase += tablebase_adjustments[abjad_type]

		abjad = Abjad()
		logger.debug(f"Calling abjad.abjad with text={text}, tablebase={tablebase}, shadda={shadda}, detail={detail}, alphabeta={alphabeta}")
		result = abjad.abjad(
			text,
			tablebase,
			int(shadda),
			detail,
			alphabeta,
		)

		if isinstance(result, str) and result.startswith("Error"):
			logger.error(f"Abjad computation failed: {result}")
			await query.message.reply_text(
				i18n.t("ERROR_GENERAL", language, error=result),
				parse_mode=ParseMode.MARKDOWN
			)
			return ConversationHandler.END

		value = result["sum"] if isinstance(result, dict) else result
		detail_json = result.get("details", "") if isinstance(result, dict) and detail == 1 else ""
		details = "".join(f"[{d['char']}={d['value']}]" for d in detail_json) if detail_json else ""

		response = i18n.t("ABJAD_RESULT", language, text=text, value=value)
		if details:
			response += "\n" + i18n.t("ABJAD_DETAILS", language, details=details)

		if detail == 0:
			warning_desc = get_warning_description(value, language)
			if warning_desc:
				response += "\n\n" + i18n.t("WARNING_NUMBER", language, value=value, description=warning_desc)

		commentary = await get_ai_commentary(response, language)
		if commentary:
			response += "\n\n" + i18n.t("AI_COMMENTARY", language, commentary=commentary)

		keyboard = []
		if value >= 15:
			keyboard.append(
				[
					InlineKeyboardButton(
						i18n.t("CREATE_MAGIC_SQUARE", language),
						callback_data=f"magic_square_{value}",
					)
				]
			)
			keyboard.append(
				[
					InlineKeyboardButton(
						i18n.t("CREATE_INDIAN_MAGIC_SQUARE", language),
						callback_data=f"indian_square_{value}",
					)
				]
			)
		keyboard.append(
			[
				InlineKeyboardButton(
					i18n.t("SPELL_NUMBER", language),
					callback_data=f"nutket_{value}_{alphabeta}",
				)
			]
		)
		if details:
			keyboard.append(
				[
					InlineKeyboardButton(
						i18n.t("SHOW_DETAILS", language),
						callback_data=f"abjad_details_{user_id}",
					)
				]
			)
		reply_markup = InlineKeyboardMarkup(keyboard)

		await query.message.reply_text(
			response,
			parse_mode=ParseMode.MARKDOWN,
			reply_markup=reply_markup,
		)
		context.user_data["abjad_result"] = result

		context.user_data.clear()
		return ConversationHandler.END

	except ValueError as e:
		logger.error(f"Abjad detail error: Invalid callback data {query.data}, {str(e)}")
		await query.message.reply_text(
			i18n.t("ERROR_GENERAL", language, error=str(e)),
			parse_mode=ParseMode.MARKDOWN
		)
		context.user_data.clear()
		return ConversationHandler.END
	except BadRequest as e:
		logger.error(f"Telegram BadRequest: {str(e)}")
		if "Query is too old" in str(e):
			await query.message.reply_text(
				i18n.t("ERROR_TIMEOUT", language, error="Processing took too long. Result sent separately."),
				parse_mode=ParseMode.MARKDOWN
			)
		else:
			await query.message.reply_text(
				i18n.t("ERROR_GENERAL", language, error=str(e)),
				parse_mode=ParseMode.MARKDOWN
			)
		context.user_data.clear()
		return ConversationHandler.END
	except Exception as e:
		logger.error(f"Abjad error: {str(e)}")
		await query.message.reply_text(
			i18n.t("ERROR_GENERAL", language, error=str(e)),
			parse_mode=ParseMode.MARKDOWN
		)
		context.user_data.clear()
		return ConversationHandler.END

async def abjad_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
	logger.info(f"Cancelling /abjad for user {update.effective_user.id}")
	try:
		user_id = update.message.from_user.id
		db = Database()
		i18n = I18n()
		language = db.get_user_language(user_id)
		await update.message.reply_text(
			i18n.t("ABJAD_CANCEL", language),
			parse_mode=ParseMode.MARKDOWN
		)
		context.user_data.clear()
		return ConversationHandler.END
	except Exception as e:
		logger.error(f"Error in abjad_cancel: {str(e)}")
		await update.message.reply_text(
			i18n.t("ERROR_GENERAL", language, error=str(e)),
			parse_mode=ParseMode.MARKDOWN
		)
		return ConversationHandler.END

def get_abjad_conversation_handler():
	try:
		handler = ConversationHandler(
			entry_points=[CommandHandler("abjad", abjad_start)],
			states={
				ALPHABET_ORDER: [CallbackQueryHandler(abjad_alphabet_order)],
				ABJAD_TYPE: [CallbackQueryHandler(abjad_type)],
				SHADDA: [CallbackQueryHandler(abjad_shadda)],
				DETAIL: [CallbackQueryHandler(abjad_detail)],
			},
			fallbacks=[CommandHandler("cancel", abjad_cancel)],
			allow_reentry=True,
		)
		logger.info("Abjad conversation handler initialized successfully")
		return handler
	except Exception as e:
		logger.error(f"Failed to initialize abjad conversation handler: {str(e)}")
		raise