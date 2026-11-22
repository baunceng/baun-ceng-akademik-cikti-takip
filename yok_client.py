"""YÖK Akademik (akademik.yok.gov.tr) açık API istemcisi ve kayıt normalizasyonu.

Sitenin kendi arayüzünün kullandığı JSON uç noktaları kullanılır:
  /akademisyen/list, /akademisyen/detay, /yayin/list, /yayin/detay,
  /proje/list, /patent/list
"""
import html
import json
import re
import time
import urllib.parse
import urllib.request

BASE = "https://akademik.yok.gov.tr/api"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (BAUN-CENG akademik cikti takip)",
    "Accept": "application/json",
}

# /yayin/ana/tur/list cevabındaki ana tür kimlikleri
ANA_TUR = {
    "makale": "Tr0N9rqN2YIsFawDexhdyg",
    "bildiri": "O0K3y0N_nzZJu1cSqC9jQw",
    "kitap": "MYzjo0boReFaw05Isx0G9Q",
}


class YokError(Exception):
    pass


def _get(path, retries=3, **params):
    url = BASE + path + "?" + urllib.parse.urlencode(params)
    last = None
    for i in range(retries):
        try:
            req = urllib.request.Request(url, headers=HEADERS)
            with urllib.request.urlopen(req, timeout=40) as r:
                body = json.load(r)
            if not body.get("result", True):
                raise YokError(body.get("errorMessage") or "YÖK API hatası")
            return body.get("data")
        except YokError:
            raise
        except Exception as e:  # ağ hatası -> tekrar dene
            last = e
            time.sleep(1.5 * (i + 1))
    raise YokError(f"{path} isteği başarısız: {last}")


def _paged(path, **params):
    page, out = 1, []
    while True:
        d = _get(path, page=page, length=100, **params) or {}
        rows = d.get("data") or []
        out.extend(rows)
        total = d.get("totalElements") or 0
        if not rows or len(out) >= total:
            return out
        page += 1


# --------------------------------------------------------------- yardımcılar
def clean(s):
    if s is None:
        return ""
    s = str(s)
    for _ in range(3):  # API bazen çift kaçışlı (&amp;amp;) döndürüyor
        n = html.unescape(s)
        if n == s:
            break
        s = n
    s = re.sub(r"<[^>]+>", "", s)
    return re.sub(r"\s+", " ", s).strip()


def parse_date(s):
    """'21.05.2026' -> (2026, 5, 21)"""
    m = re.match(r"\s*(\d{1,2})\.(\d{1,2})\.(\d{4})", s or "")
    if not m:
        return None
    return int(m.group(3)), int(m.group(2)), int(m.group(1))


def to_int(s):
    try:
        return int(str(s).strip()[:4])
    except Exception:
        return None


_TR_UP = str.maketrans("iı", "İI")
_TR_LO = str.maketrans("İI", "iı")


def tr_upper(s):
    return s.translate(_TR_UP).upper()


def tr_title(word):
    if not word:
        return word
    return word[0].translate(_TR_UP).upper() + word[1:].translate(_TR_LO).lower()


def split_name(full):
    """'MUSTAFA FURKAN CEYLAN' -> ('Mustafa Furkan', 'CEYLAN')"""
    parts = clean(full).split()
    if not parts:
        return "", ""
    soyad = tr_upper(parts[-1])
    ad = " ".join(tr_title(p) for p in parts[:-1])
    return ad, soyad


# --------------------------------------------------------------- akademisyen
def search_academician(query):
    rows = _get("/akademisyen/list", page=1, length=50, globalSearch=query) or {}
    out = []
    for r in rows.get("data") or []:
        ad, soyad = split_name(r.get("personelAdiSoyadi"))
        out.append({
            "yok_id": r.get("authorGuidId"),
            "ad": ad,
            "soyad": soyad,
            "kadro_yeri": clean(r.get("kadroYeri")),
        })
    return out


def get_academician(yok_id):
    d = _get("/akademisyen/detay", authorGuidId=yok_id)
    if not d:
        raise YokError("Bu ID ile akademisyen bulunamadı")
    ad, soyad = split_name(d.get("personelAdiSoyadi"))
    return {"yok_id": d.get("authorGuidId"), "ad": ad, "soyad": soyad,
            "kadro_yeri": clean(d.get("kadroYeri"))}


# --------------------------------------------------------------- yayınlar
def _kapsam(v):
    return {"1": "Uluslararası", "0": "Ulusal"}.get(str(v), "")


