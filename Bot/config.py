import os
import logging
import yaml
from pathlib import Path

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class Config:
	def __init__(self):
		self.available_languages = ['en', 'tr', 'ar', 'he', 'la']
		self._config = {
			'mysql': {},
			'ai_settings': {}
		}
		self._load_yaml_config()
		self._load_attributes()
		self.models = self.load_models()

	def _load_yaml_config(self):
		config_file = Path('Config/config.yml')
		if config_file.exists():
			try:
				with open(config_file, 'r') as f:
					yaml_config = yaml.safe_load(f) or {}
				self._config.update(yaml_config)
			except Exception as e:
				logger.error(f"Failed to load config.yml: {str(e)}")

	def _load_attributes(self):
		# Standard settings
		self.config_dir = Path('Config')
		self.teskilat_creditentials = self._config.get('teskilat_creditentials') or os.getenv('TESKILAT_CREDITENTIALS')
		self.telegram_token = self._config.get('telegram_token') or os.getenv('TELEGRAM_TOKEN')
		self.bot_username = self._config.get('bot_username') or os.getenv('BOT_USERNAME', '@NumberFansBot')
		self.webhook_url = self._config.get('webhook_url') or os.getenv('WEBHOOK_URL')
		self.mysql_host = self._config.get('mysql', {}).get('host') or os.getenv('MYSQL_HOST', 'mysql-numberfansbot-numberfansbot.j.aivencloud.com')
		self.mysql_user = self._config.get('mysql', {}).get('user') or os.getenv('MYSQL_USER', 'avnadmin')
		self.mysql_port = self._config.get('mysql', {}).get('user') or os.getenv('MYSQL_PORT', 28236)
		self.mysql_password = self._config.get('mysql', {}).get('password') or os.getenv('MYSQL_PASSWORD', 'your_password_here')  # Replace with actual password
		self.mysql_database = self._config.get('mysql', {}).get('database') or os.getenv('MYSQL_DATABASE', 'numberfansbot')  # Replace with actual database name
		self.github_username = self._config.get('github_username') or os.getenv('GITHUB_USERNAME')
		self.github_token = self._config.get('github_token') or os.getenv('GITHUB_TOKEN')
		self.github_repo = self._config.get('github_repo') or os.getenv('GITHUB_REPO')
		self.github_pages_url = os.getenv('GITHUB_PAGES_URL') or self._config.get('github_pages_url')
		self.payment_provider_token = self._config.get('payment_provider_token') or os.getenv('PAYMENT_PROVIDER_TOKEN')
		self.currency_exchange_token = self._config.get('currency_exchange_token') or os.getenv('CURRENCY_EXCHANGE_TOKEN')
		self.huggingface_access_token = self._config.get('huggingface_access_token') or os.getenv('HUGGINGFACE_ACCESS_TOKEN')
		self.flask_secret_key = self._config.get('flask_secret_key') or os.getenv('FLASK_SECRET_KEY')

		# AI settings
		self.ai_model_url = self._config.get('ai_settings', {}).get('model_url') or os.getenv('AI_MODEL_URL')
		self.ai_access_token = self._config.get('ai_settings', {}).get('access_token') or os.getenv('AI_ACCESS_TOKEN', self.huggingface_access_token)

		# Validate critical configurations
		if not self.telegram_token:
			logger.error("TELEGRAM_TOKEN is not set")
			raise ValueError("TELEGRAM_TOKEN is required")
		if not all([self.mysql_host, self.mysql_user, self.mysql_password, self.mysql_database]):
			logger.error("MySQL configuration incomplete")
			raise ValueError("MySQL host, user, password, and database are required")
		if not self.flask_secret_key:
			logger.error("FLASK_SECRET_KEY is not set")
			raise ValueError("FLASK_SECRET_KEY is required")

	def load_models(self):
		"""Load models from Config/models.yml"""
		models_file = Path("Config/models.yml")
		if models_file.exists():
			try:
				with open(models_file, "r") as f:
					models_data = yaml.safe_load(f) or {"models": []}
				return {m["name"]: type("Model", (), m) for m in models_data["models"]}
			except Exception as e:
				logger.error(f"Failed to load models.yml: {str(e)}")
				return {}
		return {}

	def save_config(self, config_data):
		"""Save configuration to config.yml"""
		try:
			self._config.update(config_data)
			with open('Config/config.yml', 'w') as f:
				yaml.dump(self._config, f)
			self._load_attributes()  # Reload attributes after saving
		except Exception as e:
			logger.error(f"Failed to save config.yml: {str(e)}")
			raise

config = Config()