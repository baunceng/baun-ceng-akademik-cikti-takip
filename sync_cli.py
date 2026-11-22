"""Komut satırından / zamanlanmış görevden YÖKSİS güncellemesi.

  python sync_cli.py            -> bu ay henüz güncelleme yapılmadıysa çalışır (zamanlayıcı bunu çağırır)
  python sync_cli.py --zorla    -> her durumda çalışır
"""
import os
import sys

os.chdir(os.path.dirname(os.path.abspath(__file__)))

import db  # noqa: E402
import senkron  # noqa: E402


def main():
    db.init()
    zorla = "--zorla" in sys.argv
    if not zorla and not senkron.bu_ay_gerekli():
        print(f"[{db.now()}] Bu ay zaten güncellendi ({db.ayar_oku('son_tam_senkron')}) "
              f"veya otomatik güncelleme kapalı. Çıkılıyor.")
        return 0
    print(f"[{db.now()}] YÖKSİS güncellemesi başlıyor…")
    senkron.calistir(kaynak="zamanlayici" if not zorla else "komut")
    hatalar = senkron.JOB["hatalar"]
    print(f"[{db.now()}] Bitti. {len(hatalar)} hata." + ("".join(f"\n  - {h}" for h in hatalar)))
    return 1 if hatalar else 0


if __name__ == "__main__":
    sys.exit(main())
