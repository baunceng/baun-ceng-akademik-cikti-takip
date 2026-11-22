"""BAÜN Bilgisayar Mühendisliği — YÖKSİS Akademik Çıktı Takip platformu.

Çalıştırma:  python app.py   ->  http://127.0.0.1:5050
"""
import os
import threading
import time
import traceback
from datetime import datetime

from flask import Flask, jsonify, request, send_file, send_from_directory

import db
import excel_export
import senkron
import yok_client as yok
from schema import AYLAR, TURLER, filtrele, meta

app = Flask(__name__, static_folder="static", static_url_path="/static")
app.json.sort_keys = False  # sekme/alan sırası korunsun
db.init()

# ------------------------------------------------------------------ senkronizasyon
@app.post("/api/senkron")
def senkron_baslat():
    b = request.get_json(silent=True) or {}
    ok = senkron.baslat_arkaplan(hoca_ids=b.get("hocalar"), kinds=b.get("turler"),
                                 min_year=b.get("min_yil"), detay=b.get("detay", True), kaynak="elle")
    if not ok:
        return jsonify(hata="Zaten bir senkronizasyon çalışıyor"), 409
    return jsonify(ok=True)


@app.get("/api/senkron")
def senkron_durum():
    return jsonify({**senkron.JOB, **senkron.durum()})


@app.post("/api/otomatik")
def otomatik_ayarla():
    b = request.get_json(force=True)
    db.ayar_yaz("oto_aktif", "1" if b.get("aktif") else "0")
    return jsonify(senkron.durum())


def _aylik_zamanlayici():
    """Sunucu açık kaldığı sürece saatte bir kontrol eder; bu ay güncelleme yapılmadıysa çalıştırır."""
    time.sleep(20)  # açılışta arayüzün yüklenmesine fırsat ver
    while True:
        try:
            if senkron.bu_ay_gerekli() and not senkron.JOB["calisiyor"]:
                print(f"[{db.now()}] Aylık otomatik YÖKSİS güncellemesi başlıyor…")
                senkron.calistir(kaynak="otomatik")
        except Exception:
            traceback.print_exc()
        time.sleep(3600)


# ------------------------------------------------------------------ meta & hocalar
@app.get("/api/meta")
def api_meta():
    return jsonify(meta())


@app.get("/api/hocalar")
def api_hocalar():
    return jsonify(db.hocalar())


@app.post("/api/hocalar")
def api_hoca_ekle():
    b = request.get_json(force=True)
    yok_id = (b.get("yok_id") or "").strip()
    if "authorGuidId=" in yok_id:  # profil linki yapıştırılırsa ID'yi ayıkla
        yok_id = yok_id.split("authorGuidId=")[1].split("&")[0]
    if not yok_id:
        return jsonify(hata="YÖK ID gerekli"), 400
    ad, soyad = (b.get("ad") or "").strip(), (b.get("soyad") or "").strip()
    if not (ad and soyad):
        try:
            info = yok.get_academician(yok_id)
        except Exception as e:
            return jsonify(hata=f"YÖK Akademik'te bulunamadı: {e}"), 400
        ad, soyad = ad or info["ad"], soyad or info["soyad"]
    db.hoca_ekle(ad, soyad, yok_id)
    return jsonify(ok=True, yok_id=yok_id)


@app.patch("/api/hocalar/<yok_id>")
def api_hoca_guncelle(yok_id):
    db.hoca_guncelle(yok_id, **(request.get_json(force=True) or {}))
    return jsonify(ok=True)


@app.delete("/api/hocalar/<yok_id>")
def api_hoca_sil(yok_id):
    db.hoca_sil(yok_id)
    return jsonify(ok=True)


@app.get("/api/ara")
def api_ara():
    q = (request.args.get("q") or "").strip()
    if len(q) < 3:
        return jsonify([])
    try:
        return jsonify(yok.search_academician(q))
    except Exception as e:
        return jsonify(hata=str(e)), 502


# ------------------------------------------------------------------ kayıtlar
def _hoca_adi():
    return {h["yok_id"]: f"{h['ad']} {h['soyad']}" for h in db.hocalar()}


@app.get("/api/kayitlar")
def api_kayitlar():
    return jsonify(filtrele(db.kayitlar(), request.args, _hoca_adi()))


@app.post("/api/kayitlar")
def api_kayit_ekle():
    b = request.get_json(force=True)
    if b.get("kind") not in TURLER or not b.get("hoca_id"):
        return jsonify(hata="Tür ve öğretim üyesi gerekli"), 400
    return jsonify(db.kayit_ekle(b["hoca_id"], b["kind"], {"tur_kod": b["kind"], **(b.get("data") or {})}))


@app.patch("/api/kayitlar/<int:id_>")
def api_kayit_guncelle(id_):
    b = request.get_json(force=True)
    if "gizli" in b:
        db.kayit_gizle(id_, b["gizli"])
    if b.get("sifirla"):
        db.kayit_sifirla(id_)
    if b.get("hoca_id"):
        db.kayit_hoca_degistir(id_, b["hoca_id"])
    if b.get("data"):
        db.kayit_guncelle(id_, b["data"])
    return jsonify(db.kayit(id_))


@app.delete("/api/kayitlar/<int:id_>")
def api_kayit_sil(id_):
    r = db.kayit(id_)
    if r and not r["manuel"]:
        db.kayit_gizle(id_, True)  # YÖKSİS kaydı silinmez, gizlenir (senkronda geri gelmesin)
    else:
        db.kayit_sil(id_)
    return jsonify(ok=True)


@app.get("/api/excel")
def api_excel():
    args = request.args
    ha = _hoca_adi()
    rows = filtrele(db.kayitlar(), args, ha)
    hocalar = db.hocalar()
    sec = {h for h in (args.get("hocalar") or "").split(",") if h}
    if sec:
        hocalar = [h for h in hocalar if h["yok_id"] in sec]

    def ay(a):
        try:
            return AYLAR[int(a) - 1]
        except (TypeError, ValueError, IndexError):
            return ""
    aralik = f"{ay(args.get('bas_ay') or 1)} {args.get('bas_yil') or '…'} – {ay(args.get('bit_ay') or 12)} {args.get('bit_yil') or '…'}"
    aciklama = f"Dönem: {aralik} · Oluşturma: {db.now()} · Kaynak: YÖK Akademik (akademik.yok.gov.tr)"
    buf = excel_export.uret(rows, ha, hocalar, aciklama, birlesik=args.get("birlestir", "1") == "1")
    ad = f"BAUN_CENG_Akademik_Cikti_{datetime.now():%Y%m%d}.xlsx"
    return send_file(buf, as_attachment=True, download_name=ad,
                     mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")


@app.get("/")
def index():
    return send_from_directory("static", "index.html")


if __name__ == "__main__":
    threading.Thread(target=_aylik_zamanlayici, daemon=True).start()
    port = int(os.environ.get("PORT", 5050))
    print(f"\n  Akademik Çıktı Takip çalışıyor →  http://127.0.0.1:{port}\n")
    app.run(host="127.0.0.1", port=port, debug=False, threaded=True)
