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

from agents.action_agent import ActionAgent
from agents.environment_agent import EnvironmentAgent
from agents.ui_parser_agent import UIParserAgent
from config import CONFIG
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
    return parser.parse_args()


# ---------------------------------------------------------------------------
# Ayarlari komut satiri ile guncelle
# ---------------------------------------------------------------------------
def apply_args(args: argparse.Namespace) -> None:
    if args.serial:
        CONFIG.device.serial = args.serial
    if args.max is not None:
        CONFIG.run.max_cancellations = args.max
    if args.debug:
        CONFIG.run.save_hierarchy = True
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
    result = action_agent.execute()
    action_agent.report(result)

    return 0


if __name__ == "__main__":
    sys.exit(main())
