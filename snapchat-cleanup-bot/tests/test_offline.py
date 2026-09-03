"""
tests/test_offline.py
---------------------
Emulator olmadan calisan dogrulama testleri.
Sahte cihaz (tests/fake_device.py) uzerinde botun tum mantigini isletir.

Calistirmak icin proje kokunde:
    python -m tests.test_offline
"""

from __future__ import annotations

import copy
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from agents.action_agent import ActionAgent          # noqa: E402
from agents.ui_parser_agent import UIParserAgent     # noqa: E402
from config import AppConfig                         # noqa: E402
from tests.fake_device import FakeDevice             # noqa: E402
from utils.logger import get_logger                  # noqa: E402


def fast_config(dry_run: bool, max_cancellations: int = 0) -> AppConfig:
    """Testler icin beklemeleri neredeyse sifirlanmis ayar nesnesi."""
    cfg = copy.deepcopy(AppConfig())
    cfg.timing.click_delay_min = 0.001
    cfg.timing.click_delay_max = 0.002
    cfg.timing.cooldown_every = 1000            # testte mola istemiyoruz
    cfg.timing.cooldown_seconds = 0.001
    cfg.timing.dialog_wait = 0.05
    cfg.timing.scroll_settle_min = 0.001
    cfg.timing.scroll_settle_max = 0.002
    cfg.run.dry_run = dry_run
    cfg.run.max_cancellations = max_cancellations
    cfg.run.max_empty_scrolls = 2
    cfg.run.save_hierarchy = False
    return cfg


def check(label: str, condition: bool, detail: str = "") -> bool:
    mark = "GECTI " if condition else "KALDI "
    print(f"  [{mark}] {label}" + (f"  ({detail})" if detail else ""))
    return condition


