import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InlineQueryResultArticle, InputTextMessageContent
from telegram.ext import CallbackContext, InlineQueryHandler
from uuid import uuid4
from Bot.database import Database

logger = logging.getLogger(__name__)

class UpdateInlineCommand:
	def __init__(self):
		self.db = Database()

	def register_handlers(self, dispatcher):
		dispatcher.add_handler(InlineQueryHandler(self.inline_update, pattern=r'^update'))

	def inline_update(self, update: Update, context: CallbackContext) -> None:
		"""Handle inline queries for product updates in groups"""
		query = update.inline_query.query
		user_id = update.effective_user.id

		# Check if user is blacklisted
		if self.db.is_blacklisted(user_id):
			return

		# Check if user is a shop admin
		if not self.db.is_shop_admin(user_id):
			results = [
				InlineQueryResultArticle(
					id=str(uuid4()),
					title="Permission Denied",
					description="You don't have permission to use shop update commands",
					input_message_content=InputTextMessageContent(
						"You don't have permission to use shop update commands. Please contact the administrator."
					)
				)
			]
			update.inline_query.answer(results, cache_time=300)
			return

		# Extract update type and parameters
		parts = query.split()
		if len(parts) < 2:
			# Show help for update commands
			results = [
				InlineQueryResultArticle(
					id=str(uuid4()),
					title="Shop Update Commands",
					description="Available commands: new, sale, restock, announcement",
					input_message_content=InputTextMessageContent(
						"Shop Update Commands:\n\n"
						"• @YourBot update new [product_name] - Announce a new product\n"
						"• @YourBot update sale [discount]% - Announce a sale\n"
						"• @YourBot update restock [product_id] - Announce a product restock\n"
						"• @YourBot update announcement [text] - Make a general announcement"
					)
				)
			]
		else:
			update_type = parts[1].lower()

			if update_type == "new" and len(parts) > 2:
				# New product announcement
				product_name = " ".join(parts[2:])
				results = self.create_new_product_announcement(product_name)
			elif update_type == "sale" and len(parts) > 2:
				# Sale announcement
				try:
					discount = int(parts[2].rstrip("%"))
					results = self.create_sale_announcement(discount)
				except ValueError:
					results = [
						InlineQueryResultArticle(
							id=str(uuid4()),
							title="Invalid Format",
							description="Use: update sale [number]%",
							input_message_content=InputTextMessageContent(
								"Invalid sale format. Use: @YourBot update sale [number]%\n"
								"Example: @YourBot update sale 20%"
							)
						)
					]
			elif update_type == "restock" and len(parts) > 2:
				# Restock announcement
				try:
					product_id = int(parts[2])
					results = self.create_restock_announcement(product_id)
				except ValueError:
					results = [
						InlineQueryResultArticle(
							id=str(uuid4()),
							title="Invalid Format",
							description="Use: update restock [product_id]",
							input_message_content=InputTextMessageContent(
								"Invalid restock format. Use: @YourBot update restock [product_id]\n"
								"Example: @YourBot update restock 2"
							)
						)
					]
			elif update_type == "announcement" and len(parts) > 2:
				# General announcement
				announcement_text = " ".join(parts[2:])
				results = self.create_general_announcement(announcement_text)
			else:
				# Unknown update type
				results = [
					InlineQueryResultArticle(
						id=str(uuid4()),
						title="Unknown Update Type",
						description="Available types: new, sale, restock, announcement",
						input_message_content=InputTextMessageContent(
							"Unknown update type. Available commands:\n\n"
							"• @YourBot update new [product_name] - Announce a new product\n"
							"• @YourBot update sale [discount]% - Announce a sale\n"
							"• @YourBot update restock [product_id] - Announce a product restock\n"
							"• @YourBot update announcement [text] - Make a general announcement"
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
					"chat_id": chat_id
				}
			)

		update.inline_query.answer(results, cache_time=300)

	def create_new_product_announcement(self, product_name):
		"""Create announcement for a new product"""
		keyboard = [
			[InlineKeyboardButton("View Product", url=f"https://t.me/YourBot?start=shop")]
		]
		reply_markup = InlineKeyboardMarkup(keyboard)

		return [
			InlineQueryResultArticle(
				id=str(uuid4()),
				title=f"New Product: {product_name}",
				description="Announce a new product to the group",
				input_message_content=InputTextMessageContent(
					f"🆕 *NEW PRODUCT ANNOUNCEMENT* 🆕\n\n"
					f"We're excited to announce our newest product:\n"
					f"*{product_name}*\n\n"
					f"Check it out now in our shop! Limited quantities available."
				),
				reply_markup=reply_markup
			)
		]

	def create_sale_announcement(self, discount):
		"""Create announcement for a sale"""
		keyboard = [
			[InlineKeyboardButton("Shop Now", url=f"https://t.me/YourBot?start=shop")]
		]
		reply_markup = InlineKeyboardMarkup(keyboard)

		return [
			InlineQueryResultArticle(
				id=str(uuid4()),
				title=f"{discount}% Off Sale!",
				description=f"Announce a {discount}% discount sale",
				input_message_content=InputTextMessageContent(
					f"🔥 *SALE ANNOUNCEMENT* 🔥\n\n"
					f"We're running a special promotion!\n\n"
					f"*{discount}% OFF* on selected items\n\n"
					f"Limited time offer - shop now while supplies last!"
				),
				reply_markup=reply_markup
			)
		]

	def create_restock_announcement(self, product_id):
		"""Create announcement for a product restock"""
		# Get product details
		product = self.db.get_product_by_id(product_id)

		if not product:
			return [
				InlineQueryResultArticle(
					id=str(uuid4()),
					title="Product Not Found",
					description=f"No product found with ID {product_id}",
					input_message_content=InputTextMessageContent(
						f"Error: No product found with ID {product_id}."
					)
				)
			]

		keyboard = [
			[InlineKeyboardButton("Buy Now", url=f"https://t.me/YourBot?start=buy_{product_id}")]
		]
		reply_markup = InlineKeyboardMarkup(keyboard)

		return [
			InlineQueryResultArticle(
				id=str(uuid4()),
				title=f"Restock: {product['name']}",
				description=f"Announce restock of {product['name']}",
				input_message_content=InputTextMessageContent(
					f"📦 *RESTOCK ALERT* 📦\n\n"
					f"*{product['name']}* is back in stock!\n\n"
					f"Price: {product['price']} TL\n\n"
					f"Get yours before they're gone again!"
				),
				reply_markup=reply_markup,
				thumb_url=product.get('image_url')
			)
		]

	def create_general_announcement(self, announcement_text):
		"""Create a general shop announcement"""
		keyboard = [
			[InlineKeyboardButton("Visit Shop", url=f"https://t.me/YourBot?start=shop")]
		]
		reply_markup = InlineKeyboardMarkup(keyboard)

		return [
			InlineQueryResultArticle(
				id=str(uuid4()),
				title="Shop Announcement",
				description="Send a general shop announcement",
				input_message_content=InputTextMessageContent(
					f"📢 *SHOP ANNOUNCEMENT* 📢\n\n"
					f"{announcement_text}"
				),
				reply_markup=reply_markup
			)
		]
