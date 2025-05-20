import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InlineQueryResultArticle, InputTextMessageContent
from telegram.ext import Application, CallbackContext, InlineQueryHandler
from uuid import uuid4
from Bot.database import Database
from Bot.Helpers.i18n import I18n

logger = logging.getLogger(__name__)

class ShopInlineCommand:
	def __init__(self):
		self.db = Database()
		self.i18n = I18n()
		self.bot_username = "@EgrigoreBot"	# Replace with actual bot username or config

	def register_handlers(self, application: Application):
		application.add_handler(InlineQueryHandler(self.inline_shop, pattern=r'^shop'))

	async def inline_shop(self, update: Update, context: CallbackContext) -> None:
		"""Handle inline queries for shop listings"""
		query = update.inline_query.query
		user_id = update.effective_user.id
		language = self.db.get_user_language(user_id) or 'en'

		# Check if user is blacklisted
		if self.db.is_blacklisted(user_id):
			logger.info(f"Blacklisted user {user_id} attempted inline shop query")
			return

		# Extract search terms if any (after "shop" keyword)
		search_terms = query[4:].strip() if len(query) > 4 else ""

		# Get available products
		products = self.db.get_available_products(search_terms=search_terms, active_only=True)

		if not products:
			# No products found
			results = [
				InlineQueryResultArticle(
					id=str(uuid4()),
					title=self.i18n.t('SHOP_NO_PRODUCTS_TITLE', language),
					description=self.i18n.t('SHOP_NO_PRODUCTS_DESC', language),
					input_message_content=InputTextMessageContent(
						self.i18n.t('SHOP_NO_PRODUCTS_MESSAGE', language)
					)
				)
			]
		else:
			# Create results for each product
			results = []
			for product in products:
				# Create keyboard for the product
				keyboard = [
					[InlineKeyboardButton(self.i18n.t('BUY_NOW_BUTTON', language), url=f"https://t.me/{self.bot_username}?start=buy_{product['id']}")],
					[InlineKeyboardButton(self.i18n.t('VIEW_DETAILS_BUTTON', language), url=f"https://t.me/{self.bot_username}?start=product_{product['id']}")]
				]
				reply_markup = InlineKeyboardMarkup(keyboard)

				# Format price and availability
				price_text = f"{product['price']} TL"
				if product['quantity'] is not None:
					availability = f"In stock: {product['quantity']}" if product['quantity'] > 0 else "Out of stock"
				else:
					availability = "Digital product (unlimited)"

				results.append(
					InlineQueryResultArticle(
						id=str(uuid4()),
						title=product['name'],
						description=self.i18n.t('PRODUCT_PRICE_AVAILABILITY', language, price_text=price_text, availability=availability),
						input_message_content=InputTextMessageContent(
							self.i18n.t('SHOP_PRODUCT_DETAILS', language,
										product_name=product['name'],
										price_text=price_text,
										product_type=product['type'].capitalize(),
										availability=availability,
										description=product.get('description', 'No description available.'))
						),
						reply_markup=reply_markup,
						thumb_url=product.get('image_url')
					)
				)

		# Log inline usage
		chat_id = update.inline_query.chat_type
		if chat_id:
			self.db.log_user_activity(
				user_id=user_id,
				action="inline_shop_query",
				details={
					"query": query,
					"chat_id": chat_id,
					"results_count": len(results),
					"user_id": user_id
				}
			)

		await update.inline_query.answer(results, cache_time=300)