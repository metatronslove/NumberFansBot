from telegram import Update
from telegram.ext import (
	Application,
	CommandHandler,
	MessageHandler,
	ConversationHandler,
	filters,
	ContextTypes,
)
from Bot.config import Config
from Bot.database import Database
from Bot.Helpers.i18n import I18n
import base64
import os
import uuid
import logging

logger = logging.getLogger(__name__)

# Conversation states
CHECK_SELLER, SELECT_TYPE, PRODUCT_NAME, PRODUCT_DESCRIPTION, PRODUCT_PRICE, PRODUCT_QUANTITY, TAX_RATES, SHIPPING_FEE, UPLOAD_IMAGES, MEMBERSHIP_DETAILS, UPLOAD_FILE = range(11)

async def start_sell(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
	user_id = update.effective_user.id
	language = Database().get_user_language(user_id)

	# Check if user has Papara merchant account and email
	db = Database()
	i18n = I18n()
	user = db.execute_query("SELECT payment_info FROM users WHERE user_id = %s", (user_id,))
	if not user or not user[0].get('payment_info'):
		await update.message.reply_text(i18n.t("SELL_SETUP_PAPARA", language))
		return ConversationHandler.END

	await update.message.reply_text(i18n.t("SELL_SELECT_TYPE", language))
	return SELECT_TYPE

async def select_type(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
	user_id = update.effective_user.id
	language = Database().get_user_language(user_id)
	product_type = update.message.text.lower()

	if product_type not in ['shipped', 'download', 'membership']:
		await update.message.reply_text(i18n.t("SELL_INVALID_TYPE", language))
		return SELECT_TYPE

	context.user_data['product_type'] = product_type
	await update.message.reply_text(i18n.t("SELL_ENTER_PRODUCT_NAME", language))
	return PRODUCT_NAME

async def get_product_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
	context.user_data["product_name"] = update.message.text
	user_id = update.effective_user.id
	language = Database().get_user_language(user_id)
	await update.message.reply_text(i18n.t("SELL_ENTER_PRODUCT_DESCRIPTION", language))
	return PRODUCT_DESCRIPTION

async def get_product_description(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
	context.user_data["product_description"] = update.message.text
	user_id = update.effective_user.id
	language = Database().get_user_language(user_id)
	await update.message.reply_text(i18n.t("SELL_ENTER_PRODUCT_PRICE", language))
	return PRODUCT_PRICE

async def get_product_price(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
	user_id = update.effective_user.id
	language = Database().get_user_language(user_id)
	try:
		price = float(update.message.text)
		if price <= 0:
			await update.message.reply_text(i18n.t("SELL_INVALID_PRICE", language))
			return PRODUCT_PRICE
		context.user_data["product_price"] = price
	except ValueError:
		await update.message.reply_text(i18n.t("SELL_INVALID_PRICE", language))
		return PRODUCT_PRICE

	if context.user_data['product_type'] == 'shipped':
		await update.message.reply_text(i18n.t("SELL_ENTER_QUANTITY", language))
		return PRODUCT_QUANTITY
	elif context.user_data['product_type'] == 'membership':
		await update.message.reply_text(i18n.t("SELL_ENTER_MEMBERSHIP_DETAILS", language))
		return MEMBERSHIP_DETAILS
	else:
		await update.message.reply_text(i18n.t("SELL_UPLOAD_FILE", language))
		return UPLOAD_FILE

async def get_product_quantity(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
	user_id = update.effective_user.id
	language = Database().get_user_language(user_id)
	try:
		quantity = int(update.message.text)
		if quantity <= 0:
			await update.message.reply_text(i18n.t("SELL_INVALID_QUANTITY", language))
			return PRODUCT_QUANTITY
		context.user_data["product_quantity"] = quantity
	except ValueError:
		await update.message.reply_text(i18n.t("SELL_INVALID_QUANTITY", language))
		return PRODUCT_QUANTITY

	await update.message.reply_text(i18n.t("SELL_ENTER_TAX_RATES", language))
	return TAX_RATES

async def get_tax_rates(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
	user_id = update.effective_user.id
	language = Database().get_user_language(user_id)
	try:
		tax_input = update.message.text  # Format: "KDV:20,ÖTV:5"
		tax_rates = []
		for tax in tax_input.split(','):
			if tax:
				name, percentage = tax.split(':')
				tax_rates.append({"type": name.strip(), "percentage": float(percentage.strip())})
		context.user_data["tax_rates"] = tax_rates
	except ValueError:
		await update.message.reply_text(i18n.t("SELL_INVALID_TAX_RATES", language))
		return TAX_RATES

	await update.message.reply_text(i18n.t("SELL_ENTER_SHIPPING_FEE", language))
	return SHIPPING_FEE

async def get_shipping_fee(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
	user_id = update.effective_user.id
	language = Database().get_user_language(user_id)
	try:
		shipping_fee = float(update.message.text)
		if shipping_fee < 0:
			await update.message.reply_text(i18n.t("SELL_INVALID_SHIPPING_FEE", language))
			return SHIPPING_FEE
		context.user_data["shipping_fee"] = shipping_fee
	except ValueError:
		await update.message.reply_text(i18n.t("SELL_INVALID_SHIPPING_FEE", language))
		return SHIPPING_FEE

	await update.message.reply_text(i18n.t("SELL_UPLOAD_IMAGES", language))
	return UPLOAD_IMAGES

async def upload_images(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
	user_id = update.effective_user.id
	language = Database().get_user_language(user_id)

	if not update.message.photo:
		await update.message.reply_text(i18n.t("SELL_INVALID_IMAGE", language))
		return UPLOAD_IMAGES

	images = context.user_data.get("images", [])
	if len(images) >= 3:
		await update.message.reply_text(i18n.t("SELL_MAX_IMAGES", language))
		return await save_product(update, context)

	photo = update.message.photo[-1]
	file = await photo.get_file()
	file_bytes = await file.download_as_bytearray()
	image_base64 = base64.b64encode(file_bytes).decode('utf-8')
	images.append(image_base64)
	context.user_data["images"] = images

	if len(images) < 3:
		await update.message.reply_text(i18n.t("SELL_UPLOAD_MORE_IMAGES", language, remaining=3-len(images)))
		return UPLOAD_IMAGES
	return await save_product(update, context)

async def get_membership_details(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
	user_id = update.effective_user.id
	language = Database().get_user_language(user_id)
	try:
		details = update.message.text.split(',')
		group_id = int(details[0].strip())
		duration = details[1].strip().lower()
		if duration not in ['lifetime', 'yearly', 'monthly', 'weekly']:
			raise ValueError
		context.user_data["membership_details"] = {"group_id": group_id, "duration": duration}
		return await save_product(update, context)
	except (ValueError, IndexError):
		await update.message.reply_text(i18n.t("SELL_INVALID_MEMBERSHIP_DETAILS", language))
		return MEMBERSHIP_DETAILS

async def upload_file(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
	user_id = update.effective_user.id
	language = Database().get_user_language(user_id)

	if not update.message.document:
		await update.message.reply_text(i18n.t("SELL_INVALID_FILE", language))
		return UPLOAD_FILE

	document = update.message.document
	allowed_extensions = ['.pdf', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx', '.jpg', '.png', '.gif', '.mp4', '.zip', '.apk', '.stl', '.xcf']
	file_ext = os.path.splitext(document.file_name)[1].lower()
	if file_ext not in allowed_extensions:
		await update.message.reply_text(i18n.t("SELL_INVALID_FILE_TYPE", language))
		return UPLOAD_FILE

	file = await document.get_file()
	file_bytes = await file.download_as_bytearray()
	upload_dir = os.path.join("Uploads", str(user_id))
	os.makedirs(upload_dir, exist_ok=True)
	file_path = os.path.join(upload_dir, f"{uuid.uuid4()}{file_ext}")
	with open(file_path, 'wb') as f:
		f.write(file_bytes)
	context.user_data["file_path"] = file_path

	return await save_product(update, context)

async def save_product(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
	user_id = update.effective_user.id
	language = Database().get_user_language(user_id)
	db = Database()
	i18n = I18n()

	try:
		features = {
			"images": context.user_data.get("images", []),
			"tax_rates": context.user_data.get("tax_rates", []),
			"shipping_fee": context.user_data.get("shipping_fee", 0.0),
			"is_top_sale": False,
			"membership_details": context.user_data.get("membership_details", {})
		}

		product_id = db.create_product(
			name=context.user_data["product_name"],
			description=context.user_data["product_description"],
			price=context.user_data["product_price"],
			quantity=context.user_data.get("product_quantity"),
			product_type=context.user_data["product_type"],
			features=features,
			created_by=user_id
		)

		if context.user_data["product_type"] == "download":
			db.log_user_activity(
				user_id=user_id,
				action="upload_file",
				details={"product_id": product_id, "file_path": context.user_data.get("file_path")}
			)

		await update.message.reply_text(i18n.t("SELL_PRODUCT_ADDED", language))
	except Exception as err:
		logger.error(f"Error saving product: {str(err)}")
		await update.message.reply_text(i18n.t("SELL_ERROR", language, error=str(err)))
		return ConversationHandler.END

	context.user_data.clear()
	return ConversationHandler.END

async def cancel_sell(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
	user_id = update.effective_user.id
	language = Database().get_user_language(user_id)
	await update.message.reply_text(i18n.t("SELL_CANCELLED", language))
	context.user_data.clear()
	return ConversationHandler.END

def setup_sell_handler(application: Application) -> None:
	conv_handler = ConversationHandler(
		entry_points=[CommandHandler("sell", start_sell)],
		states={
			CHECK_SELLER: [MessageHandler(filters.TEXT & ~filters.COMMAND, start_sell)],
			SELECT_TYPE: [MessageHandler(filters.TEXT & ~filters.COMMAND, select_type)],
			PRODUCT_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_product_name)],
			PRODUCT_DESCRIPTION: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_product_description)],
			PRODUCT_PRICE: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_product_price)],
			PRODUCT_QUANTITY: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_product_quantity)],
			TAX_RATES: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_tax_rates)],
			SHIPPING_FEE: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_shipping_fee)],
			UPLOAD_IMAGES: [MessageHandler(filters.PHOTO, upload_images)],
			MEMBERSHIP_DETAILS: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_membership_details)],
			UPLOAD_FILE: [MessageHandler(filters.Document.ALL, upload_file)],
		},
		fallbacks=[CommandHandler("cancel", cancel_sell)],
	)
	application.add_handler(conv_handler)