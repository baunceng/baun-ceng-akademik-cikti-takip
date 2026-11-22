"""YÖKSİS senkronizasyonu — hem web sunucusu hem zamanlanmış görev (sync_cli.py) kullanır."""
import threading
import traceback
from datetime import datetime

import db
import yok_client as yok
from schema import TURLER

JOB = {"calisiyor": False, "mesaj": "", "ilerleme": 0, "toplam": 0, "hatalar": [], "bitis": None, "kaynak": ""}
_lock = threading.Lock()


def varsayilan_min_yil():
    return 0  # tüm yıllar çekilir; "son 5 yıl" yalnızca ekrandaki varsayılan filtredir


def calistir(hoca_ids=None, kinds=None, min_year=None, detay=True, kaynak="elle", log=print):
    """Senkronizasyonu çalıştırır (bloklar). Zaten çalışıyorsa False döner."""
    with _lock:
        if JOB["calisiyor"]:
            return False
        JOB.update(calisiyor=True, mesaj="Başlıyor…", kaynak=kaynak)
    try:
        hocalar = {h["yok_id"]: h for h in db.hocalar()}
        hoca_ids = hoca_ids or [h["yok_id"] for h in db.hocalar(sadece_aktif=True)]
        kinds = kinds or list(TURLER)
        min_year = int(min_year or varsayilan_min_yil()) or None
        tam = set(kinds) == set(TURLER) and set(hoca_ids) >= {h["yok_id"] for h in db.hocalar(sadece_aktif=True)}
        JOB.update(toplam=len(hoca_ids), ilerleme=0, hatalar=[], bitis=None)
        for i, hid in enumerate(hoca_ids):
            h = hocalar.get(hid, {"ad": "", "soyad": hid})
            ad = f"{h['ad']} {h['soyad']}".strip()
            try:
                JOB["mesaj"] = f"{ad}: yayınlar çekiliyor…"
                yk = [k for k in kinds if k in ("makale", "bildiri", "kitap")]
                if yk:
                    n = {"c": 0}

                    def tick():
                        n["c"] += 1
                        JOB["mesaj"] = f"{ad}: {n['c']} yayın işlendi…"
                    items = [it for it in yok.fetch_yayinlar(hid, min_year, detail=detay, progress=tick)
                             if it["kind"] in yk]
                    db.senkron_yaz(hid, yk, items, min_year)
                if "proje" in kinds:
                    JOB["mesaj"] = f"{ad}: projeler çekiliyor…"
                    db.senkron_yaz(hid, ["proje"], yok.fetch_projeler(hid, min_year), min_year)
                if "patent" in kinds:
                    JOB["mesaj"] = f"{ad}: patentler çekiliyor…"
                    db.senkron_yaz(hid, ["patent"], yok.fetch_patentler(hid, min_year), min_year)
                db.hoca_senkron_isaretle(hid)
                log(f"  ✓ {ad}")
            except Exception as e:
                traceback.print_exc()
                JOB["hatalar"].append(f"{ad}: {e}")
                log(f"  ✗ {ad}: {e}")
            JOB["ilerleme"] = i + 1
        bitis = db.now()
        JOB.update(bitis=bitis, mesaj="Tamamlandı" + (f" ({len(JOB['hatalar'])} hata)" if JOB["hatalar"] else ""))
        # Tüm hocalar + tüm türler başarıyla çekildiyse bu ayın güncellemesi yapılmış sayılır
        if tam and len(JOB["hatalar"]) < len(hoca_ids):
            db.ayar_yaz("son_tam_senkron", bitis)
            db.ayar_yaz("son_tam_senkron_ay", datetime.now().strftime("%Y-%m"))
        # Web sayfasını (GitHub Pages) güncelle; internet/GitHub sorunu güncellemeyi bozmasın
        try:
            import yayinla
            JOB["mesaj"] += " · " + yayinla.yayinla()
        except Exception as e:
            log(f"  ! Web sayfası güncellenemedi: {e}")
            JOB["mesaj"] += " · Web sayfası güncellenemedi"
        return True
    finally:
        JOB["calisiyor"] = False


def baslat_arkaplan(**kw):
    if JOB["calisiyor"]:
        return False
    threading.Thread(target=calistir, kwargs=kw, daemon=True).start()
    return True


# ------------------------------------------------------------------ aylık otomatik
def oto_aktif():
    return db.ayar_oku("oto_aktif", "1") == "1"


def bu_ay_gerekli():
    """Otomatik güncelleme açık ve bu ay henüz tam güncelleme yapılmadıysa True."""
    return oto_aktif() and db.ayar_oku("son_tam_senkron_ay") != datetime.now().strftime("%Y-%m")


def sonraki_tarih():
    n = datetime.now()
    if bu_ay_gerekli():
        return "bugün / ilk fırsatta"
    y, m = (n.year + 1, 1) if n.month == 12 else (n.year, n.month + 1)
    return f"01.{m:02d}.{y}"


def durum():
    return {
        "oto_aktif": oto_aktif(),
        "son_tam_senkron": db.ayar_oku("son_tam_senkron"),
        "sonraki": sonraki_tarih() if oto_aktif() else None,
    }
