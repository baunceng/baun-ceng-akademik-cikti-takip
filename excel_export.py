"""Filtrelenmiş kayıtlardan Excel (.xlsx) üretir."""
import io
from collections import Counter

from openpyxl import Workbook
from openpyxl.chart import BarChart, Reference
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

from schema import AYLAR, birlestir

HEAD_FILL = PatternFill("solid", fgColor="DDEBF7")
TITLE_FONT = Font(bold=True, size=13)
HEAD_FONT = Font(bold=True)
THIN = Side(style="thin", color="000000")
BORDER = Border(left=THIN, right=THIN, top=THIN, bottom=THIN)
WRAP = Alignment(wrap_text=True, vertical="top")

# sayfa adı, tür, [(başlık, alan, genişlik)]
SAYFALAR = [
    ("Makaleler", "makale", [
        ("Başlık", "baslik", 50), ("Yıl", "yil", 7), ("Ay", "ay", 9), ("Öğretim Üyesi", "_hoca", 24),
        ("Tür", "tur", 14), ("Dergi", "dergi", 32), ("Kapsam", "kapsam", 13), ("Q (JIF)", "quartile", 8),
        ("Yazarlar", "yazarlar", 34), ("Cilt", "cilt", 6), ("Sayı", "sayi", 6), ("Sayfa", "sayfa", 9),
        ("Plain Citation", "atif", 60), ("DOI/URL", "link", 38)]),
    ("Bildiriler", "bildiri", [
        ("Başlık", "baslik", 50), ("Yıl", "yil", 7), ("Ay", "ay", 9), ("Öğretim Üyesi", "_hoca", 24),
        ("Tür", "tur", 13), ("Kategori", "kategori", 16), ("Etkinlik", "etkinlik", 40), ("Şehir", "sehir", 12),
        ("Ülke", "ulke", 12), ("Tarih", "tarih", 11), ("Yazarlar", "yazarlar", 34),
        ("Plain Citation", "atif", 60), ("Link", "link", 38)]),
    ("Kitaplar", "kitap", [
        ("Başlık", "baslik", 46), ("Yıl", "yil", 7), ("Ay", "ay", 9), ("Öğretim Üyesi", "_hoca", 24),
        ("Tür", "tur", 14), ("Kitap Adı", "kitap_adi", 40), ("Yayınevi", "yayinevi", 24), ("Editör", "editor", 20),
        ("ISBN", "isbn", 18), ("Kapsam", "kapsam", 13), ("Yazarlar", "yazarlar", 30),
        ("Plain Citation", "atif", 60), ("Link", "link", 34)]),
    ("Projeler", "proje", [
        ("Proje Adı", "baslik", 50), ("Proje Numarası", "proje_no", 16), ("Proje Türü", "tur", 26),
        ("Öğretim Üyesi", "_hoca", 24), ("Rol", "rol", 12), ("Durum", "durum", 12),
        ("Başlangıç", "baslangic", 11), ("Bitiş", "bitis", 11), ("Başlangıç Yılı", "yil", 9),
        ("Bitiş Yılı", "bitis_yili", 9), ("Bütçe", "butce", 13), ("Yürütücü Kurum", "kurum", 24),
        ("Çalışan Öğrenciler", "ogrenciler", 30), ("Proje Ekibi", "ekip", 50)]),
    ("Patentler", "patent", [
        ("Patent Adı", "baslik", 50), ("Yıl", "yil", 7), ("Ay", "ay", 9), ("Sahip", "_hoca", 24),
        ("Tür", "tur", 12), ("Durum", "durum", 12), ("Başvuru No", "basvuru_no", 16),
        ("Başvuru Sahibi", "basvuru_sahibi", 28), ("Buluş Sahipleri", "bulus_sahibi", 36),
        ("Kategori", "kategori", 28), ("Link", "link", 30)]),
]


def _val(r, alan):
    if alan == "_hoca":
        return ", ".join(r["hocalar"])
    v = r.get(alan)
    if alan == "ay":
        try:
            return AYLAR[int(v) - 1]
        except (TypeError, ValueError, IndexError):
            return ""
    if alan in ("yil", "bitis_yili"):
        try:
            return int(v)
        except (TypeError, ValueError):
            return v or ""
    return v if v is not None else ""


def _baslik_yaz(ws, cols, row):
    for i, (h, _, w) in enumerate(cols, start=2):
        c = ws.cell(row=row, column=i, value=h)
        c.fill, c.font, c.border = HEAD_FILL, HEAD_FONT, BORDER
        ws.column_dimensions[get_column_letter(i)].width = w
    c = ws.cell(row=row, column=1, value="ID")
    c.fill, c.font, c.border = HEAD_FILL, HEAD_FONT, BORDER
    ws.column_dimensions["A"].width = 5


