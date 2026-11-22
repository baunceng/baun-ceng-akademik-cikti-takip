"""SQLite depolama.

Her kayıt iki katmanlıdır:
  data      -> YÖKSİS'ten çekilen ham (normalize edilmiş) veri; senkronizasyonda güncellenir
  overrides -> kullanıcının elle yaptığı düzeltmeler; senkronizasyon bunlara dokunmaz
Görünen değer = data + overrides.
"""
import json
import os
import sqlite3
import threading
from datetime import datetime

DB_PATH = os.environ.get("AKADEMIK_DB", os.path.join(os.path.dirname(os.path.abspath(__file__)), "veri.db"))
_lock = threading.Lock()

# Excel'deki mevcut BAÜN Bilgisayar Müh. listesi (YÖK Akademik ID'leri doğrulandı)
VARSAYILAN_HOCALAR = [
    ("Ayhan", "İSTANBULLU", "3BEDFBC833909A67"),
    ("Selçuk", "KAVUT", "21C2A7B124062AE2"),
    ("Hüseyin", "GÜNEŞ", "9898EA0C1C993EDB"),
    ("Fatih", "AYDIN", "31D274595D26E88D"),
    ("Gültekin", "KUVAT", "32A621BD656CC136"),
    ("Sevdanur", "GENÇ", "8FB451CAC8E1CEAE"),
    ("Abdulgani", "KAHRAMAN", "1659C369FB7866B5"),
    ("Abdurrahim Hüseyin", "EZİRMİK", "10883B81284A1BFE"),
    ("Mehmet", "ÖZCAN", "E23A4544B61DEFAF"),
    ("Mustafa Furkan", "CEYLAN", "45E814E7BF469FA5"),
]


def conn():
    c = sqlite3.connect(DB_PATH, check_same_thread=False)
    c.row_factory = sqlite3.Row
    return c


YEDEK = os.path.join(os.path.dirname(os.path.abspath(__file__)), "yedek", "veri.sql")


def yedek_al():
    """Veritabanını metin olarak yedekler (GitHub'a gönderilir; devirde/kayıpta geri yüklenir)."""
    os.makedirs(os.path.dirname(YEDEK), exist_ok=True)
    with _lock, conn() as c, open(YEDEK, "w", encoding="utf-8") as f:
        for satir in c.iterdump():
            f.write(satir + "\n")


def init():
    # Yeni bir bilgisayarda veri.db yoksa GitHub'daki yedekten kur (düzeltmeler dahil)
    if not os.path.exists(DB_PATH) and os.path.exists(YEDEK):
        with open(YEDEK, encoding="utf-8") as f, sqlite3.connect(DB_PATH) as c:
            c.executescript(f.read())
    with _lock, conn() as c:
        c.executescript("""
        CREATE TABLE IF NOT EXISTS hocalar(
            yok_id TEXT PRIMARY KEY,
            ad TEXT NOT NULL,
            soyad TEXT NOT NULL,
            aktif INTEGER NOT NULL DEFAULT 1,
            son_senkron TEXT
        );
        CREATE TABLE IF NOT EXISTS kayitlar(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source_id TEXT,              -- 'yayin:123' / 'proje:..' ; elle eklenende NULL
            hoca_id TEXT NOT NULL,
            kind TEXT NOT NULL,          -- makale|bildiri|kitap|proje|patent
            data TEXT NOT NULL DEFAULT '{}',
            overrides TEXT NOT NULL DEFAULT '{}',
            gizli INTEGER NOT NULL DEFAULT 0,
            manuel INTEGER NOT NULL DEFAULT 0,
            yoksiste_yok INTEGER NOT NULL DEFAULT 0,
            eklenme TEXT,
            guncelleme TEXT,
            UNIQUE(source_id, hoca_id)
        );
        CREATE TABLE IF NOT EXISTS ayarlar(
            anahtar TEXT PRIMARY KEY,
            deger TEXT
        );
        """)
        if c.execute("SELECT COUNT(*) FROM hocalar").fetchone()[0] == 0:
            c.executemany("INSERT INTO hocalar(ad,soyad,yok_id) VALUES(?,?,?)", VARSAYILAN_HOCALAR)


def now():
    return datetime.now().strftime("%Y-%m-%d %H:%M")


def ayar_oku(anahtar, varsayilan=None):
    with conn() as c:
        r = c.execute("SELECT deger FROM ayarlar WHERE anahtar=?", (anahtar,)).fetchone()
    return r["deger"] if r else varsayilan


def ayar_yaz(anahtar, deger):
    with _lock, conn() as c:
        c.execute("INSERT INTO ayarlar(anahtar,deger) VALUES(?,?) "
                  "ON CONFLICT(anahtar) DO UPDATE SET deger=excluded.deger", (anahtar, str(deger)))


# ------------------------------------------------------------------ hocalar
def hocalar(sadece_aktif=False):
    q = "SELECT * FROM hocalar" + (" WHERE aktif=1" if sadece_aktif else "")
    with conn() as c:
        rows = [dict(r) for r in c.execute(q)]
    return sorted(rows, key=lambda h: (tr_key(h["soyad"]), tr_key(h["ad"])))


_TR_ALFABE = "abcçdefgğhıijklmnoöprsştuüvyz"


def tr_key(s):
    s = (s or "").replace("I", "ı").replace("İ", "i").lower()
    return [(_TR_ALFABE.index(ch) if ch in _TR_ALFABE else 100 + ord(ch)) for ch in s]


