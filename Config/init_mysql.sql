CREATE DATABASE IF NOT EXISTS numberfansbot;
USE numberfansbot;

CREATE TABLE IF NOT EXISTS users (
	user_id BIGINT PRIMARY KEY,
	chat_id BIGINT NOT NULL,
	username VARCHAR(255),
	first_name VARCHAR(255),
	last_name VARCHAR(255),
	language_code VARCHAR(10) DEFAULT 'en',
	is_beta_tester BOOLEAN DEFAULT FALSE,
	is_blacklisted BOOLEAN DEFAULT FALSE,
	is_teskilat BOOLEAN DEFAULT FALSE,
	credits INT DEFAULT 0,
	is_admin BOOLEAN DEFAULT FALSE,
	password VARCHAR(255),
	created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
	last_interaction DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS groups (
    group_id BIGINT PRIMARY KEY,
    group_name VARCHAR(255),
    type VARCHAR(50),          -- e.g., "group", "supergroup", "channel"
    is_public BOOLEAN,         -- True if public, False if private
    member_count INT,          -- Number of members
    creator_id BIGINT,         -- ID of the founder
    admins JSON,               -- List of admin IDs as JSON
    is_blacklisted BOOLEAN DEFAULT FALSE,
    added_at DATETIME
);

CREATE TABLE IF NOT EXISTS transliterations (
	id BIGINT AUTO_INCREMENT PRIMARY KEY,
	source_name VARCHAR(255) NOT NULL,
	source_lang VARCHAR(50) NOT NULL,
	target_lang VARCHAR(50) NOT NULL,
	transliterated_name VARCHAR(255) NOT NULL,
	suffix VARCHAR(255),
	score INT DEFAULT 1,
	user_id BIGINT,
	created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
	INDEX idx_transliteration (source_name, source_lang, target_lang, transliterated_name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS transliteration_cache (
	cache_id VARCHAR(8) PRIMARY KEY,
	user_id BIGINT NOT NULL,
	source_lang VARCHAR(10) NOT NULL,
	target_lang VARCHAR(10) NOT NULL,
	source_name TEXT NOT NULL,
	alternatives JSON NOT NULL,
	created_at DOUBLE NOT NULL,
	INDEX idx_created_at (created_at)
);

CREATE TABLE IF NOT EXISTS command_usage (
	id BIGINT AUTO_INCREMENT PRIMARY KEY,
	user_id BIGINT NOT NULL,
	last_used DATETIME,
	last_user_id BIGINT,
	command VARCHAR(255) NOT NULL,
	count INT DEFAULT 1,
	UNIQUE INDEX idx_user_command (user_id, command)
);

CREATE TABLE IF NOT EXISTS inline_usage (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id BIGINT,
    chat_id BIGINT,
    query TEXT,
    timestamp DATETIME
);

CREATE TABLE IF NOT EXISTS user_settings (
	id BIGINT AUTO_INCREMENT PRIMARY KEY,
	user_id BIGINT NOT NULL,
	setting_key VARCHAR(255) NOT NULL,
	setting_value TEXT,
	UNIQUE INDEX idx_user_setting (user_id, setting_key)
);

CREATE TABLE IF NOT EXISTS orders (
	id BIGINT AUTO_INCREMENT PRIMARY KEY,
	user_id BIGINT NOT NULL,
	amount INT NOT NULL,
	currency VARCHAR(10) NOT NULL,
	payload TEXT,
	credits_added INT DEFAULT 0,
	created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS user_activity (
	id BIGINT AUTO_INCREMENT PRIMARY KEY,
	user_id BIGINT NOT NULL,
	action VARCHAR(255) NOT NULL,
	details JSON,
	timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- TTL-like behavior for transliteration_cache
DELIMITER //
CREATE EVENT IF NOT EXISTS clean_transliteration_cache
ON SCHEDULE EVERY 1 HOUR
DO
BEGIN
	DELETE FROM transliteration_cache WHERE created_at < UNIX_TIMESTAMP() - 3600;
END //
DELIMITER ;