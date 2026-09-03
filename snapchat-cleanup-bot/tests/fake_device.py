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
