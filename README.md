# BAÜN Bilgisayar Mühendisliği · Akademik Çıktı Takip

Bu platform, öğretim üyelerinin YÖK Akademik (YÖKSİS) ID'lerini kullanarak makale, bildiri, kitap, kitap bölümü, proje ve patent bilgilerini otomatik olarak çeker. Çekilen kayıtlar web arayüzünde düzenlenebilir ve filtrelenmiş hâliyle Excel'e aktarılabilir.

## Çalıştırma
```bash
pip install -r requirements.txt
python3 app.py          # ardından http://127.0.0.1:5050 adresini açın
```
macOS'ta `baslat.command`, Windows'ta `baslat.bat` dosyasına çift tıklamanız da yeterli.

## Aylık otomatik güncelleme
Veriler ayda bir kez YÖKSİS'ten otomatik olarak güncellenir: tüm aktif öğretim üyeleri, tüm türler, son 5 yıl. Bu özellik "YÖKSİS'ten Güncelle" penceresinden açılıp kapatılabilir ve varsayılan olarak açıktır. Güncellemeyi iki mekanizma tetikleyebilir:

1. **Platform açıkken:** Sunucu saatte bir kontrol eder. O ay güncelleme yapılmamışsa kendisi başlatır. Windows, macOS ve Linux'ta ek kurulum gerektirmez.
2. **Platform kapalıyken:** Bir kez şu komutu çalıştırmanız gerekir:
   ```bash
   python otomatik_kur.py           # kurar   (Windows: Görev Zamanlayıcı · macOS: launchd · Linux: cron)
   python otomatik_kur.py --kaldir  # kaldırır
   ```
   Kurulan görev her gün 09:00'da `sync_cli.py` dosyasını çalıştırır. Betik, o ay güncelleme zaten yapıldıysa hemen çıkar. Bu sayede ayın 1'inde bilgisayar kapalı olsa bile açıldığı ilk gün güncelleme yapılır. Çıktılar `otomatik_guncelleme.log` dosyasına yazılır.

İstediğiniz an elle güncellemek için: `python sync_cli.py --zorla`

> Bölümde sürekli açık duran bir sunucuya kurulursa 1. madde tek başına yeterlidir. Herkes aynı veriyi tarayıcıdan görür, kimsenin kendi bilgisayarında bir şey çalıştırması gerekmez.

## Özellikler
- **Öğretim üyeleri:** Her öğretim üyesi için ad, soyad ve YÖK ID tutulur (ünvan tutulmaz). Yeni bir üye isimle aranarak ya da profil linki yapıştırılarak eklenebilir. Bir üye pasife alınabilir ya da silinebilir.
- **YÖKSİS'ten güncelle:** Seçilen öğretim üyeleri ve türler için `akademik.yok.gov.tr` üzerindeki açık JSON API'sinden veri çekilir. Makalelerin indeks bilgisi (SCI-E, ESCI, Scopus, TR Dizin vb.), Q değeri, yazarlar, DOI/link ve atıf metni de bu sırada alınır.
- **Düzenleme:** Her alan değiştirilebilir. Elle yaptığınız düzeltmeler ayrı bir katmanda saklanır, bu yüzden sonraki güncellemelerde kaybolmaz. "YÖKSİS değerlerine dön" ile özgün veriye dönebilirsiniz. İstemediğiniz kayıtları gizleyebilirsiniz. YÖKSİS'te bulunmayan çıktıları (örneğin TÜBİTAK 2209 danışmanlıkları) elle ekleyebilirsiniz.
- **Filtreler:** Ay/yıl aralığı seçilebilir (varsayılan son 5 yıl, Ocak–Aralık). Bunun yanında öğretim üyesi, tür/indeks, kapsam ve metin araması ile filtreleme yapılabilir.
- **Sıralama:** Kayıtlar yeniden eskiye sıralanır, en eski kayıt en altta yer alır.
- **Excel:** Özet sayfası (yıllara göre sayımlar ve grafik), Makaleler, Bildiriler, Kitaplar, Projeler, Patentler ve Öğretim Üyeleri sayfalarından oluşur. Aynı yayını giren hocalar isteğe bağlı olarak tek satırda birleştirilir.

## Ay bilgisi hakkında
YÖKSİS, ay bilgisini yalnızca **bildirilerde** (etkinlik tarihi) ve **projelerde** (başlangıç tarihi) veriyor. Makale, kitap ve patentlerde yalnızca yıl bulunuyor. Bu kayıtlar ay filtresinde "Ay bilgisi olmayanları dahil et" seçeneğine göre yıl bazında değerlendirilir. Ayı tablodaki tarih sütunundan seçerek elle girebilirsiniz.

## Dosyalar
`app.py` (sunucu) · `yok_client.py` (YÖK API istemcisi) · `db.py` (SQLite, `veri.db`) · `schema.py` (alanlar/filtre) · `excel_export.py` · `static/` (arayüz)
