import logging
import re
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CallbackContext, CommandHandler, ConversationHandler, CallbackQueryHandler, MessageHandler, filters
from Bot.database import Database

# States for the conversation handler
SELECTING_PRODUCT, CONFIRMING_PURCHASE, SELECTING_QUANTITY, SELECTING_ADDRESS = range(4)

logger = logging.getLogger(__name__)

class BuyCommand:
	def __init__(self):
		self.db = Database()

	def register_handlers(self, dispatcher):
		# Create a conversation handler for the buy command
		conv_handler = ConversationHandler(
			entry_points=[CommandHandler('buy', self.buy_command)],
			states={
				SELECTING_PRODUCT: [
					CallbackQueryHandler(self.product_selected, pattern=r'^product_\d+$'),
					CallbackQueryHandler(self.cancel_purchase, pattern=r'^cancel$')
				],
				SELECTING_QUANTITY: [
					MessageHandler(filters.text & ~filters.command, self.quantity_selected),
					CallbackQueryHandler(self.cancel_purchase, pattern=r'^cancel$')
				],
				SELECTING_ADDRESS: [
					CallbackQueryHandler(self.address_selected, pattern=r'^address_\d+$'),
					CallbackQueryHandler(self.cancel_purchase, pattern=r'^cancel$')
				],
				CONFIRMING_PURCHASE: [
					CallbackQueryHandler(self.confirm_purchase, pattern=r'^confirm$'),
					CallbackQueryHandler(self.cancel_purchase, pattern=r'^cancel$')
				]
			},
			fallbacks=[CommandHandler('cancel', self.cancel_purchase)]
		)
		dispatcher.add_handler(conv_handler)

	def buy_command(self, update: Update, context: CallbackContext) -> int:
		"""Handle the /buy command to start the purchase process"""
		user_id = update.effective_user.id

		# Check if user is blacklisted
		if self.db.is_blacklisted(user_id):
			update.message.reply_text("You are not allowed to use this command.")
			return ConversationHandler.END

		# Log command usage
		self.db.increment_command_usage('buy', user_id, update.effective_chat.id)

		# Get available products
		products = self.db.get_available_products(active_only=True)

		if not products:
			update.message.reply_text("No products are currently available for purchase.")
			return ConversationHandler.END

		# Create keyboard with product options
		keyboard = []
		for product in products:
			keyboard.append([InlineKeyboardButton(
				f"{product['name']} - {product['price']} TL",
				callback_data=f"product_{product['id']}"
			)])

		# Add cancel button
		keyboard.append([InlineKeyboardButton("Cancel", callback_data="cancel")])

		reply_markup = InlineKeyboardMarkup(keyboard)

		update.message.reply_text(
			"Please select a product to purchase:",
			reply_markup=reply_markup
		)

		return SELECTING_PRODUCT

	def product_selected(self, update: Update, context: CallbackContext) -> int:
		"""Handle product selection"""
		query = update.callback_query
		query.answer()

		# Extract product ID from callback data
		product_id = int(query.data.split('_')[1])

		# Get product details
		product = self.db.get_product_by_id(product_id)

		if not product:
			query.edit_message_text("Sorry, this product is no longer available.")
			return ConversationHandler.END

		# Store product in context for later use
		context.user_data['selected_product'] = product

		# If product has limited quantity, ask for quantity
		if product['quantity'] is not None:
			query.edit_message_text(
				f"You selected: {product['name']}\n"
				f"Price: {product['price']} TL\n"
				f"Available: {product['quantity']}\n\n"
				f"How many would you like to purchase? (1-{min(product['quantity'], 10)})"
			)
			return SELECTING_QUANTITY
		else:
			# For digital products with unlimited quantity, default to 1
			context.user_data['selected_quantity'] = 1

			# Get user's addresses
			addresses = self.db.get_user_addresses(update.effective_user.id)

			if not addresses:
				query.edit_message_text(
					f"You selected: {product['name']}\n"
					f"Price: {product['price']} TL\n\n"
					f"You don't have any saved addresses. Please use /address to add one first."
				)
				return ConversationHandler.END

			# Create keyboard with address options
			keyboard = []
			for address in addresses:
				keyboard.append([InlineKeyboardButton(
					f"{address['name']}: {address['city']}",
					callback_data=f"address_{address['id']}"
				)])

			# Add cancel button
			keyboard.append([InlineKeyboardButton("Cancel", callback_data="cancel")])

			reply_markup = InlineKeyboardMarkup(keyboard)

			query.edit_message_text(
				f"You selected: {product['name']}\n"
				f"Price: {product['price']} TL\n"
				f"Quantity: 1\n\n"
				f"Please select a delivery address:",
				reply_markup=reply_markup
			)

			return SELECTING_ADDRESS

	def quantity_selected(self, update: Update, context: CallbackContext) -> int:
		"""Handle quantity selection"""
		try:
			quantity = int(update.message.text.strip())
			product = context.user_data['selected_product']

			# Validate quantity
			if quantity < 1:
				update.message.reply_text("Please enter a positive number.")
				return SELECTING_QUANTITY

			if quantity > min(product['quantity'], 10):
				update.message.reply_text(
					f"Maximum allowed quantity is {min(product['quantity'], 10)}. "
					f"Please enter a smaller number."
				)
				return SELECTING_QUANTITY

			# Store quantity in context
			context.user_data['selected_quantity'] = quantity

			# Get user's addresses
			addresses = self.db.get_user_addresses(update.effective_user.id)

			if not addresses:
				update.message.reply_text(
					f"You don't have any saved addresses. Please use /address to add one first."
				)
				return ConversationHandler.END

			# Create keyboard with address options
			keyboard = []
			for address in addresses:
				keyboard.append([InlineKeyboardButton(
					f"{address['name']}: {address['city']}",
					callback_data=f"address_{address['id']}"
				)])

			# Add cancel button
			keyboard.append([InlineKeyboardButton("Cancel", callback_data="cancel")])

			reply_markup = InlineKeyboardMarkup(keyboard)

			update.message.reply_text(
				f"You selected: {product['name']}\n"
				f"Price: {product['price']} TL\n"
				f"Quantity: {quantity}\n"
				f"Total: {float(product['price']) * quantity} TL\n\n"
				f"Please select a delivery address:",
				reply_markup=reply_markup
			)

			return SELECTING_ADDRESS

		except ValueError:
			update.message.reply_text("Please enter a valid number.")
			return SELECTING_QUANTITY

	def address_selected(self, update: Update, context: CallbackContext) -> int:
		"""Handle address selection"""
		query = update.callback_query
		query.answer()

		user_id = update.effective_user.id

		# Extract address ID from callback data
		address_id = query.data.split('_')[1]

		# Get address details
		address = self.db.get_address_by_id(user_id, address_id)

		if not address:
			query.edit_message_text("Sorry, this address is no longer available.")
			return ConversationHandler.END

		# Store address in context
		context.user_data['selected_address'] = address

		# Get product and quantity from context
		product = context.user_data['selected_product']
		quantity = context.user_data['selected_quantity']
		total_price = float(product['price']) * quantity

		# Create confirmation keyboard
		keyboard = [
			[
				InlineKeyboardButton("Confirm", callback_data="confirm"),
				InlineKeyboardButton("Cancel", callback_data="cancel")
			]
		]
		reply_markup = InlineKeyboardMarkup(keyboard)

		query.edit_message_text(
			f"Order Summary:\n\n"
			f"Product: {product['name']}\n"
			f"Price: {product['price']} TL\n"
			f"Quantity: {quantity}\n"
			f"Total: {total_price} TL\n\n"
			f"Delivery Address:\n"
			f"{address['name']}\n"
			f"{address['address']}\n"
			f"{address['city']}\n\n"
			f"Please confirm your order:",
			reply_markup=reply_markup
		)

		return CONFIRMING_PURCHASE

	def confirm_purchase(self, update: Update, context: CallbackContext) -> int:
		"""Handle purchase confirmation"""
		query = update.callback_query
		query.answer()

		user_id = update.effective_user.id
		product = context.user_data['selected_product']
		quantity = context.user_data['selected_quantity']
		address = context.user_data['selected_address']
		total_price = float(product['price']) * quantity

		# Check if user has enough credits
		user_credits = self.db.get_user_credits(user_id)

		if user_credits < total_price:
			query.edit_message_text(
				f"You don't have enough credits for this purchase.\n"
				f"Required: {total_price} TL\n"
				f"Your balance: {user_credits} TL\n\n"
				f"Please use /papara to add credits to your account."
			)
			return ConversationHandler.END

		# Create order in database
		order_id = self.db.create_order(
			user_id=user_id,
			product_id=product['id'],
			quantity=quantity,
			address_id=address['id'],
			total_price=total_price
		)

		if not order_id:
			query.edit_message_text("Sorry, there was an error processing your order. Please try again later.")
			return ConversationHandler.END

		# Deduct credits from user
		self.db.add_credits(user_id, -int(total_price))

		# Update product quantity if applicable
		if product['quantity'] is not None:
			self.db.update_product_quantity(product['id'], product['quantity'] - quantity)

		# Log user activity
		self.db.log_user_activity(
			user_id=user_id,
			action="purchase",
			details={
				"product_id": product['id'],
				"product_name": product['name'],
				"quantity": quantity,
				"total_price": float(total_price),
				"order_id": order_id
			}
		)

		query.edit_message_text(
			f"🎉 Order placed successfully! 🎉\n\n"
			f"Order ID: #{order_id}\n"
			f"Product: {product['name']}\n"
			f"Quantity: {quantity}\n"
			f"Total: {total_price} TL\n\n"
			f"Your order will be processed shortly. You can check the status with /orders."
		)

		return ConversationHandler.END

	def cancel_purchase(self, update: Update, context: CallbackContext) -> int:
		"""Cancel the purchase process"""
		if update.callback_query:
			update.callback_query.answer()
			update.callback_query.edit_message_text("Purchase cancelled.")
		else:
			update.message.reply_text("Purchase cancelled.")

		# Clear user data
		context.user_data.clear()

		return ConversationHandler.END
