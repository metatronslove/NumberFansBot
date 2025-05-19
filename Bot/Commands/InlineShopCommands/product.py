import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InlineQueryResultArticle, InputTextMessageContent
from telegram.ext import Application, CallbackContext, InlineQueryHandler
from uuid import uuid4
from Bot.database import Database
from Bot.Helpers.i18n import I18n

logger = logging.getLogger(__name__)

class ProductInlineCommand:
	def __init__(self):
		self.db = Database()
		self.i18n = I18n()
		self.bot_username = "@EgrigoreBot"  # Replace with actual bot username or config

	def register_handlers(self, application: Application):
		application.add_handler(InlineQueryHandler(self.inline_product, pattern=r'^product'))

	async def inline_product(self, update: Update, context: CallbackContext) -> None:
		"""Handle inline queries for specific product details"""
		query = update.inline_query.query
		user_id = update.effective_user.id
		language = self.db.get_user_language(user_id) or 'en'

		# Check if user is blacklisted
		if self.db.is_blacklisted(user_id):
			logger.info(f"Blacklisted user {user_id} attempted inline product query")
			return

		# Extract product ID if any (after "product" keyword)
		product_id = None
		try:
			if len(query) > 8:  # "product " + at least one digit
				product_id = int(query[8:].strip())
		except ValueError:
			pass

		if product_id is not None:
			# Get specific product details
			product = self.db.get_product_by_id(product_id)

			if not product:
				# Product not found
				results = [
					InlineQueryResultArticle(
						id=str(uuid4()),
						title=self.i18n.t('PRODUCT_NOT_FOUND_TITLE', language),
						description=self.i18n.t('PRODUCT_NOT_FOUND_DESC', language, product_id=product_id),
						input_message_content=InputTextMessageContent(
							self.i18n.t('PRODUCT_NOT_FOUND_MESSAGE', language, product_id=product_id)
						)
					)
				]
			else:
				# Create keyboard for the product
				keyboard = [
					[InlineKeyboardButton(self.i18n.t('BUY_NOW_BUTTON', language), url=f"https://t.me/{self.bot_username}?start=buy_{product['id']}")],
					[InlineKeyboardButton(self.i18n.t('VIEW_ALL_PRODUCTS_BUTTON', language), url=f"https://t.me/{self.bot_username}?start=shop")]
				]
				reply_markup = InlineKeyboardMarkup(keyboard)

				# Format price and availability
				price_text = f"{product['price']} TL"
				if product['quantity'] is not None:
					availability = f"In stock: {product['quantity']}" if product['quantity'] > 0 else "Out of stock"
				else:
					availability = "Digital product (unlimited)"

				# Create detailed product description
				description = product.get('description', 'No description available.')
				features = product.get('features', [])
				features_text = "\n".join([f"• {feature}" for feature in features]) if features else ""

				message_content = self.i18n.t('PRODUCT_DETAILS', language,
											  product_name=product['name'],
											  price_text=price_text,
											  product_type=product['type'].capitalize(),
											  availability=availability,
											  description=description)

				if features_text:
					message_content += self.i18n.t('PRODUCT_FEATURES', language, features_text=features_text)

				message_content += self.i18n.t('PRODUCT_PURCHASE_PROMPT', language)

				results = [
					InlineQueryResultArticle(
						id=str(uuid4()),
						title=product['name'],
						description=self.i18n.t('PRODUCT_PRICE_AVAILABILITY', language, price_text=price_text, availability=availability),
						input_message_content=InputTextMessageContent(message_content),
						reply_markup=reply_markup,
						thumb_url=product.get('image_url')
					)
				]
		else:
			# No specific product ID, show help
			results = [
				InlineQueryResultArticle(
					id=str(uuid4()),
					title=self.i18n.t('PRODUCT_SEARCH_TITLE', language),
					description=self.i18n.t('PRODUCT_SEARCH_DESC', language),
					input_message_content=InputTextMessageContent(
						self.i18n.t('PRODUCT_SEARCH_HELP', language, bot_username=self.bot_username)
					)
				)
			]

		# Log inline usage
		chat_id = update.inline_query.chat_type
		if chat_id:
			self.db.log_user_activity(
				user_id=user_id,
				action="inline_product_query",
				details={
					"query": query,
					"chat_id": chat_id,
					"product_id": product_id,
					"user_id": user_id
				}
			)

		await update.inline_query.answer(results, cache_time=300)