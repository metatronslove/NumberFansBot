import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InlineQueryResultArticle, InputTextMessageContent
from telegram.ext import Application, CallbackContext, InlineQueryHandler
from uuid import uuid4
from Bot.database import Database

logger = logging.getLogger(__name__)

class ProductInlineCommand:
	def __init__(self):
		self.db = Database()
		self.bot_username = "@YourBot"  # Replace with actual bot username or config

	def register_handlers(self, application: Application):
		application.add_handler(InlineQueryHandler(self.inline_product, pattern=r'^product'))

	async def inline_product(self, update: Update, context: CallbackContext) -> None:
		"""Handle inline queries for specific product details"""
		query = update.inline_query.query
		user_id = update.effective_user.id

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
						title="Product not found",
						description=f"No product found with ID {product_id}",
						input_message_content=InputTextMessageContent(
							f"No product found with ID {product_id}. Try browsing all products with /buy."
						)
					)
				]
			else:
				# Create keyboard for the product
				keyboard = [
					[InlineKeyboardButton("Buy Now", url=f"https://t.me/{self.bot_username}?start=buy_{product['id']}")],
					[InlineKeyboardButton("View All Products", url=f"https://t.me/{self.bot_username}?start=shop")]
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

				message_content = (
					f"*{product['name']}*\n\n"
					f"Price: {price_text}\n"
					f"Type: {product['type'].capitalize()}\n"
					f"{availability}\n\n"
					f"{description}\n\n"
				)

				if features_text:
					message_content += f"Features:\n{features_text}\n\n"

				message_content += "Use the buttons below to purchase this product."

				results = [
					InlineQueryResultArticle(
						id=str(uuid4()),
						title=product['name'],
						description=f"{price_text} - {availability}",
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
					title="Product Search",
					description="Use 'product [ID]' to view details of a specific product",
					input_message_content=InputTextMessageContent(
						f"To view product details, use the inline query format: {self.bot_username} product [ID]\n"
						f"For example: {self.bot_username} product 1\n\n"
						f"Or browse all products with: {self.bot_username} shop"
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