def makale_turu(yayin_turu, endeks, kapsam):
    t = clean(yayin_turu)
    e = clean(endeks)
    tl = t.lower()
    if t in ("SCI-Expanded", "SCI-E"):
        return "SCI-E"
    if t in ("SCI", "SSCI", "AHCI", "Scopus"):
        return t
    if "tr di" in tl or "tr dİ" in tl or t.upper().replace("İ", "I") == "TR DIZIN":
        return "TR Dizin"
    if re.search(r"\bESCI\b", e):
        return "ESCI"
    if re.search(r"\bScopus\b", e, re.I):
        return "Scopus"
    if "alan endeks" in tl:
        return "Alan Endeksi"
    if "taranm" in tl:
        return "Endekste Taranmıyor"
    return f"{kapsam} Diğer".strip() if kapsam else "Diğer"


def _authors(detail, row):
    return clean((detail or {}).get("yazarAdi") or row.get("yazarAdi"))


def _pages(r):
    a, b = clean(r.get("ilkSayfa")), clean(r.get("sonSayfa"))
    if a and b:
        return f"{a}-{b}"
    return a or b


def make_citation(rec):
    """IEEE benzeri sade atıf metni."""
    parts = []
    if rec.get("yazarlar"):
        parts.append(rec["yazarlar"].replace(",", ", ") + ",")
    parts.append(f"\"{rec.get('baslik', '')},\"")
    venue = rec.get("dergi") or rec.get("etkinlik") or rec.get("kitap_adi") or ""
    if rec.get("tur_kod") == "kitap" and rec.get("alt_tur") == "Kitap Bölümü":
        venue = f"in {rec.get('kitap_adi', '')}"
        if rec.get("yayinevi"):
            venue += f", {rec['yayinevi']}"
    elif rec.get("tur_kod") == "kitap":
        venue = rec.get("yayinevi", "")
    if venue:
        parts.append(venue + ",")
    if rec.get("cilt"):
        parts.append(f"vol. {rec['cilt']},")
    if rec.get("sayi"):
        parts.append(f"no. {rec['sayi']},")
    if rec.get("sayfa"):
        parts.append(f"pp. {rec['sayfa']},")
    if rec.get("sehir") or rec.get("ulke"):
        parts.append(", ".join(x for x in [rec.get("sehir"), rec.get("ulke")] if x) + ",")
    parts.append(f"{rec.get('yil') or ''}.")
    if rec.get("doi"):
        parts.append(f"doi: {rec['doi']}.")
    elif rec.get("isbn"):
        parts.append(f"ISBN: {rec['isbn']}.")
    return " ".join(p for p in parts if p).replace(",.", ".")


def normalize_yayin(kind, row, detail, hoca_id):
    r = dict(row)
    if detail:
        r.update({k: v for k, v in detail.items() if v not in (None, "")})
    yil = to_int(r.get("yil"))
    bas = parse_date(r.get("basTarih"))
    ay = bas[1] if bas and bas[0] == yil else None
    gun = bas[2] if bas and bas[0] == yil else None
    kapsam = _kapsam(r.get("kapsam"))
    doi = clean(r.get("doi"))
    link = clean(r.get("erisimLinki")) or (f"https://doi.org/{doi}" if doi else "")
    q = ""
    for ql in (detail or {}).get("dergiQuartileListesi") or []:
        if ql.get("metrikTuru") == "JIF" and ql.get("quartile"):
            q = ql["quartile"]
            break
    rec = {
        "tur_kod": kind,
        "baslik": clean(r.get("yayinAdi")),
        "yil": yil,
        "ay": ay,
        "gun": gun,
        "kapsam": kapsam,
        "yazarlar": _authors(detail, row),
        "doi": doi,
        "link": link,
        "dil": clean(r.get("dilAdi")),
        "endeks": clean(r.get("endeksAdi")),
        "yok_tur": clean(r.get("yayinTuruAdi")),
    }
    if kind == "makale":
        rec.update({
            "tur": makale_turu(r.get("yayinTuruAdi"), r.get("endeksAdi"), kapsam),
            "dergi": clean(r.get("yayinYeri")),
            "cilt": clean(r.get("cilt")),
            "sayi": clean(r.get("sayi")),
            "sayfa": _pages(r),
            "issn": clean(r.get("issn")),
            "quartile": q,
        })
    elif kind == "bildiri":
        yt = clean(r.get("yayinTuruAdi")).lower()
        kat = "Tam Metin Bildiri" if "tam" in yt else "Özet Bildiri" if "özet" in yt or "ozet" in yt \
            else "Poster" if "poster" in yt else clean(r.get("yayinTuruAdi"))
        rec.update({
            "tur": kapsam,
            "kategori": kat,
            "etkinlik": clean(r.get("yayinYeri")),
            "sehir": clean(r.get("sehir")),
            "ulke": clean(r.get("ulkeAdi")),
            "tarih": clean(r.get("basTarih")),
            "sayfa": _pages(r),
        })
    elif kind == "kitap":
        bolum = clean(r.get("bolumAdi"))
        rec.update({
            "alt_tur": "Kitap Bölümü" if bolum else "Kitap",
            "tur": "Kitap Bölümü" if bolum else "Kitap",
            "kitap_adi": clean(r.get("yayinAdi")),
            "baslik": bolum or clean(r.get("yayinAdi")),
            "yayinevi": clean(r.get("yayinYeri")),
            "editor": clean(r.get("editorAdi")),
            "isbn": clean(r.get("isbn")),
            "sayfa": clean(r.get("sayfaSayisi")) or _pages(r),
        })
    rec["atif"] = make_citation(rec)
    return {"source_id": f"yayin:{row.get('yayinId')}", "hoca_id": hoca_id, "kind": kind, "data": rec}


