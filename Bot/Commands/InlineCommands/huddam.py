import logging
from telegram import InlineQueryResultArticle, InputTextMessageContent
from Bot.Helpers.Abjad import Abjad
from Bot.database import Database
from Bot.Helpers.i18n import I18n
from Bot.utils import get_warning_description, get_ai_commentary

logger = logging.getLogger(__name__)

async def handle(update, context, query_text, language):
	user = update.inline_query.from_user
	logger.info(f"Processing inline huddam query '{query_text}' from user {user.id if user else 'unknown'}")

	results = []
	db = Database()
	i18n = I18n()

	try:
		if not query_text:
			results.append(
				InlineQueryResultArticle(
					id="huddam_help",
					title=i18n.t("HUDDAM_INLINE_HELP_TITLE", language),
					description=i18n.t("HUDDAM_INLINE_HELP_DESC", language),
					input_message_content=InputTextMessageContent(
						i18n.t("HUDDAM_INLINE_HELP_MESSAGE", language),
						parse_mode="Markdown"
					)
				)
			)
			return results

		# Parse query: number and optional flags
		parts = query_text.split()
		number = None
		params = {
			"entity": "ulvi",
			"alphabet": "arabic_abjadi",
			"multiplier": "regular"
		}
		i = 0
		if i < len(parts) and parts[i].isdigit():
			number = int(parts[i])
			i += 1
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
				break

		if number is None:
			results.append(
				InlineQueryResultArticle(
					id="huddam_no_number",
					title=i18n.t("HUDDAM_NO_NUMBER_TITLE", language),
					description=i18n.t("HUDDAM_NO_NUMBER_DESC", language),
					input_message_content=InputTextMessageContent(
						i18n.t("HUDDAM_NO_NUMBER_MESSAGE", language),
						parse_mode="Markdown"
					)
				)
			)
			return results

		# Validate parameters
		valid_entities = ["ulvi", "sufli", "ser"]
		valid_alphabets = [
			"arabic_abjadi", "arabic_maghribi", "arabic_quranic", "arabic_hija",
			"arabic_maghribi_hija", "arabic_ikleels", "arabic_shamse_abjadi",
			"hebrew", "turkish", "english", "latin"
		]
		valid_multipliers = ["regular", "eacher"]

		if params["entity"] not in valid_entities:
			results.append(
				InlineQueryResultArticle(
					id="huddam_invalid_entity",
					title=i18n.t("HUDDAM_INVALID_ENTITY_TITLE", language),
					description=i18n.t("HUDDAM_INVALID_ENTITY_DESC", language, entity=params["entity"]),
					input_message_content=InputTextMessageContent(
						i18n.t("HUDDAM_INVALID_ENTITY_MESSAGE", language, entity=params["entity"],
								 valid=", ".join(valid_entities)),
						parse_mode="Markdown"
					)
				)
			)
			return results

		if params["alphabet"] not in valid_alphabets:
			results.append(
				InlineQueryResultArticle(
					id="huddam_invalid_alphabet",
					title=i18n.t("HUDDAM_INVALID_ALPHABET_TITLE", language),
					description=i18n.t("HUDDAM_INVALID_ALPHABET_DESC", language, alphabet=params["alphabet"]),
					input_message_content=InputTextMessageContent(
						i18n.t("HUDDAM_INVALID_ALPHABET_MESSAGE", language, alphabet=params["alphabet"],
								 valid=", ".join(valid_alphabets)),
						parse_mode="Markdown"
					)
				)
			)
			return results

		if params["multiplier"] not in valid_multipliers:
			results.append(
				InlineQueryResultArticle(
					id="huddam_invalid_multiplier",
					title=i18n.t("HUDDAM_INVALID_MULTIPLIER_TITLE", language),
					description=i18n.t("HUDDAM_INVALID_MULTIPLIER_DESC", language, multiplier=params["multiplier"]),
					input_message_content=InputTextMessageContent(
						i18n.t("HUDDAM_INVALID_MULTIPLIER_MESSAGE", language, multiplier=params["multiplier"],
								 valid=", ".join(valid_multipliers)),
						parse_mode="Markdown"
					)
				)
			)
			return results

		# Generate huddam name
		abjad = Abjad()
		alphabet_map = {
			"arabic_abjadi": ("arabic", 1), "arabic_maghribi": ("arabic", 7), "arabic_quranic": ("arabic", 12),
			"arabic_hija": ("arabic", 17), "arabic_maghribi_hija": ("arabic", 22), "arabic_ikleels": ("arabic", 27),
			"arabic_shamse_abjadi": ("arabic", 32), "hebrew": ("hebrew", 1), "turkish": ("turkish", 1),
			"english": ("english", 1), "latin": ("latin", 1)
		}
		alphabeta, tablebase = alphabet_map[params["alphabet"]]
		multiplier = 1 if params["multiplier"] == "regular" else 2
		entity_type = params["entity"]

		name = abjad.huddam(number, entity_type, tablebase, multiplier, alphabeta.upper())
		if isinstance(name, str) and name.startswith("Error"):
			results.append(
				InlineQueryResultArticle(
					id="huddam_error",
					title=i18n.t("ERROR_TITLE", language),
					description=i18n.t("ERROR_DESC", language, error=name),
					input_message_content=InputTextMessageContent(
						i18n.t("ERROR_GENERAL", language, error=name),
						parse_mode="Markdown"
					)
				)
			)
			return results

		response = i18n.t("HUDDAM_RESULT", language,
						 number=number,
						 type=entity_type.title(),
						 huddam_lang=params["alphabet"].replace("_", " ").title(),
						 name=name)

		warning_desc = get_warning_description(number, language)
		if warning_desc:
			response += "\n\n" + i18n.t("WARNING_NUMBER", language, value=number, description=warning_desc)

		commentary = await get_ai_commentary(response, language)
		if commentary:
			response += "\n\n" + i18n.t("AI_COMMENTARY", language, commentary=commentary)

		results.append(
			InlineQueryResultArticle(
				id=f"huddam_{number}_{entity_type}",
				title=i18n.t("HUDDAM_INLINE_TITLE", language, name=name),
				description=i18n.t("HUDDAM_INLINE_DESC", language, number=number, type=entity_type.title()),
				input_message_content=InputTextMessageContent(
					response,
					parse_mode="Markdown"
				)
			)
		)

	except Exception as e:
		logger.error(f"Error in inline huddam: {str(e)}")
		results.append(
			InlineQueryResultArticle(
				id="huddam_error",
				title=i18n.t("ERROR_TITLE", language),
				description=i18n.t("ERROR_DESC", language, error=str(e)),
				input_message_content=InputTextMessageContent(
					i18n.t("ERROR_GENERAL", language, error=str(e)),
					parse_mode="Markdown"
				)
			)
		)

	return results