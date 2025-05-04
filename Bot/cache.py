import mysql.connector
from .config import config
import hashlib
import time
import json

class Cache:
    def __init__(self):
        self.conn = mysql.connector.connect(
            host=config.mysql_host.split(':')[0],
            port=int(config.mysql_host.split(':')[1]) if ':' in config.mysql_host else 3306,
            user=config.mysql_user,
            password=config.mysql_password,
            database=config.mysql_database
        )
        self.cursor = self.conn.cursor(dictionary=True)

    def store_alternatives(self, user_id: int, source_lang: str, target_lang: str, text: str, alternatives: list) -> str:
        """Store alternatives and return a cache ID."""
        cache_id = hashlib.md5(f"{user_id}:{text}:{time.time()}".encode()).hexdigest()[:8]
        query = """
        INSERT INTO transliteration_cache (cache_id, user_id, source_lang, target_lang, source_name, alternatives, created_at)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        """
        self.cursor.execute(query, (
            cache_id,
            user_id,
            source_lang,
            target_lang,
            text,
            json.dumps(alternatives),
            time.time()
        ))
        self.conn.commit()
        return cache_id

    def get_alternatives(self, cache_id: str) -> dict:
        """Retrieve alternatives by cache ID."""
        query = "SELECT * FROM transliteration_cache WHERE cache_id = %s"
        self.cursor.execute(query, (cache_id,))
        result = self.cursor.fetchone()
        if result:
            result['alternatives'] = json.loads(result['alternatives'])
        return result or {}

    def __del__(self):
        self.cursor.close()
        self.conn.close()