import logging
import re
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InlineQueryResultArticle, InputTextMessageContent
from telegram.ext import Application, CallbackContext, InlineQueryHandler
from uuid import uuid4
from Bot.database import Database
from Bot.Helpers.i18n import I18n

logger = logging.getLogger(__name__)

class UpdateInlineCommand:
	def __init__(self):
		self.db = Database()
		self.i18n = I18n()
		self.bot_username = "@EgrigoreBot"  # Replace with actual bot username or config

	def register_handlers(self, application: Application):
		application.add_handler(InlineQueryHandler(self.inline_update, pattern=r'^update'))

	async def inline_update(self, update: Update, context: CallbackContext) -> None:
		"""Handle inline queries for product updates in groups"""
		query = update.inline_query.query
		user_id = update.effective_user.id
		language = self.db.get_user_language(user_id) or 'en'

		# Check if user is blacklisted
		if self.db.is_blacklisted(user_id):
			logger.info(f"Blacklisted user {user_id} attempted inline update query")
			return

		# Check if user is a shop admin
		if not self.db.is_shop_admin(user_id):
			results = [
				InlineQueryResultArticle(
					id=str(uuid4()),
					title=self.i18n.t('UPDATE_PERMISSION_DENIED_TITLE', language),
					description=self.i18n.t('UPDATE_PERMISSION_DENIED_DESC', language),
					input_message_content=InputTextMessageContent(
						self.i18n.t('UPDATE_PERMISSION_DENIED_MESSAGE', language)
					)
				)
			]
			await update.inline_query.answer(results, cache_time=300)
			return

		# Extract update type and parameters
		parts = query.split()
		if len(parts) < 2:
			# Show help for update commands
			results = [
				InlineQueryResultArticle(
					id=str(uuid4()),
					title=self.i18n.t('UPDATE_COMMANDS_TITLE', language),
					description=self.i18n.t('UPDATE_COMMANDS_DESC', language),
					input_message_content=InputTextMessageContent(
						self.i18n.t('UPDATE_COMMANDS_HELP', language, bot_username=self.bot_username)
					)
				)
			]
		else:
			update_type = parts[1].lower()

			if update_type == "new" and len(parts) > 2:
				# New product announcement
				product_name = " ".join(parts[2:]).strip()[:100]  # Limit length
				if not product_name:
					results = [self.create_error_result(language, self.i18n.t('UPDATE_EMPTY_PRODUCT_NAME', language))]
				else:
					results = self.create_new_product_announcement(language, product_name)
			elif update_type == "sale" and len(parts) > 2:
				# Sale announcement
				try:
					discount = int(parts[2].rstrip("%"))
					if not 1 <= discount <= 100:
						raise ValueError("Discount out of range")
					results = self.create_sale_announcement(language, discount)
				except ValueError:
					results = [
						InlineQueryResultArticle(
							id=str(uuid4()),
							title=self.i18n.t('UPDATE_INVALID_FORMAT_TITLE', language),
							description=self.i18n.t('UPDATE_SALE_FORMAT_DESC', language),
							input_message_content=InputTextMessageContent(
								self.i18n.t('UPDATE_SALE_FORMAT_MESSAGE', language, bot_username=self.bot_username)
							)
						)
					]
			elif update_type == "restock" and len(parts) > 2:
				# Restock announcement
				try:
					product_id = int(parts[2])
					results = self.create_restock_announcement(language, product_id)
				except ValueError:
					results = [
						InlineQueryResultArticle(
							id=str(uuid4()),
							title=self.i18n.t('UPDATE_INVALID_FORMAT_TITLE', language),
							description=self.i18n.t('UPDATE_RESTOCK_FORMAT_DESC', language),
							input_message_content=InputTextMessageContent(
								self.i18n.t('UPDATE_RESTOCK_FORMAT_MESSAGE', language, bot_username=self.bot_username)
							)
						)
					]
			elif update_type == "announcement" and len(parts) > 2:
				# General announcement
				announcement_text = " ".join(parts[2:]).strip()[:500]  # Limit length
				if not announcement_text:
					results = [self.create_error_result(language, self.i18n.t('UPDATE_EMPTY_ANNOUNCEMENT', language))]
				else:
					results = self.create_general_announcement(language, announcement_text)
			else:
				# Unknown update type
				results = [
					InlineQueryResultArticle(
						id=str(uuid4()),
						title=self.i18n.t('UPDATE_UNKNOWN_TYPE_TITLE', language),
						description=self.i18n.t('UPDATE_UNKNOWN_TYPE_DESC', language),
						input_message_content=InputTextMessageContent(
							self.i18n.t('UPDATE_COMMANDS_HELP', language, bot_username=self.bot_username)
						)
					)
				]

		# Log inline usage
		chat_id = update.inline_query.chat_type
		if chat_id:
			self.db.log_user_activity(
				user_id=user_id,
				action="inline_update_query",
				details={
					"query": query,
					"chat_id": chat_id,
					"user_id": user_id
				}
			)

		await update.inline_query.answer(results, cache_time=300)

	def create_error_result(self, language, message):
		"""Create an error result for invalid input"""
		return InlineQueryResultArticle(
			id=str(uuid4()),
			title=self.i18n.t('UPDATE_INVALID_INPUT_TITLE', language),
			description=message,
			input_message_content=InputTextMessageContent(message)
		)

	def create_new_product_announcement(self, language, product_name):
		"""Create announcement for a new product"""
		keyboard = [
			[InlineKeyboardButton(self.i18n.t('VIEW_PRODUCT_BUTTON', language), url=f"https://t.me/{self.bot_username}?start=shop")]
		]
		reply_markup = InlineKeyboardMarkup(keyboard)

		return [
			InlineQueryResultArticle(
				id=str(uuid4()),
				title=self.i18n.t('UPDATE_NEW_PRODUCT_TITLE', language, product_name=product_name),
				description=self.i18n.t('UPDATE_NEW_PRODUCT_DESC', language),
				input_message_content=InputTextMessageContent(
					self.i18n.t('UPDATE_NEW_PRODUCT_MESSAGE', language, product_name=product_name)
				),
				reply_markup=reply_markup
			)
		]

	def create_sale_announcement(self, language, discount):
		"""Create announcement for a sale"""
		keyboard = [
			[InlineKeyboardButton(self.i18n.t('SHOP_NOW_BUTTON', language), url=f"https://t.me/{self.bot_username}?start=shop")]
		]
		reply_markup = InlineKeyboardMarkup(keyboard)

		return [
			InlineQueryResultArticle(
				id=str(uuid4()),
				title=self.i18n.t('UPDATE_SALE_TITLE', language, discount=discount),
				description=self.i18n.t('UPDATE_SALE_DESC', language, discount=discount),
				input_message_content=InputTextMessageContent(
					self.i18n.t('UPDATE_SALE_MESSAGE', language, discount=discount)
				),
				reply_markup=reply_markup
			)
		]

	def create_restock_announcement(self, language, product_id):
		"""Create announcement for a product restock"""
		# Get product details
		product = self.db.get_product_by_id(product_id)

		if not product:
			return [
				InlineQueryResultArticle(
					id=str(uuid4()),
					title=self.i18n.t('UPDATE_PRODUCT_NOT_FOUND_TITLE', language),
					description=self.i18n.t('UPDATE_PRODUCT_NOT_FOUND_MESSAGE', language, product_id=product_id),
					input_message_content=InputTextMessageContent(
						self.i18n.t('UPDATE_PRODUCT_NOT_FOUND_MESSAGE', language, product_id=product_id)
					)
				)
			]

		keyboard = [
			[InlineKeyboardButton(self.i18n.t('BUY_NOW_BUTTON', language), url=f"https://t.me/{self.bot_username}?start=buy_{product_id}")]
		]
		reply_markup = InlineKeyboardMarkup(keyboard)

		return [
			InlineQueryResultArticle(
				id=str(uuid4()),
				title=self.i18n.t('UPDATE_RESTOCK_TITLE', language, product_name=product['name']),
				description=self.i18n.t('UPDATE_RESTOCK_DESC', language, product_name=product['name']),
				input_message_content=InputTextMessageContent(
					self.i18n.t('UPDATE_RESTOCK_MESSAGE', language, product_name=product['name'], price=product['price'])
				),
				reply_markup=reply_markup,
				thumb_url=product.get('image_url')
			)
		]

	def create_general_announcement(self, language, announcement_text):
		"""Create a general shop announcement"""
		keyboard = [
			[InlineKeyboardButton(self.i18n.t('VISIT_SHOP_BUTTON', language), url=f"https://t.me/{self.bot_username}?start=shop")]
		]
		reply_markup = InlineKeyboardMarkup(keyboard)

		return [
			InlineQueryResultArticle(
				id=str(uuid4()),
				title=self.i18n.t('UPDATE_ANNOUNCEMENT_TITLE', language),
				description=self.i18n.t('UPDATE_ANNOUNCEMENT_DESC', language),
				input_message_content=InputTextMessageContent(
					self.i18n.t('UPDATE_ANNOUNCEMENT_MESSAGE', language, announcement_text=announcement_text)
				),
				reply_markup=reply_markup
			)
		]