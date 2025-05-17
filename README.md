# NumberFansBot
Ustalar şimdi ben buna Papara ile entegre bir kullanıcılarla paylaşımlı bir alış veriş modeli uydurdum ama tutar ama tutmaz denemedim ve zaten güvenlik geliştirmesi de yapmadım; hiç bir garantisi de yok; denemek isteyene serbest ama para kazanma gibi bir durumla karşılaşırsanız beni de görmezseniz yemin olsun helâl etmem. Şart olsun etmem :) Bu bota emeğim 30 günü geçti tâllahi büyük ayıp edersiniz bağış yapmadan geçerseniz; bu kadar da MIT license ile geliştirme hakkınız var. Zaten benim temel amacım bir konsept oluşturmak; öncelikli hedefim bu botu kendim çalıştırmak şimdilik değil; zaten maliyeti de karşılayamam çünkü bağış gelmiyor; devletiniz hepinizin gelirlerini kurutmuş ki size söz geçirebilsin. Bir de kodlarımı indirip geçenler oluyor sanki yol kenarındaki ağaçtan meyve yolup geçiyor; sadaka sayıyor para da vermiyor, bağış da yapmıyor ve dahası benim ismim geçerse kendi namı yere dökülecekmiş gibi forklamaya asla yanaşmadan kodu indirip kullanıyor ve geliştirmeleri hakkında edindiği ilhama katkılarını benimle paylaşmaktan kaçınıyor çünkü bu alış veriş tek taraflı oluyor; alıp kaçma şeklinde yani; kap kaç yapmayın, madem indiriyorsun merakını gideriyorsun demek ki bir yarar sağlıyorsun; her delikanlı adama yakışacağı gibi bir geri dönüş yap; bağış yapabilecek mecalin, dermanın yoksa bile geri bildirim yapmaya üşenme ki alemde halâ adam varmış diyebilelim içimizden
NumberFansBot, Telegram üzerinden numeroloji, ebced (abjad), sihirli kare ve element analizi hesaplamaları yapan gelişmiş bir bottur. Kullanıcıların metin veya sayılar için çeşitli hesaplamalar yapmasına olanak tanır ve 5 dilde destek sunar (Türkçe, İngilizce, Arapça, İbranice, Latince). Bot, Render.com üzerinde çalışır ve MySQL veritabanı kullanır.

![Bot Örnek Görseli](https://metatronslove.github.io/github-repo-traffic-viewer/assets/bot-preview.png)

## ✨ Öne Çıkan Özellikler
- **Çok Dilli Destek**: `/language` komutuyla dil değiştirebilir
- **20+ Komut**: Ebced, numeroloji, element analizi ve sihirli kareler
- **AI Entegrasyonu**: Hugging Face API ile akıllı yorumlar
- **Yönetici Paneli**: Kullanıcı yönetimi ve istatistikler için web arayüzü
- **Kredi Sistemi**: Premium özellikler için esnek ödeme entegrasyonu

## 🛠️ Teknik Yapı
| Bileşen          | Teknoloji               |
|------------------|-------------------------|
| Backend          | Python 3.10+            |
| Framework        | python-telegram-bot v20 |
| Veritabanı       | MySQL                   |
| Web Arayüzü      | Flask + Bootstrap       |
| Hosting          | Render.com              |
| Ödeme Sistemi    | Papara API              |

## 📋 Komut Listesi
| Komut           | Açıklama                          | Örnek Kullanım            |
|-----------------|-----------------------------------|---------------------------|
| `/abjad`        | Metnin ebced değerini hesaplar    | `/abjad selam`            |
| `/bastet`       | Sayısal tekrarlı hesaplama        | `/bastet 19`              |
| `/huddam`       | Varlık ismi üretir                | `/huddam 36`              |
| `/unsur`        | Element analizi yapar             | `/unsur ateş`             |
| `/magicsquare`  | Sihirli kare oluşturur            | `/magicsquare 15`         |
| `/nutket`       | Sayıyı harflere çevirir           | `/nutket 100`             |
| `/payment`      | Kredi satın alma paneli           | `/payment`                |

## 🚀 Kurulum Rehberi

### Ön Koşullar
- **MySQL Veritabanı** (Aiven veya benzeri)
- **Telegram Bot Token** (@BotFather'dan)
- **Render.com Hesabı**
- **Papara API Anahtarı** (Ödeme için)

### 1. Ortam Değişkenleri
`Config/config.yml` dosyasını veya Render.com ortam değişkenlerini şu şekilde ayarlayın:

```env
TELEGRAM_TOKEN=123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11
MYSQL_HOST=mysql-numberfansbot-numberfansbot.aivencloud.com
MYSQL_USER=avnadmin
MYSQL_PASSWORD=sifreniz
MYSQL_DATABASE=numberfansbot
MYSQL_PORT=28236
PAYMENT_PROVIDER_TOKEN=papara_api_anahtari
HUGGINGFACE_ACCESS_TOKEN=hf_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
FLASK_SECRET_KEY=benzersiz-gizli-anahtar-32-karakter
```

### 2. Veritabanı Kurulumu
MySQL'de şu tabloları oluşturun:

```sql
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
	type VARCHAR(50),		  	-- e.g., "group", "supergroup", "channel"
	is_public BOOLEAN,		 	-- True if public, False if private
	member_count INT,		  	-- Number of members
	creator_id BIGINT,		 	-- ID of the founder
	admins JSON,   				-- List of admin IDs as JSON
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
```

### 3. Render.com Dağıtımı
1. GitHub reposunu Render'a bağlayın
2. `Web Service` tipinde yeni servis oluşturun
3. Build komutu olarak `pip install -r requirements.txt` ekleyin (Dockerfile bunu hallediyor)
4. Start komutu: `gunicorn admin_panel:app --worker-class gevent`

## 💰 Bağış Desteği
Bu proje eski bir bilgisayarda geliştirilmiştir. Daha fazla özellik ekleyebilmemiz için bağışlarınız büyük önem taşır; arkadaşlar, telegrama, render'a, sql veritabanına, internet faturasına, elektrik faturasına size dayatıldığı için para buluyorsunuz; bu kadar emek verdim bir 1000'lira etmiyor mu paylaştığım kodun size verdiği ilham siz bana nasıl çok görmüş iseniz hayat da size gerekeni çok göre meğer ki lutfu ikramdan cömertliğiniz soframa nimet olmuş ise benim ikramım cenabınıza ancak helâl ola öyle:

**Papara**:
[![Papara ile Destekle](https://img.shields.io/badge/Bağış%20Yap-%E2%9D%A4-blue)](https://ppr.ist/1T9dx8tUT)

## 🌐 Yönetici Paneli
`https://your-render-url.com/en/login` adresinden erişebilirsiniz:

- Kullanıcı yönetimi
- Komut istatistikleri
- Gerçek zamanlı log görüntüleme
- Dosya editörü entegrasyonu

![Admin Panel](https://metatronslove.github.io/github-repo-traffic-viewer/assets/admin-preview.png)

## 📜 Lisans
MIT Lisansı - Detaylar için `LICENSE` dosyasına bakınız.

## 🤝 Katkıda Bulunma
1. Forklayın ve `develop` branch'inde değişiklik yapın
2. Pull Request açın
3. Yeni dil eklemek için `Bot/Locales/` dizinine JSON dosyası ekleyin

## 📞 İletişim
Sorularınız için GitHub Issues kullanın veya Telegram'dan @MetatronsLove hesabına ulaşın.