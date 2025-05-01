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
            'ai_settings': {}
        }
        self._load_yaml_config()
        self._load_attributes()

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
        self.telegram_token = self._config.get('telegram_token') or os.getenv('TELEGRAM_TOKEN')
        self.bot_username = self._config.get('bot_username') or os.getenv('BOT_USERNAME', '@NumberFansBot')
        self.webhook_url = self._config.get('webhook_url') or os.getenv('WEBHOOK_URL')
        self.mongodb_uri = self._config.get('mongodb_uri') or os.getenv('MONGODB_URI')
        self.github_username = self._config.get('github_username') or os.getenv('GITHUB_USERNAME')
        self.github_token = self._config.get('github_token') or os.getenv('GITHUB_TOKEN')
        self.github_repo = self._config.get('github_repo') or os.getenv('GITHUB_REPO')
        self.github_pages_url = self._config.get('github_pages_url') or os.getenv('GITHUB_PAGES_URL')
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
        if not self.mongodb_uri:
            logger.error("MONGODB_URI is not set")
            raise ValueError("MONGODB_URI is required")
        if not self.flask_secret_key:
            logger.error("FLASK_SECRET_KEY is not set")
            raise ValueError("FLASK_SECRET_KEY is required")

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