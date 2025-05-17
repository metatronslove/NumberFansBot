import logging
import re
from telegram import InlineQueryResultArticle, InputTextMessageContent
from Bot.Helpers.Abjad import Abjad
from Bot.database import Database
from Bot.Helpers.i18n import I18n
from Bot.utils import get_warning_description, get_ai_commentary

logger = logging.getLogger(__name__)

async def handle(update, context, query_text, language):
	user = update.inline_query.from_user
	logger.info(f"Processing inline abjad query '{query_text}' from user {user.id if user else 'unknown'}")

	results = []
	db = Database()
	i18n = I18n()

	try:
		if not query_text:
			results.append(
				InlineQueryResultArticle(
					id="abjad_help",
					title=i18n.t("ABJAD_INLINE_HELP_TITLE", language),
					description=i18n.t("ABJAD_INLINE_HELP_DESC", language),
					input_message_content=InputTextMessageContent(
						i18n.t("ABJAD_INLINE_HELP_MESSAGE", language),
						parse_mode="Markdown"
					)
				)
			)
			return results

		# Parse query: text and optional flags
		parts = query_text.split()
		text = ""
		params = {
			"alphabet": "arabic_abjadi",
			"type": "saghir",
			"shadda": "once",
			"detail": "summary"
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
					id="abjad_no_text",
					title=i18n.t("ABJAD_NO_TEXT_TITLE", language),
					description=i18n.t("ABJAD_NO_TEXT_DESC", language),
					input_message_content=InputTextMessageContent(
						i18n.t("ABJAD_NO_TEXT_MESSAGE", language),
						parse_mode="Markdown"
					)
				)
			)
			return results

		# Map inline parameters to user command values
		alphabet_map = {
			"arabic_abjadi": ("arabic", 1), "arabic_maghribi": ("arabic", 7), "arabic_quranic": ("arabic", 12),
			"arabic_hija": ("arabic", 17), "arabic_maghribi_hija": ("arabic", 22), "arabic_ikleels": ("arabic", 27),
			"arabic_shamse_abjadi": ("arabic", 32), "hebrew": ("hebrew", 1), "turkish": ("turkish", 1),
			"english": ("english", 1), "latin": ("latin", 1)
		}
		type_map = {
			"asghar": -1, "saghir": 0, "kebeer": 1, "akbar": 2,
			"saghir_plus_quantity": 3, "letter_quantity": 5
		}
		shadda_map = {"once": 1, "twice": 2}
		detail_map = {"summary": 0, "full": 1}

		# Validate parameters
		if params["alphabet"] not in alphabet_map:
			results.append(
				InlineQueryResultArticle(
					id="abjad_invalid_alphabet",
					title=i18n.t("ABJAD_INVALID_ALPHABET_TITLE", language),
					description=i18n.t("ABJAD_INVALID_ALPHABET_DESC", language, alphabet=params["alphabet"]),
					input_message_content=InputTextMessageContent(
						i18n.t("ABJAD_INVALID_ALPHABET_MESSAGE", language, alphabet=params["alphabet"],
							   valid=", ".join(alphabet_map.keys())),
						parse_mode="Markdown"
					)
				)
			)
			return results

		if params["type"] not in type_map:
			results.append(
				InlineQueryResultArticle(
					id="abjad_invalid_type",
					title=i18n.t("ABJAD_INVALID_TYPE_TITLE", language),
					description=i18n.t("ABJAD_INVALID_TYPE_DESC", language, type=params["type"]),
					input_message_content=InputTextMessageContent(
						i18n.t("ABJAD_INVALID_TYPE_MESSAGE", language, type=params["type"],
							   valid=", ".join(type_map.keys())),
						parse_mode="Markdown"
					)
				)
			)
			return results

		if params["shadda"] not in shadda_map:
			results.append(
				InlineQueryResultArticle(
					id="abjad_invalid_shadda",
					title=i18n.t("ABJAD_INVALID_SHADDA_TITLE", language),
					description=i18n.t("ABJAD_INVALID_SHADDA_DESC", language, shadda=params["shadda"]),
					input_message_content=InputTextMessageContent(
						i18n.t("ABJAD_INVALID_SHADDA_MESSAGE", language, shadda=params["shadda"],
							   valid=", ".join(shadda_map.keys())),
						parse_mode="Markdown"
					)
				)
			)
			return results

		if params["detail"] not in detail_map:
			results.append(
				InlineQueryResultArticle(
					id="abjad_invalid_detail",
					title=i18n.t("ABJAD_INVALID_DETAIL_TITLE", language),
					description=i18n.t("ABJAD_INVALID_DETAIL_DESC", language, detail=params["detail"]),
					input_message_content=InputTextMessageContent(
						i18n.t("ABJAD_INVALID_DETAIL_MESSAGE", language, detail=params["detail"],
							   valid=", ".join(detail_map.keys())),
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
					id="abjad_shadda_invalid",
					title=i18n.t("ABJAD_SHADDA_INVALID_TITLE", language),
					description=i18n.t("ABJAD_SHADDA_INVALID_DESC", language),
					input_message_content=InputTextMessageContent(
						i18n.t("ABJAD_SHADDA_INVALID_MESSAGE", language),
						parse_mode="Markdown"
					)
				)
			)
			return results

		# Calculate Abjad value
		abjad = Abjad()
		alphabeta, tablebase = alphabet_map[params["alphabet"]]
		tablebase += type_map[params["type"]]
		shadda_value = shadda_map[params["shadda"]]
		detail = detail_map[params["detail"]]

		result = abjad.abjad(text, tablebase, shadda_value, detail, alphabeta)
		if isinstance(result, str) and result.startswith("Error"):
			results.append(
				InlineQueryResultArticle(
					id="abjad_error",
					title=i18n.t("ERROR_TITLE", language),
					description=i18n.t("ERROR_DESC", language, error=result),
					input_message_content=InputTextMessageContent(
						i18n.t("ERROR_GENERAL", language, error=result),
						parse_mode="Markdown"
					)
				)
			)
			return results

		value = result["sum"] if detail else result
		details = "".join(f"[{d['char']}={d['value']}]" for d in result.get("details", [])) if detail else ""

		calc_summary = i18n.t("ABJAD_CALC_SUMMARY", language,
							 alphabet=params["alphabet"].replace("_", " ").title(),
							 abjad_type=params["type"].replace("_", " ").title(),
							 shadda=params["shadda"])
		if detail:
			calc_summary += "\n" + i18n.t("ABJAD_CALC_DETAILS", language, details=details)
		calc_summary += "\n" + i18n.t("ABJAD_CALC_TOTAL", language, total=value)

		response = i18n.t("ABJAD_RESULT", language, text=text, value=value)
		response += "\n\n" + calc_summary

		warning_desc = get_warning_description(value, language)
		if warning_desc:
			response += "\n\n" + i18n.t("WARNING_NUMBER", language, value=value, description=warning_desc)

		commentary = await get_ai_commentary(response, language)
		if commentary:
			response += "\n\n" + i18n.t("AI_COMMENTARY", language, commentary=commentary)

		results.append(
			InlineQueryResultArticle(
				id=f"abjad_{value}",
				title=i18n.t("ABJAD_INLINE_TITLE", language, value=value),
				description=i18n.t("ABJAD_INLINE_DESC", language, text=text, value=value),
				input_message_content=InputTextMessageContent(
					response,
					parse_mode="Markdown"
				)
			)
		)

	except Exception as e:
		logger.error(f"Error in inline abjad: {str(e)}")
		results.append(
			InlineQueryResultArticle(
				id="abjad_error",
				title=i18n.t("ERROR_TITLE", language),
				description=i18n.t("ERROR_DESC", language, error=str(e)),
				input_message_content=InputTextMessageContent(
					i18n.t("ERROR_GENERAL", language, error=str(e)),
					parse_mode="Markdown"
				)
			)
		)

	return results