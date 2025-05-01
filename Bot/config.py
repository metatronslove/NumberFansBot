import os
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class Config:
	def __init__(self):
		self.available_languages = ['en', 'tr', 'ar', 'he', 'la']
		self._load_attributes()

	def _load_attributes(self):
		# Standard settings
		self.telegram_token = os.getenv('TELEGRAM_TOKEN')
		self.bot_username = os.getenv('BOT_USERNAME', '@NumberFansBot')
		self.webhook_url = os.getenv('WEBHOOK_URL')
		self.mongodb_uri = os.getenv('MONGODB_URI')
		self.github_username = os.getenv('GITHUB_USERNAME')
		self.github_token = os.getenv('GITHUB_TOKEN')
		self.github_repo = os.getenv('GITHUB_REPO')
		self.github_pages_url = os.getenv('GITHUB_PAGES_URL')
		self.payment_provider_token = os.getenv('PAYMENT_PROVIDER_TOKEN')
		self.currency_exchange_token = os.getenv('CURRENCY_EXCHANGE_TOKEN')
		self.huggingface_access_token = os.getenv('HUGGINGFACE_ACCESS_TOKEN')
		self.flask_secret_key = os.getenv('FLASK_SECRET_KEY')

		# AI settings
		self.ai_model_url = os.getenv('AI_MODEL_URL')
		self.ai_access_token = os.getenv('AI_ACCESS_TOKEN', self.huggingface_access_token)

		# Validate critical configurations
		if not self.telegram_token:
			logger.error("TELEGRAM_TOKEN is not set")
			raise ValueError("TELEGRAM_TOKEN is required")
		if not self.mongodb_uri:
			logger.error("MONGODB_URI is not set")
			raise ValueError("MONGODB_URI is required")
		if not self.flask_secret_key:
			logger.error("FLASK_SECRET_KEY is not set")
			raise ValueError("FLASK_SECRET_KEY is required")

config = Config()