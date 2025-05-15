from telegram import InlineQueryResultArticle, InputTextMessageContent
from Bot.database import Database
from Bot.Helpers.i18n import I18n
from Bot.MagicSquare import MagicSquareGenerator
import logging

logger = logging.getLogger(__name__)

async def inline_magic_square(update, context):
    query = update.inline_query.query
    user = update.inline_query.from_user
    db = Database()
    i18n = I18n()
    language = db.get_user_language(user.id) or "en"  # Default to English if not found

    # Safely get chat_id, if available
    chat_id = None
    if update.effective_chat:
        chat_id = update.effective_chat.id

    # Check group blacklist if chat_id is available
    if chat_id:
        try:
            if db.is_group_blacklisted(chat_id):
                await update.inline_query.answer([
                    InlineQueryResultArticle(
                        id="blacklist_error",
                        title=i18n.t("ERROR", language),
                        input_message_content=InputTextMessageContent(
                            i18n.t("GROUP_BLACKLISTED", language)
                        )
                    )
                ])
                return
            # Optional: Restrict based on group attributes (e.g., only public groups)
            group = db.get_group(chat_id)
            if group and not group.get('is_public', False):
                await update.inline_query.answer([
                    InlineQueryResultArticle(
                        id="group_restricted",
                        title=i18n.t("ERROR", language),
                        input_message_content=InputTextMessageContent(
                            i18n.t("PRIVATE_GROUP_RESTRICTED", language)
                        )
                    )
                ])
                return
        except Exception as e:
            logger.error(f"Error checking group data for chat_id {chat_id}: {str(e)}")
            await update.inline_query.answer([
                InlineQueryResultArticle(
                    id="db_error",
                    title=i18n.t("ERROR", language),
                    input_message_content=InputTextMessageContent(
                        i18n.t("ERROR_GENERAL", language, error="Database error")
                    )
                )
            ])
            return

    args = query.split()[1:]  # Skip "/magicsquare"

    try:
        # Validate input
        number = int(args[0]) if args else None
        if not number or number < 15:
            raise ValueError(i18n.t("ERROR_MIN_SUM", language))

        # Generate the magic square
        magic_square = MagicSquareGenerator()
        square = magic_square.generate_magic_square(3, number, 0, False, 'arabic')
        response = i18n.t("MAGICSQUARE_RESULT", language, number=number, square=square["box"])

        # Log inline query activity if in a group
        if chat_id:
            try:
                db.update_group_inline_activity(
                    chat_id=chat_id,
                    username=user.username or user.first_name,
                    query=query,
                    timestamp=datetime.now()
                )
            except Exception as e:
                logger.error(f"Error logging inline query for chat_id {chat_id}: {str(e)}")

        content = InputTextMessageContent(
            response,
            parse_mode="Markdown"
        )

        await update.inline_query.answer([
            InlineQueryResultArticle(
                id=f"magic_square_{number}",
                title=i18n.t("MAGIC_SQUARE_TITLE", language, number=number),
                input_message_content=content
            )
        ])
    except ValueError as e:
        error_content = InputTextMessageContent(str(e))
        await update.inline_query.answer([
            InlineQueryResultArticle(
                id="error",
                title=i18n.t("INVALID_INPUT", language),
                input_message_content=error_content
            )
        ])
    except Exception as e:
        logger.error(f"Error generating magic square: {str(e)}")
        error_content = InputTextMessageContent(i18n.t("ERROR_GENERAL", language, error=str(e)))
        await update.inline_query.answer([
            InlineQueryResultArticle(
                id="error",
                title=i18n.t("ERROR", language),
                input_message_content=error_content
            )
        ])