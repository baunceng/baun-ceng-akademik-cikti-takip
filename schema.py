"""Kayıt türleri, alanlar, filtreleme ve sıralama — web arayüzü ve Excel ortak kullanır."""
import re
import unicodedata

AYLAR = ["Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran",
         "Temmuz", "Ağustos", "Eylül", "Ekim", "Kasım", "Aralık"]

TURLER = {
    "makale": "Makaleler",
    "bildiri": "Bildiriler",
    "kitap": "Kitap / Kitap Bölümü",
    "proje": "Projeler",
    "patent": "Patentler",
}

# Seçenek listeleri (Excel'deki "Listeler" sayfası ile uyumlu)
SECENEK = {
    "makale_tur": ["SCI", "SCI-E", "SSCI", "AHCI", "ESCI", "Scopus", "TR Dizin", "Alan Endeksi",
                   "Ulusal Diğer", "Uluslararası Diğer", "Endekste Taranmıyor", "Diğer"],
    "kapsam": ["Uluslararası", "Ulusal"],
    "bildiri_kategori": ["Tam Metin Bildiri", "Özet Bildiri", "Poster", "Diğer"],
    "kitap_tur": ["Kitap", "Kitap Bölümü", "Kitap Editörlüğü"],
    "proje_rol": ["Yürütücü", "Araştırmacı", "Danışman", "Bursiyer", "Diğer"],
    "durum": ["Devam", "Tamamlandı", "Başvuru", "Red"],
    "patent_tur": ["Patent", "Faydalı Model", "Tasarım", "Diğer"],
    "proje_tur": ["TÜBİTAK 1001", "TÜBİTAK 1002", "TÜBİTAK 1507", "TÜBİTAK 2209", "TÜBİTAK 3005",
                  "TÜBİTAK Araştırma", "TÜBİTAK Sanayi", "BAP", "Horizon", "UNİDES Projesi",
                  "Yükseköğretim Kurumları tarafından destekli bilimsel araştırma projesi", "Diğer"],
}

# (alan, etiket, tip, seçenek-anahtarı)   tip: text|long|int|month|select|url
ALANLAR = {
    "makale": [
        ("baslik", "Başlık", "long", None), ("yil", "Yıl", "int", None), ("ay", "Ay", "month", None),
        ("tur", "Tür / İndeks", "select", "makale_tur"), ("dergi", "Dergi", "text", None),
        ("kapsam", "Kapsam", "select", "kapsam"), ("quartile", "Q (JIF)", "text", None),
        ("yazarlar", "Yazarlar", "long", None), ("cilt", "Cilt", "text", None), ("sayi", "Sayı", "text", None),
        ("sayfa", "Sayfa", "text", None), ("endeks", "Endeks (YÖKSİS)", "text", None),
        ("doi", "DOI", "text", None), ("link", "Link", "url", None), ("atif", "Atıf (Plain Citation)", "long", None),
    ],
    "bildiri": [
        ("baslik", "Başlık", "long", None), ("yil", "Yıl", "int", None), ("ay", "Ay", "month", None),
        ("tur", "Tür", "select", "kapsam"), ("kategori", "Kategori", "select", "bildiri_kategori"),
        ("etkinlik", "Etkinlik / Kongre", "long", None), ("sehir", "Şehir", "text", None),
        ("ulke", "Ülke", "text", None), ("tarih", "Tarih", "text", None), ("yazarlar", "Yazarlar", "long", None),
        ("sayfa", "Sayfa", "text", None), ("endeks", "Endeks", "text", None), ("doi", "DOI", "text", None),
        ("link", "Link", "url", None), ("atif", "Atıf (Plain Citation)", "long", None),
    ],
    "kitap": [
        ("baslik", "Başlık (Bölüm adı)", "long", None), ("yil", "Yıl", "int", None), ("ay", "Ay", "month", None),
        ("tur", "Tür", "select", "kitap_tur"), ("kitap_adi", "Kitap Adı", "long", None),
        ("yayinevi", "Yayınevi", "text", None), ("editor", "Editör", "text", None),
        ("isbn", "ISBN", "text", None), ("kapsam", "Kapsam", "select", "kapsam"),
        ("yazarlar", "Yazarlar", "long", None), ("sayfa", "Sayfa", "text", None),
        ("link", "Link", "url", None), ("atif", "Atıf (Plain Citation)", "long", None),
    ],
    "proje": [
        ("baslik", "Proje Adı", "long", None), ("yil", "Başlangıç Yılı", "int", None), ("ay", "Başlangıç Ayı", "month", None),
        ("proje_no", "Proje Numarası", "text", None), ("tur", "Proje Türü", "select", "proje_tur"),
        ("rol", "Rol", "select", "proje_rol"), ("durum", "Durum", "select", "durum"),
        ("baslangic", "Başlangıç Tarihi", "text", None), ("bitis", "Bitiş Tarihi", "text", None),
        ("bitis_yili", "Bitiş Yılı", "int", None), ("butce", "Bütçe", "text", None),
        ("kurum", "Yürütücü Kurum", "text", None), ("ogrenciler", "Çalışan Öğrenciler", "long", None),
        ("ekip", "Proje Ekibi", "long", None),
    ],
    "patent": [
        ("baslik", "Patent Adı", "long", None), ("yil", "Yıl", "int", None), ("ay", "Ay", "month", None),
        ("tur", "Tür", "select", "patent_tur"), ("durum", "Durum", "select", "durum"),
        ("basvuru_no", "Başvuru No", "text", None), ("basvuru_sahibi", "Başvuru Sahibi", "text", None),
        ("bulus_sahibi", "Buluş Sahipleri", "long", None), ("kategori", "Kategori", "text", None),
        ("link", "Link", "url", None),
    ],
}


