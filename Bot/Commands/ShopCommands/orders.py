import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
	Application,
	CallbackContext,
	CommandHandler,
	ConversationHandler,
	CallbackQueryHandler,
	filters
)
from Bot.database import Database
from Bot.Helpers.i18n import I18n

# States for the conversation handler
VIEWING_ORDER, SELECTING_ORDER = range(2)

logger = logging.getLogger(__name__)

class OrdersCommand:
	def __init__(self):
		self.db = Database()
		self.i18n = I18n()

	def register_handlers(self, application: Application):
		conv_handler = ConversationHandler(
			entry_points=[CommandHandler('orders', self.orders_command)],
			states={
				SELECTING_ORDER: [
					CallbackQueryHandler(self.view_order, pattern=r'^order_\d+$'),
					CallbackQueryHandler(self.cancel_orders, pattern=r'^cancel$'),
					CallbackQueryHandler(self.cancel_order, pattern=r'^cancel_order_\d+$'),
					CallbackQueryHandler(self.back_to_orders, pattern=r'^back$')
				],
				VIEWING_ORDER: [
					CallbackQueryHandler(self.cancel_order, pattern=r'^cancel_order_\d+$'),
					CallbackQueryHandler(self.back_to_orders, pattern=r'^back$'),
					CallbackQueryHandler(self.cancel_orders, pattern=r'^cancel$')
				]
			},
			fallbacks=[CommandHandler('cancel', self.cancel_orders)]
		)
		application.add_handler(conv_handler)

	async def orders_command(self, update: Update, context: CallbackContext) -> int:
		user_id = update.effective_user.id
		language = self.db.get_user_language(user_id) or 'en'

		if self.db.is_blacklisted(user_id):
			await update.message.reply_text(self.i18n.t('ORDERS_BLACKLISTED', language))
			return ConversationHandler.END

		self.db.increment_command_usage('orders', user_id, update.effective_chat.id)
		orders = self.db.get_user_orders(user_id)

		if not orders:
			await update.message.reply_text(self.i18n.t('ORDERS_NO_ORDERS', language))
			return ConversationHandler.END

		keyboard = []
		for order in orders:
			keyboard.append([InlineKeyboardButton(
				f"Order #{order['id']} - {order['status']}",
				callback_data=f"order_{order['id']}"
			)])
		keyboard.append([InlineKeyboardButton(self.i18n.t('CANCEL_BUTTON', language), callback_data="cancel")])
		reply_markup = InlineKeyboardMarkup(keyboard)

		await update.message.reply_text(
			self.i18n.t('ORDERS_SELECT_ORDER', language),
			reply_markup=reply_markup
		)
		return SELECTING_ORDER

	async def view_order(self, update: Update, context: CallbackContext) -> int:
		query = update.callback_query
		await query.answer()
		user_id = update.effective_user.id
		language = self.db.get_user_language(user_id) or 'en'

		order_id = int(query.data.split('_')[1])
		order = self.db.get_order_by_id(user_id, order_id)

		if not order:
			await query.edit_message_text(self.i18n.t('ORDERS_ORDER_NOT_FOUND', language))
			return ConversationHandler.END

		status_emoji = {
			'pending': '⏳',
			'pending_payment': '⚠️',
			'processing': '🔄',
			'shipped': '🚚',
			'delivered': '✅',
			'cancelled': '❌'
		}.get(order['status'], '❓')

		message = self.i18n.t('ORDERS_DETAILS', language,
							  status_emoji=status_emoji,
							  order_id=order['id'],
							  product_name=order['product_name'],
							  quantity=order['quantity'],
							  total_price=order['total_price'],
							  status=order['status'],
							  order_date=order['order_date'],
							  address_name=order['address_name'],
							  address=order['address'],
							  city=order['city'])

		if order['status'] == 'pending_payment':
			message += self.i18n.t('ORDERS_PENDING_PAYMENT', language)
		elif order['status'] == 'processing':
			message += self.i18n.t('ORDERS_PROCESSING', language)
		elif order['status'] == 'shipped':
			message += self.i18n.t('ORDERS_SHIPPED', language, shipped_date=order['shipped_date'])
		elif order['status'] == 'delivered':
			message += self.i18n.t('ORDERS_DELIVERED', language, delivery_date=order['delivery_date'])
		elif order['status'] == 'cancelled':
			message += self.i18n.t('ORDERS_CANCELLED_STATUS', language, cancelled_date=order['cancelled_date'])

		keyboard = [
			[InlineKeyboardButton(self.i18n.t('CANCEL', language), callback_data=f"cancel_order_{order['id']}")],
			[InlineKeyboardButton(self.i18n.t('BACK', language), callback_data="back")],
			[InlineKeyboardButton(self.i18n.t('CANCEL_BUTTON', language), callback_data="cancel")]
		]
		reply_markup = InlineKeyboardMarkup(keyboard)

		await query.edit_message_text(
			message,
			reply_markup=reply_markup
		)
		return VIEWING_ORDER

	async def back_to_orders(self, update: Update, context: CallbackContext) -> int:
		query = update.callback_query
		await query.answer()
		user_id = update.effective_user.id
		language = self.db.get_user_language(user_id) or 'en'

		orders = self.db.get_user_orders(user_id)

		if not orders:
			await query.edit_message_text(self.i18n.t('ORDERS_NO_ORDERS', language))
			return ConversationHandler.END

		keyboard = []
		for order in orders:
			keyboard.append([InlineKeyboardButton(
				f"Order #{order['id']} - {order['status']}",
				callback_data=f"order_{order['id']}"
			)])
		keyboard.append([InlineKeyboardButton(self.i18n.t('CANCEL_BUTTON', language), callback_data="cancel")])
		reply_markup = InlineKeyboardMarkup(keyboard)

		await query.edit_message_text(
			self.i18n.t('ORDERS_SELECT_ORDER', language),
			reply_markup=reply_markup
		)
		return SELECTING_ORDER

	async def cancel_order(self, update: Update, context: CallbackContext) -> int:
		query = update.callback_query
		await query.answer()
		user_id = update.effective_user.id
		language = self.db.get_user_language(user_id) or 'en'

		order_id = int(query.data.split('_')[2])
		order = self.db.get_order_by_id(user_id, order_id)

		if not order:
			await query.edit_message_text(self.i18n.t('ORDERS_ORDER_NOT_FOUND', language))
			return ConversationHandler.END

		success, refund_amount = self.db.cancel_order(user_id, order_id)

		if not success:
			await query.edit_message_text(self.i18n.t('ORDERS_CANCEL_ERROR', language))
			return ConversationHandler.END

		await query.edit_message_text(
			self.i18n.t('ORDERS_CANCEL_SUCCESS', language, order_id=order_id, refund_amount=refund_amount)
		)
		return ConversationHandler.END

	async def cancel_orders(self, update: Update, context: CallbackContext) -> int:
		user_id = update.effective_user.id
		language = self.db.get_user_language(user_id) or 'en'

		if update.callback_query:
			await update.callback_query.answer()
			await update.callback_query.edit_message_text(self.i18n.t('ORDERS_CANCELLED', language))
		else:
			await update.message.reply_text(self.i18n.t('ORDERS_CLOSED', language))

		context.user_data.clear()
		return ConversationHandler.END