# NumberFansBot

NumberFansBot, Telegram üzerinden numeroloji, ebced (abjad) ve sihirli kare hesaplamaları yapan bir bottur. Kullanıcıların metin veya sayılar için çeşitli hesaplamalar yapmasına olanak tanır ve çok dilli destek sunar (Türkçe, İngilizce, Arapça, İbranice, Latince). Bot, Render.com üzerinde çalışır ve yapılandırma için ortam değişkenlerini kullanır.

## Özellikler
- **Çok Dilli Destek**: Türkçe, İngilizce, Arapça, İbranice ve Latince dillerinde çalışır. Kullanıcılar `/language` komutuyla dil değiştirebilir; `/start` komutu, Telegram dilini otomatik algılar.
- **Komutlar**:
  - `/start`: Botu başlatır, kullanıcının Telegram diline göre dili ayarlar (ör. Türkçe için `tr`).
  - `/abjad <metin>`: Verilen metnin ebced değerini hesaplar, alfabe sırası ve şedde seçenekleriyle.
  - `/bastet <sayı>`: Sayılar üzerinde tekrarlı ebced hesaplamaları yapar, tablo ve dil seçenekleriyle.
  - `/numerology <metin> [yöntem] <alfabe>`: Metnin numeroloji değerini hesaplar, farklı alfabe ve yöntemlerle.
- **Uyarı Numaraları**: `/abjad`, `/bastet` ve `/numerology` komutları, sonuç 36 veya 37 gibi özel değerler döndüğünde `/Config/warningNumbers.json` dosyasından dil bazlı açıklamalar ekler.
- **Yönetici Paneli**: `https://<your-render-url>/en/login` adresinde kullanıcı verilerini ve komut kullanımını izlemek için Flask tabanlı bir arayüz.
- **AI Yorumları**: Hesaplama sonuçlarına Hugging Face API üzerinden AI tabanlı yorumlar ekler.

## Kurulum

### Ön Koşullar
- **GitHub Hesabı**: Kodu saklamak ve Render.com ile entegre etmek için.
- **Render.com Hesabı**: Botu barındırmak için.
- **Telegram BotFather**: Bot oluşturmak ve `TELEGRAM_TOKEN` almak için.
- **MongoDB Atlas**: Kullanıcı verilerini saklamak için `MONGODB_URI`.
- **Hugging Face API**: AI yorumları için `HUGGINGFACE_ACCESS_TOKEN` ve `AI_ACCESS_TOKEN`.

### Adım Adım Kurulum

1. **Depoyu Klonlayın**:
   ```bash
   git clone https://github.com/<kullanici-adi>/<depo-adi>.git
   cd <depo-adi>
   ```

2. **Ortam Değişkenlerini Ayarlayın**:
   - Render.com'da yeni bir Web Servisi oluşturun.
   - "Ortam" sekmesinde aşağıdaki ortam değişkenlerini ekleyin:
     ```plaintext
     TELEGRAM_TOKEN=123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11
     MONGODB_URI=mongodb+srv://kullanici:sifre@cluster0.mongodb.net/numberfansbot
     GITHUB_USERNAME=kullanici-adi
     GITHUB_TOKEN=ghp_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
     PAYMENT_PROVIDER_TOKEN=pk_test_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
     CURRENCY_EXCHANGE_TOKEN=doviz-api-anahtari
     HUGGINGFACE_ACCESS_TOKEN=hf_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
     AI_ACCESS_TOKEN=hf_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
     AI_MODEL_URL=https://api-inference.huggingface.co/models/mixtralai/Mixtral-8x7B-Instruct-v0.1
     FLASK_SECRET_KEY=benzersiz-gizli-anahtar
     PORT=8000
     PYTHONUNBUFFERED=1
     BOT_USERNAME=@BotKullaniciAdi
     WEBHOOK_URL=https://<your-render-url>/webhook
     GITHUB_REPO=kullanici-adi/depo-adi
     GITHUB_PAGES_URL=https://kullanici-adi.github.io/depo-adi
     ```
   - `FLASK_SECRET_KEY` oluşturmak için:
     ```bash
     python -c "import secrets; print(secrets.token_urlsafe(32))"
     ```

