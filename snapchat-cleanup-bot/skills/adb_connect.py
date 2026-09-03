"""
skills/adb_connect.py
---------------------
SKILL: adb_connect

Gorevi: Emulator (LDPlayer / BlueStacks / MEmu) veya fiziksel cihaz ile
ADB baglantisini kurar ve uzerine uiautomator2 oturumu acar.

Disari acilan fonksiyonlar:
    adb_binary()      -> Sistemde kullanilabilir adb yolunu bulur.
    run_adb()         -> Tek bir adb komutu calistirir.
    list_devices()    -> Bagli cihazlarin listesini dondurur.
    adb_connect()     -> TCP baglantisi kurar + uiautomator2 cihazi dondurur.
"""

from __future__ import annotations

import shutil
import subprocess
import time
from typing import List, Optional, Tuple


class AdbError(RuntimeError):
    """ADB ile ilgili tum hatalar bu tip altinda toplanir."""


# ---------------------------------------------------------------------------
# ADB ikili dosyasini bulma
# ---------------------------------------------------------------------------
# Emulatorlerin kendi icinde gomulu gelen adb yollari.
_COMMON_ADB_PATHS = [
    r"C:\Program Files\Nox\bin\adb.exe",
    r"C:\LDPlayer\LDPlayer9\adb.exe",
    r"C:\LDPlayer\LDPlayer4.0\adb.exe",
    r"C:\Program Files\BlueStacks_nxt\HD-Adb.exe",
    r"C:\Program Files (x86)\Microvirt\MEmu\adb.exe",
    "/usr/local/bin/adb",
    "/usr/bin/adb",
]


def adb_binary() -> str:
    """
    Calistirilabilir adb yolunu dondurur.
    Once PATH icinde arar, bulamazsa bilinen emulator klasorlerine bakar.
    """
    found = shutil.which("adb")
    if found:
        return found

    for candidate in _COMMON_ADB_PATHS:
        if shutil.which(candidate) or _file_exists(candidate):
            return candidate

    raise AdbError(
        "adb bulunamadi. Android Platform Tools kurup PATH'e ekle "
        "veya skills/adb_connect.py icindeki _COMMON_ADB_PATHS listesine "
        "kendi adb.exe yolunu yaz."
    )


def _file_exists(path: str) -> bool:
    """shutil.which mutlak yollarda calismayabiliyor; yedek kontrol."""
    from pathlib import Path
    return Path(path).is_file()


# ---------------------------------------------------------------------------
# Temel adb komut calistirici
# ---------------------------------------------------------------------------
def run_adb(args: List[str], timeout: float = 30.0) -> Tuple[int, str, str]:
    """
    adb komutunu calistirir ve (donus_kodu, stdout, stderr) uclusunu verir.
    Ornek: run_adb(["connect", "127.0.0.1:5555"])
    """
    cmd = [adb_binary()] + args
    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            encoding="utf-8",
            errors="replace",
        )
    except subprocess.TimeoutExpired as exc:
        raise AdbError(f"adb komutu zaman asimina ugradi: {' '.join(args)}") from exc

    return proc.returncode, (proc.stdout or "").strip(), (proc.stderr or "").strip()


def list_devices() -> List[Tuple[str, str]]:
    """
    'adb devices' ciktisini ayristirir.
    Donus: [(seri_no, durum), ...]  durum ornek: 'device', 'offline', 'unauthorized'
    """
    code, out, err = run_adb(["devices"])
    if code != 0:
        raise AdbError(f"'adb devices' basarisiz oldu: {err or out}")

    devices: List[Tuple[str, str]] = []
    for line in out.splitlines()[1:]:          # ilk satir baslik: "List of devices attached"
        line = line.strip()
        if not line or "\t" not in line:
            continue
        serial, state = line.split("\t", 1)
        devices.append((serial.strip(), state.strip()))
    return devices


