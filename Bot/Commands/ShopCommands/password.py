import logging
import re
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
	Application,
	CallbackContext,
	CommandHandler,
	ConversationHandler,
	CallbackQueryHandler,
	MessageHandler,
	filters
)
from Bot.database import Database

# States for the conversation handler
ENTERING_OLD_PASSWORD, ENTERING_NEW_PASSWORD, CONFIRMING_PASSWORD = range(3)

logger = logging.getLogger(__name__)

class PasswordCommand:
	def __init__(self):
		self.db = Database()

	def register_handlers(self, application: Application):
		# Create a conversation handler for the password command
		conv_handler = ConversationHandler(
			entry_points=[CommandHandler('password', self.password_command)],
			states={
				ENTERING_OLD_PASSWORD: [
					MessageHandler(filters.Text() & ~filters.COMMAND, self.old_password_received),
					CommandHandler('cancel', self.cancel_password_change)
				],
				ENTERING_NEW_PASSWORD: [
					MessageHandler(filters.Text() & ~filters.COMMAND, self.new_password_received),
					CommandHandler('cancel', self.cancel_password_change)
				],
				CONFIRMING_PASSWORD: [
					MessageHandler(filters.Text() & ~filters.COMMAND, self.confirm_password_received),
					CommandHandler('cancel', self.cancel_password_change)
				]
			},
			fallbacks=[CommandHandler('cancel', self.cancel_password_change)]
		)
		application.add_handler(conv_handler)

	async def password_command(self, update: Update, context: CallbackContext) -> int:
		"""Handle the /password command to change user password"""
		user_id = update.effective_user.id

		# Check if user is blacklisted
		if self.db.is_blacklisted(user_id):
			await update.message.reply_text("You are not allowed to use this command.")
			return ConversationHandler.END

		# Log command usage
		self.db.increment_command_usage('password', user_id, update.effective_chat.id)

		# Check if user has a password set
		has_password = self.db.user_has_password(user_id)

		if has_password:
			await update.message.reply_text(
				"You're about to change your password.\n\n"
				"First, please enter your current password:\n\n"
				"(Send /cancel to abort this operation)"
			)
			return ENTERING_OLD_PASSWORD
		else:
			await update.message.reply_text(
				"You don't have a password set yet.\n\n"
				"Please create a new password:\n\n"
				"(Send /cancel to abort this operation)"
			)
			return ENTERING_NEW_PASSWORD

	async def old_password_received(self, update: Update, context: CallbackContext) -> int:
		"""Handle receiving the old password"""
		user_id = update.effective_user.id
		old_password = update.message.text

		# Delete the message containing the password for security
		try:
			await update.message.delete()
		except Exception as e:
			logger.warning(f"Could not delete password message: {e}")

		# Verify old password
		if not self.db.verify_password(user_id, old_password):
			await update.message.reply_text(
				"❌ Incorrect password. Please try again or send /cancel to abort."
			)
			return ENTERING_OLD_PASSWORD

		await update.message.reply_text(
			"Password verified.\n\n"
			"Please enter your new password:\n\n"
			"(Send /cancel to abort this operation)"
		)

		return ENTERING_NEW_PASSWORD

	async def new_password_received(self, update: Update, context: CallbackContext) -> int:
		"""Handle receiving the new password"""
		new_password = update.message.text

		# Delete the message containing the password for security
		try:
			await update.message.delete()
		except Exception as e:
			logger.warning(f"Could not delete password message: {e}")

		# Validate password strength
		if len(new_password) < 8:
			await update.message.reply_text(
				"Password is too short. Please use at least 8 characters.\n\n"
				"Enter a stronger password:"
			)
			return ENTERING_NEW_PASSWORD

		# Store new password in context
		context.user_data['new_password'] = new_password

		await update.message.reply_text(
			"Please confirm your new password by entering it again:\n\n"
			"(Send /cancel to abort this operation)"
		)

		return CONFIRMING_PASSWORD

	async def confirm_password_received(self, update: Update, context: CallbackContext) -> int:
		"""Handle password confirmation"""
		user_id = update.effective_user.id
		confirm_password = update.message.text
		new_password = context.user_data.get('new_password', '')

		# Delete the message containing the password for security
		try:
			await update.message.delete()
		except Exception as e:
			logger.warning(f"Could not delete password message: {e}")

		# Check if passwords match
		if confirm_password != new_password:
			await update.message.reply_text(
				"❌ Passwords don't match. Please try again.\n\n"
				"Enter your new password:"
			)
			return ENTERING_NEW_PASSWORD

		# Update password in database
		success = self.db.update_user_password(user_id, new_password)

		if not success:
			await update.message.reply_text(
				"Sorry, there was an error updating your password. Please try again later."
			)
			return ConversationHandler.END

		# Log user activity
		self.db.log_user_activity(
			user_id=user_id,
			action="change_password",
			details={"success": True}
		)

		# Clear sensitive data from context
		if 'new_password' in context.user_data:
			del context.user_data['new_password']

		await update.message.reply_text(
			"✅ Password updated successfully!\n\n"
			"You can use your new password to log in to the web dashboard."
		)

		return ConversationHandler.END

	async def cancel_password_change(self, update: Update, context: CallbackContext) -> int:
		"""Cancel the password change process"""
		# Clear sensitive data from context
		if 'new_password' in context.user_data:
			del context.user_data['new_password']

		await update.message.reply_text("Password change cancelled.")
		return ConversationHandler.END