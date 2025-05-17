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
VIEWING_ORDERS, SELECTING_ORDER, VIEWING_ORDER_DETAILS = range(3)

logger = logging.getLogger(__name__)

class OrdersCommand:
	def __init__(self):
		self.db = Database()

	def register_handlers(self, application: Application):
		# Create a conversation handler for the orders command
		conv_handler = ConversationHandler(
			entry_points=[CommandHandler('orders', self.orders_command)],
			states={
				VIEWING_ORDERS: [
					CallbackQueryHandler(self.view_order, pattern=r'^order_\d+$'),
					CallbackQueryHandler(self.cancel_orders, pattern=r'^cancel$')
				],
				VIEWING_ORDER_DETAILS: [
					CallbackQueryHandler(self.back_to_orders, pattern=r'^back$'),
					CallbackQueryHandler(self.cancel_order, pattern=r'^cancel_order_\d+$'),
					CallbackQueryHandler(self.cancel_orders, pattern=r'^done$')
				]
			},
			fallbacks=[CommandHandler('cancel', self.cancel_orders)]
		)
		application.add_handler(conv_handler)

	async def orders_command(self, update: Update, context: CallbackContext) -> int:
		"""Handle the /orders command to view user orders"""
		user_id = update.effective_user.id

		# Check if user is blacklisted
		if self.db.is_blacklisted(user_id):
			await update.message.reply_text("You are not allowed Ascending order (most recent first): 1. **ERROR:Bot.admin_panel:Failed to register PaparaCommand handlers: PaparaPaymentHandler.__init__() missing 1 required positional argument: 'db_connection'**
   - This error occurs because the `PaparaPaymentHandler` class in `papara.py` requires a `db_connection` parameter, which is not provided when instantiated. The solution is to pass the `Database` instance to `PaparaPaymentHandler`.

2. **ERROR:Bot.database:Error closing database connection: weakly-referenced object no longer exists**
   - This error indicates that the database connection is being closed prematurely or multiple `Database` instances are created, leading to garbage collection issues. A singleton pattern with connection pooling is implemented to manage connections.

3. **Inconsistent Telegram Bot Framework Usage**
   - The provided command files (`password.py`, `buy.py`, `address.py`, `orders.py`) use the older `Dispatcher` and synchronous methods, while `bastet.py` and the error logs suggest `python-telegram-bot` v20.0+, which uses `Application` and async methods. All command files are updated to use `Application` and async methods for consistency.

---

### Updated Files

Below are the corrected versions of the affected files, incorporating the fixes for the `PaparaPaymentHandler` initialization, database connection management, and Telegram bot framework compatibility.

#### 1. `papara.py`

The primary issue is the missing `db_connection` argument in `PaparaPaymentHandler`. We pass the `Database` instance and update the file for `python-telegram-bot` v20.0+ compatibility.

<xaiArtifact artifact_id="66b51e0b-9579-4b79-88b3-c6b2ccd8d081" artifact_version_id="e5f07e12-70cf-4ed8-acf6-827cf9c7402a" title="papara.py" contentType="text/python">
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
	filters,
)
from Bot.database import Database
from Bot.Helpers.papara_integration import PaparaPaymentHandler

# States for the conversation handler
SELECTING_ACTION, ENTERING_AMOUNT, CONFIRMING_PAYMENT, CHECKING_PAYMENT = range(4)

logger = logging.getLogger(__name__)