def uret(kayitlar, hoca_adi, hocalar, filtre_aciklama, birlesik=True):
    wb = Workbook()
    wb.remove(wb.active)
    satirlar = birlestir(kayitlar, hoca_adi) if birlesik else \
        [{**r, "hocalar": [hoca_adi.get(r["hoca_id"], r["hoca_id"])]} for r in kayitlar]

    sayim = Counter()
    for ad, kind, cols in SAYFALAR:
        ws = wb.create_sheet(ad)
        ws.cell(row=1, column=1, value=f"BALIKESİR ÜNİVERSİTESİ – BİLGİSAYAR MÜHENDİSLİĞİ · {ad}").font = TITLE_FONT
        ws.cell(row=2, column=1, value=filtre_aciklama).font = Font(italic=True, color="555555")
        _baslik_yaz(ws, cols, 4)
        n = 0
        for r in satirlar:
            if r["kind"] != kind:
                continue
            n += 1
            rown = 4 + n
            ws.cell(row=rown, column=1, value=n).border = BORDER
            for i, (_, alan, _) in enumerate(cols, start=2):
                v = _val(r, alan)
                c = ws.cell(row=rown, column=i, value=v)
                c.alignment, c.border = WRAP, BORDER
                if alan == "link" and isinstance(v, str) and v.startswith("http"):
                    c.hyperlink = v
                    c.font = Font(color="0563C1", underline="single")
            y = r.get("yil")
            try:
                sayim[(int(y), kind)] += 1
            except (TypeError, ValueError):
                pass
        ws.freeze_panes = "C5"
        if n:
            ws.auto_filter.ref = f"A4:{get_column_letter(len(cols) + 1)}{4 + n}"

    # --- Özet sayfası
    ws = wb.create_sheet("Özet", 0)
    ws.cell(row=1, column=1, value="BALIKESİR ÜNİVERSİTESİ – BİLGİSAYAR MÜHENDİSLİĞİ · Akademik Çıktı Özeti").font = TITLE_FONT
    ws.cell(row=2, column=1, value=filtre_aciklama).font = Font(italic=True, color="555555")
    basl = ["Yıl", "Makale", "Bildiri", "Kitap", "Proje", "Patent", "GENEL TOPLAM"]
    for i, h in enumerate(basl, start=1):
        c = ws.cell(row=4, column=i, value=h)
        c.fill, c.font, c.border = HEAD_FILL, HEAD_FONT, BORDER
        ws.column_dimensions[get_column_letter(i)].width = 14
    yillar = sorted({y for y, _ in sayim}, reverse=True)
    for j, y in enumerate(yillar, start=5):
        vals = [sayim[(y, k)] for k in ("makale", "bildiri", "kitap", "proje", "patent")]
        for i, v in enumerate([y, *vals, sum(vals)], start=1):
            ws.cell(row=j, column=i, value=v).border = BORDER
    if yillar:
        last = 4 + len(yillar)
        tr = last + 1
        ws.cell(row=tr, column=1, value="TOPLAM").font = HEAD_FONT
        for i in range(2, 8):
            col = get_column_letter(i)
            c = ws.cell(row=tr, column=i, value=f"=SUM({col}5:{col}{last})")
            c.font, c.border = HEAD_FONT, BORDER
        ch = BarChart()
        ch.title = "Yıllara Göre Akademik Çıktılar"
        ch.y_axis.title = "Adet"
        ch.height, ch.width = 9, 20
        data = Reference(ws, min_col=2, max_col=6, min_row=4, max_row=last)
        cats = Reference(ws, min_col=1, min_row=5, max_row=last)
        ch.add_data(data, titles_from_data=True)
        ch.set_categories(cats)
        ws.add_chart(ch, "I4")

    # --- Öğretim üyeleri
    ws = wb.create_sheet("Öğretim Üyeleri")
    for i, (h, w) in enumerate([("Ad", 22), ("Soyad", 18), ("YÖK Akademik ID", 20), ("Profil", 70)], start=1):
        c = ws.cell(row=1, column=i, value=h)
        c.fill, c.font, c.border = HEAD_FILL, HEAD_FONT, BORDER
        ws.column_dimensions[get_column_letter(i)].width = w
    for j, h in enumerate(hocalar, start=2):
        url = f"https://akademik.yok.gov.tr/academician-details?authorGuidId={h['yok_id']}"
        for i, v in enumerate([h["ad"], h["soyad"], h["yok_id"], url], start=1):
            ws.cell(row=j, column=i, value=v).border = BORDER
        ws.cell(row=j, column=4).hyperlink = url

    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    return buf
