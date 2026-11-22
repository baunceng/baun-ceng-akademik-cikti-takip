# Akademik Çıktı Takibi: Kurulum ve Devir Kılavuzu

Bu kılavuz, platformu yeni bir Mac'e kurmak içindir. Kurulum bir kez yapılır ve yaklaşık 15 dakika sürer. Sonrasında sistem her ay kendiliğinden çalışır.

## Sistem nasıl çalışıyor?

- Platform sizin Mac'inizde çalışır. Verileri YÖK Akademik'ten bu Mac çeker. YÖK, yurt dışındaki sunuculardan gelen istekleri kabul etmediği için bu işi internetteki bir sunucu yapamıyor.
- Mac her gün 09:00'da ve her açılışta kısa bir kontrol yapar. O ay güncelleme yapılmamışsa verileri YÖK'ten çeker.
- Güncellemeden sonra veriler GitHub'a gönderilir. Bölümün herkese açık web sayfası da bu sayede güncellenir. Sayfa, Mac kapalıyken de açılır.
- Elle yaptığınız düzeltmeler (ay bilgisi, gizlenen ya da elle eklenen kayıtlar) da GitHub'a yedeklenir. Bilgisayar değişse bile kaybolmaz.

**Web sayfası:** https://gulheda.github.io/baun-ceng-akademik-cikti-takip/
**Kaynak kodu ve yedek:** https://github.com/gulheda/baun-ceng-akademik-cikti-takip

> Depo bölüm hesabına taşındığında bu iki adres değişecek. Yeni adresleri buraya yazın.

Tek koşul, Mac'in ayda en az bir kez açılıp oturum açılmasıdır. Platformun ya da tarayıcının açık olması gerekmez.

---

## Kurulum (yeni Mac)

### 1. GitHub hesabı
Bir GitHub hesabınız yoksa https://github.com/signup adresinden açın. Hesabınızın depoya yazma izni olmalıdır. Depo bölüm organizasyonundaysa organizasyona üye olarak eklenmeniz gerekir.

### 2. Gerekli araçlar
1. **Terminal**'i açın: Spotlight'ı (⌘ + Boşluk) açıp "Terminal" yazın.
2. Aşağıdaki satırı yapıştırıp Enter'a basın:
   ```
   git --version
   ```
3. "Komut satırı geliştirici araçlarını yüklemek ister misiniz?" diye sorarsa **Yükle**'ye basın ve kurulumun bitmesini bekleyin. Bu araçlar Python'u ve Git'i birlikte kurar. Soru gelmez de bir sürüm numarası görürseniz araçlar zaten kuruludur.
4. **GitHub CLI**'yi kurun: https://cli.github.com adresinden macOS için olan `.pkg` dosyasını indirip açın ve kurulumu tamamlayın.

### 3. GitHub'a giriş
Terminal'de şunu çalıştırın:
```
gh auth login
```
Soruları şöyle yanıtlayın:
- **GitHub.com**
- **HTTPS**
- "Authenticate Git with your GitHub credentials?" sorusuna **Yes**
- **Login with a web browser**

Ekranda çıkan kodu kopyalayın, açılan tarayıcıya yapıştırıp girişi onaylayın.

### 4. Platformu indirme
```
cd ~/Desktop
gh repo clone gulheda/baun-ceng-akademik-cikti-takip akademik-cikti
```
Masaüstünde `akademik-cikti` adında bir klasör oluşur. **Bu klasörü daha sonra başka bir yere taşımayın.** Otomatik güncelleme bu konumu kullanır.

### 5. İlk açılış
1. Klasördeki **`baslat.command`** dosyasına çift tıklayın.
2. macOS "geliştiricisi doğrulanamadı" uyarısı verirse dosyaya sağ tıklayıp **Aç** deyin ve onaylayın. Bu yalnızca ilk seferde olur.
3. Birkaç saniye sonra tarayıcıda platform açılır. Tüm kayıtlar ve önceki düzeltmeler GitHub'daki yedekten otomatik olarak gelir.

Platformu kapatmak için Terminal penceresini kapatmanız yeterlidir.

### 6. Aylık otomatik güncellemeyi kurma
Terminal'de şunu çalıştırın:
```
cd ~/Desktop/akademik-cikti && python3 otomatik_kur.py
```
"Kuruldu (Darwin)…" mesajını görürseniz kurulum tamamdır.

### 7. Deneme
Platformda **YÖKSİS'ten güncelle** düğmesine basın ve pencerenin altındaki **Web sayfasını şimdi güncelle** bağlantısına tıklayın. "Sayfa güncellendi" ya da "Sayfa zaten güncel" mesajı çıkıyorsa her şey çalışıyor demektir.

---

## Eski bilgisayardan kaldırma (önemli)
Platform aynı anda iki bilgisayarda otomatik çalışmamalıdır. Eski Mac'te Terminal'de şunu çalıştırın:
```
cd ~/Desktop/yöksis-bot && python3 otomatik_kur.py --kaldir
```
Bunu yapmadan önce eski Mac'te bir kez **Web sayfasını şimdi güncelle**'ye basın. Böylece son düzeltmeler GitHub'a gider.

---

## Günlük kullanım
| Ne yapmak istiyorsunuz? | Nasıl? |
|---|---|
| Platformu açmak | `baslat.command`'a çift tıklayın |
| Bir kaydı düzeltmek, ay girmek | Kayda tıklayın, sağdaki panelde düzeltin, **Kaydet**'e basın |
| Hatalı kaydı listeden çıkarmak | Kayda tıklayıp **Gizle**'ye basın |
| YÖKSİS'te olmayan bir çıktı eklemek | **+ Yeni kayıt** |
| Öğretim üyesi eklemek veya çıkarmak | **Öğretim üyeleri** |
| Excel almak | **Excel'e aktar** (web sayfasında da vardır) |
| Düzeltmeleri web sayfasına hemen yansıtmak | **YÖKSİS'ten güncelle** penceresinde **Web sayfasını şimdi güncelle** |

Düzeltmeleriniz sonraki YÖKSİS güncellemelerinde korunur.

---

## Sorun giderme
- **Web sayfası eski görünüyor:** Sayfadaki "Veri tarihi"ne bakın. Tarih eskiyse Mac'i açıp platformda **YÖKSİS'ten güncelle**'yi çalıştırın.
- **"GitHub'a gönderilemedi" uyarısı:** GitHub girişinin süresi dolmuş olabilir. Terminal'de `gh auth login` komutunu tekrar çalıştırın.
- **Otomatik güncelleme çalışmıyor:** Klasördeki `otomatik_guncelleme.log` dosyasını açıp son satırlara bakın. Klasörü taşıdıysanız 6. adımı yeni konumda tekrarlayın.
- **Platform açılmıyor:** Terminal'de `cd ~/Desktop/akademik-cikti && python3 app.py` çalıştırın ve çıkan hata mesajını not edin.
- **Veri tamamen kayboldu:** Klasördeki `veri.db` dosyasını silip platformu yeniden açın. Veriler `yedek/veri.sql` dosyasından, yani son GitHub yedeğinden geri yüklenir.