def meta():
    return {
        "aylar": AYLAR,
        "turler": TURLER,
        "secenek": SECENEK,
        "alanlar": {k: [{"ad": a, "etiket": e, "tip": t, "secenek": s} for a, e, t, s in v]
                    for k, v in ALANLAR.items()},
    }


# ------------------------------------------------------------------ filtre
def _int(v):
    try:
        return int(v)
    except (TypeError, ValueError):
        return None


def _norm(s):
    s = unicodedata.normalize("NFKD", str(s or "")).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", " ", s).strip()


def sort_key(r):
    return (_int(r.get("yil")) or 0, _int(r.get("ay")) or 0, _int(r.get("gun")) or 0)


def filtrele(kayitlar, p, hoca_adi):
    """p: dict benzeri. Döndürür: kronolojik (yeni -> eski) liste."""
    bas = (_int(p.get("bas_yil")), _int(p.get("bas_ay")) or 1)
    bit = (_int(p.get("bit_yil")), _int(p.get("bit_ay")) or 12)
    aysizlar = str(p.get("aysizlar", "1")) == "1"
    gizliler = str(p.get("gizliler", "0")) == "1"
    hocalar = {h for h in (p.get("hocalar") or "").split(",") if h}
    turler = {t for t in (p.get("turler") or "").split(",") if t}
    alt = {t for t in (p.get("alt_tur") or "").split("|") if t}
    kapsam = p.get("kapsam") or ""
    ara = _norm(p.get("ara"))

    out = []
    for r in kayitlar:
        if r.get("gizli") and not gizliler:
            continue
        if hocalar and r["hoca_id"] not in hocalar:
            continue
        if turler and r["kind"] not in turler:
            continue
        if alt and (r.get("tur") or "") not in alt and (r.get("kategori") or "") not in alt:
            continue
        if kapsam and r.get("kapsam") != kapsam and r.get("tur") != kapsam:
            continue
        y, a = _int(r.get("yil")), _int(r.get("ay"))
        if bas[0] or bit[0]:
            if y is None:
                continue
            if a:
                if bas[0] and (y, a) < bas:
                    continue
                if bit[0] and (y, a) > bit:
                    continue
            else:
                if not aysizlar:
                    continue
                if bas[0] and y < bas[0]:
                    continue
                if bit[0] and y > bit[0]:
                    continue
        if ara:
            hay = _norm(" ".join(str(r.get(k) or "") for k in
                                 ("baslik", "dergi", "etkinlik", "kitap_adi", "yazarlar", "tur", "kategori",
                                  "proje_no", "basvuru_no", "doi")) + " " + hoca_adi.get(r["hoca_id"], ""))
            if ara not in hay:
                continue
        out.append(r)
    out.sort(key=sort_key, reverse=True)
    return out


def birlestir(kayitlar, hoca_adi):
    """Aynı yayını giren birden fazla hoca varsa tek satırda topla (başlık+yıl+tür)."""
    gruplar, sira = {}, []
    for r in kayitlar:
        key = (r["kind"], _norm(r.get("baslik"))[:120], _int(r.get("yil")))
        if not key[1]:
            key = (r["kind"], f"id{r['id']}", None)
        if key not in gruplar:
            gruplar[key] = {**r, "hocalar": [hoca_adi.get(r["hoca_id"], r["hoca_id"])]}
            sira.append(key)
        else:
            ad = hoca_adi.get(r["hoca_id"], r["hoca_id"])
            if ad not in gruplar[key]["hocalar"]:
                gruplar[key]["hocalar"].append(ad)
    return [gruplar[k] for k in sira]