def fetch_yayinlar(hoca_id, min_year, detail=True, progress=None):
    out = []
    for kind, tur_id in ANA_TUR.items():
        rows = _paged("/yayin/list", yayinAnaTurId=tur_id, authorGuidId=hoca_id)
        for row in rows:
            y = to_int(row.get("yil"))
            if min_year and (y is None or y < min_year):
                continue
            d = None
            if detail:
                try:
                    d = _get("/yayin/detay", yayinId=row.get("yayinId"))
                except YokError:
                    d = None
            out.append(normalize_yayin(kind, row, d, hoca_id))
            if progress:
                progress()
    return out


# --------------------------------------------------------------- projeler
def normalize_proje(row, hoca_id):
    bas = parse_date(row.get("baslangicTarihi"))
    bit = parse_date(row.get("bitisTarihi"))
    rol, ekip = "", []
    for m in row.get("projeEkip") or []:
        name = f"{tr_title(clean(m.get('yazarad')))} {tr_upper(clean(m.get('yazarsoyad')))}".strip()
        gorev = clean(m.get("projedekiGoreviAd"))
        ekip.append(f"{name} ({gorev})" if gorev else name)
        if m.get("authorGuidId") == hoca_id:
            rol = gorev
    rec = {
        "tur_kod": "proje",
        "baslik": clean(row.get("projeAdi")),
        "yil": bas[0] if bas else to_int(row.get("bitisyil")),
        "ay": bas[1] if bas else None,
        "gun": bas[2] if bas else None,
        "proje_no": "",
        "tur": clean(row.get("projeTuruAd")),
        "rol": rol,
        "durum": clean(row.get("projeDurumuAd")),
        "baslangic": clean(row.get("baslangicTarihi")),
        "bitis": clean(row.get("bitisTarihi")),
        "baslangic_yili": bas[0] if bas else None,
        "bitis_yili": bit[0] if bit else to_int(row.get("bitisyil")),
        "butce": clean(row.get("butcesi")),
        "ekip": "; ".join(ekip),
        "kurum": "",
        "ogrenciler": "",
    }
    return {"source_id": f"proje:{row.get('projeId')}", "hoca_id": hoca_id, "kind": "proje", "data": rec}


def fetch_projeler(hoca_id, min_year):
    out = []
    for row in _paged("/proje/list", authorGuidId=hoca_id):
        n = normalize_proje(row, hoca_id)
        end = n["data"]["bitis_yili"] or n["data"]["yil"]
        if min_year and end and end < min_year:
            continue
        out.append(n)
    return out


# --------------------------------------------------------------- patentler
def normalize_patent(row, hoca_id):
    rec = {
        "tur_kod": "patent",
        "baslik": clean(row.get("patentBaslik")),
        "yil": to_int(row.get("patentTarih")),
        "ay": None,
        "gun": None,
        "tur": clean(row.get("patentDosyaTipi")),
        "durum": "",
        "basvuru_no": clean(row.get("patentNo")),
        "basvuru_sahibi": clean(row.get("patentBasvuruSahip")),
        "bulus_sahibi": clean(row.get("patentBulusSahip")),
        "kategori": clean(row.get("kategoriAd")),
        "link": "",
    }
    return {"source_id": f"patent:{row.get('patentId')}", "hoca_id": hoca_id, "kind": "patent", "data": rec}


def fetch_patentler(hoca_id, min_year):
    out = []
    for row in _paged("/patent/list", authorGuidId=hoca_id):
        n = normalize_patent(row, hoca_id)
        if min_year and n["data"]["yil"] and n["data"]["yil"] < min_year:
            continue
        out.append(n)
    return out