def hoca_ekle(ad, soyad, yok_id):
    with _lock, conn() as c:
        c.execute("INSERT INTO hocalar(ad,soyad,yok_id) VALUES(?,?,?) "
                  "ON CONFLICT(yok_id) DO UPDATE SET ad=excluded.ad, soyad=excluded.soyad, aktif=1",
                  (ad, soyad, yok_id))


def hoca_guncelle(yok_id, **f):
    allowed = {k: v for k, v in f.items() if k in ("ad", "soyad", "aktif")}
    if not allowed:
        return
    with _lock, conn() as c:
        c.execute("UPDATE hocalar SET " + ",".join(f"{k}=?" for k in allowed) + " WHERE yok_id=?",
                  (*allowed.values(), yok_id))


def hoca_sil(yok_id, kayitlari_da=True):
    with _lock, conn() as c:
        c.execute("DELETE FROM hocalar WHERE yok_id=?", (yok_id,))
        if kayitlari_da:
            c.execute("DELETE FROM kayitlar WHERE hoca_id=?", (yok_id,))


def hoca_senkron_isaretle(yok_id):
    with _lock, conn() as c:
        c.execute("UPDATE hocalar SET son_senkron=? WHERE yok_id=?", (now(), yok_id))


# ------------------------------------------------------------------ kayıtlar
def _row(r):
    d = json.loads(r["data"] or "{}")
    o = json.loads(r["overrides"] or "{}")
    eff = {**d, **o}
    return {
        "id": r["id"], "source_id": r["source_id"], "hoca_id": r["hoca_id"], "kind": r["kind"],
        "gizli": bool(r["gizli"]), "manuel": bool(r["manuel"]), "yoksiste_yok": bool(r["yoksiste_yok"]),
        "duzenlendi": sorted(o.keys()), "kaynak": d, **eff,
    }


def kayitlar():
    with conn() as c:
        return [_row(r) for r in c.execute("SELECT * FROM kayitlar")]


def kayit(id_):
    with conn() as c:
        r = c.execute("SELECT * FROM kayitlar WHERE id=?", (id_,)).fetchone()
        return _row(r) if r else None


def senkron_yaz(hoca_id, kinds, items, min_year):
    """YÖKSİS'ten gelen kayıtları yazar. Kullanıcı düzeltmeleri korunur.
    Kapsam içinde olup artık YÖKSİS'te bulunmayan kayıtlar silinmez, 'yoksiste_yok' olarak işaretlenir."""
    t = now()
    seen = set()
    with _lock, conn() as c:
        for it in items:
            seen.add(it["source_id"])
            c.execute("""
              INSERT INTO kayitlar(source_id,hoca_id,kind,data,eklenme,guncelleme)
              VALUES(?,?,?,?,?,?)
              ON CONFLICT(source_id,hoca_id) DO UPDATE SET
                 kind=excluded.kind, data=excluded.data, guncelleme=excluded.guncelleme, yoksiste_yok=0
            """, (it["source_id"], hoca_id, it["kind"], json.dumps(it["data"], ensure_ascii=False), t, t))
        rows = c.execute("SELECT id,source_id,data FROM kayitlar WHERE hoca_id=? AND manuel=0 AND kind IN (%s)"
                         % ",".join("?" * len(kinds)), (hoca_id, *kinds)).fetchall()
        for r in rows:
            if r["source_id"] in seen:
                continue
            y = json.loads(r["data"]).get("yil")
            if not min_year or (y and y >= min_year):
                c.execute("UPDATE kayitlar SET yoksiste_yok=1 WHERE id=?", (r["id"],))


def kayit_guncelle(id_, alanlar):
    """alanlar: {alan: deger}. Kaynak değerle aynıysa override kaldırılır."""
    with _lock, conn() as c:
        r = c.execute("SELECT * FROM kayitlar WHERE id=?", (id_,)).fetchone()
        if not r:
            return None
        d = json.loads(r["data"] or "{}")
        o = json.loads(r["overrides"] or "{}")
        if r["manuel"]:
            d.update(alanlar)
            c.execute("UPDATE kayitlar SET data=?, guncelleme=? WHERE id=?",
                      (json.dumps(d, ensure_ascii=False), now(), id_))
        else:
            for k, v in alanlar.items():
                if d.get(k) == v or (d.get(k) in (None, "") and v in (None, "")):
                    o.pop(k, None)
                else:
                    o[k] = v
            c.execute("UPDATE kayitlar SET overrides=?, guncelleme=? WHERE id=?",
                      (json.dumps(o, ensure_ascii=False), now(), id_))
    return kayit(id_)


def kayit_hoca_degistir(id_, hoca_id):
    with _lock, conn() as c:
        c.execute("UPDATE kayitlar SET hoca_id=? WHERE id=? AND manuel=1", (hoca_id, id_))


def kayit_sifirla(id_):
    with _lock, conn() as c:
        c.execute("UPDATE kayitlar SET overrides='{}' WHERE id=?", (id_,))
    return kayit(id_)


def kayit_gizle(id_, gizli):
    with _lock, conn() as c:
        c.execute("UPDATE kayitlar SET gizli=? WHERE id=?", (1 if gizli else 0, id_))


def kayit_ekle(hoca_id, kind, data):
    with _lock, conn() as c:
        cur = c.execute("INSERT INTO kayitlar(source_id,hoca_id,kind,data,manuel,eklenme,guncelleme) "
                        "VALUES(NULL,?,?,?,1,?,?)",
                        (hoca_id, kind, json.dumps(data, ensure_ascii=False), now(), now()))
        new_id = cur.lastrowid
    return kayit(new_id)


def kayit_sil(id_):
    with _lock, conn() as c:
        c.execute("DELETE FROM kayitlar WHERE id=?", (id_,))
