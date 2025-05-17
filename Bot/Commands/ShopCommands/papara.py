import logging
import re
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CallbackContext, CommandHandler, ConversationHandler, CallbackQueryHandler, MessageHandler, filters
from Bot.database import Database
from Bot.Helpers.papara_integration import PaparaPaymentHandler

# States for the conversation handler
SELECTING_ACTION, ENTERING_AMOUNT, CONFIRMING_PAYMENT, CHECKING_PAYMENT = range(4)

logger = logging.getLogger(__name__)

class PaparaCommand:
	def __init__(self):
		self.db = Database()
		self.papara_handler = PaparaPaymentHandler()

	def register_handlers(self, dispatcher):
		# Create a conversation handler for the papara command
		conv_handler = ConversationHandler(
			entry_points=[CommandHandler('papara', self.papara_command)],
			states={
				SELECTING_ACTION: [
					CallbackQueryHandler(self.add_credits, pattern=r'^add$'),
					CallbackQueryHandler(self.check_payment, pattern=r'^check$'),
					CallbackQueryHandler(self.view_balance, pattern=r'^balance$'),
					CallbackQueryHandler(self.cancel_papara, pattern=r'^cancel$')
				],
				ENTERING_AMOUNT: [
					MessageHandler(filters.Text() & ~filters.COMMAND, self.amount_received),
					CallbackQueryHandler(self.cancel_papara, pattern=r'^cancel$')
				],
				CONFIRMING_PAYMENT: [
					CallbackQueryHandler(self.confirm_payment, pattern=r'^confirm$'),
					CallbackQueryHandler(self.cancel_papara, pattern=r'^cancel$')
				],
				CHECKING_PAYMENT: [
					MessageHandler(filters.Text() & ~filters.COMMAND, self.payment_reference_received),
					CallbackQueryHandler(self.cancel_papara, pattern=r'^cancel$')
				]
			},
			fallbacks=[CommandHandler('cancel', self.cancel_papara)]
		)
		dispatcher.add_handler(conv_handler)

	def papara_command(self, update: Update, context: CallbackContext) -> int:
		"""Handle the /papara command for payment operations"""
		user_id = update.effective_user.id

		# Check if user is blacklisted
		if self.db.is_blacklisted(user_id):
			update.message.reply_text("You are not allowed to use this command.")
			return ConversationHandler.END

		# Log command usage
		self.db.increment_command_usage('papara', user_id, update.effective_chat.id)

		# Create keyboard with payment options
		keyboard = [
			[InlineKeyboardButton("Add Credits", callback_data="add")],
			[InlineKeyboardButton("Check Payment Status", callback_data="check")],
			[InlineKeyboardButton("View Balance", callback_data="balance")],
			[InlineKeyboardButton("Cancel", callback_data="cancel")]
		]

		reply_markup = InlineKeyboardMarkup(keyboard)

		update.message.reply_text(
			"Papara Payment System\n\n"
			"What would you like to do?",
			reply_markup=reply_markup
		)

		return SELECTING_ACTION

	def add_credits(self, update: Update, context: CallbackContext) -> int:
		"""Start the process of adding credits"""
		query = update.callback_query
		query.answer()

		query.edit_message_text(
			"Adding Credits\n\n"
			"Please enter the amount in TL you want to add to your account:\n"
			"(Minimum: 10 TL, Maximum: 1000 TL)"
		)

		return ENTERING_AMOUNT

	def amount_received(self, update: Update, context: CallbackContext) -> int:
		"""Handle receiving the payment amount"""
		try:
			amount = float(update.message.text.strip())

			# Validate amount
			if amount < 10:
				update.message.reply_text(
					"The minimum amount is 10 TL. Please enter a larger amount."
				)
				return ENTERING_AMOUNT

			if amount > 1000:
				update.message.reply_text(
					"The maximum amount is 1000 TL. Please enter a smaller amount."
				)
				return ENTERING_AMOUNT

			# Store amount in context
			context.user_data['payment_amount'] = amount

			# Generate payment details
			user_id = update.effective_user.id
			payment_details = self.db.create_papara_payment(user_id, amount)

			if not payment_details:
				update.message.reply_text(
					"Sorry, there was an error generating your payment request. Please try again later."
				)
				return ConversationHandler.END

			# Store payment details in context
			context.user_data['payment_details'] = payment_details

			# Create confirmation keyboard
			keyboard = [
				[
					InlineKeyboardButton("Confirm", callback_data="confirm"),
					InlineKeyboardButton("Cancel", callback_data="cancel")
				]
			]
			reply_markup = InlineKeyboardMarkup(keyboard)

			update.message.reply_text(
				f"Payment Details\n\n"
				f"Amount: {amount} TL\n"
				f"Recipient: {payment_details['recipient_name']}\n"
				f"Papara Number: {payment_details['papara_number']}\n\n"
				f"Please confirm this payment request:",
				reply_markup=reply_markup
			)

			return CONFIRMING_PAYMENT

		except ValueError:
			update.message.reply_text("Please enter a valid number.")
			return ENTERING_AMOUNT

	def confirm_payment(self, update: Update, context: CallbackContext) -> int:
		"""Handle payment confirmation"""
		query = update.callback_query
		query.answer()

		user_id = update.effective_user.id
		payment_details = context.user_data['payment_details']
		amount = context.user_data['payment_amount']

		# Log user activity
		self.db.log_user_activity(
			user_id=user_id,
			action="create_payment",
			details={
				"payment_id": payment_details['payment_id'],
				"amount": amount
			}
		)

		query.edit_message_text(
			f"✅ Payment request created successfully!\n\n"
			f"Payment ID: #{payment_details['payment_id']}\n"
			f"Amount: {amount} TL\n"
			f"Recipient: {payment_details['recipient_name']}\n"
			f"Papara Number: {payment_details['papara_number']}\n"
			f"Reference: {payment_details['reference']}\n\n"
			f"Please make the payment using the Papara app or website, then use the 'Check Payment Status' option with your payment reference to confirm your payment."
		)

		return ConversationHandler.END

	def check_payment(self, update: Update, context: CallbackContext) -> int:
		"""Start the process of checking payment status"""
		query = update.callback_query
		query.answer()

		query.edit_message_text(
			"Check Payment Status\n\n"
			"Please enter your payment reference or payment ID:"
		)

		return CHECKING_PAYMENT

	def payment_reference_received(self, update: Update, context: CallbackContext) -> int:
		"""Handle receiving the payment reference"""
		user_id = update.effective_user.id
		payment_ref = update.message.text.strip()

		# Check payment status
		payment_status = self.db.check_papara_payment_status(user_id, payment_ref)

		if not payment_status:
			update.message.reply_text(
				"Sorry, we couldn't find a payment with that reference. Please check and try again."
			)
			return ConversationHandler.END

		if payment_status['status'] == 'completed':
			# Payment is already completed
			amount = payment_status['amount']

			update.message.reply_text(
				f"✅ Payment confirmed!\n\n"
				f"Payment ID: #{payment_status['id']}\n"
				f"Amount: {amount} TL\n"
				f"Credits Added: {int(amount)}\n\n"
				f"Your account has been credited. Thank you for your payment!"
			)
		elif payment_status['status'] == 'pending':
			# Try to verify the payment
			if self.db.verify_papara_payment(payment_ref):
				# Payment was verified and processed
				payment_status = self.db.check_papara_payment_status(user_id, payment_ref)
				amount = payment_status['amount']

				update.message.reply_text(
					f"✅ Payment verified and processed!\n\n"
					f"Payment ID: #{payment_status['id']}\n"
					f"Amount: {amount} TL\n"
					f"Credits Added: {int(amount)}\n\n"
					f"Your account has been credited. Thank you for your payment!"
				)
			else:
				update.message.reply_text(
					f"⏳ Payment is still pending\n\n"
					f"Payment ID: #{payment_status['id']}\n"
					f"Amount: {payment_status['amount']} TL\n\n"
					f"Please complete the payment using the Papara app or website, then check again."
				)
		elif payment_status['status'] == 'cancelled':
			update.message.reply_text(
				f"❌ Payment was cancelled\n\n"
				f"Payment ID: #{payment_status['id']}\n"
				f"Amount: {payment_status['amount']} TL\n\n"
				f"This payment request has been cancelled. Please create a new payment if needed."
			)
		else:
			update.message.reply_text(
				f"❓ Unknown payment status\n\n"
				f"Payment ID: #{payment_status['id']}\n"
				f"Status: {payment_status['status']}\n\n"
				f"Please contact support for assistance."
			)

		return ConversationHandler.END

	def view_balance(self, update: Update, context: CallbackContext) -> int:
		"""Show user's current balance"""
		query = update.callback_query
		query.answer()

		user_id = update.effective_user.id
		credits = self.db.get_user_credits(user_id)

		query.edit_message_text(
			f"Your Current Balance\n\n"
			f"Credits: {credits} TL\n\n"
			f"You can use these credits to purchase products or services."
		)

		return ConversationHandler.END

	def cancel_papara(self, update: Update, context: CallbackContext) -> int:
		"""Cancel the papara payment process"""
		if update.callback_query:
			update.callback_query.answer()
			update.callback_query.edit_message_text("Payment operation cancelled.")
		else:
			update.message.reply_text("Payment operation cancelled.")

		# Clear user data
		context.user_data.clear()

		return ConversationHandler.END
