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

    def __init__(self, people: dict, pending_text: str = "Bekliyor"):
        self.people = dict(people)
        self.pending_text = pending_text

        self.screen = "list"          # list | profile | menu | dialog
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

        if self.screen == "list":
            parts.append(
                self._node("En Son Eklenenler", 40, 120, 700, 200, clickable=False)
            )
            for index, name in enumerate(self._names()):
                top = FIRST_ROW_TOP + index * ROW_HEIGHT
                parts.append(self._node(name, 120, top, 700, top + 100))

        elif self.screen == "profile":
            parts.append(self._node(self.current or "", 120, 200, 700, 300,
                                    clickable=False))
            if self.people.get(self.current) == "pending":
                parts.append(self._node(self.pending_text, 120, 320, 400, 400,
                                        clickable=False))
            parts.append(self._node("Arkadasligi Yonet", 120, 500, 800, 600))

        elif self.screen == "menu":
            parts.append(self._node("Arkadasi Sil", 120, 700, 800, 800))
            parts.append(self._node("Engelle", 120, 820, 800, 920))

        elif self.screen == "dialog":
            parts.append(self._node("Emin misin?", 60, 800, 1020, 900,
                                    clickable=False))
            parts.append(self._node("Vazgec", 100, 950, 480, 1050))
            parts.append(self._node("Kaldir", 560, 950, 980, 1050))

        parts.append("</hierarchy>")
        return "\n".join(parts)

    def _node(self, text, left, top, right, bottom, clickable=True) -> str:
        return (
            f'<node text="{text}" content-desc="" resource-id="" '
            f'class="android.widget.TextView" clickable="{str(clickable).lower()}" '
            f'bounds="[{left},{top}][{right},{bottom}]" />'
        )

    def click(self, x: int, y: int) -> None:
        self.clicks += 1
        if self.screen != "list":
            return
        index = (y - FIRST_ROW_TOP) // ROW_HEIGHT
        names = self._names()
        if not 0 <= index < len(names):
            return
        self.current = names[index]
        self.screen = "profile"

    def press(self, key: str) -> None:
        if key != "back":
            return
        self.back_presses += 1
        order = {"dialog": "menu", "menu": "profile", "profile": "list"}
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
        if self.screen == "profile":
            return ["Arkadasligi Yonet"]
        if self.screen == "menu":
            return ["Arkadasi Sil", "Engelle"]
        if self.screen == "dialog":
            return ["Vazgec", "Kaldir"]
        return []

    def _confirm_dialog(self) -> None:
        """_Selector.click() buraya duser: ekrandaki butona basilmis sayilir."""
        if self.screen == "profile":
            self.screen = "menu"
        elif self.screen == "menu":
            self.screen = "dialog"
        elif self.screen == "dialog":
            if self.current and self.current not in self.removed:
                self.removed.append(self.current)
            self.screen = "profile"

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
