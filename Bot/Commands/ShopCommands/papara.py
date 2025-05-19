import logging
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
SELECTING_ACTION, ENTERING_AMOUNT, CHECKING_PAYMENT, CONFIRMING_PAYMENT = range(4)

logger = logging.getLogger(__name__)

class PaparaCommand:
	def __init__(self):
		self.db = Database()
		self.i18n = I18n()

	def register_handlers(self, application: Application):
		conv_handler = ConversationHandler(
			entry_points=[CommandHandler('papara', self.papara_command)],
			states={
				SELECTING_ACTION: [
					CallbackQueryHandler(self.add_balance, pattern=r'^add_balance$'),
					CallbackQueryHandler(self.check_payment, pattern=r'^check_payment$'),
					CallbackQueryHandler(self.view_balance, pattern=r'^view_balance$'),
					CallbackQueryHandler(self.cancel_papara, pattern=r'^cancel$')
				],
				ENTERING_AMOUNT: [
					MessageHandler(filters.Text() & ~filters.COMMAND, self.amount_received),
					CallbackQueryHandler(self.cancel_papara, pattern=r'^cancel$')
				],
				CONFIRMING_PAYMENT: [
					CallbackQueryHandler(self.confirm_payment, pattern=r'^confirm_payment$'),
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
		user_id = update.effective_user.id
		language = self.db.get_user_language(user_id) or 'en'

		if self.db.is_blacklisted(user_id):
			await update.message.reply_text(self.i18n.t('PAPARA_BLACKLISTED', language))
			return ConversationHandler.END

		self.db.increment_command_usage('papara', user_id, update.effective_chat.id)
		keyboard = [
			[InlineKeyboardButton(self.i18n.t('PAYMENT_TYPE_BALANCE', language), callback_data="add_balance")],
			[InlineKeyboardButton(self.i18n.t('CHECK_STATUS', language), callback_data="check_payment")],
			[InlineKeyboardButton(self.i18n.t('VIEW_BALANCE', language), callback_data="view_balance")],
			[InlineKeyboardButton(self.i18n.t('CANCEL_BUTTON', language), callback_data="cancel")]
		]
		reply_markup = InlineKeyboardMarkup(keyboard)

		await update.message.reply_text(
			self.i18n.t('PAPARA_SELECT_ACTION', language),
			reply_markup=reply_markup
		)
		return SELECTING_ACTION

	async def add_balance(self, update: Update, context: CallbackContext) -> int:
		query = update.callback_query
		await query.answer()
		user_id = update.effective_user.id
		language = self.db.get_user_language(user_id) or 'en'

		await query.edit_message_text(self.i18n.t('PAPARA_ENTER_AMOUNT', language))
		return ENTERING_AMOUNT

	async def amount_received(self, update: Update, context: CallbackContext) -> int:
		user_id = update.effective_user.id
		language = self.db.get_user_language(user_id) or 'en'
		try:
			amount = float(update.message.text.strip())
			if amount < 10:
				await update.message.reply_text(self.i18n.t('PAPARA_AMOUNT_TOO_LOW', language))
				return ENTERING_AMOUNT
			if amount > 1000:
				await update.message.reply_text(self.i18n.t('PAPARA_AMOUNT_TOO_HIGH', language))
				return ENTERING_AMOUNT

			payment_details = self.db.create_papara_payment(user_id, amount)
			if not payment_details:
				await update.message.reply_text(self.i18n.t('PAPARA_PAYMENT_ERROR', language))
				return ConversationHandler.END

			context.user_data['payment_details'] = payment_details
			keyboard = [
				[InlineKeyboardButton(self.i18n.t('CONFIRM_PAYMENT', language), callback_data="confirm_payment")],
				[InlineKeyboardButton(self.i18n.t('CANCEL_BUTTON', language), callback_data="cancel")]
			]
			reply_markup = InlineKeyboardMarkup(keyboard)

			await update.message.reply_text(
				self.i18n.t('PAPARA_CONFIRM_PAYMENT', language,
							amount=payment_details['amount'],
							recipient_name=payment_details['recipient_name'],
							papara_number=payment_details['papara_number']),
				reply_markup=reply_markup
			)
			return CONFIRMING_PAYMENT

		except ValueError:
			await update.message.reply_text(self.i18n.t('PAPARA_INVALID_AMOUNT', language))
			return ENTERING_AMOUNT

	async def confirm_payment(self, update: Update, context: CallbackContext) -> int:
		query = update.callback_query
		await query.answer()
		user_id = update.effective_user.id
		language = self.db.get_user_language(user_id) or 'en'
		payment_details = context.user_data.get('payment_details')

		await query.edit_message_text(
			self.i18n.t('PAPARA_PAYMENT_SUCCESS', language,
						payment_id=payment_details['payment_id'],
						amount=payment_details['amount'],
						recipient_name=payment_details['recipient_name'],
						papara_number=payment_details['papara_number'],
						reference=payment_details['reference'])
		)
		context.user_data.clear()
		return ConversationHandler.END

	async def check_payment(self, update: Update, context: CallbackContext) -> int:
		query = update.callback_query
		await query.answer()
		user_id = update.effective_user.id
		language = self.db.get_user_language(user_id) or 'en'

		await query.edit_message_text(self.i18n.t('PAPARA_CHECK_STATUS', language))
		return CHECKING_PAYMENT

	async def payment_reference_received(self, update: Update, context: CallbackContext) -> int:
		user_id = update.effective_user.id
		language = self.db.get_user_language(user_id) or 'en'
		reference = update.message.text.strip()

		payment = self.db.check_payment_status(user_id, reference)
		if not payment:
			await update.message.reply_text(self.i18n.t('PAPARA_PAYMENT_NOT_FOUND', language))
			return CHECKING_PAYMENT

		status = payment['status']
		if status == 'confirmed':
			await update.message.reply_text(
				self.i18n.t('PAPARA_PAYMENT_CONFIRMED', language,
							payment_id=payment['payment_id'],
							amount=payment['amount'])
			)
		elif status == 'verified':
			await update.message.reply_text(
				self.i18n.t('PAPARA_PAYMENT_VERIFIED', language,
							payment_id=payment['payment_id'],
							amount=payment['amount'])
			)
		elif status == 'pending':
			await update.message.reply_text(
				self.i18n.t('PAPARA_PAYMENT_PENDING', language,
							payment_id=payment['payment_id'],
							amount=payment['amount'])
			)
		elif status == 'cancelled':
			await update.message.reply_text(
				self.i18n.t('PAPARA_PAYMENT_CANCELLED', language,
							payment_id=payment['payment_id'],
							amount=payment['amount'])
			)
		else:
			await update.message.reply_text(
				self.i18n.t('PAPARA_PAYMENT_UNKNOWN', language,
							payment_id=payment['payment_id'],
							status=status)
			)

		context.user_data.clear()
		return ConversationHandler.END

	async def view_balance(self, update: Update, context: CallbackContext) -> int:
		query = update.callback_query
		await query.answer()
		user_id = update.effective_user.id
		language = self.db.get_user_language(user_id) or 'en'

		balance = self.db.get_user_balance(user_id)
		await query.edit_message_text(
			self.i18n.t('PAPARA_BALANCE', language, balance=balance)
		)
		return ConversationHandler.END

	async def cancel_papara(self, update: Update, context: CallbackContext) -> int:
		user_id = update.effective_user.id
		language = self.db.get_user_language(user_id) or 'en'

		if update.callback_query:
			await update.callback_query.answer()
			await update.callback_query.edit_message_text(self.i18n.t('PAPARA_CANCELLED', language))
		else:
			await update.message.reply_text(self.i18n.t('PAPARA_CANCELLED', language))

		context.user_data.clear()
		return ConversationHandler.END