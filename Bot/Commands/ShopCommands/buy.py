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
from Bot.Helpers.i18n import I18n

# States for the conversation handler
SELECTING_PRODUCT, CONFIRMING_PURCHASE, SELECTING_QUANTITY, SELECTING_ADDRESS = range(4)

logger = logging.getLogger(__name__)

class BuyCommand:
	def __init__(self):
		self.db = Database()
		self.i18n = I18n()

	def register_handlers(self, application: Application):
		conv_handler = ConversationHandler(
			entry_points=[CommandHandler('buy', self.buy_command)],
			states={
				SELECTING_PRODUCT: [
					CallbackQueryHandler(self.product_selected, pattern=r'^product_\d+$'),
					CallbackQueryHandler(self.cancel_purchase, pattern=r'^cancel$')
				],
				SELECTING_QUANTITY: [
					MessageHandler(filters.Text() & ~filters.COMMAND, self.quantity_selected),
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
		application.add_handler(conv_handler)

	async def buy_command(self, update: Update, context: CallbackContext) -> int:
		"""Handle the /buy command to start the purchase process"""
		user_id = update.effective_user.id
		language = self.db.get_user_language(user_id) or 'en'

		if self.db.is_blacklisted(user_id):
			await update.message.reply_text(self.i18n.t('BUY_BLACKLISTED', language))
			return ConversationHandler.END

		self.db.increment_command_usage('buy', user_id, update.effective_chat.id)
		products = self.db.get_available_products(active_only=True)

		if not products:
			await update.message.reply_text(self.i18n.t('BUY_NO_PRODUCTS', language))
			return ConversationHandler.END

		keyboard = []
		for product in products:
			keyboard.append([InlineKeyboardButton(
				f"{product['name']} - {product['price']} TL",
				callback_data=f"product_{product['id']}"
			)])
		keyboard.append([InlineKeyboardButton(self.i18n.t('CANCEL_BUTTON', language), callback_data="cancel")])
		reply_markup = InlineKeyboardMarkup(keyboard)

		await update.message.reply_text(
			self.i18n.t('BUY_SELECT_PRODUCT', language),
			reply_markup=reply_markup
		)
		return SELECTING_PRODUCT

	async def product_selected(self, update: Update, context: CallbackContext) -> int:
		"""Handle product selection"""
		query = update.callback_query
		await query.answer()
		user_id = update.effective_user.id
		language = self.db.get_user_language(user_id) or 'en'

		product_id = int(query.data.split('_')[1])
		product = self.db.get_product_by_id(product_id)

		if not product:
			await query.edit_message_text(self.i18n.t('BUY_PRODUCT_UNAVAILABLE', language))
			return ConversationHandler.END

		context.user_data['selected_product'] = product

		if product['quantity'] is not None:
			await query.edit_message_text(
				self.i18n.t('BUY_QUANTITY_PROMPT', language, product_name=product['name'], price=product['price'], quantity=product['quantity'], max_quantity=min(product['quantity'], 10))
			)
			return SELECTING_QUANTITY
		else:
			context.user_data['selected_quantity'] = 1
			addresses = self.db.get_user_addresses(user_id)

			if not addresses:
				await query.edit_message_text(
					self.i18n.t('BUY_NO_ADDRESSES', language, product_name=product['name'], price=product['price'])
				)
				return ConversationHandler.END

			keyboard = []
			for address in addresses:
				keyboard.append([InlineKeyboardButton(
					f"{address['name']}: {address['city']}",
					callback_data=f"address_{address['id']}"
				)])
			keyboard.append([InlineKeyboardButton(self.i18n.t('CANCEL_BUTTON', language), callback_data="cancel")])
			reply_markup = InlineKeyboardMarkup(keyboard)

			await query.edit_message_text(
				self.i18n.t('BUY_SELECT_ADDRESS', language, product_name=product['name'], price=product['price']),
				reply_markup=reply_markup
			)
			return SELECTING_ADDRESS

	async def quantity_selected(self, update: Update, context: CallbackContext) -> int:
		"""Handle quantity selection"""
		user_id = update.effective_user.id
		language = self.db.get_user_language(user_id) or 'en'
		try:
			quantity = int(update.message.text.strip())
			product = context.user_data['selected_product']

			if quantity < 1:
				await update.message.reply_text(self.i18n.t('BUY_INVALID_QUANTITY_NEGATIVE', language))
				return SELECTING_QUANTITY

			if quantity > min(product['quantity'], 10):
				await update.message.reply_text(
					self.i18n.t('BUY_QUANTITY_EXCEEDS', language, max_quantity=min(product['quantity'], 10))
				)
				return SELECTING_QUANTITY

			context.user_data['selected_quantity'] = quantity
			addresses = self.db.get_user_addresses(user_id)

			if not addresses:
				await update.message.reply_text(self.i18n.t('BUY_NO_ADDRESSES', language, product_name=product['name'], price=product['price']))
				return ConversationHandler.END

			keyboard = []
			for address in addresses:
				keyboard.append([InlineKeyboardButton(
					f"{address['name']}: {address['city']}",
					callback_data=f"address_{address['id']}"
				)])
			keyboard.append([InlineKeyboardButton(self.i18n.t('CANCEL_BUTTON', language), callback_data="cancel")])
			reply_markup = InlineKeyboardMarkup(keyboard)

			await update.message.reply_text(
				self.i18n.t('BUY_QUANTITY_ADDRESS', language, product_name=product['name'], price=product['price'], quantity=quantity, total=float(product['price']) * quantity),
				reply_markup=reply_markup
			)
			return SELECTING_ADDRESS

		except ValueError:
			await update.message.reply_text(self.i18n.t('BUY_INVALID_QUANTITY', language))
			return SELECTING_QUANTITY

	async def address_selected(self, update: Update, context: CallbackContext) -> int:
		"""Handle address selection"""
		query = update.callback_query
		await query.answer()
		user_id = update.effective_user.id
		language = self.db.get_user_language(user_id) or 'en'

		address_id = query.data.split('_')[1]
		address = self.db.get_address_by_id(user_id, address_id)

		if not address:
			await query.edit_message_text(self.i18n.t('BUY_ADDRESS_UNAVAILABLE', language))
			return ConversationHandler.END

		context.user_data['selected_address'] = address
		product = context.user_data['selected_product']
		quantity = context.user_data['selected_quantity']
		total_price = float(product['price']) * quantity

		keyboard = [
			[
				InlineKeyboardButton(self.i18n.t('CONFIRM', language), callback_data="confirm"),
				InlineKeyboardButton(self.i18n.t('CANCEL_BUTTON', language), callback_data="cancel")
			]
		]
		reply_markup = InlineKeyboardMarkup(keyboard)

		await query.edit_message_text(
			self.i18n.t('BUY_ORDER_SUMMARY', language, product_name=product['name'], price=product['price'], quantity=quantity, total=total_price, address_name=address['name'], address=address['address'], city=address['city']),
			reply_markup=reply_markup
		)
		return CONFIRMING_PURCHASE

	async def confirm_purchase(self, update: Update, context: CallbackContext) -> int:
		"""Handle purchase confirmation"""
		query = update.callback_query
		await query.answer()
		user_id = update.effective_user.id
		language = self.db.get_user_language(user_id) or 'en'

		product = context.user_data['selected_product']
		quantity = context.user_data['selected_quantity']
		address = context.user_data['selected_address']
		total_price = float(product['price']) * quantity
		user_balance = self.db.get_user_balance(user_id)

		if user_balance < total_price:
			await query.edit_message_text(
				self.i18n.t('BUY_INSUFFICIENT_BALANCE', language, required=total_price, balance=user_balance)
			)
			return ConversationHandler.END

		order_id = self.db.create_order(
			user_id=user_id,
			product_id=product['id'],
			quantity=quantity,
			address_id=address['id'],
			total_price=total_price
		)

		if not order_id:
			await query.edit_message_text(self.i18n.t('BUY_ORDER_ERROR', language))
			return ConversationHandler.END

		# Deduct from balance
		if not self.db.subtract_balance(user_id, total_price):
			await query.edit_message_text(self.i18n.t('BUY_PAYMENT_ERROR', language))
			return ConversationHandler.END

		if product['quantity'] is not None:
			self.db.update_product_quantity(product['id'], product['quantity'] - quantity)

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

		await query.edit_message_text(
			self.i18n.t('BUY_ORDER_SUCCESS', language, order_id=order_id, product_name=product['name'], quantity=quantity, total=total_price)
		)
		return ConversationHandler.END

	async def cancel_purchase(self, update: Update, context: CallbackContext) -> int:
		"""Cancel the purchase process"""
		user_id = update.effective_user.id
		language = self.db.get_user_language(user_id) or 'en'

		if update.callback_query:
			await update.callback_query.answer()
			await update.callback_query.edit_message_text(self.i18n.t('BUY_CANCELLED', language))
		else:
			await update.message.reply_text(self.i18n.t('BUY_CANCELLED', language))

		context.user_data.clear()
		return ConversationHandler.END