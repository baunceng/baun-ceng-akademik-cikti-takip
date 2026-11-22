"""Aylık otomatik YÖKSİS güncellemesini işletim sisteminin zamanlayıcısına kurar / kaldırır.

  python otomatik_kur.py          -> kur
  python otomatik_kur.py --kaldir -> kaldır

Görev HER GÜN 09:00'da kısa bir kontrol yapar; o ay güncelleme yapılmamışsa YÖKSİS'ten çeker.
Böylece ayın 1'inde bilgisayar kapalı olsa bile açıldığı ilk gün güncelleme yapılır.
  Windows -> Görev Zamanlayıcı (schtasks)
  macOS   -> launchd (~/Library/LaunchAgents)
  Linux   -> crontab
"""
import os
import platform
import subprocess
import sys

AD = "BAUN-CENG-Akademik-Guncelleme"
KLASOR = os.path.dirname(os.path.abspath(__file__))
BETIK = os.path.join(KLASOR, "sync_cli.py")
LOG = os.path.join(KLASOR, "otomatik_guncelleme.log")
PY = sys.executable


def windows(kaldir):
    if kaldir:
        subprocess.run(["schtasks", "/Delete", "/TN", AD, "/F"], check=False)
        subprocess.run(["schtasks", "/Delete", "/TN", AD + "-Giris", "/F"], check=False)
        return
    bat = os.path.join(KLASOR, "otomatik_guncelle.bat")
    with open(bat, "w", encoding="utf-8") as f:
        f.write(f'@echo off\r\ncd /d "{KLASOR}"\r\n"{PY}" "{BETIK}" >> "{LOG}" 2>&1\r\n')
    subprocess.run(["schtasks", "/Create", "/TN", AD, "/TR", f'"{bat}"', "/SC", "DAILY", "/ST", "09:00", "/F"],
                   check=True)
    # Bilgisayar 09:00'da kapalıysa: oturum açılışında da kontrol et
    subprocess.run(["schtasks", "/Create", "/TN", AD + "-Giris", "/TR", f'"{bat}"', "/SC", "ONLOGON", "/F"],
                   check=False)
    print("Not: Her oturum açılışında ve her gün 09:00'da kontrol eder.")


def macos(kaldir):
    plist = os.path.expanduser(f"~/Library/LaunchAgents/tr.edu.baun.{AD}.plist")
    subprocess.run(["launchctl", "unload", plist], check=False, capture_output=True)
    if kaldir:
        if os.path.exists(plist):
            os.remove(plist)
        return
    os.makedirs(os.path.dirname(plist), exist_ok=True)
    with open(plist, "w", encoding="utf-8") as f:
        f.write(f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
  <key>Label</key><string>tr.edu.baun.{AD}</string>
  <key>ProgramArguments</key><array><string>{PY}</string><string>{BETIK}</string></array>
  <key>WorkingDirectory</key><string>{KLASOR}</string>
  <key>StartCalendarInterval</key><dict><key>Hour</key><integer>9</integer><key>Minute</key><integer>0</integer></dict>
  <key>RunAtLoad</key><true/>
  <key>StandardOutPath</key><string>{LOG}</string>
  <key>StandardErrorPath</key><string>{LOG}</string>
</dict></plist>
""")
    subprocess.run(["launchctl", "load", plist], check=True)
    print("Not: Her oturum açılışında ve her gün 09:00'da kontrol eder; Mac uykudaysa uyanınca çalışır.")


def linux(kaldir):
    mevcut = subprocess.run(["crontab", "-l"], capture_output=True, text=True).stdout
    satirlar = [s for s in mevcut.splitlines() if AD not in s]
    if not kaldir:
        satirlar.append(f'0 9 * * * cd "{KLASOR}" && "{PY}" "{BETIK}" >> "{LOG}" 2>&1  # {AD}')
        satirlar.append(f'@reboot sleep 120 && cd "{KLASOR}" && "{PY}" "{BETIK}" >> "{LOG}" 2>&1  # {AD}')
    subprocess.run(["crontab", "-"], input="\n".join(satirlar) + "\n", text=True, check=True)


def main():
    kaldir = "--kaldir" in sys.argv
    sistem = platform.system()
    {"Windows": windows, "Darwin": macos, "Linux": linux}.get(sistem, lambda k: sys.exit(f"Desteklenmeyen sistem: {sistem}"))(kaldir)
    if kaldir:
        print("Otomatik güncelleme görevi kaldırıldı.")
    else:
        print(f"Kuruldu ({sistem}). Her gün 09:00'da kontrol edilir, ayda bir YÖKSİS'ten güncellenir.")
        print(f"Kayıt dosyası: {LOG}")


if __name__ == "__main__":
    main()