class PaparaCommand:
	def __init__(self):
		self.db = Database()
		self.papara_handler = PaparaPaymentHandler(db_connection=self.db)

	def register_handlers(self, application: Application):
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
		application.add_handler(conv_handler)

	async def papara_command(self, update: Update, context: CallbackContext) -> int:
		"""Handle the /papara command for payment operations"""
		user_id = update.effective_user.id

		# Check if user is blacklisted
		if self.db.is_blacklisted(user_id):
			await update.message.reply_text("You are not allowed to use this command.")
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

		await update.message.reply_text(
			"Papara Payment System\n\n"
			"What would you like to do?",
			reply_markup=reply_markup
		)

		return SELECTING_ACTION

	async def add_credits(self, update: Update, context: CallbackContext) -> int:
		"""Start the process of adding credits"""
		query = update.callback_query
		await query.answer()

		await query.edit_message_text(
			"Adding Credits\n\n"
			"Please enter the amount in TL you want to add to your account:\n"
			"(Minimum: 10 TL, Maximum: 1000 TL)"
		)

		return ENTERING_AMOUNT

	async def amount_received(self, update: Update, context: CallbackContext) -> int:
		"""Handle receiving the payment amount"""
		try:
			amount = float(update.message.text.strip())

			# Validate amount
			if amount < 10:
				await update.message.reply_text(
					"The minimum amount is 10 TL. Please enter a larger amount."
				)
				return ENTERING_AMOUNT

			if amount > 1000:
				await update.message.reply_text(
					"The maximum amount is 1000 TL. Please enter a smaller amount."
				)
				return ENTERING_AMOUNT

			# Store amount in context
			context.user_data['payment_amount'] = amount

			# Generate payment details
			user_id = update.effective_user.id
			payment_details = self.db.create_papara_payment(user_id, amount)

			if not payment_details:
				await update.message.reply_text(
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

			await update.message.reply_text(
				f"Payment Details\n\n"
				f"Amount: {amount} TL\n"
				f"Recipient: {payment_details['recipient_name']}\n"
				f"Papara Number: {payment_details['papara_number']}\n\n"
				f"Please confirm this payment request:",
				reply_markup=reply_markup
			)

			return CONFIRMING_PAYMENT

		except ValueError:
			await update.message.reply_text("Please enter a valid number.")
			return ENTERING_AMOUNT

	async def confirm_payment(self, update: Update, context: CallbackContext) -> int:
		"""Handle payment confirmation"""
		query = update.callback_query
		await query.answer()

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

		await query.edit_message_text(
			f"✅ Payment request created successfully!\n\n"
			f"Payment ID: #{payment_details['payment_id']}\n"
			f"Amount: {amount} TL\n"
			f"Recipient: {payment_details['recipient_name']}\n"
			f"Papara Number: {payment_details['papara_number']}\n"
			f"Reference: {payment_details['reference']}\n\n"
			f"Please make the payment using the Papara app or website, then use the 'Check Payment Status' option with your payment reference to confirm your payment."
		)

		return ConversationHandler.END

	async def check_payment(self, update: Update, context: CallbackContext) -> int:
		"""Start the process of checking payment status"""
		query = update.callback_query
		await query.answer()

		await query.edit_message_text(
			"Check Payment Status\n\n"
			"Please enter your payment reference or payment ID:"
		)

		return CHECKING_PAYMENT

	async def payment_reference_received(self, update: Update, context: CallbackContext) -> int:
		"""Handle receiving the payment reference"""
		user_id = update.effective_user.id
		payment_ref = update.message.text.strip()

		# Check payment status
		payment_status = self.db.check_papara_payment_status(user_id, payment_ref)

		if not payment_status:
			await update.message.reply_text(
				"Sorry, we couldn't find a payment with that reference. Please check and try again."
			)
			return ConversationHandler.END

		if payment_status['status'] == 'completed':
			# Payment is already completed
			amount = payment_status['amount']

			await update.message.reply_text(
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

				await update.message.reply_text(
					f"✅ Payment verified and processed!\n\n"
					f"Payment ID: #{payment_status['id']}\n"
					f"Amount: {amount} TL\n"
					f"Credits Added: {int(amount)}\n\n"
					f"Your account has been credited. Thank you for your payment!"
				)
			else:
				await update.message.reply_text(
					f"⏳ Payment is still pending\n\n"
					f"Payment ID: #{payment_status['id']}\n"
					f"Amount: {payment_status['amount']} TL\n\n"
					f"Please complete the payment using the Papara app or website, then check again."
				)
		elif payment_status['status'] == 'cancelled':
			await update.message.reply_text(
				f"❌ Payment was cancelled\n\n"
				f"Payment ID: #{payment_status['id']}\n"
				f"Amount: {payment_status['amount']} TL\n\n"
				f"This payment request has been cancelled. Please create a new payment if needed."
			)
		else:
			await update.message.reply_text(
				f"❓ Unknown payment status\n\n"
				f"Payment ID: #{payment_status['id']}\n"
				f"Status: {payment_status['status']}\n\n"
				f"Please contact support for assistance."
			)

		return ConversationHandler.END

	async def view_balance(self, update: Update, context: CallbackContext) -> int:
		"""Show user's current balance"""
		query = update.callback_query
		await query.answer()

		user_id = update.effective_user.id
		credits = self.db.get_user_credits(user_id)

		await query.edit_message_text(
			f"Your Current Balance\n\n"
			f"Credits: {credits} TL\n\n"
			f"You can use these credits to purchase products or services."
		)

		return ConversationHandler.END

	async def cancel_papara(self, update: Update, context: CallbackContext) -> int:
		"""Cancel the papara payment process"""
		if update.callback_query:
			await update.callback_query.answer()
			await update.callback_query.edit_message_text("Payment operation cancelled.")
		else:
			await update.message.reply_text("Payment operation cancelled.")

		# Clear user data
		context.user_data.clear()

		return ConversationHandler.END