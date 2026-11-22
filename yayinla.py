"""Verileri GitHub Pages'teki salt okunur sayfaya yayınlar.

  python yayinla.py          -> docs/ klasörünü üretir, değişiklik varsa GitHub'a gönderir
  python yayinla.py --yerel  -> yalnızca docs/ klasörünü üretir (göndermez)

Sayfa: https://gulheda.github.io/baun-ceng-akademik-cikti-takip/
Gizlenen kayıtlar ve pasif öğretim üyeleri sayfada gösterilmez.
Ayrıca veritabanının tamamı (düzeltmeler dahil) yedek/veri.sql olarak GitHub'a yedeklenir.
"""
import json
import os
import shutil
import subprocess
import sys

import db
import excel_export
from schema import meta

KLASOR = os.path.dirname(os.path.abspath(__file__))
DOCS = os.path.join(KLASOR, "docs")
STATIC = os.path.join(KLASOR, "static")
GIZLE = ("kaynak", "source_id")  # sayfada gerekmeyen alanlar


def uret():
    db.yedek_al()
    os.makedirs(DOCS, exist_ok=True)
    hocalar = db.hocalar(sadece_aktif=True)
    aktif = {h["yok_id"] for h in hocalar}
    kayitlar = [{k: v for k, v in r.items() if k not in GIZLE}
                for r in db.kayitlar() if not r["gizli"] and r["hoca_id"] in aktif]
    veri = {
        "olusturma": db.ayar_oku("son_tam_senkron") or db.now(),
        "meta": meta(),
        "hocalar": [{k: h[k] for k in ("yok_id", "ad", "soyad", "aktif")} for h in hocalar],
        "excel": [{"ad": ad, "kind": kind, "cols": [[b, a, w] for b, a, w in cols]}
                  for ad, kind, cols in excel_export.SAYFALAR],
        "kayitlar": kayitlar,
    }
    with open(os.path.join(DOCS, "veri.json"), "w", encoding="utf-8") as f:
        json.dump(veri, f, ensure_ascii=False, separators=(",", ":"))

    for ad in ("style.css", "app.js"):
        shutil.copyfile(os.path.join(STATIC, ad), os.path.join(DOCS, ad))
    with open(os.path.join(STATIC, "index.html"), encoding="utf-8") as f:
        html = f.read()
    html = html.replace('href="/static/style.css"', 'href="style.css"')
    html = html.replace('<script src="/static/app.js"></script>',
                        '<script src="https://cdnjs.cloudflare.com/ajax/libs/exceljs/4.4.0/exceljs.min.js"></script>\n'
                        '<script>window.SITE_DATA_URL = "veri.json";</script>\n'
                        '<script src="app.js"></script>')
    html = html.replace("<body>", '<body class="ro">', 1)
    with open(os.path.join(DOCS, "index.html"), "w", encoding="utf-8") as f:
        f.write(html)
    open(os.path.join(DOCS, ".nojekyll"), "w").close()
    return len(kayitlar)


def gonder():
    def git(*a):
        return subprocess.run(["git", *a], cwd=KLASOR, capture_output=True, text=True)
    git("add", "docs", "yedek")
    if git("diff", "--cached", "--quiet", "--", "docs", "yedek").returncode == 0:
        return "Sayfa zaten güncel."
    r = git("commit", "-m", f"Veri güncellemesi {db.now()[:10]}", "--", "docs", "yedek")
    if r.returncode:
        raise RuntimeError(r.stderr or r.stdout)
    git("pull", "--rebase", "-q")  # GitHub'da web üzerinden yapılmış bir değişiklik varsa önce al
    r = git("push", "-q")
    if r.returncode:
        raise RuntimeError("GitHub'a gönderilemedi: " + (r.stderr or r.stdout).strip())
    return "Sayfa güncellendi."


def yayinla(push=True):
    n = uret()
    return f"{n} kayıt hazırlandı. " + (gonder() if push else "")


if __name__ == "__main__":
    print(yayinla(push="--yerel" not in sys.argv))
