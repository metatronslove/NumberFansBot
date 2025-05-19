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
SELECTING_ACTION, ENTERING_NAME, ENTERING_ADDRESS, ENTERING_CITY, CONFIRMING_ADDRESS, DELETING_ADDRESS = range(6)

logger = logging.getLogger(__name__)

class AddressCommand:
	def __init__(self):
		self.db = Database()
		self.i18n = I18n()

	def register_handlers(self, application: Application):
		conv_handler = ConversationHandler(
			entry_points=[CommandHandler('address', self.address_command)],
			states={
				SELECTING_ACTION: [
					CallbackQueryHandler(self.add_address, pattern=r'^add_address$'),
					CallbackQueryHandler(self.list_addresses, pattern=r'^list_addresses$'),
					CallbackQueryHandler(self.delete_address_start, pattern=r'^delete_address$'),
					CallbackQueryHandler(self.cancel_address, pattern=r'^cancel$')
				],
				ENTERING_NAME: [
					MessageHandler(filters.Text() & ~filters.COMMAND, self.address_name_received),
					CallbackQueryHandler(self.cancel_address, pattern=r'^cancel$')
				],
				ENTERING_ADDRESS: [
					MessageHandler(filters.Text() & ~filters.COMMAND, self.address_line_received),
					CallbackQueryHandler(self.cancel_address, pattern=r'^cancel$')
				],
				ENTERING_CITY: [
					MessageHandler(filters.Text() & ~filters.COMMAND, self.address_city_received),
					CallbackQueryHandler(self.cancel_address, pattern=r'^cancel$')
				],
				CONFIRMING_ADDRESS: [
					CallbackQueryHandler(self.confirm_address, pattern=r'^confirm_address$'),
					CallbackQueryHandler(self.cancel_address, pattern=r'^cancel$')
				],
				DELETING_ADDRESS: [
					CallbackQueryHandler(self.delete_address, pattern=r'^delete_address_\d+$'),
					CallbackQueryHandler(self.cancel_address, pattern=r'^cancel$')
				]
			},
			fallbacks=[CommandHandler('cancel', self.cancel_address)]
		)
		application.add_handler(conv_handler)

	async def address_command(self, update: Update, context: CallbackContext) -> int:
		user_id = update.effective_user.id
		language = self.db.get_user_language(user_id) or 'en'

		if self.db.is_blacklisted(user_id):
			await update.message.reply_text(self.i18n.t('ADDRESS_BLACKLISTED', language))
			return ConversationHandler.END

		self.db.increment_command_usage('address', user_id, update.effective_chat.id)
		keyboard = [
			[InlineKeyboardButton(self.i18n.t('ADD', language), callback_data="add_address")],
			[InlineKeyboardButton(self.i18n.t('VIEW', language), callback_data="list_addresses")],
			[InlineKeyboardButton(self.i18n.t('DELETE', language), callback_data="delete_address")],
			[InlineKeyboardButton(self.i18n.t('CANCEL_BUTTON', language), callback_data="cancel")]
		]
		reply_markup = InlineKeyboardMarkup(keyboard)

		await update.message.reply_text(
			self.i18n.t('ADDRESS_SELECT_ACTION', language),
			reply_markup=reply_markup
		)
		return SELECTING_ACTION

	async def add_address(self, update: Update, context: CallbackContext) -> int:
		query = update.callback_query
		await query.answer()
		user_id = update.effective_user.id
		language = self.db.get_user_language(user_id) or 'en'

		await query.edit_message_text(self.i18n.t('ADDRESS_ENTER_NAME', language))
		return ENTERING_NAME

	async def address_name_received(self, update: Update, context: CallbackContext) -> int:
		user_id = update.effective_user.id
		language = self.db.get_user_language(user_id) or 'en'
		address_name = update.message.text.strip()

		if len(address_name) > 50:
			await update.message.reply_text(self.i18n.t('ADDRESS_NAME_TOO_LONG', language))
			return ENTERING_NAME

		context.user_data['address_name'] = address_name
		await update.message.reply_text(
			self.i18n.t('ADDRESS_ENTER_STREET', language, address_name=address_name)
		)
		return ENTERING_ADDRESS

	async def address_line_received(self, update: Update, context: CallbackContext) -> int:
		user_id = update.effective_user.id
		language = self.db.get_user_language(user_id) or 'en'
		address_line = update.message.text.strip()

		if len(address_line) > 200:
			await update.message.reply_text(self.i18n.t('ADDRESS_LINE_TOO_LONG', language))
			return ENTERING_ADDRESS

		context.user_data['address_line'] = address_line
		await update.message.reply_text(
			self.i18n.t('ADDRESS_ENTER_CITY', language, address_line=address_line)
		)
		return ENTERING_CITY

	async def address_city_received(self, update: Update, context: CallbackContext) -> int:
		user_id = update.effective_user.id
		language = self.db.get_user_language(user_id) or 'en'
		city = update.message.text.strip()

		if len(city) > 50:
			await update.message.reply_text(self.i18n.t('ADDRESS_CITY_TOO_LONG', language))
			return ENTERING_CITY

		context.user_data['city'] = city
		keyboard = [
			[InlineKeyboardButton(self.i18n.t('CONFIRM', language), callback_data="confirm_address")],
			[InlineKeyboardButton(self.i18n.t('CANCEL_BUTTON', language), callback_data="cancel")]
		]
		reply_markup = InlineKeyboardMarkup(keyboard)

		await update.message.reply_text(
			self.i18n.t('ADDRESS_CONFIRM', language,
						address_name=context.user_data['address_name'],
						address_line=context.user_data['address_line'],
						city=city),
			reply_markup=reply_markup
		)
		return CONFIRMING_ADDRESS

	async def confirm_address(self, update: Update, context: CallbackContext) -> int:
		query = update.callback_query
		await query.answer()
		user_id = update.effective_user.id
		language = self.db.get_user_language(user_id) or 'en'

		address_data = {
			'name': context.user_data['address_name'],
			'address': context.user_data['address_line'],
			'city': context.user_data['city']
		}
		success = self.db.save_address(user_id, address_data)

		if not success:
			await query.edit_message_text(self.i18n.t('ADDRESS_SAVE_ERROR', language))
			return ConversationHandler.END

		await query.edit_message_text(
			self.i18n.t('ADDRESS_SAVE_SUCCESS', language,
						address_name=address_data['name'],
						address_line=address_data['address'],
						city=address_data['city'])
		)
		context.user_data.clear()
		return ConversationHandler.END

	async def list_addresses(self, update: Update, context: CallbackContext) -> int:
		query = update.callback_query
		await query.answer()
		user_id = update.effective_user.id
		language = self.db.get_user_language(user_id) or 'en'

		addresses = self.db.get_user_addresses(user_id)
		if not addresses:
			await query.edit_message_text(self.i18n.t('ADDRESS_NO_ADDRESSES', language))
			return ConversationHandler.END

		address_list = "\n".join([f"{addr['name']}: {addr['address']}, {addr['city']}" for addr in addresses])
		await query.edit_message_text(
			self.i18n.t('ADDRESS_LIST', language, address_list=address_list)
		)
		return SELECTING_ACTION

	async def delete_address_start(self, update: Update, context: CallbackContext) -> int:
		query = update.callback_query
		await query.answer()
		user_id = update.effective_user.id
		language = self.db.get_user_language(user_id) or 'en'

		addresses = self.db.get_user_addresses(user_id)
		if not addresses:
			await query.edit_message_text(self.i18n.t('ADDRESS_NO_ADDRESSES_DELETE', language))
			return ConversationHandler.END

		keyboard = []
		for address in addresses:
			keyboard.append([InlineKeyboardButton(
				f"{address['name']}: {address['city']}",
				callback_data=f"delete_address_{address['id']}"
			)])
		keyboard.append([InlineKeyboardButton(self.i18n.t('CANCEL_BUTTON', language), callback_data="cancel")])
		reply_markup = InlineKeyboardMarkup(keyboard)

		await query.edit_message_text(
			self.i18n.t('ADDRESS_SELECT_DELETE', language),
			reply_markup=reply_markup
		)
		return DELETING_ADDRESS

	async def delete_address(self, update: Update, context: CallbackContext) -> int:
		query = update.callback_query
		await query.answer()
		user_id = update.effective_user.id
		language = self.db.get_user_language(user_id) or 'en'

		address_id = int(query.data.split('_')[2])
		success = self.db.delete_address(user_id, address_id)

		if not success:
			await query.edit_message_text(self.i18n.t('ADDRESS_DELETE_ERROR', language))
			return ConversationHandler.END

		await query.edit_message_text(self.i18n.t('ADDRESS_DELETE_SUCCESS', language))
		return SELECTING_ACTION

	async def cancel_address(self, update: Update, context: CallbackContext) -> int:
		user_id = update.effective_user.id
		language = self.db.get_user_language(user_id) or 'en'

		if update.callback_query:
			await update.callback_query.answer()
			await update.callback_query.edit_message_text(self.i18n.t('ADDRESS_CANCELLED', language))
		else:
			await update.message.reply_text(self.i18n.t('ADDRESS_CANCELLED', language))

		context.user_data.clear()
		return ConversationHandler.END