def main() -> int:
    logger = get_logger("test", log_file="/tmp/snapbot_test.log")
    logger.setLevel(40)                          # testte log gurultusunu kis
    results = []
    names = [f"kullanici_{i:02d}" for i in range(1, 21)]

    # ---------------------------------------------------------------
    print("\n1) Ayristirma: ekrandaki bekleyen butonlar ve isimler")
    device = FakeDevice(names=list(names), visible_count=6)
    cfg = fast_config(dry_run=True)
    parser = UIParserAgent(device, cfg.ui, cfg.run, logger)

    found = parser.find_pending()
    results.append(check("6 bekleyen buton bulundu", len(found) == 6, f"bulunan={len(found)}"))
    results.append(
        check(
            "Ilk satirin kullanici adi dogru okundu",
            bool(found) and found[0].row_label == "kullanici_01",
            found[0].row_label if found else "yok",
        )
    )
    results.append(
        check(
            "Butonlar yukaridan asagiya sirali",
            [e.bounds[1] for e in found] == sorted(e.bounds[1] for e in found),
        )
    )
    ok_screen, reason = parser.detect_screen()
    results.append(check("Ekran dogru algilandi", ok_screen, reason))

    # ---------------------------------------------------------------
    print("\n2) Deneme modu: hicbir sey iptal edilmemeli")
    device = FakeDevice(names=list(names), visible_count=6)
    cfg = fast_config(dry_run=True)
    parser = UIParserAgent(device, cfg.ui, cfg.run, logger)
    agent = ActionAgent(device, parser, cfg, logger)
    result = agent.execute()

    results.append(check("Cihazda hicbir kayit silinmedi", len(device.names) == 20,
                         f"kalan={len(device.names)}"))
    results.append(check("Cihaza hic tiklanmadi", device.clicks == 0, f"tiklama={device.clicks}"))
    results.append(check("Tum liste tarandi", len(result.processed) == 20,
                         f"islenen={len(result.processed)}"))

    # ---------------------------------------------------------------
    print("\n3) Gercek mod (onay penceresi acilan surum)")
    device = FakeDevice(names=list(names), visible_count=6, require_dialog=True)
    cfg = fast_config(dry_run=False)
    parser = UIParserAgent(device, cfg.ui, cfg.run, logger)
    agent = ActionAgent(device, parser, cfg, logger)
    result = agent.execute()

    results.append(check("Tum istekler iptal edildi", len(device.names) == 0,
                         f"kalan={len(device.names)}"))
    results.append(check("Iptal sayaci dogru", result.cancelled == 20,
                         f"iptal={result.cancelled}"))
    results.append(check("Basarisiz islem yok", result.failed == 0, f"basarisiz={result.failed}"))
    results.append(check("Ayni kisi iki kez iptal edilmedi",
                         len(set(device.cancelled)) == len(device.cancelled)))

    # ---------------------------------------------------------------
    print("\n4) Gercek mod (onay penceresi acilmayan surum)")
    device = FakeDevice(names=list(names), visible_count=6, require_dialog=False)
    cfg = fast_config(dry_run=False)
    parser = UIParserAgent(device, cfg.ui, cfg.run, logger)
    agent = ActionAgent(device, parser, cfg, logger)
    result = agent.execute()

    results.append(check("Tum istekler iptal edildi", len(device.names) == 0,
                         f"kalan={len(device.names)}"))

    # ---------------------------------------------------------------
    print("\n5) Islem limiti (--max 7)")
    device = FakeDevice(names=list(names), visible_count=6, require_dialog=True)
    cfg = fast_config(dry_run=False, max_cancellations=7)
    parser = UIParserAgent(device, cfg.ui, cfg.run, logger)
    agent = ActionAgent(device, parser, cfg, logger)
    result = agent.execute()

    results.append(check("Tam 7 iptal yapildi", result.cancelled == 7, f"iptal={result.cancelled}"))
    results.append(check("Cihazda 13 kayit kaldi", len(device.names) == 13,
                         f"kalan={len(device.names)}"))
    results.append(check("Durma nedeni limit", "limit" in result.stop_reason.lower(),
                         result.stop_reason))

    # ---------------------------------------------------------------
    print("\n6) Ingilizce arayuz ('Pending' etiketi)")
    device = FakeDevice(names=list(names)[:8], visible_count=4, pending_text="Pending")
    cfg = fast_config(dry_run=False)
    parser = UIParserAgent(device, cfg.ui, cfg.run, logger)
    agent = ActionAgent(device, parser, cfg, logger)
    result = agent.execute()

    results.append(check("Ingilizce etiket tanindi", result.cancelled == 8,
                         f"iptal={result.cancelled}"))

    # ---------------------------------------------------------------
    print("\n7) Bos liste: guvenli sekilde durmali")
    device = FakeDevice(names=[], visible_count=6)
    cfg = fast_config(dry_run=False)
    parser = UIParserAgent(device, cfg.ui, cfg.run, logger)
    agent = ActionAgent(device, parser, cfg, logger)
    result = agent.execute()

    results.append(check("Hic tiklama yapilmadi", device.clicks == 0, f"tiklama={device.clicks}"))
    results.append(check("Liste sonu olarak durdu", "son" in result.stop_reason.lower(),
                         result.stop_reason))

    # ---------------------------------------------------------------
    print("\n8) Cihaz secimi (--serial auto)")
    import skills.adb_connect as adb

    original = adb.list_devices
    try:
        # Tek cihaz bagli: otomatik secilmeli
        adb.list_devices = lambda: [("R58M12ABCDE", "device")]
        results.append(check("Tek USB cihaz otomatik secildi",
                             adb.resolve_serial("auto") == "R58M12ABCDE"))

        # Acik adres verildiyse dokunulmamali
        results.append(check("Elle verilen adres degistirilmedi",
                             adb.resolve_serial("127.0.0.1:5555") == "127.0.0.1:5555"))

        # Yetkilendirilmemis cihaz secilmemeli
        adb.list_devices = lambda: [("R58M12ABCDE", "unauthorized")]
        try:
            adb.resolve_serial("auto")
            results.append(check("Yetkisiz cihaz reddedildi", False))
        except adb.AdbError:
            results.append(check("Yetkisiz cihaz reddedildi", True))

        # Birden fazla cihazda net hata verilmeli
        adb.list_devices = lambda: [("emulator-5554", "device"), ("R58M12ABCDE", "device")]
        try:
            adb.resolve_serial("auto")
            results.append(check("Coklu cihazda hata verildi", False))
        except adb.AdbError as exc:
            results.append(check("Coklu cihazda hata verildi", "--serial" in str(exc)))
    finally:
        adb.list_devices = original

    # ---------------------------------------------------------------
    passed = sum(1 for r in results if r)
    total = len(results)
    print("\n" + "=" * 55)
    print(f"SONUC: {passed}/{total} kontrol gecti")
    print("=" * 55)
    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())