3. **Bağımlılıkları Yükleyin**:
   - `requirements.txt` dosyasını kontrol edin:
     ```plaintext
     python-telegram-bot>=20.0
     pymongo>=4.0
     flask>=2.0
     gunicorn>=20.0
     requests>=2.0
     ```
   - Render.com otomatik olarak `requirements.txt` üzerinden bağımlılıkları yükler.

4. **Değişiklikleri Yükleyin**:
   ```bash
   git add .
   git commit -m "İlk kurulum ve yapılandırma"
   git push origin main
   ```

5. **Render.com'da Dağıtım**:
   - Render.com, GitHub push'undan sonra otomatik dağıtım yapar.
   - "Olaylar" sekmesinden dağıtım durumunu izleyin.

6. **Webhook Ayarlayın**:
   ```bash
   curl https://<your-render-url>/set_webhook
   curl https://api.telegram.org/bot<TELEGRAM_TOKEN>/getWebhookInfo
   ```
   - Çıktı: `{"ok":true,"result":{"url":"https://<your-render-url>/webhook",...}}`

## Kullanım

1. **Botu Başlatın**:
   - Telegram'da `@BotKullaniciAdi` ile konuşmaya başlayın.
   - `/start` komutunu gönderin. Bot, Telegram dilinizi algılar (ör. Türkçe için `Merhaba! NumberFansBot'a hoş geldiniz...`).

2. **Komut Örnekleri**:
   - **Ebced Hesaplama**:
     ```plaintext
     /abjad naber
     ```
     - Alfabe sırası, tür, şedde ve detay seçeneklerini seçin.
     - Sonuç: `Naber için ebced değeri: 36\nUyarı: Bu değer (36) önemlidir: İlah isminin ebced değeri (şeddeliler tek)`
   - **Bastet Hesaplama**:
     ```plaintext
     /bastet 37
     ```
     - Tekrar sayısı, tablo ve dil seçin.
     - Sonuç: `37 için Bastet sonucu (tekrar: 1, tablo: 0): 37\nUyarı: Bu değer (37) önemlidir: Evvel isminin ebced değeri (şeddeliler tek)`
   - **Numeroloji Hesaplama**:
     ```plaintext
     /numerology naber turkish
     ```
     - Sonuç: `Naber için numeroloji (türkçe, normal): 36\nUyarı: Bu değer (36) önemlidir: İlah isminin ebced değeri (şeddeliler tek)`

3. **Yönetici Paneli**:
   - `https://<your-render-url>/en/login` adresine gidin.
   - Kullanıcı verilerini ve komut kullanımını görüntüleyin.

## Hata Giderme
- **Webhook Çalışmıyor**:
  - `WEBHOOK_URL` değişkenini kontrol edin.
  - Webhook'u tekrar ayarlayın.
- **Çeviri Sorunları**:
  - `/Locales/` klasöründe `en.json`, `tr.json`, `ar.json`, `he.json`, `la.json` dosyalarının varlığını doğrulayın.
- **Veritabanı Hataları**:
  - `MONGODB_URI` doğru mu? MongoDB Atlas bağlantısını test edin.
- **Uyarı Numaraları Görünmüyor**:
  - `/Config/warningNumbers.json` dosyasının varlığını ve içeriğini kontrol edin.

## Katkıda Bulunma
- Hataları bildirmek veya yeni özellik önermek için GitHub'da bir "Issue" açın.
- Yeni diller eklemek için `/Locales/` altına `.json` dosyaları ekleyin ve `config.py` içinde `available_languages` listesini güncelleyin.

## Lisans
Bu proje MIT Lisansı altında lisanslanmıştır. Ayrıntılar için `LICENSE` dosyasına bakın.

---

**İletişim**: Sorularınız için GitHub üzerinden iletişime geçin veya Telegram'da `@BotKullaniciAdi` ile test edin!