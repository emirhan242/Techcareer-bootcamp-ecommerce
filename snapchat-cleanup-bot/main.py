#!/usr/bin/env python3
"""
main.py
-------
Snapchat bekleyen arkadaslik isteklerini toplu iptal eden botun giris noktasi.

Calisma sirasi:
    1. EnvironmentAgent  -> ADB / emulator / Snapchat kontrolu
    2. UIParserAgent     -> Ekrandaki bekleyen butonlarin tespiti
    3. ActionAgent       -> Tiklama + kaydirma + zamanlama dongusu

Kullanim ornekleri:
    python main.py --scan                 # sadece ekrani oku, hicbir sey yapma
    python main.py                        # deneme modu (varsayilan, tiklamaz)
    python main.py --live --max 30        # gercek mod, en fazla 30 istek iptal et
    python main.py --serial 127.0.0.1:5565 --live
"""

from __future__ import annotations

import argparse
import sys
import time

from agents.action_agent import ActionAgent
from agents.environment_agent import EnvironmentAgent
from agents.ui_parser_agent import UIParserAgent
from config import CONFIG
from skills.open_recent_added import open_recent_added
from utils.logger import banner, get_logger


# ---------------------------------------------------------------------------
# Komut satiri secenekleri
# ---------------------------------------------------------------------------
def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Snapchat bekleyen arkadaslik isteklerini toplu iptal eder.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--serial",
        default=None,
        help="Cihaz adresi (varsayilan: config.py icindeki deger)",
    )
    parser.add_argument(
        "--live",
        action="store_true",
        help="Gercek mod. Bu bayrak verilmezse hicbir tiklama yapilmaz.",
    )
    parser.add_argument(
        "--max",
        type=int,
        default=None,
        help="Bu oturumda iptal edilecek en fazla istek sayisi (0 = limitsiz)",
    )
    parser.add_argument(
        "--scan",
        action="store_true",
        help="Tani modu: ekrandaki tum metinleri listeler, hicbir islem yapmaz. "
             "config.py icindeki etiketleri kendi Snapchat surumune gore "
             "duzenlemek icin bunu kullan.",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Her taramada arayuz XML'ini ve ekran goruntusunu diske kaydeder.",
    )
    parser.add_argument(
        "--yes",
        action="store_true",
        help="Gercek modda onay sorusunu atlar (gozetimsiz calistirma icin).",
    )
    parser.add_argument(
        "--usb",
        action="store_true",
        help="Fiziksel telefon USB ile bagli. 'adb connect' adimini atlar.",
    )
    parser.add_argument(
        "--pair",
        nargs=2,
        metavar=("ADRES", "KOD"),
        default=None,
        help="Android 11+ kablosuz hata ayiklama eslestirmesi. "
             "Ornek: --pair 192.168.1.42:37215 123456 "
             "(telefondaki eslestirme ekranindaki adres ve 6 haneli kod)",
    )
    parser.add_argument(
        "--profile-flow",
        action="store_true",
        help="Liste ekraninda 'Bekliyor' butonu olmayan Snapchat surumleri icin. "
             "Kisinin profiline girip 'Arkadasligi Yonet > Arkadasi Sil' "
             "yolunu izler. Guvenlik icin profilde bekleyen isareti "
             "gormedigi kisiyi atlar.",
    )
    parser.add_argument(
        "--inspect-profile",
        nargs="?",
        type=int,
        const=1,
        default=None,
        metavar="SIRA",
        help="Tani: listedeki N. kisinin profilini acar, ekrandaki tum "
             "metinleri yazar ve geri doner. Hicbir sey silmez. "
             "Profil akisindaki gercek buton yazilarini ogrenmek icin.",
    )
    return parser.parse_args()


# ---------------------------------------------------------------------------
# Ayarlari komut satiri ile guncelle
# ---------------------------------------------------------------------------
def apply_args(args: argparse.Namespace) -> None:
    if args.serial:
        CONFIG.device.serial = args.serial
    if args.usb:
        # USB cihazda 'adb connect' calistirmak anlamsizdir.
        CONFIG.device.use_tcp_connect = False
    if args.max is not None:
        CONFIG.run.max_cancellations = args.max
    if args.debug:
        CONFIG.run.save_hierarchy = True
    if args.profile_flow:
        CONFIG.run.profile_flow = True
    # --live verilmedikce her zaman deneme modunda kal.
    CONFIG.run.dry_run = not args.live


