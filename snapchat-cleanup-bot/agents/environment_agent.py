"""
agents/environment_agent.py
---------------------------
AGENT: EnvironmentAgent

Sorumlulugu: Bot calismaya baslamadan once ortamin hazir oldugunu dogrulamak.
Amac, yarim yamalak bir ortamda calisip ekranda rastgele yerlere tiklayan
bir bot ortaya cikmasini engellemek.

Yaptigi kontroller:
    1. adb komutu sistemde bulunuyor mu?
    2. Emulator / cihaz ADB uzerinden erisilebilir mi?
    3. uiautomator2 oturumu aciliyor mu?
    4. Ekran acik ve kilitli degil mi?
    5. Snapchat kurulu mu ve on planda mi?
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Optional

from skills.adb_connect import (
    AdbError,
    adb_binary,
    adb_connect,
    ensure_app_running,
    list_devices,
    resolve_serial,
    run_adb,
    set_stay_awake,
)


@dataclass
class EnvironmentReport:
    """Ortam kontrolu sonucu."""

    ok: bool
    device: object = None
    screen_size: tuple = (0, 0)
    android_version: str = ""
    app_installed: bool = False
    app_foreground: bool = False
    message: str = ""


class EnvironmentAgent:
    """Emulator ve ADB baglantisini dogrulayan ajan."""

    def __init__(self, config, logger):
        self.config = config          # AppConfig.device
        self.logger = logger
        self.device = None
        # 'auto' cozuldukten sonraki gercek seri numarasi
        self.resolved_serial: str = config.serial

    # -- Adim 1: adb var mi -------------------------------------------------
    def check_adb_binary(self) -> bool:
        try:
            path = adb_binary()
        except AdbError as exc:
            self.logger.error(str(exc))
            return False
        self.logger.info(f"adb bulundu: {path}")

        code, out, _ = run_adb(["version"])
        if code == 0:
            self.logger.debug(f"adb surumu: {out.splitlines()[0] if out else 'bilinmiyor'}")
        return True

    # -- Adim 2 + 3: cihaza baglan -----------------------------------------
    def connect(self) -> Optional[object]:
        try:
            # "auto" gibi degerleri once gercek seri numarasina cevir; sonraki
            # adb komutlari (-s <serial>) bu cozulmus degeri kullanacak.
            self.resolved_serial = resolve_serial(self.config.serial, logger=self.logger)
            self.device = adb_connect(
                serial=self.resolved_serial,
                use_tcp_connect=self.config.use_tcp_connect,
                timeout=self.config.connect_timeout,
                logger=self.logger,
            )
        except AdbError as exc:
            self.logger.error(f"Baglanti kurulamadi:\n{exc}")
            self._print_device_list()
            return None
        return self.device

    def _print_device_list(self) -> None:
        """Hata durumunda kullaniciya mevcut cihazlari gosterir."""
        try:
            devices = list_devices()
        except AdbError:
            return
        if devices:
            self.logger.info("Su an bagli gorunen cihazlar:")
            for serial, state in devices:
                self.logger.info(f"   - {serial}  ({state})")
            self.logger.info(
                "Bunlardan birini config.py icindeki DeviceConfig.serial alanina yaz."
            )
        else:
            self.logger.info(
                "Hicbir cihaz bagli degil. Emulatoru ac ve ADB ayarini etkinlestir."
            )

    # -- Adim 4: ekran acik mi ---------------------------------------------
    def ensure_screen_on(self) -> bool:
        """Ekran kapaliysa acar, kilit ekranindaysa yukari kaydirmayi dener."""
        if self.device is None:
            return False

        try:
            if not self.device.info.get("screenOn", True):
                self.logger.info("Ekran kapali, aciliyor...")
                self.device.screen_on()
                time.sleep(1.5)

            # Kilit ekrani kontrolu: uygulama paketi kilit ekranina aitse kaydir.
            current = self.device.app_current().get("package", "")
            if "keyguard" in current.lower() or "lockscreen" in current.lower():
                self.logger.info("Kilit ekrani algilandi, aciliyor...")
                self.device.swipe(0.5, 0.8, 0.5, 0.2, duration=0.3)
                time.sleep(1.5)
        except Exception as exc:  # noqa: BLE001
            self.logger.warning(f"Ekran durumu kontrol edilemedi: {exc}")
            return False

        return True

    # -- Ekrani acik tutma (fiziksel telefonda kritik) ---------------------
    def keep_awake(self, enable: bool = True) -> bool:
        """
        Calisma boyunca ekranin kapanmasini engeller.
        Telefon ekrani kapanirsa arayuz agaci okunamaz ve bot yarida kalir.
        Is bitince main.py bunu enable=False ile geri alir.
        """
        if not getattr(self.config, "keep_screen_awake", False):
            return False
        return set_stay_awake(self.resolved_serial, enable, logger=self.logger)

    # -- Adim 5: Snapchat kurulu mu / on planda mi -------------------------
    def check_app(self) -> tuple:
        """
        Donus: (kurulu_mu, on_planda_mi)
        """
        if self.device is None:
            return False, False

        package = self.config.package_name

        # Kurulu paketler arasinda ara.
        try:
            installed = package in self.device.app_list()
        except Exception:  # noqa: BLE001 - yedek olarak pm list packages kullan
            code, out, _ = run_adb(["-s", self.resolved_serial, "shell", "pm", "list", "packages", package])
            installed = code == 0 and package in out

        if not installed:
            self.logger.error(
                f"{package} bu cihazda kurulu degil.\n"
                "Emulator icindeki Play Store'dan Snapchat'i kur, "
                "giris yap ve bir kez elle ac."
            )
            return False, False

        self.logger.info(f"{package} kurulu.")
        foreground = ensure_app_running(self.device, package, logger=self.logger)
        return True, foreground

    # -- Tum kontrolleri sirayla calistir ----------------------------------
    def verify(self) -> EnvironmentReport:
        """
        Butun kontrolleri sirayla yapar ve tek bir rapor dondurur.
        Herhangi bir adim basarisiz olursa ok=False doner ve
        main.py calismayi guvenli sekilde durdurur.
        """
        self.logger.info("--- Ortam kontrolu basliyor ---")

        if not self.check_adb_binary():
            return EnvironmentReport(ok=False, message="adb bulunamadi")

        device = self.connect()
        if device is None:
            return EnvironmentReport(ok=False, message="Cihaza baglanilamadi")

        if not self.ensure_screen_on():
            self.logger.warning("Ekran durumu dogrulanamadi, yine de devam ediliyor.")

        # Uzun surecek bir islem: ekranin kendiliginden kapanmasini engelle.
        self.keep_awake(True)

        installed, foreground = self.check_app()
        if not installed:
            return EnvironmentReport(
                ok=False, device=device, message="Snapchat kurulu degil"
            )
        if not foreground:
            return EnvironmentReport(
                ok=False,
                device=device,
                app_installed=True,
                message="Snapchat on plana getirilemedi",
            )

        info = device.info
        report = EnvironmentReport(
            ok=True,
            device=device,
            screen_size=(info.get("displayWidth", 0), info.get("displayHeight", 0)),
            android_version=str(info.get("sdkInt", "")),
            app_installed=True,
            app_foreground=True,
            message="Ortam hazir",
        )
        self.logger.info(
            f"--- Ortam hazir | Ekran {report.screen_size[0]}x{report.screen_size[1]} ---"
        )
        return report
