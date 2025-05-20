import logging
import re
from telegram import InlineQueryResultArticle, InputTextMessageContent
from Bot.Helpers.ElementClassifier import ElementClassifier
from Bot.database import Database
from Bot.Helpers.i18n import I18n
from Bot.utils import get_warning_description, get_ai_commentary

logger = logging.getLogger(__name__)

async def handle(update, context, query_text, language):
	user = update.inline_query.from_user
	logger.info(f"Processing inline unsur query '{query_text}' from user {user.id if user else 'unknown'}")

	results = []
	db = Database()
	i18n = I18n()

	try:
		if not query_text:
			results.append(
				InlineQueryResultArticle(
					id="unsur_help",
					title=i18n.t("UNSUR_INLINE_HELP_TITLE", language),
					description=i18n.t("UNSUR_INLINE_HELP_DESC", language),
					input_message_content=InputTextMessageContent(
						i18n.t("UNSUR_INLINE_HELP_MESSAGE", language),
						parse_mode="Markdown"
					)
				)
			)
			return results

		# Parse query: text and optional flags
		parts = query_text.split()
		text = ""
		params = {
			"language": "default",
			"table": "default",
			"shadda": "once"
		}
		i = 0
		while i < len(parts):
			if parts[i].startswith("--"):
				key_value = parts[i][2:].split("=", 1)
				if len(key_value) == 2:
					key, value = key_value
					if key in params:
						params[key] = value
					i += 1
				else:
					break
			else:
				text += parts[i] + " "
				i += 1
		text = text.strip()

		if not text:
			results.append(
				InlineQueryResultArticle(
					id="unsur_no_text",
					title=i18n.t("UNSUR_NO_TEXT_TITLE", language),
					description=i18n.t("UNSUR_NO_TEXT_DESC", language),
					input_message_content=InputTextMessageContent(
						i18n.t("UNSUR_NO_TEXT_MESSAGE", language),
						parse_mode="Markdown"
					)
				)
			)
			return results

		# Validate parameters
		valid_languages = ["turkish", "arabic", "buni", "huseyni", "hebrew", "english", "latin", "default"]
		valid_tables = ["fire", "water", "air", "earth", "default"]
		valid_shadda = ["once", "twice"]

		if params["language"] not in valid_languages:
			results.append(
				InlineQueryResultArticle(
					id="unsur_invalid_language",
					title=i18n.t("UNSUR_INVALID_LANGUAGE_TITLE", language),
					description=i18n.t("UNSUR_INVALID_LANGUAGE_DESC", language, language=params["language"]),
					input_message_content=InputTextMessageContent(
						i18n.t("UNSUR_INVALID_LANGUAGE_MESSAGE", language, language=params["language"],
								 valid=", ".join(valid_languages)),
						parse_mode="Markdown"
					)
				)
			)
			return results

		if params["table"] not in valid_tables:
			results.append(
				InlineQueryResultArticle(
					id="unsur_invalid_table",
					title=i18n.t("UNSUR_INVALID_TABLE_TITLE", language),
					description=i18n.t("UNSUR_INVALID_TABLE_DESC", language, table=params["table"]),
					input_message_content=InputTextMessageContent(
						i18n.t("UNSUR_INVALID_TABLE_MESSAGE", language, table=params["table"],
								 valid=", ".join(valid_tables)),
						parse_mode="Markdown"
					)
				)
			)
			return results

		if params["shadda"] not in valid_shadda:
			results.append(
				InlineQueryResultArticle(
					id="unsur_invalid_shadda",
					title=i18n.t("UNSUR_INVALID_SHADDA_TITLE", language),
					description=i18n.t("UNSUR_INVALID_SHADDA_DESC", language, shadda=params["shadda"]),
					input_message_content=InputTextMessageContent(
						i18n.t("UNSUR_INVALID_SHADDA_MESSAGE", language, shadda=params["shadda"],
								 valid=", ".join(valid_shadda)),
						parse_mode="Markdown"
					)
				)
			)
			return results

		# Check shadda applicability
		is_arabic = bool(re.search(r"[\u0600-\u06FF]", text))
		if not is_arabic and params["shadda"] == "twice":
			results.append(
				InlineQueryResultArticle(
					id="unsur_shadda_invalid",
					title=i18n.t("UNSUR_SHADDA_INVALID_TITLE", language),
					description=i18n.t("UNSUR_SHADDA_INVALID_DESC", language),
					input_message_content=InputTextMessageContent(
						i18n.t("UNSUR_SHADDA_INVALID_MESSAGE", language),
						parse_mode="Markdown"
					)
				)
			)
			return results

		# Classify element
		classifier = ElementClassifier()
		shadda_value = 2 if params["shadda"] == "twice" else 1
		result = classifier.classify(text, params["language"], params["table"], shadda_value)
		if isinstance(result, str) and result.startswith("Error"):
			results.append(
				InlineQueryResultArticle(
					id="unsur_error",
					title=i18n.t("ERROR_TITLE", language),
					description=i18n.t("ERROR_DESC", language, error=result),
					input_message_content=InputTextMessageContent(
						i18n.t("ERROR_GENERAL", language, error=result),
						parse_mode="Markdown"
					)
				)
			)
			return results

		liste, value, element = result
		response = i18n.t("UNSUR_RESULT", language,
						 input=text,
						 liste=liste,
						 value=value,
						 element=element.title())

		warning_desc = get_warning_description(value, language)
		if warning_desc:
			response += "\n\n" + i18n.t("WARNING_NUMBER", language, value=value, description=warning_desc)

		commentary = await get_ai_commentary(response, language)
		if commentary:
			response += "\n\n" + i18n.t("AI_COMMENTARY", language, commentary=commentary)

		results.append(
			InlineQueryResultArticle(
				id=f"unsur_{value}",
				title=i18n.t("UNSUR_INLINE_TITLE", language, element=element.title()),
				description=i18n.t("UNSUR_INLINE_DESC", language, input=text, element=element.title()),
				input_message_content=InputTextMessageContent(
					response,
					parse_mode="Markdown"
				)
			)
		)

	except Exception as e:
		logger.error(f"Error in inline unsur: {str(e)}")
		results.append(
			InlineQueryResultArticle(
				id="unsur_error",
				title=i18n.t("ERROR_TITLE", language),
				description=i18n.t("ERROR_DESC", language, error=str(e)),
				input_message_content=InputTextMessageContent(
					i18n.t("ERROR_GENERAL", language, error=str(e)),
					parse_mode="Markdown"
				)
			)
		)

	return results