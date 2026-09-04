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
from skills.open_recent_added import (                # noqa: E402
    on_recent_list,
    open_recent_added,
)
from tests.fake_device import FakeDevice, FakeProfileDevice   # noqa: E402
from utils.logger import get_logger                  # noqa: E402


def fast_config(dry_run: bool, max_cancellations: int = 0) -> AppConfig:
    """
    Testler icin beklemeleri neredeyse sifirlanmis ayar nesnesi.

    TimingConfig'teki her sure alanini tek tek yazmak yerine hepsini
    dolasiyoruz: yeni bir bekleme ayari eklendiginde testler kendiliginden
    hizli kalsin, kimse listeye eklemeyi unutunca suite dakikalara
    uzamasin. Sadece anlamli olmasi gereken birkac deger elle veriliyor.
    """
    cfg = copy.deepcopy(AppConfig())

    for name, value in vars(cfg.timing).items():
        if isinstance(value, float):
            setattr(cfg.timing, name, 0.001)

    cfg.timing.click_delay_max = 0.002
    cfg.timing.scroll_settle_max = 0.002
    cfg.timing.dialog_wait = 0.05               # dialog aramasi bir tur donsun
    cfg.timing.cooldown_every = 1000            # testte mola istemiyoruz

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
    print("\n9) Profil akisi: liste > profil > Arkadasligi Yonet > Arkadasi Sil")
    # Listede bekleyen istekler ve kabul etmis gercek arkadaslar bir arada.
    people = {
        "bekleyen_01": "pending",
        "arkadas_01": "friend",
        "bekleyen_02": "pending",
        "arkadas_02": "friend",
        "bekleyen_03": "pending",
    }
    device = FakeProfileDevice(people=dict(people))
    cfg = fast_config(dry_run=False)
    cfg.run.profile_flow = True
    parser = UIParserAgent(device, cfg.ui, cfg.run, logger)
    agent = ActionAgent(device, parser, cfg, logger)
    result = agent.execute()

    results.append(
        check(
            "Bekleyen istekler iptal edildi",
            sorted(device.removed) == ["bekleyen_01", "bekleyen_02", "bekleyen_03"],
            f"silinen={sorted(device.removed)}",
        )
    )
    results.append(
        check(
            "Gercek arkadaslara dokunulmadi",
            "arkadas_01" not in device.removed and "arkadas_02" not in device.removed,
            f"silinen={sorted(device.removed)}",
        )
    )
    results.append(
        check("Iptal sayaci dogru", result.cancelled == 3, f"iptal={result.cancelled}")
    )
    results.append(
        check(
            "Arkadaslar atlandi olarak sayildi",
            result.skipped >= 2,
            f"atlanan={result.skipped}",
        )
    )
    results.append(
        check("Listeye geri donuldu", device.screen == "list", f"ekran={device.screen}")
    )

    # ---------------------------------------------------------------
    print("\n10) Profil akisi guvenlik kapisi: isaret yoksa hicbir sey silinmez")
    # Snapchat surumu farkli bir kelime kullaniyorsa (config'de olmayan),
    # bot hicbir kaydi bekleyen sayamaz ve HICBIRINI silmemelidir.
    device = FakeProfileDevice(
        people={"a": "pending", "b": "pending"}, pending_text="TanimsizDurum"
    )
    cfg = fast_config(dry_run=False)
    cfg.run.profile_flow = True
    parser = UIParserAgent(device, cfg.ui, cfg.run, logger)
    agent = ActionAgent(device, parser, cfg, logger)
    result = agent.execute()

    results.append(
        check(
            "Taninmayan durumda hicbir kayit silinmedi",
            device.removed == [],
            f"silinen={device.removed}",
        )
    )
    results.append(
        check("Iptal sayaci sifir", result.cancelled == 0, f"iptal={result.cancelled}")
    )

    # ---------------------------------------------------------------
    print("\n11) Profil akisi deneme modu: hicbir sey silinmemeli")
    device = FakeProfileDevice(people=dict(people))
    cfg = fast_config(dry_run=True)
    cfg.run.profile_flow = True
    parser = UIParserAgent(device, cfg.ui, cfg.run, logger)
    agent = ActionAgent(device, parser, cfg, logger)
    result = agent.execute()

    results.append(
        check("Deneme modunda silme yok", device.removed == [], f"silinen={device.removed}")
    )

    # ---------------------------------------------------------------
    print("\n12) Navigasyon: 'Arkadas Ekle' ekranindan hedef listeye gecis")
    # Snapchat oneri ekraninda aciliyor. O ekrandaki kisiler istek
    # gonderdiklerimiz degil, onerilerdir; orada calismak yanlis olur.
    device = FakeProfileDevice(
        people={"bekleyen_01": "pending"}, start_on_add_friends=True
    )
    cfg = fast_config(dry_run=True)

    results.append(
        check(
            "Baslangicta hedef listede degiliz",
            not on_recent_list(device, cfg.ui),
            f"ekran={device.screen}",
        )
    )

    reached = open_recent_added(device, cfg.ui, logger=logger,
                                menu_wait=0.001, list_wait=0.001)
    results.append(check("Hedef listeye gecildi", reached, f"ekran={device.screen}"))
    results.append(
        check(
            "Oneri ekranindaki kisilere dokunulmadi",
            device.removed == [],
            f"silinen={device.removed}",
        )
    )

    # Zaten listedeyken bosuna dokunmamali.
    clicks_before = device.clicks
    open_recent_added(device, cfg.ui, logger=logger,
                      menu_wait=0.001, list_wait=0.001)
    results.append(
        check(
            "Zaten listedeyken tiklama yapilmadi",
            device.clicks == clicks_before,
            f"tiklama={device.clicks - clicks_before}",
        )
    )

    # ---------------------------------------------------------------
    print("\n13) Hedef listesi: sadece verilen isimlere dokunulmali")
    # Snapchat veri dokumunden gelen kesin liste. Arayuzden tahmin yok:
    # listede olmayan hicbir kisiye dokunulmamali.
    device = FakeProfileDevice(
        people={
            "hedef_01": "pending",
            "arkadas_01": "friend",
            "hedef_02": "pending",
            "arkadas_02": "friend",
        }
    )
    cfg = fast_config(dry_run=False)
    cfg.run.profile_flow = True
    cfg.run.target_names = ["hedef_01", "hedef_02"]
    cfg.ui.require_pending_marker = False        # kaynak zaten kesin
    parser = UIParserAgent(device, cfg.ui, cfg.run, logger)
    agent = ActionAgent(device, parser, cfg, logger)
    result = agent.execute()

    results.append(
        check(
            "Sadece hedefler silindi",
            sorted(device.removed) == ["hedef_01", "hedef_02"],
            f"silinen={sorted(device.removed)}",
        )
    )
    results.append(
        check("Iptal sayaci dogru", result.cancelled == 2, f"iptal={result.cancelled}")
    )

    # Ayni listede buyuk/kucuk harf ve Turkce karakter farki tolere edilmeli.
    device = FakeProfileDevice(people={"Zehra Dalkılıç": "pending", "Ayse": "friend"})
    cfg = fast_config(dry_run=False)
    cfg.run.profile_flow = True
    cfg.run.target_names = ["zehra dalkilic"]
    cfg.ui.require_pending_marker = False
    parser = UIParserAgent(device, cfg.ui, cfg.run, logger)
    agent = ActionAgent(device, parser, cfg, logger)
    agent.execute()

    results.append(
        check(
            "Harf/aksan farki eslesmeyi bozmadi",
            device.removed == ["Zehra Dalkılıç"],
            f"silinen={device.removed}",
        )
    )

    # ---------------------------------------------------------------
    print("\n14) Veri dokumu ayristirici")
    from tools.parse_snapchat_export import extract_pending

    export = {
        "Friends": [{"Username": "kabul_eden", "Display Name": "Kabul Eden"}],
        "Sent Friend Requests": [
            {"Username": "bekleyen_a", "Display Name": "Bekleyen A"},
            {"Username": "bekleyen_b", "Display Name": "Bekleyen B"},
        ],
        "Deleted Friends": [{"Username": "silinmis_istek"}],
    }
    sections = extract_pending(export)
    names = set()
    for values in sections.values():
        names |= values

    results.append(
        check(
            "Bekleyen istekler cikarildi",
            {"bekleyen_a", "bekleyen_b", "Bekleyen A", "Bekleyen B"} <= names,
            f"bulunan={sorted(names)}",
        )
    )
    results.append(
        check("Kabul etmis arkadaslar alinmadi", "kabul_eden" not in names)
    )
    results.append(
        check("Silinmis kayitlar alinmadi", "silinmis_istek" not in names)
    )

    # ---------------------------------------------------------------
    print("\n15) Uzun basma akisi: basili tut > Arkadasligi Yonet > Kaldir > onay")
    device = FakeProfileDevice(people={"bekleyen_01": "pending", "bekleyen_02": "pending"})
    cfg = fast_config(dry_run=False)
    cfg.run.profile_flow = True
    parser = UIParserAgent(device, cfg.ui, cfg.run, logger)
    agent = ActionAgent(device, parser, cfg, logger)
    result = agent.execute()

    results.append(
        check(
            "Menu basili tutarak acildi",
            device.long_presses >= 2,
            f"basili_tutma={device.long_presses}",
        )
    )
    results.append(
        check(
            "Basili tutma suresi ayardan geldi",
            device.last_press_seconds == cfg.timing.long_press_seconds,
            f"sure={device.last_press_seconds}",
        )
    )
    results.append(
        check(
            "Iki kayit da kaldirildi",
            sorted(device.removed) == ["bekleyen_01", "bekleyen_02"],
            f"silinen={sorted(device.removed)}",
        )
    )
    results.append(
        check("Zararli islem yapilmadi", device.harmful_actions == [],
              f"zararli={device.harmful_actions}")
    )

    # ---------------------------------------------------------------
    print("\n16) Esnek metin: 'Kaldir' yerine 'Arkadasi Kaldir' yazsa da bulunmali")
    device = FakeProfileDevice(
        people={"bekleyen_01": "pending"}, remove_text="Arkadaşı Kaldır"
    )
    cfg = fast_config(dry_run=False)
    cfg.run.profile_flow = True
    parser = UIParserAgent(device, cfg.ui, cfg.run, logger)
    ActionAgent(device, parser, cfg, logger).execute()

    results.append(
        check("Farkli yazim tanindi", device.removed == ["bekleyen_01"],
              f"silinen={device.removed}")
    )

    # ---------------------------------------------------------------
    print("\n17) Yedek tiklama: metin tutmazsa koordinatla, ama tehlikeli satira asla")
    # Silme butonunun yazisi hicbir listede yok -> yedek devreye girer.
    # Menudeki 2. satir "Engelle". Yedek oraya basmayi REDDETMELI.
    device = FakeProfileDevice(
        people={"bekleyen_01": "pending"}, remove_text="Bilinmeyen Kelime"
    )
    cfg = fast_config(dry_run=False)
    cfg.run.profile_flow = True
    cfg.ui.remove_fallback_enabled = True
    cfg.ui.remove_fallback_row_index = 2          # "Engelle"
    parser = UIParserAgent(device, cfg.ui, cfg.run, logger)
    ActionAgent(device, parser, cfg, logger).execute()

    results.append(
        check("Engelle satirina basilmadi", device.harmful_actions == [],
              f"zararli={device.harmful_actions}")
    )
    results.append(
        check("Hicbir kayit silinmedi", device.removed == [],
              f"silinen={device.removed}")
    )

    # Ayni durumda dogru satir (4.) verilirse yedek calismali.
    device = FakeProfileDevice(
        people={"bekleyen_01": "pending"}, remove_text="Bilinmeyen Kelime"
    )
    cfg = fast_config(dry_run=False)
    cfg.run.profile_flow = True
    cfg.ui.remove_fallback_enabled = True
    cfg.ui.remove_fallback_row_index = 4          # silme satiri
    parser = UIParserAgent(device, cfg.ui, cfg.run, logger)
    ActionAgent(device, parser, cfg, logger).execute()

    results.append(
        check("Dogru satirda yedek tiklama calisti",
              device.removed == ["bekleyen_01"], f"silinen={device.removed}")
    )
    results.append(
        check("Yedek yolunda da zararli islem yok", device.harmful_actions == [],
              f"zararli={device.harmful_actions}")
    )

    # Yedek kapaliyken hicbir sey olmamali.
    device = FakeProfileDevice(
        people={"bekleyen_01": "pending"}, remove_text="Bilinmeyen Kelime"
    )
    cfg = fast_config(dry_run=False)
    cfg.run.profile_flow = True
    cfg.ui.remove_fallback_enabled = False
    parser = UIParserAgent(device, cfg.ui, cfg.run, logger)
    ActionAgent(device, parser, cfg, logger).execute()

    results.append(
        check("Yedek kapaliyken tiklama yok", device.removed == [],
              f"silinen={device.removed}")
    )

    # ---------------------------------------------------------------
    passed = sum(1 for r in results if r)
    total = len(results)
    print("\n" + "=" * 55)
    print(f"SONUC: {passed}/{total} kontrol gecti")
    print("=" * 55)
    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())