# ---------------------------------------------------------------------------
# Gercek moda gecmeden once kullanici onayi
# ---------------------------------------------------------------------------
def confirm_live_run(logger, skip: bool) -> bool:
    if skip:
        return True

    limit = CONFIG.run.max_cancellations or "LIMITSIZ"
    logger.warning("")
    logger.warning("GERCEK MOD ETKIN. Bot ekrana gercekten tiklayacak.")
    logger.warning(f"Bu oturumda en fazla {limit} istek iptal edilecek.")
    logger.warning("Devam etmeden once emin ol:")
    logger.warning("  - Emulatorde dogru Snapchat hesabi acik")
    logger.warning("  - Bekleyen istekler listesi ekranda gorunuyor")
    logger.warning("  - Once --scan ve deneme modunu calistirdin")
    logger.warning("")

    try:
        answer = input("Devam edilsin mi? (evet/hayir): ").strip().lower()
    except (EOFError, KeyboardInterrupt):
        return False

    return answer in ("evet", "e", "yes", "y")


# ---------------------------------------------------------------------------
# Tani modu
# ---------------------------------------------------------------------------
def run_scan(parser: UIParserAgent, logger) -> int:
    """Ekrani okur, bulduklarini listeler ve cikar. Hicbir tiklama yapmaz."""
    banner(logger, "TANI MODU - ekran okunuyor, hicbir islem yapilmayacak")

    ok, reason = parser.detect_screen()
    logger.info(f"Ekran kontrolu: {'UYGUN' if ok else 'UYGUN DEGIL'} - {reason}")

    logger.info("")
    logger.info("Ekranda gorunen metinler:")
    for text in parser.list_all_texts():
        logger.info(f"   - {text!r}")

    logger.info("")
    elements = parser.find_pending()
    if elements:
        logger.info(f"Bekleyen istek olarak algilanan {len(elements)} kayit:")
        for element in elements:
            logger.info(f"   - {element}")
    else:
        logger.warning("Bekleyen istek algilanamadi.")
        logger.warning(
            "Yukaridaki metin listesinde istek butonunun yazisini bul "
            "(ornek: 'Bekliyor', 'Pending', 'Added') ve config.py icindeki "
            "UIConfig.pending_labels listesine ekle."
        )

    path = parser.save_debug_dump(prefix="scan")
    if path:
        logger.info(f"Arayuz dokumu kaydedildi: {path}")
    return 0


def run_inspect_profile(parser: UIParserAgent, device, index: int, logger) -> int:
    """
    Listedeki N. kisinin profilini acar, ekrandaki her metni yazar ve geri
    doner. Hicbir sey silmez.

    Amaci: profil akisinin ("Arkadasligi Yonet" > "Arkadasi Sil") kendi
    Snapchat surumunde hangi yazilari kullandigini ve bekleyen bir istegi
    kabul edilmis bir arkadastan neyin ayirdigini ogrenmek. Bu iki bilgi
    olmadan bot listedeki gercek arkadaslari da silebilir, o yuzden
    --profile-flow kullanmadan once bunu calistir.
    """
    from skills.find_and_cancel_requests import screen_texts

    banner(logger, "PROFIL INCELEME - hicbir sey silinmeyecek")

    rows = parser.find_person_rows()
    if not rows:
        logger.error("Listede kisi satiri bulunamadi.")
        logger.error("Once 'En Son Eklenenler' listesini ekrana getir.")
        return 1

    logger.info(f"Listede {len(rows)} satir goruldu:")
    for position, row in enumerate(rows, start=1):
        logger.info(f"  {position}. {row.row_label}")

    if index < 1 or index > len(rows):
        logger.error(f"Gecersiz sira: {index}. 1 ile {len(rows)} arasinda olmali.")
        return 1

    target = rows[index - 1]
    logger.info("")
    logger.info(f"{index}. kisinin profili aciliyor: {target.row_label}")

    device.click(*target.center)
    time.sleep(2.5)

    texts = screen_texts(device)
    logger.info("")
    logger.info("Profil ekranindaki metinler:")
    for text in texts:
        logger.info(f"   - {text!r}")

    path = parser.save_debug_dump(prefix="profile")
    if path:
        logger.info(f"Arayuz dokumu kaydedildi: {path}")

    logger.info("")
    logger.info("Listeye donuluyor.")
    try:
        device.press("back")
    except Exception as exc:  # noqa: BLE001
        logger.warning(f"Geri donulemedi: {exc}")

    logger.info("")
    logger.info("Simdi yukaridaki listeden su ikisini bul ve config.py'ye yaz:")
    logger.info("  1. Menuyu acan buton  -> UIConfig.manage_friendship_labels")
    logger.info("  2. Bekleyen istegi kabul edilmis arkadastan ayiran yazi")
    logger.info("     -> UIConfig.profile_pending_markers")
    logger.info("")
    logger.info("Ikinci madde onemli: o yazi olmadan bot bekleyen istekle")
    logger.info("gercek arkadasi ayirt edemez ve ikisini de siler.")
    return 0


