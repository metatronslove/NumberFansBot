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
SELECTING_ACTION, ADDING_NAME, ADDING_ADDRESS, ADDING_CITY, CONFIRMING_ADDRESS, SELECTING_ADDRESS_TO_DELETE = range(6)

logger = logging.getLogger(__name__)

class AddressCommand:
	def __init__(self):
		self.db = Database()

	def register_handlers(self, application: Application):
		# Create a conversation handler for the address command
		conv_handler = ConversationHandler(
			entry_points=[CommandHandler('address', self.address_command)],
			states={
				SELECTING_ACTION: [
					CallbackQueryHandler(self.add_address, pattern=r'^add$'),
					CallbackQueryHandler(self.list_addresses, pattern=r'^list$'),
					CallbackQueryHandler(self.delete_address_start, pattern=r'^delete$'),
					CallbackQueryHandler(self.cancel_address, pattern=r'^cancel$')
				],
				ADDING_NAME: [
					MessageHandler(filters.Text() & ~filters.COMMAND, self.address_name_received),
					CallbackQueryHandler(self.cancel_address, pattern=r'^cancel$')
				],
				ADDING_ADDRESS: [
					MessageHandler(filters.Text() & ~filters.COMMAND, self.address_line_received),
					CallbackQueryHandler(self.cancel_address, pattern=r'^cancel$')
				],
				ADDING_CITY: [
					MessageHandler(filters.Text() & ~filters.COMMAND, self.address_city_received),
					CallbackQueryHandler(self.cancel_address, pattern=r'^cancel$')
				],
				CONFIRMING_ADDRESS: [
					CallbackQueryHandler(self.confirm_address, pattern=r'^confirm$'),
					CallbackQueryHandler(self.cancel_address, pattern=r'^cancel$')
				],
				SELECTING_ADDRESS_TO_DELETE: [
					CallbackQueryHandler(self.delete_address, pattern=r'^delete_\d+$'),
					CallbackQueryHandler(self.cancel_address, pattern=r'^cancel$')
				]
			},
			fallbacks=[CommandHandler('cancel', self.cancel_address)]
		)
		application.add_handler(conv_handler)

	async def address_command(self, update: Update, context: CallbackContext) -> int:
		"""Handle the /address command to manage delivery addresses"""
		user_id = update.effective_user.id

		# Check if user is blacklisted
		if self.db.is_blacklisted(user_id):
			await update.message.reply_text("You are not allowed to use this command.")
			return ConversationHandler.END

		# Log command usage
		self.db.increment_command_usage('address', user_id, update.effective_chat.id)

		# Create keyboard with address management options
		keyboard = [
			[InlineKeyboardButton("Add New Address", callback_data="add")],
			[InlineKeyboardButton("List My Addresses", callback_data="list")],
			[InlineKeyboardButton("Delete Address", callback_data="delete")],
			[InlineKeyboardButton("Cancel", callback_data="cancel")]
		]

		reply_markup = InlineKeyboardMarkup(keyboard)

		await update.message.reply_text(
			"Address Management\n\n"
			"What would you like to do?",
			reply_markup=reply_markup
		)

		return SELECTING_ACTION

	async def add_address(self, update: Update, context: CallbackContext) -> int:
		"""Start the process of adding a new address"""
		query = update.callback_query
		await query.answer()

		await query.edit_message_text(
			"Let's add a new delivery address.\n\n"
			"First, please give this address a name (e.g., 'Home', 'Work', etc.):"
		)

		return ADDING_NAME

	async def address_name_received(self, update: Update, context: CallbackContext) -> int:
		"""Handle receiving the address name"""
		address_name = update.message.text.strip()

		# Validate address name
		if len(address_name) > 50:
			await update.message.reply_text(
				"Address name is too long. Please use a shorter name (max 50 characters)."
			)
			return ADDING_NAME

		# Store address name in context
		context.user_data['address_name'] = address_name

		await update.message.reply_text(
			f"Address name: {address_name}\n\n"
			f"Now, please enter the street address:"
		)

		return ADDING_ADDRESS

	async def address_line_received(self, update: Update, context: CallbackContext) -> int:
		"""Handle receiving the street address"""
		address_line = update.message.text.strip()

		# Validate address line
		if len(address_line) > 200:
			await update.message.reply_text(
				"Address is too long. Please use a shorter address (max 200 characters)."
			)
			return ADDING_ADDRESS

		# Store address line in context
		context.user_data['address_line'] = address_line

		await update.message.reply_text(
			f"Street address: {address_line}\n\n"
			f"Finally, please enter the city:"
		)

		return ADDING_CITY

	async def address_city_received(self, update: Update, context: CallbackContext) -> int:
		"""Handle receiving the city"""
		city = update.message.text.strip()

		# Validate city
		if len(city) > 50:
			await update.message.reply_text(
				"City name is too long. Please use a shorter name (max 50 characters)."
			)
			return ADDING_CITY

		# Store city in context
		context.user_data['city'] = city

		# Create confirmation keyboard
		keyboard = [
			[
				InlineKeyboardButton("Confirm", callback_data="confirm"),
				InlineKeyboardButton("Cancel", callback_data="cancel")
			]
		]
		reply_markup = InlineKeyboardMarkup(keyboard)

		await update.message.reply_text(
			"Please confirm your address details:\n\n"
			f"Name: {context.user_data['address_name']}\n"
			f"Address: {context.user_data['address_line']}\n"
			f"City: {context.user_data['city']}\n\n"
			f"Is this correct?",
			reply_markup=reply_markup
		)

		return CONFIRMING_ADDRESS

	async def confirm_address(self, update: Update, context: CallbackContext) -> int:
		"""Handle address confirmation"""
		query = update.callback_query
		await query.answer()

		user_id = update.effective_user.id
		address_name = context.user_data['address_name']
		address_line = context.user_data['address_line']
		city = context.user_data['city']

		# Save address to database
		address_id = self.db.save_user_address(
			user_id=user_id,
			name=address_name,
			address=address_line,
			city=city
		)

		if not address_id:
			await query.edit_message_text("Sorry, there was an error saving your address. Please try again later.")
			return ConversationHandler.END

		# Log user activity
		self.db.log_user_activity(
			user_id=user_id,
			action="add_address",
			details={
				"address_id": address_id,
				"address_name": address_name
			}
		)

		await query.edit_message_text(
			f"✅ Address saved successfully!\n\n"
			f"Name: {address_name}\n"
			f"Address: {address_line}\n"
			f"City: {city}\n\n"
			f"You can manage your addresses anytime with the /address command."
		)

		return ConversationHandler.END

	async def list_addresses(self, update: Update, context: CallbackContext) -> int:
		"""List user's saved addresses"""
		query = update.callback_query
		await query.answer()

		user_id = update.effective_user.id
		addresses = self.db.get_user_addresses(user_id)

		if not addresses:
			await query.edit_message_text(
				"You don't have any saved addresses yet.\n\n"
				"Use the /address command and select 'Add New Address' to add one."
			)
			return ConversationHandler.END

		address_text = "Your saved addresses:\n\n"
		for i, address in enumerate(addresses, 1):
			default_mark = " (Default)" if address.get('is_default') else ""
			address_text += f"{i}. {address['name']}{default_mark}\n"
			address_text += f"   {address['address']}\n"
			address_text += f"   {address['city']}\n\n"

		await query.edit_message_text(address_text)
		return ConversationHandler.END

	async def delete_address_start(self, update: Update, context: CallbackContext) -> int:
		"""Start the process of deleting an address"""
		query = update.callback_query
		await query.answer()

		user_id = update.effective_user.id
		addresses = self.db.get_user_addresses(user_id)

		if not addresses:
			await query.edit_message_text(
				"You don't have any saved addresses to delete.\n\n"
				"Use the /address command and select 'Add New Address' to add one."
			)
			return ConversationHandler.END

		# Create keyboard with address options
		keyboard = []
		for address in addresses:
			default_mark = " (Default)" if address.get('is_default') else ""
			keyboard.append([InlineKeyboardButton(
				f"{address['name']}{default_mark} - {address['city']}",
				callback_data=f"delete_{address['id']}"
			)])

		# Add cancel button
		keyboard.append([InlineKeyboardButton("Cancel", callback_data="cancel")])

		reply_markup = InlineKeyboardMarkup(keyboard)

		await query.edit_message_text(
			"Select an address to delete:",
			reply_markup=reply_markup
		)

		return SELECTING_ADDRESS_TO_DELETE

	async def delete_address(self, update: Update, context: CallbackContext) -> int:
		"""Handle address deletion"""
		query = update.callback_query
		await query.answer()

		# Extract address ID from callback data
		address_id = query.data.split('_')[1]
		user_id = update.effective_user.id

		# Delete address from database
		success = self.db.delete_user_address(user_id, address_id)

		if not success:
			await query.edit_message_text("Sorry, there was an error deleting the address. Please try again later.")
			return ConversationHandler.END

		# Log user activity
		self.db.log_user_activity(
			user_id=user_id,
			action="delete_address",
			details={
				"address_id": address_id
			}
		)

		await query.edit_message_text("✅ Address deleted successfully!")
		return ConversationHandler.END

	async def cancel_address(self, update: Update, context: CallbackContext) -> int:
		"""Cancel the address management process"""
		if update.callback_query:
			await update.callback_query.answer()
			await update.callback_query.edit_message_text("Address management cancelled.")
		else:
			await update.message.reply_text("Address management cancelled.")

		# Clear user data
		context.user_data.clear()

		return ConversationHandler.END