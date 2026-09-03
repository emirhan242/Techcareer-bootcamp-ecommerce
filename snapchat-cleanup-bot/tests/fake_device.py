"""
tests/fake_device.py
--------------------
Emulator olmadan botun mantigini test etmek icin sahte bir uiautomator2
cihazi. Gercek bir Android arayuz agacini taklit eden XML uretir,
tiklamalari kabul eder ve iptal edilen kayitlari listeden cikarir.

Bu sayede ADB / emulator kurmadan once:
  - Ayristirma dogru calisiyor mu
  - Onay penceresi mantigi dogru mu
  - Dongu ve limitler dogru duruyor mu
sorularini yanitlayabilirsin.
"""

from __future__ import annotations

from typing import List, Optional


ROW_HEIGHT = 160
FIRST_ROW_TOP = 400
BUTTON_LEFT = 760
BUTTON_RIGHT = 980


class _Selector:
    """device(textMatches=...) cagrisinin dondurdugu nesneyi taklit eder."""

    def __init__(self, device: "FakeDevice", pattern: str):
        self.device = device
        self.pattern = pattern

    @property
    def exists(self) -> bool:
        return self.device._dialog_matches(self.pattern)

    def click(self) -> None:
        if self.exists:
            self.device._confirm_dialog()


class FakeDevice:
    """
    Basit bir 'bekleyen istekler' listesi simulasyonu.

    names          : listedeki tum kullanici adlari
    visible_count  : ayni anda ekranda gorunen satir sayisi
    require_dialog : True ise tiklamadan sonra onay penceresi acilir
    """

    def __init__(
        self,
        names: List[str],
        visible_count: int = 6,
        require_dialog: bool = True,
        pending_text: str = "Bekliyor",
    ):
        self.names = list(names)
        self.visible_count = visible_count
        self.require_dialog = require_dialog
        self.pending_text = pending_text

        self.offset = 0                      # kaydirma konumu (satir cinsinden)
        self.cancelled: List[str] = []       # iptal edilenler
        self.clicks = 0
        self.swipes = 0
        self._pending_dialog: Optional[str] = None   # onay bekleyen kullanici

    # -- uiautomator2 arayuzu ------------------------------------------
    @property
    def info(self) -> dict:
        return {
            "displayWidth": 1080,
            "displayHeight": 1920,
            "screenOn": True,
            "sdkInt": 29,
        }

    def __call__(self, **kwargs) -> _Selector:
        return _Selector(self, kwargs.get("textMatches", ""))

    def dump_hierarchy(self, compressed: bool = True) -> str:
        """Su anki ekran durumunu XML olarak uretir."""
        parts = ['<?xml version="1.0" encoding="UTF-8"?>', "<hierarchy>"]
        parts.append(self._node("Bekleyen Istekler", 40, 120, 700, 200, clickable=False))

        if self._pending_dialog:
            # Onay penceresi aciksa listenin ustunu kapatir.
            parts.append(
                self._node(
                    f"{self._pending_dialog} adli kisiye gonderilen istek geri cekilsin mi?",
                    60, 800, 1020, 900, clickable=False,
                )
            )
            parts.append(self._node("Vazgec", 100, 950, 480, 1050))
            parts.append(self._node("Istegi Iptal Et", 560, 950, 980, 1050))
        else:
            visible = self._visible_names()
            for index, name in enumerate(visible):
                top = FIRST_ROW_TOP + index * ROW_HEIGHT
                bottom = top + 100
                # Kullanici adi (butonun solunda)
                parts.append(self._node(name, 120, top, 700, bottom, clickable=False))
                # Bekleyen buton
                parts.append(
                    self._node(self.pending_text, BUTTON_LEFT, top, BUTTON_RIGHT, bottom)
                )

        parts.append("</hierarchy>")
        return "\n".join(parts)

    def click(self, x: int, y: int) -> None:
        """Koordinata tiklar. Hangi satira denk geldigini hesaplar."""
        self.clicks += 1
        if self._pending_dialog:
            return                              # dialog acikken satira tiklanmaz

        if not (BUTTON_LEFT <= x <= BUTTON_RIGHT):
            return                              # butonun disina tiklanmis

        index = (y - FIRST_ROW_TOP) // ROW_HEIGHT
        visible = self._visible_names()
        if not 0 <= index < len(visible):
            return

        name = visible[index]
        if self.require_dialog:
            self._pending_dialog = name         # onay penceresi acilir
        else:
            self._remove(name)                  # dogrudan iptal

    def swipe_points(self, points, duration_per_step: float) -> None:
        """Kaydirma: listede bir sonraki sayfaya gecer."""
        self.swipes += 1
        if points and points[0][1] > points[-1][1]:      # yukari surukleme = asagi kaydir
            self.offset = min(self.offset + self.visible_count, max(0, len(self.names)))
        else:
            self.offset = max(0, self.offset - self.visible_count)

    def swipe(self, sx, sy, tx, ty, duration=0.3) -> None:
        self.swipe_points([(sx, sy), (tx, ty)], duration)

    def screenshot(self, path: str) -> None:
        pass

    def app_current(self) -> dict:
        return {"package": "com.snapchat.android"}

    def app_list(self) -> List[str]:
        return ["com.snapchat.android"]

    def app_start(self, package: str, use_monkey: bool = False) -> None:
        pass

    def screen_on(self) -> None:
        pass

    # -- Dahili yardimcilar --------------------------------------------
    def _visible_names(self) -> List[str]:
        return self.names[self.offset : self.offset + self.visible_count]

    def _node(self, text, left, top, right, bottom, clickable=True) -> str:
        safe = (
            text.replace("&", "&amp;").replace("<", "&lt;").replace('"', "&quot;")
        )
        return (
            f'<node text="{safe}" content-desc="" resource-id="com.snapchat.android:id/x" '
            f'clickable="{str(clickable).lower()}" bounds="[{left},{top}][{right},{bottom}]" />'
        )

    def _dialog_matches(self, pattern: str) -> bool:
        """device(textMatches=...) sorgusunun ekranda karsiligi var mi?"""
        if not self._pending_dialog:
            return False
        import re
        for label in ("Vazgec", "Istegi Iptal Et"):
            try:
                if re.match(pattern, label):
                    return True
            except re.error:
                continue
        return False

    def _confirm_dialog(self) -> None:
        """Onay butonuna basildi: kaydi listeden cikar, pencereyi kapat."""
        if self._pending_dialog:
            self._remove(self._pending_dialog)
            self._pending_dialog = None

    def _remove(self, name: str) -> None:
        if name in self.names:
            self.names.remove(name)
            self.cancelled.append(name)