# ---------------------------------------------------------------------------
# Ana akis
# ---------------------------------------------------------------------------
def main() -> int:
    args = parse_args()
    apply_args(args)

    logger = get_logger("snapbot")
    banner(logger, "Snapchat Bekleyen Istek Temizleyici")
    logger.info(f"Hedef cihaz : {CONFIG.device.serial}")
    logger.info(f"Mod         : {'GERCEK' if args.live else 'DENEME (tiklama yok)'}")
    logger.info(f"Islem limiti: {CONFIG.run.max_cancellations or 'limitsiz'}")

    # --- 0) Kablosuz eslestirme (sadece --pair verildiyse) ---
    if args.pair:
        from skills.adb_connect import AdbError, adb_pair
        try:
            adb_pair(args.pair[0], args.pair[1], logger=logger)
        except AdbError as exc:
            logger.error(str(exc))
            return 1
        logger.info(
            "Eslestirme tamam. Simdi telefondaki 'Kablosuz hata ayiklama' "
            "ekranindaki IP:PORT degerini --serial ile ver."
        )

    # --- 1) Ortam kontrolu ---
    env_agent = EnvironmentAgent(CONFIG.device, logger)
    report = env_agent.verify()
    if not report.ok:
        logger.error(f"Ortam hazir degil: {report.message}")
        logger.error("Kurulum adimlari icin README.md dosyasina bak.")
        return 1

    device = report.device

    # --- 2) Arayuz ayristirici ---
    parser = UIParserAgent(device, CONFIG.ui, CONFIG.run, logger)

    if args.scan:
        return run_scan(parser, logger)

    # Profil akisinda Snapchat "Arkadas Ekle" ekraninda aciliyor; bekleyen
    # istekler orada degil, uc nokta menusunun altindaki listede. Once oraya
    # gecmeyi dene, olmazsa kullanici elle acsin.
    if CONFIG.run.profile_flow or args.inspect_profile is not None:
        open_recent_added(device, CONFIG.ui, logger=logger)

    if args.inspect_profile is not None:
        return run_inspect_profile(parser, device, args.inspect_profile, logger)

    # --- 3) Dogru ekranda miyiz? ---
    ok, reason = parser.detect_screen()
    if not ok:
        logger.warning(f"Beklenen ekranda gorunmuyoruz: {reason}")
        logger.warning(
            "Emulatorde elle su yolu ac: Profil > Arkadaslarim / Arkadas Ekle > "
            "gonderilmis (bekleyen) istekler listesi."
        )
        try:
            input("Listeyi ekrana getirdikten sonra Enter'a bas (vazgecmek icin Ctrl+C): ")
        except (EOFError, KeyboardInterrupt):
            logger.info("Iptal edildi.")
            return 1

        ok, reason = parser.detect_screen()
        if not ok:
            logger.error(f"Hala dogru ekran algilanamadi: {reason}")
            logger.error("Once 'python main.py --scan' calistirip etiketleri kontrol et.")
            return 1

    logger.info(f"Ekran dogrulandi: {reason}")

    # --- 4) Gercek mod onayi ---
    if args.live and not confirm_live_run(logger, skip=args.yes):
        logger.info("Kullanici onaylamadi, cikiliyor.")
        return 0

    # --- 5) Ana dongu ---
    action_agent = ActionAgent(device, parser, CONFIG, logger)
    try:
        result = action_agent.execute()
        action_agent.report(result)
    finally:
        # Hata cikse de ekran zaman asimini normale dondur, aksi halde
        # telefonun ekrani surekli acik kalir ve pil biter.
        env_agent.keep_awake(False)

    return 0


if __name__ == "__main__":
    sys.exit(main())
