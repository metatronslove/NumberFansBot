import logging
from telegram import InlineQueryResultArticle, InputTextMessageContent
from Bot.Helpers.NumberConverter import NumberConverter
from Bot.database import Database
from Bot.Helpers.i18n import I18n
from Bot.utils import get_warning_description, get_ai_commentary

logger = logging.getLogger(__name__)

async def handle(update, context, query_text, language):
	user = update.inline_query.from_user
	logger.info(f"Processing inline nutket query '{query_text}' from user {user.id if user else 'unknown'}")

	results = []
	db = Database()
	i18n = I18n()

	try:
		if not query_text:
			results.append(
				InlineQueryResultArticle(
					id="nutket_help",
					title=i18n.t("NUTKET_INLINE_HELP_TITLE", language),
					description=i18n.t("NUTKET_INLINE_HELP_DESC", language),
					input_message_content=InputTextMessageContent(
						i18n.t("NUTKET_INLINE_HELP_MESSAGE", language),
						parse_mode="Markdown"
					)
				)
			)
			return results

		# Parse query: number and optional flags
		parts = query_text.split()
		number = None
		params = {"language": "arabic"}
		i = 0
		if i < len(parts) and parts[i].isdigit():
			number = int(parts[i])
			i += 1
		while i < len(parts):
			if parts[i].startswith("--"):
				key_value = parts[i][2:].split("=", 1)
				if len(key_value) == 2:
					key, value = key_value
					if key == "language":
						params[key] = value
					i += 1
				else:
					break
			else:
				break

		if number is None:
			results.append(
				InlineQueryResultArticle(
					id="nutket_no_number",
					title=i18n.t("NUTKET_NO_NUMBER_TITLE", language),
					description=i18n.t("NUTKET_NO_NUMBER_DESC", language),
					input_message_content=InputTextMessageContent(
						i18n.t("NUTKET_NO_NUMBER_MESSAGE", language),
						parse_mode="Markdown"
					)
				)
			)
			return results

		# Validate language
		valid_languages = ["arabic", "hebrew", "turkish", "english", "latin"]
		if params["language"] not in valid_languages:
			results.append(
				InlineQueryResultArticle(
					id="nutket_invalid_language",
					title=i18n.t("NUTKET_INVALID_LANGUAGE_TITLE", language),
					description=i18n.t("NUTKET_INVALID_LANGUAGE_DESC", language, language=params["language"]),
					input_message_content=InputTextMessageContent(
						i18n.t("NUTKET_INVALID_LANGUAGE_MESSAGE", language, language=params["language"],
							   valid=", ".join(valid_languages)),
						parse_mode="Markdown"
					)
				)
			)
			return results

		# Spell number
		converter = NumberConverter()
		spelled = converter.spell_number(number, params["language"])
		if not spelled:
			results.append(
				InlineQueryResultArticle(
					id="nutket_error",
					title=i18n.t("ERROR_TITLE", language),
					description=i18n.t("ERROR_DESC", language, error="Failed to spell number"),
					input_message_content=InputTextMessageContent(
						i18n.t("ERROR_GENERAL", language, error="Failed to spell number"),
						parse_mode="Markdown"
					)
				)
			)
			return results

		response = i18n.t("NUTKET_RESULT", language,
						 number=number,
						 nutket_lang=params["language"].title(),
						 spelled=spelled)

		warning_desc = get_warning_description(number, language)
		if warning_desc:
			response += "\n\n" + i18n.t("WARNING_NUMBER", language, value=number, description=warning_desc)

		commentary = await get_ai_commentary(response, language)
		if commentary:
			response += "\n\n" + i18n.t("AI_COMMENTARY", language, commentary=commentary)

		results.append(
			InlineQueryResultArticle(
				id=f"nutket_{number}",
				title=i18n.t("NUTKET_INLINE_TITLE", language, spelled=spelled),
				description=i18n.t("NUTKET_INLINE_DESC", language, number=number, language=params["language"].title()),
				input_message_content=InputTextMessageContent(
					response,
					parse_mode="Markdown"
				)
			)
		)

	except Exception as e:
		logger.error(f"Error in inline nutket: {str(e)}")
		results.append(
			InlineQueryResultArticle(
				id="nutket_error",
				title=i18n.t("ERROR_TITLE", language),
				description=i18n.t("ERROR_DESC", language, error=str(e)),
				input_message_content=InputTextMessageContent(
					i18n.t("ERROR_GENERAL", language, error=str(e)),
					parse_mode="Markdown"
				)
			)
		)

	return results