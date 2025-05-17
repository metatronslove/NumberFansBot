import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InlineQueryResultArticle, InputTextMessageContent
from telegram.ext import CallbackContext, InlineQueryHandler
from uuid import uuid4
from Bot.database import Database

logger = logging.getLogger(__name__)

class ShopInlineCommand:
	def __init__(self):
		self.db = Database()

	def register_handlers(self, dispatcher):
		dispatcher.add_handler(InlineQueryHandler(self.inline_shop, pattern=r'^shop'))

	def inline_shop(self, update: Update, context: CallbackContext) -> None:
		"""Handle inline queries for shop listings"""
		query = update.inline_query.query
		user_id = update.effective_user.id

		# Check if user is blacklisted
		if self.db.is_blacklisted(user_id):
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
					title="No products found",
					description="Try a different search term or browse all products",
					input_message_content=InputTextMessageContent(
						"No products match your search criteria. Try a different search term or use /buy to browse all products."
					)
				)
			]
		else:
			# Create results for each product
			results = []
			for product in products:
				# Create keyboard for the product
				keyboard = [
					[InlineKeyboardButton("Buy Now", url=f"https://t.me/YourBot?start=buy_{product['id']}")],
					[InlineKeyboardButton("View Details", url=f"https://t.me/YourBot?start=product_{product['id']}")]
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
						description=f"{price_text} - {availability}",
						input_message_content=InputTextMessageContent(
							f"*{product['name']}*\n"
							f"Price: {price_text}\n"
							f"Type: {product['type'].capitalize()}\n"
							f"{availability}\n\n"
							f"{product.get('description', 'No description available.')}"
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
					"results_count": len(results)
				}
			)

		update.inline_query.answer(results, cache_time=300)
