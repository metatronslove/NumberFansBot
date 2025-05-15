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
    logger.info(f"Processing inline bastet query '{query_text}' from user {user.id if user else 'unknown'}")

    results = []
    db = Database()
    i18n = I18n()

    try:
        if not query_text:
            results.append(
                InlineQueryResultArticle(
                    id="bastet_help",
                    title=i18n.t("BASTET_INLINE_HELP_TITLE", language),
                    description=i18n.t("BASTET_INLINE_HELP_DESC", language),
                    input_message_content=InputTextMessageContent(
                        i18n.t("BASTET_INLINE_HELP_MESSAGE", language),
                        parse_mode="Markdown"
                    )
                )
            )
            return results

        # Parse query: number and optional flags
        parts = query_text.split()
        number = None
        params = {
            "repetition": "1",
            "alphabet": "arabic_abjadi",
            "type": "saghir"
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
                    id="bastet_no_number",
                    title=i18n.t("BASTET_NO_NUMBER_TITLE", language),
                    description=i18n.t("BASTET_NO_NUMBER_DESC", language),
                    input_message_content=InputTextMessageContent(
                        i18n.t("BASTET_NO_NUMBER_MESSAGE", language),
                        parse_mode="Markdown"
                    )
                )
            )
            return results

        # Validate parameters
        if not params["repetition"].isdigit() or int(params["repetition"]) < 1 or int(params["repetition"]) > 1000:
            results.append(
                InlineQueryResultArticle(
                    id="bastet_invalid_repetition",
                    title=i18n.t("BASTET_INVALID_REPETITION_TITLE", language),
                    description=i18n.t("BASTET_INVALID_REPETITION_DESC", language, repetition=params["repetition"]),
                    input_message_content=InputTextMessageContent(
                        i18n.t("BASTET_INVALID_REPETITION_MESSAGE", language, repetition=params["repetition"]),
                        parse_mode="Markdown"
                    )
                )
            )
            return results

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

        if params["alphabet"] not in alphabet_map:
            results.append(
                InlineQueryResultArticle(
                    id="bastet_invalid_alphabet",
                    title=i18n.t("BASTET_INVALID_ALPHABET_TITLE", language),
                    description=i18n.t("BASTET_INVALID_ALPHABET_DESC", language, alphabet=params["alphabet"]),
                    input_message_content=InputTextMessageContent(
                        i18n.t("BASTET_INVALID_ALPHABET_MESSAGE", language, alphabet=params["alphabet"],
                               valid=", ".join(alphabet_map.keys())),
                        parse_mode="Markdown"
                    )
                )
            )
            return results

        if params["type"] not in type_map:
            results.append(
                InlineQueryResultArticle(
                    id="bastet_invalid_type",
                    title=i18n.t("BASTET_INVALID_TYPE_TITLE", language),
                    description=i18n.t("BASTET_INVALID_TYPE_DESC", language, type=params["type"]),
                    input_message_content=InputTextMessageContent(
                        i18n.t("BASTET_INVALID_TYPE_MESSAGE", language, type=params["type"],
                               valid=", ".join(type_map.keys())),
                        parse_mode="Markdown"
                    )
                )
            )
            return results

        # Calculate Bastet result
        abjad = Abjad()
        alphabeta, tablebase = alphabet_map[params["alphabet"]]
        tablebase += type_map[params["type"]]
        repetition = int(params["repetition"])

        result = abjad.bastet(number, repetition, tablebase, 1, alphabeta.upper(), 0)
        if isinstance(result, str) and result.startswith("Error"):
            results.append(
                InlineQueryResultArticle(
                    id="bastet_error",
                    title=i18n.t("ERROR_TITLE", language),
                    description=i18n.t("ERROR_DESC", language, error=result),
                    input_message_content=InputTextMessageContent(
                        i18n.t("ERROR_GENERAL", language, error=result),
                        parse_mode="Markdown"
                    )
                )
            )
            return results

        calc_summary = i18n.t("BASTET_CALC_SUMMARY", language,
                             alphabet=params["alphabet"].replace("_", " ").title(),
                             abjad_type=params["type"].replace("_", " ").title(),
                             repetition=repetition)
        calc_summary += "\n" + i18n.t("BASTET_CALC_RESULT", language, result=result)

        response = i18n.t("BASTET_RESULT", language, number=number, repetition=repetition, table=params["alphabet"], value=result)
        response += "\n\n" + calc_summary

        warning_desc = get_warning_description(result, language)
        if warning_desc:
            response += "\n\n" + i18n.t("WARNING_NUMBER", language, value=result, description=warning_desc)

        commentary = await get_ai_commentary(response, language)
        if commentary:
            response += "\n\n" + i18n.t("AI_COMMENTARY", language, commentary=commentary)

        results.append(
            InlineQueryResultArticle(
                id=f"bastet_{number}_{repetition}",
                title=i18n.t("BASTET_INLINE_TITLE", language, value=result),
                description=i18n.t("BASTET_INLINE_DESC", language, number=number, repetition=repetition),
                input_message_content=InputTextMessageContent(
                    response,
                    parse_mode="Markdown"
                )
            )
        )

    except Exception as e:
        logger.error(f"Error in inline bastet: {str(e)}")
        results.append(
            InlineQueryResultArticle(
                id="bastet_error",
                title=i18n.t("ERROR_TITLE", language),
                description=i18n.t("ERROR_DESC", language, error=str(e)),
                input_message_content=InputTextMessageContent(
                    i18n.t("ERROR_GENERAL", language, error=str(e)),
                    parse_mode="Markdown"
                )
            )
        )

    return results