# ---------------------------------------------------------------------------
# Profil akisi simulasyonu
# ---------------------------------------------------------------------------
class FakeProfileDevice:
    """
    'Bekliyor' butonu olmayan Snapchat surumunu taklit eder.

    Liste ekraninda sadece isimler var. Istegi geri cekmek icin:
        satira tikla > profil > "Arkadasligi Yonet" > "Arkadasi Sil" > onay

    people: {isim: "pending" | "friend"}
        "pending" -> istek gonderilmis, kabul edilmemis (silinmeli)
        "friend"  -> istegi kabul etmis gercek arkadas (SILINMEMELI)

    Testin asil amaci ikinci grubun korundugunu dogrulamak: liste ikisini
    yan yana gosterdigi ve ikisi de ayni menuden silindigi icin, guvenlik
    kapisi calismazsa bot gercek arkadaslari da siler.
    """

    def __init__(
        self,
        people: dict,
        pending_text: str = "Bekliyor",
        start_on_add_friends: bool = False,
        remove_text: str = "Kaldır",
    ):
        self.people = dict(people)
        self.pending_text = pending_text
        # Silme butonunun yazisi. Testte "tanimadigimiz bir kelime" verip
        # koordinat yedeginin devreye girisini dogruluyoruz.
        self.remove_text = remove_text

        # start_on_add_friends=True ise cihaz Snapchat'in acildigi "Arkadas
        # Ekle" ekraninda baslar; hedef listeye uc nokta menusunden gecilir.
        self.screen = "add_friends" if start_on_add_friends else "list"
        # add_friends | overflow | list | ctx | manage | dialog
        #   ctx    : satira basili tutunca acilan menu
        #   manage : "Arkadasligi Yonet"ten sonraki menu
        self.long_presses = 0
        self.last_press_seconds = 0.0
        self.pressed_manage_rows: List[str] = []
        # Engelleme/sikayet gibi geri alinamaz islemler buraya yazilir;
        # testte bu listenin BOS kalmasi gerekiyor.
        self.harmful_actions: List[tuple] = []
        self.current: Optional[str] = None
        self.removed: List[str] = []
        self.clicks = 0
        self.swipes = 0
        self.back_presses = 0

    # -- uiautomator2 arayuzu ------------------------------------------
    @property
    def info(self) -> dict:
        return {
            "displayWidth": 1080,
            "displayHeight": 1920,
            "screenOn": True,
            "sdkInt": 33,
        }

    def __call__(self, **kwargs) -> _Selector:
        return _Selector(self, kwargs.get("textMatches", ""))

    def _names(self) -> List[str]:
        return [n for n in self.people if n not in self.removed]

    def dump_hierarchy(self, compressed: bool = True) -> str:
        parts = ['<?xml version="1.0" encoding="UTF-8"?>', "<hierarchy>"]

        if self.screen == "add_friends":
            parts.append(self._node("Arkadas Ekle", 40, 120, 700, 200, clickable=False))
            parts.append(self._node("Arkadas Bul", 40, 260, 700, 340, clickable=False))
            # Sag ustteki uc nokta ikonu: tiklanabilir ama yazisi yok.
            parts.append(self._node("", 950, 120, 1050, 220))
            for index, name in enumerate(["oneri_1", "oneri_2"]):
                top = FIRST_ROW_TOP + index * ROW_HEIGHT
                parts.append(self._node(name, 120, top, 700, top + 100))
                parts.append(self._node("Ekle", 800, top, 980, top + 100))

        elif self.screen == "overflow":
            parts.append(self._node("En Son Eklediğim Arkadaşlar", 100, 400, 900, 500))
            parts.append(self._node("Arkadaslarimi Davet Et", 100, 520, 900, 620))

        elif self.screen == "list":
            parts.append(
                self._node("En Son Eklenenler", 40, 120, 700, 200, clickable=False)
            )
            for index, name in enumerate(self._names()):
                top = FIRST_ROW_TOP + index * ROW_HEIGHT
                parts.append(self._node(name, 120, top, 700, top + 100))

        elif self.screen == "ctx":
            # Basili tutunca acilan menu.
            parts.append(self._node(self.current or "", 120, 200, 700, 300,
                                    clickable=False))
            if self.people.get(self.current) == "pending":
                parts.append(self._node(self.pending_text, 120, 320, 400, 400,
                                        clickable=False))
            parts.append(self._node("Arkadaşlığı Yönet", 120, 500, 800, 600))
            parts.append(self._node("Sohbet ve Bildirim Ayarlari", 120, 620, 800, 720))

        elif self.screen == "manage":
            # Gercek uygulamadaki sira: tehlikeli secenekler silmeden once.
            parts.append(self._node("Daha Fazla Bilgi", 120, 400, 800, 500))
            parts.append(self._node("Engelle", 120, 520, 800, 620))
            parts.append(self._node("Şikayet Et", 120, 640, 800, 740))
            parts.append(self._node(self.remove_text, 120, 760, 800, 860))
            parts.append(self._node("Adi Duzenle", 120, 880, 800, 980))

        elif self.screen == "dialog":
            parts.append(self._node("Emin misin?", 60, 800, 1020, 900,
                                    clickable=False))
            parts.append(self._node("Vazgec", 100, 950, 480, 1050))
            parts.append(self._node("Arkadaşı Sil", 560, 950, 980, 1050))

        parts.append("</hierarchy>")
        return "\n".join(parts)

    def _node(self, text, left, top, right, bottom, clickable=True) -> str:
        return (
            f'<node text="{text}" content-desc="" resource-id="" '
            f'class="android.widget.TextView" clickable="{str(clickable).lower()}" '
            f'bounds="[{left},{top}][{right},{bottom}]" />'
        )

    def long_click(self, x: int, y: int, duration: float = 0.5) -> None:
        """Satira basili tutmak menuyu acar. Normal tiklama acmaz."""
        self.long_presses += 1
        self.last_press_seconds = duration
        if self.screen != "list":
            return
        name = self._row_at(y)
        if name is None:
            return
        self.current = name
        self.screen = "ctx"

    def _row_at(self, y: int):
        index = (y - FIRST_ROW_TOP) // ROW_HEIGHT
        names = self._names()
        return names[index] if 0 <= index < len(names) else None

    def click(self, x: int, y: int) -> None:
        self.clicks += 1
        if self.screen == "add_friends":
            # Sadece sag ustteki uc nokta ikonu menuyu acar.
            if x >= 950 and y <= 220:
                self.screen = "overflow"
            return
        if self.screen == "manage":
            # Koordinat tabanli yedek tiklama buraya duser.
            self._click_manage_row(y)
            return
        if self.screen != "list":
            return
        # Listede normal tiklama menuyu ACMAZ; gercek uygulamada da profil
        # akisi ayri. use_long_press=False yolu bunu kullanir.
        name = self._row_at(y)
        if name is not None:
            self.current = name
            self.screen = "ctx"

    def _click_manage_row(self, y: int) -> None:
        """manage menusunde koordinata gore satir secer."""
        rows = [
            ("Daha Fazla Bilgi", 400, 500),
            ("Engelle", 520, 620),
            ("Şikayet Et", 640, 740),
            (self.remove_text, 760, 860),
            ("Adi Duzenle", 880, 980),
        ]
        for label, top, bottom in rows:
            if top <= y <= bottom:
                self.pressed_manage_rows.append(label)
                if label == self.remove_text:
                    self.screen = "dialog"
                elif label in ("Engelle", "Şikayet Et"):
                    # Gercek uygulamada geri donusu olmayan islem.
                    self.harmful_actions.append((self.current, label))
                return

    def press(self, key: str) -> None:
        if key != "back":
            return
        self.back_presses += 1
        order = {
            "dialog": "manage",
            "manage": "ctx",
            "ctx": "list",
            "overflow": "add_friends",
        }
        self.screen = order.get(self.screen, "list")
        if self.screen == "list":
            self.current = None

    # -- dialog / buton eslestirme -------------------------------------
    def _dialog_matches(self, pattern: str) -> bool:
        import re
        for label in self._active_labels():
            if re.match(pattern, label, re.IGNORECASE):
                return True
        return False

    def _active_labels(self) -> List[str]:
        if self.screen == "overflow":
            return ["En Son Eklediğim Arkadaşlar", "Arkadaslarimi Davet Et"]
        if self.screen == "ctx":
            return ["Arkadaşlığı Yönet", "Sohbet ve Bildirim Ayarlari"]
        if self.screen == "manage":
            return [
                "Daha Fazla Bilgi", "Engelle", "Şikayet Et",
                self.remove_text, "Adi Duzenle",
            ]
        if self.screen == "dialog":
            return ["Vazgec", "Arkadaşı Sil"]
        return []

    def _confirm_dialog(self) -> None:
        """_Selector.click() buraya duser: ekrandaki butona basilmis sayilir."""
        if self.screen == "overflow":
            self.screen = "list"
        elif self.screen == "ctx":
            self.screen = "manage"
        elif self.screen == "manage":
            self.screen = "dialog"
        elif self.screen == "dialog":
            if self.current and self.current not in self.removed:
                self.removed.append(self.current)
            self.screen = "list"
            self.current = None

    def swipe_points(self, points, duration_per_step: float) -> None:
        self.swipes += 1

    def swipe(self, sx, sy, tx, ty, duration=0.3) -> None:
        self.swipes += 1

    def screenshot(self, path: str) -> None:
        pass

    def app_current(self) -> dict:
        return {"package": "com.snapchat.android"}

    def app_list(self) -> List[str]:
        return ["com.snapchat.android"]

    def app_start(self, package: str, use_monkey: bool = False) -> None:
        pass

    def screen_on(self) -> None:
        pass
