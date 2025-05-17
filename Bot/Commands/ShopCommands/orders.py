import logging
import re
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CallbackContext, CommandHandler, ConversationHandler, CallbackQueryHandler, MessageHandler, Filters
from Bot.database import Database

# States for the conversation handler
VIEWING_ORDERS, SELECTING_ORDER, VIEWING_ORDER_DETAILS = range(3)

logger = logging.getLogger(__name__)

class OrdersCommand:
	def __init__(self):
		self.db = Database()

	def register_handlers(self, dispatcher):
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
		dispatcher.add_handler(conv_handler)

	def orders_command(self, update: Update, context: CallbackContext) -> int:
		"""Handle the /orders command to view user orders"""
		user_id = update.effective_user.id

		# Check if user is blacklisted
		if self.db.is_blacklisted(user_id):
			update.message.reply_text("You are not allowed to use this command.")
			return ConversationHandler.END

		# Log command usage
		self.db.increment_command_usage('orders', user_id, update.effective_chat.id)

		# Get user's orders
		orders = self.db.get_user_orders(user_id)

		if not orders:
			update.message.reply_text(
				"You don't have any orders yet.\n\n"
				"Use the /buy command to make a purchase."
			)
			return ConversationHandler.END

		# Create keyboard with order options
		keyboard = []
		for order in orders:
			status_emoji = self.get_status_emoji(order['status'])
			keyboard.append([InlineKeyboardButton(
				f"{status_emoji} Order #{order['id']} - {order['product_name']} ({order['status']})",
				callback_data=f"order_{order['id']}"
			)])

		# Add done button
		keyboard.append([InlineKeyboardButton("Done", callback_data="cancel")])

		reply_markup = InlineKeyboardMarkup(keyboard)

		update.message.reply_text(
			"Your Orders\n\n"
			"Select an order to view details:",
			reply_markup=reply_markup
		)

		return VIEWING_ORDERS

	def view_order(self, update: Update, context: CallbackContext) -> int:
		"""Handle order selection to view details"""
		query = update.callback_query
		query.answer()

		# Extract order ID from callback data
		order_id = int(query.data.split('_')[1])
		user_id = update.effective_user.id

		# Get order details
		order = self.db.get_order_by_id(user_id, order_id)

		if not order:
			query.edit_message_text("Sorry, this order could not be found.")
			return ConversationHandler.END

		# Create keyboard with options
		keyboard = []

		# Add cancel order button if order is pending
		if order['status'] == 'pending' or order['status'] == 'pending_payment':
			keyboard.append([InlineKeyboardButton(
				"Cancel Order",
				callback_data=f"cancel_order_{order_id}"
			)])

		# Add navigation buttons
		keyboard.append([
			InlineKeyboardButton("Back to Orders", callback_data="back"),
			InlineKeyboardButton("Done", callback_data="done")
		])

		reply_markup = InlineKeyboardMarkup(keyboard)

		# Format order details message
		status_emoji = self.get_status_emoji(order['status'])
		message = (
			f"{status_emoji} Order #{order['id']}\n\n"
			f"Product: {order['product_name']}\n"
			f"Quantity: {order['quantity']}\n"
			f"Total Price: {order['total_price']} TL\n"
			f"Status: {order['status']}\n"
			f"Order Date: {order['created_at']}\n\n"
		)

		if 'shipping_address' in order:
			message += (
				f"Shipping Address:\n"
				f"{order['shipping_address']['name']}\n"
				f"{order['shipping_address']['address']}\n"
				f"{order['shipping_address']['city']}\n\n"
			)

		if order['status'] == 'pending_payment':
			message += "⚠️ This order requires payment. Use /papara to add credits to your account."
		elif order['status'] == 'processing':
			message += "Your order is being processed and will be shipped soon."
		elif order['status'] == 'shipped':
			message += f"Your order has been shipped on {order.get('shipped_date', 'N/A')}."
		elif order['status'] == 'delivered':
			message += f"Your order was delivered on {order.get('delivery_date', 'N/A')}."
		elif order['status'] == 'cancelled':
			message += f"This order was cancelled on {order.get('cancelled_date', 'N/A')}."

		query.edit_message_text(
			message,
			reply_markup=reply_markup
		)

		return VIEWING_ORDER_DETAILS

	def back_to_orders(self, update: Update, context: CallbackContext) -> int:
		"""Go back to orders list"""
		query = update.callback_query
		query.answer()

		user_id = update.effective_user.id

		# Get user's orders
		orders = self.db.get_user_orders(user_id)

		# Create keyboard with order options
		keyboard = []
		for order in orders:
			status_emoji = self.get_status_emoji(order['status'])
			keyboard.append([InlineKeyboardButton(
				f"{status_emoji} Order #{order['id']} - {order['product_name']} ({order['status']})",
				callback_data=f"order_{order['id']}"
			)])

		# Add done button
		keyboard.append([InlineKeyboardButton("Done", callback_data="cancel")])

		reply_markup = InlineKeyboardMarkup(keyboard)

		query.edit_message_text(
			"Your Orders\n\n"
			"Select an order to view details:",
			reply_markup=reply_markup
		)

		return VIEWING_ORDERS

	def cancel_order(self, update: Update, context: CallbackContext) -> int:
		"""Handle order cancellation"""
		query = update.callback_query
		query.answer()

		# Extract order ID from callback data
		order_id = int(query.data.split('_')[2])
		user_id = update.effective_user.id

		# Cancel the order in database
		success = self.db.cancel_user_order(user_id, order_id)

		if not success:
			query.edit_message_text("Sorry, there was an error cancelling your order. Please try again later.")
			return ConversationHandler.END

		# Log user activity
		self.db.log_user_activity(
			user_id=user_id,
			action="cancel_order",
			details={"order_id": order_id}
		)

		query.edit_message_text(
			f"✅ Order #{order_id} has been cancelled successfully.\n\n"
			f"Any credits used for this order have been refunded to your account."
		)

		return ConversationHandler.END

	def cancel_orders(self, update: Update, context: CallbackContext) -> int:
		"""Exit the orders view"""
		if update.callback_query:
			update.callback_query.answer()
			update.callback_query.edit_message_text("Orders view closed.")
		else:
			update.message.reply_text("Orders view cancelled.")

		return ConversationHandler.END

	def get_status_emoji(self, status):
		"""Get emoji for order status"""
		status_emojis = {
			'pending': '⏳',
			'pending_payment': '💰',
			'processing': '🔄',
			'shipped': '📦',
			'delivered': '✅',
			'cancelled': '❌'
		}
		return status_emojis.get(status, '❓')
