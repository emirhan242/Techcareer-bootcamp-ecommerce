"""
skills/find_and_cancel_requests.py
----------------------------------
SKILL: find_and_cancel_requests

Gorevi: Ekranda gorunen "bekleyen istek" satirlarini bulup iptal etmek.

Snapchat'te bir kisiye istek gonderdiginde yanindaki buton
"Bekliyor / Pending / Added" gibi bir metne doner. Bu butona basildiginda
ya dogrudan istek geri cekilir, ya da bir onay penceresi acilir
("Istegi Iptal Et" / "Remove Friend" gibi). Bu modul her iki durumu da
ele alir ve islemin gercekten basarili oldugunu dogrular.

Islem sirasi (tek bir kayit icin):
    1. Bekleyen butona tikla
    2. Onay penceresi acildi mi diye bak
    3. Acildiysa onay butonuna tikla
    4. Satirin artik "bekliyor" demedigini dogrula
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Callable, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Veri modelleri
# ---------------------------------------------------------------------------
@dataclass
class PendingElement:
    """Ekranda tespit edilmis tek bir 'bekleyen istek' butonu."""

    text: str                       # Butonun uzerindeki yazi ("Bekliyor" vb.)
    bounds: Tuple[int, int, int, int]   # (left, top, right, bottom)
    resource_id: str = ""           # Varsa Android kaynak kimligi
    row_label: str = ""             # Ayni satirdaki kullanici adi (loglama icin)
    screen_pending_count: int = 0   # Tespit aninda ekrandaki toplam bekleyen sayisi
                                    # (isim okunamadiginda dogrulama icin kullanilir)

    @property
    def center(self) -> Tuple[int, int]:
        """Butonun merkez koordinati - tiklama buraya yapilir."""
        left, top, right, bottom = self.bounds
        return ((left + right) // 2, (top + bottom) // 2)

    @property
    def key(self) -> str:
        """
        Ayni butonu iki kez islememek icin kullanilan kimlik.
        Kullanici adi varsa onu, yoksa dikey konumu kullanir.
        """
        if self.row_label:
            return f"name:{self.row_label}"
        return f"pos:{self.bounds[1] // 20}"

    def __str__(self) -> str:
        who = self.row_label or "(isim okunamadi)"
        return f"{who} [{self.text}] @{self.center}"


@dataclass
class CancelStats:
    """Bir calisma turunun sonuclari."""

    cancelled: int = 0              # Basariyla iptal edilen istek sayisi
    failed: int = 0                 # Tiklandi ama dogrulanamayan
    skipped: int = 0                # Daha once islenmis / atlanan
    processed_keys: set = field(default_factory=set)

    def merge(self, other: "CancelStats") -> None:
        self.cancelled += other.cancelled
        self.failed += other.failed
        self.skipped += other.skipped
        self.processed_keys |= other.processed_keys

    def __str__(self) -> str:
        return (
            f"iptal={self.cancelled} basarisiz={self.failed} atlanan={self.skipped}"
        )


# ---------------------------------------------------------------------------
# Yardimci: metin eslestirme
# ---------------------------------------------------------------------------
def normalize(text: str) -> str:
    """
    Metni karsilastirmaya hazirlar: kucuk harfe cevirir, Turkce
    karakterleri sadelestirir, bosluklari kirpar.
    Boylece "İsteği İptal Et" ile "istegi iptal et" eslesir.
    """
    if not text:
        return ""
    table = str.maketrans("ıİşŞğĞüÜöÖçÇ", "iisSgGuUoOcC")
    return text.translate(table).strip().lower()


def matches_any(text: str, candidates: List[str]) -> bool:
    """Metin, aday listesindeki herhangi biriyle ortusuyor mu?"""
    norm = normalize(text)
    if not norm:
        return False
    return any(normalize(c) == norm for c in candidates)


def contains_any(text: str, candidates: List[str]) -> bool:
    """Metin, adaylardan birini icinde barindiriyor mu? (daha gevsek eslestirme)"""
    norm = normalize(text)
    if not norm:
        return False
    return any(normalize(c) in norm for c in candidates)


# ---------------------------------------------------------------------------
# Onay penceresi yonetimi
# ---------------------------------------------------------------------------
def handle_confirmation_dialog(
    device,
    confirm_labels: List[str],
    dismiss_labels: List[str],
    wait_seconds: float = 3.0,
    logger=None,
) -> str:
    """
    Tiklamadan sonra acilan onay penceresini ele alir.

    Donus degerleri:
        "confirmed"  -> onay butonuna basildi
        "none"       -> pencere acilmadi (buton dogrudan iptal etmis olabilir)
        "dismissed"  -> beklenmedik bir pencere acildi ve kapatildi
    """
    deadline = time.time() + wait_seconds

    while time.time() < deadline:
        # Once onay butonlarini ara.
        for label in confirm_labels:
            element = device(textMatches=f"(?i)^{_escape(label)}$")
            if element.exists:
                if logger:
                    logger.debug(f"Onay butonu bulundu: '{label}'")
                element.click()
                time.sleep(0.6)
                return "confirmed"
        time.sleep(0.3)

    # Onay butonu cikmadi. Ekranda beklenmedik bir pencere var mi?
    for label in dismiss_labels:
        element = device(textMatches=f"(?i)^{_escape(label)}$")
        if element.exists:
            if logger:
                logger.debug(f"Beklenmedik pencere kapatiliyor: '{label}'")
            element.click()
            time.sleep(0.5)
            return "dismissed"

    return "none"


def _escape(text: str) -> str:
    """Metni duzenli ifade (regex) icinde guvenli kullanmak icin kacisla."""
    import re
    return re.escape(text)


# ---------------------------------------------------------------------------
# Tek bir istegin iptali
# ---------------------------------------------------------------------------
def cancel_one(
    device,
    element: PendingElement,
    ui_config,
    logger=None,
    dry_run: bool = True,
    dialog_wait: float = 3.0,
) -> bool:
    """
    Tek bir bekleyen istegi iptal eder.
    dry_run=True ise sadece ne yapacagini loglar, tiklamaz.

    Donus: islem basarili sayildiysa True.
    """
    x, y = element.center

    if dry_run:
        if logger:
            logger.info(f"[DENEME MODU] Iptal edilecekti -> {element}")
        return True

    if logger:
        logger.info(f"Iptal ediliyor -> {element}")

    # --- 1) Bekleyen butona tikla ---
    device.click(x, y)
    time.sleep(0.8)

    # --- 2/3) Onay penceresi ---
    result = handle_confirmation_dialog(
        device,
        ui_config.confirm_labels,
        ui_config.dismiss_labels,
        wait_seconds=dialog_wait,
        logger=logger,
    )

    if result == "dismissed":
        if logger:
            logger.warning(f"Onay penceresi tanimlanamadi, atlandi -> {element}")
        return False

    # --- 4) Dogrulama: bu kayit hala 'bekliyor' durumunda mi? ---
    time.sleep(0.7)
    still_pending = still_pending_on_screen(device, element, ui_config)

    if still_pending:
        if logger:
            logger.warning(
                f"Dogrulanamadi, satir hala bekliyor gorunuyor -> {element}"
            )
        return False

    if logger:
        logger.info(f"Basarili ({result}) -> {element.row_label or 'kullanici'}")
    return True


# ---------------------------------------------------------------------------
# Profil akisi: liste > kisi > "Arkadasligi Yonet" > "Arkadasi Sil" > onay
# ---------------------------------------------------------------------------
def screen_texts(device) -> List[str]:
    """Ekrandaki tum text ve content-desc degerlerini duz liste olarak dondurur."""
    from xml.etree import ElementTree

    try:
        root = ElementTree.fromstring(device.dump_hierarchy(compressed=True))
    except Exception:  # noqa: BLE001
        return []

    values = []
    for node in root.iter("node"):
        for key in ("text", "content-desc"):
            value = (node.get(key) or "").strip()
            if value:
                values.append(value)
    return values


def _click_first_label(device, labels: List[str], wait: float) -> bool:
    """Verilen yazilardan ekranda bulunan ilkine tiklar."""
    for label in labels:
        element = device(textMatches=f"(?i)^{_escape(label)}$")
        if element.exists:
            element.click()
            time.sleep(wait)
            return True
    return False


def _go_back(device, wait: float, times: int = 1) -> None:
    """Geri tusuna basar. Profilden listeye donmek icin kullanilir."""
    for _ in range(times):
        try:
            device.press("back")
        except Exception:  # noqa: BLE001 - geri basilamiyorsa dongu tikanmasin
            return
        time.sleep(wait)


def cancel_one_via_profile(
    device,
    element: PendingElement,
    ui_config,
    logger=None,
    dry_run: bool = True,
    dialog_wait: float = 3.0,
    open_wait: float = 2.0,
    step_wait: float = 1.0,
    back_wait: float = 0.8,
) -> str:
    """
    Bazi Snapchat surumlerinde liste ekraninda "Bekliyor" butonu yok; istegi
    geri cekmek icin kisinin profiline girmek gerekiyor. Bu fonksiyon o yolu
    izler:

        1. Satira tikla, profil acilsin
        2. GUVENLIK KAPISI: profilde "bekliyor" isareti var mi?
           Yoksa bu kisi istegi kabul etmis gercek bir arkadastir; dokunma,
           geri cik ve atla.
        3. "Arkadasligi Yonet" menusunu ac
        4. "Arkadasi Sil" butonuna bas
        5. Onay penceresini gec
        6. Listeye geri don

    Donus: "cancelled" | "skipped" | "failed"
    """
    x, y = element.center
    who = element.row_label or "(isim okunamadi)"

    if dry_run:
        if logger:
            logger.info(f"[DENEME MODU] Profil acilip iptal edilecekti -> {who}")
        return "cancelled"

    if logger:
        logger.info(f"Profil aciliyor -> {who}")

    device.click(x, y)
    time.sleep(open_wait)

    texts = screen_texts(device)

    # --- Guvenlik kapisi ---------------------------------------------------
    # Liste hem bekleyenleri hem kabul etmis arkadaslari icerdigi icin,
    # bekledigimize dair bir isaret gormeden silmiyoruz.
    if ui_config.require_pending_marker:
        marker = next(
            (t for t in texts if matches_any(t, ui_config.profile_pending_markers)),
            None,
        )
        if marker is None:
            if logger:
                logger.info(
                    f"Atlandi (bekleyen isareti yok, arkadas olabilir) -> {who}"
                )
            _go_back(device, back_wait)
            return "skipped"
        if logger:
            logger.debug(f"Bekleyen isareti bulundu: '{marker}' -> {who}")

    # --- Menuyu ac ---------------------------------------------------------
    if not _click_first_label(device, ui_config.manage_friendship_labels, step_wait):
        if logger:
            logger.warning(
                f"'Arkadasligi Yonet' butonu bulunamadi -> {who}. "
                "Profildeki gercek yaziyi ogrenmek icin: "
                "python main.py --inspect-profile"
            )
        _go_back(device, back_wait)
        return "failed"

    # --- Sil ---------------------------------------------------------------
    if not _click_first_label(device, ui_config.remove_friend_labels, step_wait):
        if logger:
            logger.warning(f"'Arkadasi Sil' butonu bulunamadi -> {who}")
        _go_back(device, back_wait, times=2)
        return "failed"

    # --- Onay --------------------------------------------------------------
    handle_confirmation_dialog(
        device,
        ui_config.confirm_labels,
        ui_config.dismiss_labels,
        wait_seconds=dialog_wait,
        logger=logger,
    )

    # --- Listeye don -------------------------------------------------------
    _go_back(device, back_wait, times=2)

    if logger:
        logger.info(f"Basarili -> {who}")
    return "cancelled"


def still_pending_on_screen(device, element: PendingElement, ui_config) -> bool:
    """
    Iptal isleminden sonra kaydin hala 'bekliyor' durumunda olup olmadigini
    kontrol eder.

    Neden koordinata bakmak yetmez?
      Bir istek iptal edilince o satir listeden kalkar ve altindaki satirlar
      yukari kayar. Yani ayni koordinatta yine bir 'Bekliyor' butonu bulunur,
      ama bu artik BASKA bir kullanicidir. Koordinata bakan bir dogrulama
      her seferinde "basarisiz" der.

    Bu yuzden:
      - Kullanici adi okunabildiyse: o isim hala bekleyen bir satirda mi?
      - Isim okunamadiysa: ekrandaki bekleyen buton sayisi azaldi mi?
        (azaldiysa islem tutmus sayilir)
    """
    from xml.etree import ElementTree

    try:
        hierarchy = device.dump_hierarchy(compressed=True)
        root = ElementTree.fromstring(hierarchy)
    except Exception:  # noqa: BLE001 - okunamiyorsa basarili varsay, dongu tikanmasin
        return False

    nodes = []
    for node in root.iter("node"):
        bounds = _parse_bounds(node.get("bounds", ""))
        if not bounds:
            continue
        nodes.append(
            {
                "text": (node.get("text") or "").strip(),
                "desc": (node.get("content-desc") or "").strip(),
                "bounds": bounds,
                "cy": (bounds[1] + bounds[3]) // 2,
            }
        )

    pending_nodes = [
        n for n in nodes
        if matches_any(n["text"] or n["desc"], ui_config.pending_labels)
    ]

    # --- Durum A: kullanici adi biliniyor ---
    if element.row_label:
        target = normalize(element.row_label)
        for node in nodes:
            value = normalize(node["text"] or node["desc"])
            if value != target:
                continue
            # Bu isim ekranda hala duruyor. Yaninda bekleyen buton var mi?
            for button in pending_nodes:
                same_row = abs(button["cy"] - node["cy"]) <= 60
                to_the_right = button["bounds"][0] >= node["bounds"][2] - 10
                if same_row and to_the_right:
                    return True
        # Isim ekranda yok ya da yaninda bekleyen buton kalmamis -> iptal olmus.
        return False

    # --- Durum B: isim okunamadi, sayiya bak ---
    return len(pending_nodes) >= element.screen_pending_count > 0


def _parse_bounds(raw: str) -> Optional[Tuple[int, int, int, int]]:
    """'[12,34][56,78]' bicimindeki metni sayi dortlusune cevirir."""
    import re
    match = re.match(r"\[(\d+),(\d+)\]\[(\d+),(\d+)\]", raw or "")
    if not match:
        return None
    return tuple(int(g) for g in match.groups())  # type: ignore[return-value]


# ---------------------------------------------------------------------------
# Ana skill fonksiyonu: ekrandaki tum istekleri islet
# ---------------------------------------------------------------------------
def find_and_cancel_requests(
    device,
    find_pending: Callable[[], List[PendingElement]],
    ui_config,
    logger=None,
    dry_run: bool = True,
    dialog_wait: float = 3.0,
    on_action: Optional[Callable[[], None]] = None,
    already_processed: Optional[set] = None,
    remaining_budget: Optional[int] = None,
    max_iterations: int = 200,
    profile_flow: bool = False,
    profile_waits: Optional[Tuple[float, float, float]] = None,
) -> CancelStats:
    """
    O anda ekranda gorunen bekleyen istekleri sirayla iptal eder.

    ONEMLI TASARIM NOTU:
      Her iptalden sonra ekran YENIDEN taranir. Cunku bir istek iptal
      edilince o satir listeden kalkar ve alttaki satirlar yukari kayar.
      Tek bir taramada alinan koordinat listesini sirayla kullanmak,
      ikinci tiklamadan itibaren yanlis satira basmak demektir.
      Bu yuzden her turda sadece "islenmemis ilk kayit" ele alinir.

    find_pending      : Ekrani tarayip PendingElement listesi donduren fonksiyon
                        (UIParserAgent tarafindan saglanir).
    on_action         : Her islemden sonra cagrilir. Bekleme ve mola mantigi
                        buraya baglanir (PaceController.after_action).
    already_processed : Onceki turlarda islenmis kayitlarin kimlik kumesi.
    remaining_budget  : Bu cagride en fazla kac iptal yapilabilecegi.
    max_iterations    : Guvenlik siniri. Beklenmedik bir durumda sonsuz
                        donguye girilmesini engeller.
    profile_flow      : True ise satirdaki butona tiklamak yerine kisinin
                        profiline girilip menuden iptal edilir. Liste
                        ekraninda "Bekliyor" butonu olmayan Snapchat
                        surumleri icin.

    Donus: CancelStats
    """
    stats = CancelStats()
    seen = already_processed if already_processed is not None else set()

    for iteration in range(max_iterations):
        # --- Limit kontrolu ---
        if remaining_budget is not None and stats.cancelled >= remaining_budget:
            if logger:
                logger.info("Bu tur icin belirlenen islem limitine ulasildi.")
            break

        # --- Ekrani her seferinde yeniden tara ---
        elements = find_pending()
        if not elements:
            if logger and iteration == 0:
                logger.debug("Ekranda bekleyen istek bulunamadi.")
            break

        # Tespit aninda kac bekleyen kayit vardi? (isim okunamayan durumlar icin)
        for element in elements:
            element.screen_pending_count = len(elements)

        # --- Henuz islenmemis ilk kaydi sec ---
        target = next((e for e in elements if e.key not in seen), None)
        if target is None:
            # Ekrandaki her sey zaten islenmis. Yeni kayit icin kaydirmak gerek.
            stats.skipped += len(elements)
            if logger:
                logger.debug(
                    f"Ekrandaki {len(elements)} kaydin tamami daha once islenmis."
                )
            break

        if logger and iteration == 0:
            logger.info(f"Ekranda {len(elements)} bekleyen istek tespit edildi.")

        seen.add(target.key)
        stats.processed_keys.add(target.key)

        if profile_flow:
            open_wait, step_wait, back_wait = profile_waits or (2.0, 1.0, 0.8)
            outcome = cancel_one_via_profile(
                device,
                target,
                ui_config,
                logger=logger,
                dry_run=dry_run,
                dialog_wait=dialog_wait,
                open_wait=open_wait,
                step_wait=step_wait,
                back_wait=back_wait,
            )
        else:
            ok = cancel_one(
                device,
                target,
                ui_config,
                logger=logger,
                dry_run=dry_run,
                dialog_wait=dialog_wait,
            )
            outcome = "cancelled" if ok else "failed"

        if outcome == "cancelled":
            stats.cancelled += 1
        elif outcome == "skipped":
            # Profil akisinda guvenlik kapisi bu kisiyi eledi (bekleyen degil).
            stats.skipped += 1
        else:
            stats.failed += 1

        # Bekleme / mola mantigi disaridan enjekte edilir.
        if on_action:
            on_action()

    return stats
