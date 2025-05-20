import logging
from telegram import InlineQueryResultArticle, InputTextMessageContent
from Bot.Helpers.Transliteration import Transliteration
from Bot.database import Database
from Bot.Helpers.i18n import I18n
from Bot.utils import get_warning_description, get_ai_commentary

logger = logging.getLogger(__name__)

async def handle(update, context, query_text, language):
	user = update.inline_query.from_user
	logger.info(f"Processing inline transliterate query '{query_text}' from user {user.id if user else 'unknown'}")

	results = []
	db = Database()
	i18n = I18n()

	try:
		if not query_text:
			results.append(
				InlineQueryResultArticle(
					id="transliterate_help",
					title=i18n.t("TRANSLITERATE_INLINE_HELP_TITLE", language),
					description=i18n.t("TRANSLITERATE_INLINE_HELP_DESC", language),
					input_message_content=InputTextMessageContent(
						i18n.t("TRANSLITERATE_INLINE_HELP_MESSAGE", language),
						parse_mode="Markdown"
					)
				)
			)
			return results

		# Parse query: text and optional flags
		parts = query_text.split()
		text = ""
		params = {
			"source": "arabic",
			"target": "latin"
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
					id="transliterate_no_text",
					title=i18n.t("TRANSLITERATE_NO_TEXT_TITLE", language),
					description=i18n.t("TRANSLITERATE_NO_TEXT_DESC", language),
					input_message_content=InputTextMessageContent(
						i18n.t("TRANSLITERATE_NO_TEXT_MESSAGE", language),
						parse_mode="Markdown"
					)
				)
			)
			return results

		# Validate parameters
		valid_languages = ["arabic", "english", "turkish", "hebrew", "latin"]
		if params["source"] not in valid_languages:
			results.append(
				InlineQueryResultArticle(
					id="transliterate_invalid_source",
					title=i18n.t("TRANSLITERATE_INVALID_SOURCE_TITLE", language),
					description=i18n.t("TRANSLITERATE_INVALID_SOURCE_DESC", language, source=params["source"]),
					input_message_content=InputTextMessageContent(
						i18n.t("TRANSLITERATE_INVALID_SOURCE_MESSAGE", language, source=params["source"],
								 valid=", ".join(valid_languages)),
						parse_mode="Markdown"
					)
				)
			)
			return results

		if params["target"] not in valid_languages:
			results.append(
				InlineQueryResultArticle(
					id="transliterate_invalid_target",
					title=i18n.t("TRANSLITERATE_INVALID_TARGET_TITLE", language),
					description=i18n.t("TRANSLITERATE_INVALID_TARGET_DESC", language, target=params["target"]),
					input_message_content=InputTextMessageContent(
						i18n.t("TRANSLITERATE_INVALID_TARGET_MESSAGE", language, target=params["target"],
								 valid=", ".join(valid_languages)),
						parse_mode="Markdown"
					)
				)
			)
			return results

		# Transliterate text
		transliterator = Transliteration()
		result = transliterator.transliterate(text, params["source"], params["target"])
		if isinstance(result, str) and result.startswith("Error"):
			results.append(
				InlineQueryResultArticle(
					id="transliterate_error",
					title=i18n.t("ERROR_TITLE", language),
					description=i18n.t("ERROR_DESC", language, error=result),
					input_message_content=InputTextMessageContent(
						i18n.t("ERROR_GENERAL", language, error=result),
						parse_mode="Markdown"
					)
				)
			)
			return results

		response = i18n.t("TRANSLITERATION_RESULT", language,
						 text=text,
						 source_lang=params["source"].title(),
						 target_lang=params["target"].title(),
						 result=result)

		commentary = await get_ai_commentary(response, language)
		if commentary:
			response += "\n\n" + i18n.t("AI_COMMENTARY", language, commentary=commentary)

		results.append(
			InlineQueryResultArticle(
				id=f"transliterate_{params['source']}_{params['target']}",
				title=i18n.t("TRANSLITERATE_INLINE_TITLE", language, result=result),
				description=i18n.t("TRANSLITERATE_INLINE_DESC", language, text=text, source=params["source"].title(), target=params["target"].title()),
				input_message_content=InputTextMessageContent(
					response,
					parse_mode="Markdown"
				)
			)
		)

	except Exception as e:
		logger.error(f"Error in inline transliterate: {str(e)}")
		results.append(
			InlineQueryResultArticle(
				id="transliterate_error",
				title=i18n.t("ERROR_TITLE", language),
				description=i18n.t("ERROR_DESC", language, error=str(e)),
				input_message_content=InputTextMessageContent(
					i18n.t("ERROR_GENERAL", language, error=str(e)),
					parse_mode="Markdown"
				)
			)
		)

	return results