# ---------------------------------------------------------------------------
# Ana skill fonksiyonu
# ---------------------------------------------------------------------------
def adb_connect(
    serial: str,
    use_tcp_connect: bool = True,
    timeout: float = 60.0,
    logger=None,
):
    """
    Cihaza baglanir ve hazir bir uiautomator2 Device nesnesi dondurur.

    Adimlar:
      1. Gerekiyorsa 'adb connect <serial>' calistirir (emulator TCP portu).
      2. Cihazin 'device' durumunda oldugunu dogrular.
      3. uiautomator2 ile oturum acar (ilk seferde cihaza ATX agent kurulur).
    """
    log = logger.info if logger else print
    warn = logger.warning if logger else print

    # --- 1) TCP baglantisi -------------------------------------------------
    if use_tcp_connect and ":" in serial:
        log(f"ADB TCP baglantisi kuruluyor: {serial}")
        code, out, err = run_adb(["connect", serial])
        combined = f"{out} {err}".lower()
        # adb 'connect' basarisiz olsa bile 0 donebilir; ciktiyi da kontrol et.
        if "unable to connect" in combined or "cannot connect" in combined:
            raise AdbError(
                f"{serial} adresine baglanilamadi.\n"
                f"adb ciktisi: {out or err}\n"
                "Kontrol et: Emulator acik mi? ADB hata ayiklama ayari aktif mi? "
                "Port numarasi dogru mu? (LDPlayer 5555, BlueStacks 5555/5565)"
            )
        log(f"adb connect cevabi: {out or err or 'sessiz'}")

    # --- 2) Cihaz durumunu dogrula ----------------------------------------
    deadline = time.time() + timeout
    state: Optional[str] = None
    while time.time() < deadline:
        devices = list_devices()
        matched = [d for d in devices if d[0] == serial]
        if matched:
            state = matched[0][1]                # ilk eslesmenin durumu
            if state == "device":
                break
            warn(f"Cihaz '{serial}' su durumda: {state}. Bekleniyor...")
        else:
            warn(f"Cihaz '{serial}' listede yok. Mevcut: {devices or 'hicbiri'}")
        time.sleep(2.0)

    if state != "device":
        raise AdbError(
            f"Cihaz '{serial}' hazir duruma gelmedi (son durum: {state}).\n"
            "Cozum onerileri:\n"
            "  - Emulator ayarlarindan 'ADB Debugging' / 'Android Hata Ayiklama' ac\n"
            "  - 'adb kill-server' ardindan 'adb start-server' calistir\n"
            "  - Emulatorun kendi adb surumu ile sistem adb surumu cakisiyor olabilir"
        )

    log(f"Cihaz hazir: {serial}")

    # --- 3) uiautomator2 oturumu ------------------------------------------
    try:
        import uiautomator2 as u2
    except ImportError as exc:
        raise AdbError(
            "uiautomator2 kurulu degil. Kurmak icin: pip install uiautomator2"
        ) from exc

    log("uiautomator2 oturumu aciliyor (ilk calistirmada 1-2 dakika surebilir)...")
    try:
        device = u2.connect(serial)
        info = device.info                      # baglanti canli mi diye test cagrisi
    except Exception as exc:                    # noqa: BLE001 - u2 cesitli hata tipleri firlatir
        raise AdbError(
            f"uiautomator2 baglantisi kurulamadi: {exc}\n"
            "Deneyebilecegin adimlar:\n"
            "  - python -m uiautomator2 init\n"
            "  - Emulatoru yeniden baslat\n"
            "  - Android surumu 5.0+ oldugundan emin ol"
        ) from exc

    log(
        "Baglanti basarili | Ekran: "
        f"{info.get('displayWidth')}x{info.get('displayHeight')} | "
        f"Android SDK: {info.get('sdkInt')}"
    )
    return device


def ensure_app_running(device, package_name: str, logger=None, wait: float = 6.0) -> bool:
    """
    Snapchat on planda mi kontrol eder; degilse baslatir.
    Donus: uygulama on planda ise True.
    """
    log = logger.info if logger else print

    current = device.app_current()
    if current.get("package") == package_name:
        log(f"{package_name} zaten on planda.")
        return True

    log(f"{package_name} on planda degil ({current.get('package')}). Baslatiliyor...")
    device.app_start(package_name, use_monkey=True)
    time.sleep(wait)

    current = device.app_current()
    ok = current.get("package") == package_name
    if not ok:
        log(f"UYARI: Uygulama baslatilamadi. Su an on planda: {current.get('package')}")
    return ok
