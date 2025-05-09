# NumberFansBot

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
CREATE TABLE users (
    user_id BIGINT PRIMARY KEY,
    credits INT DEFAULT 100,
    is_beta_tester BOOLEAN DEFAULT FALSE,
    language_code VARCHAR(5) DEFAULT 'en'
);
```

### 3. Render.com Dağıtımı
1. GitHub reposunu Render'a bağlayın
2. `Web Service` tipinde yeni servis oluşturun
3. Build komutu olarak `pip install -r requirements.txt` ekleyin
4. Start komutu: `gunicorn admin_panel:app --worker-class gevent`

## 💰 Bağış Desteği
Bu proje eski bir bilgisayarda geliştirilmiştir. Daha fazla özellik ekleyebilmemiz için bağışlarınız büyük önem taşır:

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

### Önemli Değişiklikler:
1. **Veritabanı Güncellemesi**:
   - MongoDB → MySQL geçişi vurgulandı
   - Yeni tablo yapısı eklendi

2. **Yeni Komutlar**:
   - `/huddam`, `/unsur`, `/nutket` komutları eklendi
   - Tüm komutlar tablo halinde gösterildi

3. **Bağış Bilgisi**:
   - Papara entegrasyonu ve bağış önemi vurgulandı

4. **Teknoloji Stack**:
   - Güncel bağımlılıklar ve mimari şema eklendi

5. **Yönetici Paneli**:
   - Yeni Flask tabanlı admin özellikleri tanıtıldı

6. **Görsel Destek**:
   - Örnek ekran görüntüleri için placeholder linkler eklendi
Bu README, projenin tüm yeni özelliklerini kapsayacak şekilde güncellenmiştir. Görseller için `assets/` klasörüne örnek screenshot'lar eklemeyi unutmayı
