import logging
from telegram import InlineQueryResultArticle, InputTextMessageContent
from Bot.Helpers.NumberConverter import NumberConverter
from Bot.database import Database
from Bot.Helpers.i18n import I18n
from Bot.utils import get_warning_description, get_ai_commentary

logger = logging.getLogger(__name__)

async def handle(update, context, query_text, language):
	user = update.inline_query.from_user
	logger.info(f"Processing inline convert_numbers query '{query_text}' from user {user.id if user else 'unknown'}")

	results = []
	db = Database()
	i18n = I18n()

	try:
		if not query_text:
			results.append(
				InlineQueryResultArticle(
					id="convertnumbers_help",
					title=i18n.t("CONVERTNUMBERS_INLINE_HELP_TITLE", language),
					description=i18n.t("CONVERTNUMBERS_INLINE_HELP_DESC", language),
					input_message_content=InputTextMessageContent(
						i18n.t("CONVERTNUMBERS_INLINE_HELP_MESSAGE", language),
						parse_mode="Markdown"
					)
				)
			)
			return results

		# Parse query: number and optional flags
		parts = query_text.split()
		number = None
		params = {"format": "arabic"}
		i = 0
		if i < len(parts) and parts[i].isdigit():
			number = parts[i]
			i += 1
		while i < len(parts):
			if parts[i].startswith("--"):
				key_value = parts[i][2:].split("=", 1)
				if len(key_value) == 2:
					key, value = key_value
					if key == "format":
						params[key] = value
					i += 1
				else:
					break
			else:
				break

		if number is None:
			results.append(
				InlineQueryResultArticle(
					id="convertnumbers_no_text",
					title=i18n.t("CONVERTNUMBERS_NO_TEXT_TITLE", language),
					description=i18n.t("CONVERTNUMBERS_NO_TEXT_DESC", language),
					input_message_content=InputTextMessageContent(
						i18n.t("CONVERTNUMBERS_NO_TEXT_MESSAGE", language),
						parse_mode="Markdown"
					)
				)
			)
			return results

		# Validate format
		valid_formats = ["arabic", "indian", "invert"]
		if params["format"] not in valid_formats:
			results.append(
				InlineQueryResultArticle(
					id="convertnumbers_invalid_format",
					title=i18n.t("CONVERTNUMBERS_INVALID_FORMAT_TITLE", language),
					description=i18n.t("CONVERTNUMBERS_INVALID_FORMAT_DESC", language, format=params["format"]),
					input_message_content=InputTextMessageContent(
						i18n.t("CONVERTNUMBERS_INVALID_FORMAT_MESSAGE", language, format=params["format"],
								 valid=", ".join(valid_formats)),
						parse_mode="Markdown"
					)
				)
			)
			return results

		# Convert number
		converter = NumberConverter()
		result = converter.convert(number, params["format"])
		if isinstance(result, str) and result.startswith("Error"):
			results.append(
				InlineQueryResultArticle(
					id="convertnumbers_error",
					title=i18n.t("ERROR_TITLE", language),
					description=i18n.t("ERROR_DESC", language, error=result),
					input_message_content=InputTextMessageContent(
						i18n.t("ERROR_GENERAL", language, error=result),
						parse_mode="Markdown"
					)
				)
			)
			return results

		response = i18n.t("CONVERTNUMBERS_RESULT", language,
						 text=number,
						 format=params["format"].title(),
						 result=result)

		warning_desc = get_warning_description(int(number), language)
		if warning_desc:
			response += "\n\n" + i18n.t("WARNING_NUMBER", language, value=number, description=warning_desc)

		commentary = await get_ai_commentary(response, language)
		if commentary:
			response += "\n\n" + i18n.t("AI_COMMENTARY", language, commentary=commentary)

		results.append(
			InlineQueryResultArticle(
				id=f"convertnumbers_{number}_{params['format']}",
				title=i18n.t("CONVERTNUMBERS_INLINE_TITLE", language, result=result),
				description=i18n.t("CONVERTNUMBERS_INLINE_DESC", language, text=number, format=params["format"].title()),
				input_message_content=InputTextMessageContent(
					response,
					parse_mode="Markdown"
				)
			)
		)

	except Exception as e:
		logger.error(f"Error in inline convert_numbers: {str(e)}")
		results.append(
			InlineQueryResultArticle(
				id="convertnumbers_error",
				title=i18n.t("ERROR_TITLE", language),
				description=i18n.t("ERROR_DESC", language, error=str(e)),
				input_message_content=InputTextMessageContent(
					i18n.t("ERROR_GENERAL", language, error=str(e)),
					parse_mode="Markdown"
				)
			)
		)

	return results