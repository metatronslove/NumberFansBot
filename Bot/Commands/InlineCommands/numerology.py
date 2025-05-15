import logging
from telegram import InlineQueryResultArticle, InputTextMessageContent
from Bot.Helpers.UnifiedNumerology import UnifiedNumerology
from Bot.database import Database
from Bot.Helpers.i18n import I18n
from Bot.utils import get_warning_description, get_ai_commentary

logger = logging.getLogger(__name__)

async def handle(update, context, query_text, language):
    user = update.inline_query.from_user
    logger.info(f"Processing inline numerology query '{query_text}' from user {user.id if user else 'unknown'}")

    results = []
    db = Database()
    i18n = I18n()

    try:
        if not query_text:
            results.append(
                InlineQueryResultArticle(
                    id="numerology_help",
                    title=i18n.t("NUMEROLOGY_INLINE_HELP_TITLE", language),
                    description=i18n.t("NUMEROLOGY_INLINE_HELP_DESC", language),
                    input_message_content=InputTextMessageContent(
                        i18n.t("NUMEROLOGY_INLINE_HELP_MESSAGE", language),
                        parse_mode="Markdown"
                    )
                )
            )
            return results

        # Parse query: text and optional flags
        parts = query_text.split()
        text = ""
        params = {
            "alphabet": "english",
            "method": "normal"
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
                    id="numerology_no_text",
                    title=i18n.t("NUMEROLOGY_NO_TEXT_TITLE", language),
                    description=i18n.t("NUMEROLOGY_NO_TEXT_DESC", language),
                    input_message_content=InputTextMessageContent(
                        i18n.t("NUMEROLOGY_NO_TEXT_MESSAGE", language),
                        parse_mode="Markdown"
                    )
                )
            )
            return results

        # Validate parameters
        valid_alphabets = [
            "arabic_abjadi", "arabic_maghribi", "arabic_quranic", "arabic_hija",
            "arabic_maghribi_hija", "arabic_ikleels", "arabic_shamse_abjadi",
            "hebrew", "turkish", "english", "latin"
        ]
        valid_methods = [
            "normal", "inverse", "base36", "base36_inverse", "pythagorean",
            "chaldean", "latin", "latin_inverse", "hebrew", "hebrew_inverse"
        ]

        if params["alphabet"] not in valid_alphabets:
            results.append(
                InlineQueryResultArticle(
                    id="numerology_invalid_alphabet",
                    title=i18n.t("NUMEROLOGY_INVALID_ALPHABET_TITLE", language),
                    description=i18n.t("NUMEROLOGY_INVALID_ALPHABET_DESC", language, alphabet=params["alphabet"]),
                    input_message_content=InputTextMessageContent(
                        i18n.t("NUMEROLOGY_INVALID_ALPHABET_MESSAGE", language, alphabet=params["alphabet"],
                               valid=", ".join(valid_alphabets)),
                        parse_mode="Markdown"
                    )
                )
            )
            return results

        if params["method"] not in valid_methods:
            results.append(
                InlineQueryResultArticle(
                    id="numerology_invalid_method",
                    title=i18n.t("NUMEROLOGY_INVALID_METHOD_TITLE", language),
                    description=i18n.t("NUMEROLOGY_INVALID_METHOD_DESC", language, method=params["method"]),
                    input_message_content=InputTextMessageContent(
                        i18n.t("NUMEROLOGY_INVALID_METHOD_MESSAGE", language, method=params["method"],
                               valid=", ".join(valid_methods)),
                        parse_mode="Markdown"
                    )
                )
            )
            return results

        # Calculate numerology
        numerology = UnifiedNumerology()
        alphabet_map = {
            "arabic_abjadi": "arabic", "arabic_maghribi": "arabic", "arabic_quranic": "arabic",
            "arabic_hija": "arabic", "arabic_maghribi_hija": "arabic", "arabic_ikleels": "arabic",
            "arabic_shamse_abjadi": "arabic", "hebrew": "hebrew", "turkish": "turkish",
            "english": "english", "latin": "latin"
        }
        value = numerology.calculate(text, alphabet_map[params["alphabet"]], params["method"])
        if isinstance(value, str) and value.startswith("Error"):
            results.append(
                InlineQueryResultArticle(
                    id="numerology_error",
                    title=i18n.t("ERROR_TITLE", language),
                    description=i18n.t("ERROR_DESC", language, error=value),
                    input_message_content=InputTextMessageContent(
                        i18n.t("ERROR_GENERAL", language, error=value),
                        parse_mode="Markdown"
                    )
                )
            )
            return results

        response = i18n.t("NUMEROLOGY_RESULT", language,
                         text=text,
                         alphabet=params["alphabet"].replace("_", " ").title(),
                         method=params["method"].replace("_", " ").title(),
                         value=value)

        warning_desc = get_warning_description(value, language)
        if warning_desc:
            response += "\n\n" + i18n.t("WARNING_NUMBER", language, value=value, description=warning_desc)

        commentary = await get_ai_commentary(response, language)
        if commentary:
            response += "\n\n" + i18n.t("AI_COMMENTARY", language, commentary=commentary)

        results.append(
            InlineQueryResultArticle(
                id=f"numerology_{value}",
                title=i18n.t("NUMEROLOGY_INLINE_TITLE", language, value=value),
                description=i18n.t("NUMEROLOGY_INLINE_DESC", language, text=text, alphabet=params["alphabet"].title(), method=params["method"].title()),
                input_message_content=InputTextMessageContent(
                    response,
                    parse_mode="Markdown"
                )
            )
        )

    except Exception as e:
        logger.error(f"Error in inline numerology: {str(e)}")
        results.append(
            InlineQueryResultArticle(
                id="numerology_error",
                title=i18n.t("ERROR_TITLE", language),
                description=i18n.t("ERROR_DESC", language, error=str(e)),
                input_message_content=InputTextMessageContent(
                    i18n.t("ERROR_GENERAL", language, error=str(e)),
                    parse_mode="Markdown"
                )
            )
        )

    return results