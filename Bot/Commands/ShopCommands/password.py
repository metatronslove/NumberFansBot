import logging
from telegram import Update
from telegram.ext import (
	Application,
	CallbackContext,
	CommandHandler,
	ConversationHandler,
	MessageHandler,
	filters
)
from Bot.database import Database
from Bot.Helpers.i18n import I18n

# States for the conversation handler
ENTERING_OLD_PASSWORD, ENTERING_NEW_PASSWORD, CONFIRMING_NEW_PASSWORD = range(3)

logger = logging.getLogger(__name__)

class PasswordCommand:
	def __init__(self):
		self.db = Database()
		self.i18n = I18n()

	def register_handlers(self, application: Application):
		conv_handler = ConversationHandler(
			entry_points=[CommandHandler('password', self.password_command)],
			states={
				ENTERING_OLD_PASSWORD: [
					MessageHandler(filters.Text() & ~filters.COMMAND, self.old_password_received)
				],
				ENTERING_NEW_PASSWORD: [
					MessageHandler(filters.Text() & ~filters.COMMAND, self.new_password_received)
				],
				CONFIRMING_NEW_PASSWORD: [
					MessageHandler(filters.Text() & ~filters.COMMAND, self.confirm_password_received)
				]
			},
			fallbacks=[CommandHandler('cancel', self.cancel_password_change)]
		)
		application.add_handler(conv_handler)

	async def password_command(self, update: Update, context: CallbackContext) -> int:
		user_id = update.effective_user.id
		language = self.db.get_user_language(user_id) or 'en'

		if self.db.is_blacklisted(user_id):
			await update.message.reply_text(self.i18n.t('PASSWORD_BLACKLISTED', language))
			return ConversationHandler.END

		self.db.increment_command_usage('password', user_id, update.effective_chat.id)
		has_password = self.db.has_password(user_id)

		if has_password:
			await update.message.reply_text(self.i18n.t('PASSWORD_ENTER_CURRENT', language))
			return ENTERING_OLD_PASSWORD
		else:
			await update.message.reply_text(self.i18n.t('PASSWORD_CREATE_NEW', language))
			return ENTERING_NEW_PASSWORD

	async def old_password_received(self, update: Update, context: CallbackContext) -> int:
		user_id = update.effective_user.id
		language = self.db.get_user_language(user_id) or 'en'
		old_password = update.message.text.strip()

		if not self.db.verify_password(user_id, old_password):
			await update.message.reply_text(self.i18n.t('PASSWORD_INCORRECT', language))
			return ENTERING_OLD_PASSWORD

		await update.message.reply_text(self.i18n.t('PASSWORD_VERIFIED', language))
		return ENTERING_NEW_PASSWORD

	async def new_password_received(self, update: Update, context: CallbackContext) -> int:
		user_id = update.effective_user.id
		language = self.db.get_user_language(user_id) or 'en'
		new_password = update.message.text.strip()

		if len(new_password) < 8:
			await update.message.reply_text(self.i18n.t('PASSWORD_TOO_SHORT', language))
			return ENTERING_NEW_PASSWORD

		context.user_data['new_password'] = new_password
		await update.message.reply_text(self.i18n.t('PASSWORD_CONFIRM', language))
		return CONFIRMING_NEW_PASSWORD

	async def confirm_password_received(self, update: Update, context: CallbackContext) -> int:
		user_id = update.effective_user.id
		language = self.db.get_user_language(user_id) or 'en'
		confirm_password = update.message.text.strip()
		new_password = context.user_data.get('new_password')

		if confirm_password != new_password:
			await update.message.reply_text(self.i18n.t('PASSWORD_NO_MATCH', language))
			return ENTERING_NEW_PASSWORD

		success = self.db.update_password(user_id, new_password)

		if not success:
			await update.message.reply_text(self.i18n.t('PASSWORD_UPDATE_ERROR', language))
			return ConversationHandler.END

		await update.message.reply_text(self.i18n.t('PASSWORD_UPDATE_SUCCESS', language))
		context.user_data.clear()
		return ConversationHandler.END

	async def cancel_password_change(self, update: Update, context: CallbackContext) -> int:
		user_id = update.effective_user.id
		language = self.db.get_user_language(user_id) or 'en'

		await update.message.reply_text(self.i18n.t('PASSWORD_CANCELLED', language))
		context.user_data.clear()
		return ConversationHandler.END