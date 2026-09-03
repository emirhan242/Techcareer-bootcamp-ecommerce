"""
agents/ui_parser_agent.py
-------------------------
AGENT: UIParserAgent

Sorumlulugu: Snapchat ekranini "okumak". Ekran goruntusu yerine Android'in
kendi arayuz agacini (view hierarchy) XML olarak alir ve icinden
"bekleyen istek" butonlarini ayiklar.

Neden goruntu isleme degil de XML?
  - XML ile butonun tam koordinati, metni ve tiklanabilir olup olmadigi
    kesin olarak bilinir. Goruntu isleme tema/cozunurluk degisince bozulur.
  - Ayni satirdaki kullanici adini da okuyabildigimiz icin loglar anlamli olur.

Disari acilan metotlar:
    dump()              -> Ham XML'i alir
    detect_screen()     -> Dogru ekranda miyiz kontrol eder
    find_pending()      -> PendingElement listesi dondurur
    save_debug_dump()   -> Sorun ayiklama icin XML + ekran goruntusu kaydeder
"""

from __future__ import annotations

import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from xml.etree import ElementTree

from skills.find_and_cancel_requests import (
    PendingElement,
    _parse_bounds,
    contains_any,
    matches_any,
    normalize,
)


class UIParserAgent:
    """Arayuz agacini ayristirip ilgilendigimiz butonlari bulan ajan."""

    def __init__(self, device, ui_config, run_config, logger):
        self.device = device
        self.ui = ui_config
        self.run = run_config
        self.logger = logger
        self._last_xml: str = ""

    # ------------------------------------------------------------------
    # Ham veri alma
    # ------------------------------------------------------------------
    def dump(self, retries: int = 2) -> str:
        """
        Arayuz agacini XML olarak dondurur.
        compressed=True onemsiz ara katmanlari eleyerek agaci kucultur,
        bu da ayristirmayi hem hizlandirir hem sadelestirir.
        """
        for attempt in range(retries + 1):
            try:
                xml = self.device.dump_hierarchy(compressed=True)
                if xml:
                    self._last_xml = xml
                    return xml
            except Exception as exc:  # noqa: BLE001
                self.logger.debug(f"dump_hierarchy denemesi {attempt + 1} basarisiz: {exc}")
                time.sleep(1.0)
        self.logger.warning("Arayuz agaci alinamadi.")
        return ""

    def _nodes(self, xml: str) -> List[Dict]:
        """
        XML'i, isimize yarayan alanlari iceren duz bir sozluk listesine cevirir.
        Her kayit: text, desc, resource_id, clickable, bounds
        """
        if not xml:
            return []

        try:
            root = ElementTree.fromstring(xml)
        except ElementTree.ParseError as exc:
            self.logger.warning(f"XML ayristirilamadi: {exc}")
            return []

        nodes: List[Dict] = []
        for node in root.iter("node"):
            bounds = _parse_bounds(node.get("bounds", ""))
            if not bounds:
                continue
            left, top, right, bottom = bounds
            if right <= left or bottom <= top:      # gorunmeyen / sifir boyutlu
                continue

            nodes.append(
                {
                    "text": (node.get("text") or "").strip(),
                    "desc": (node.get("content-desc") or "").strip(),
                    "resource_id": node.get("resource-id") or "",
                    "clickable": node.get("clickable") == "true",
                    "bounds": bounds,
                    "width": right - left,
                    "height": bottom - top,
                    "cy": (top + bottom) // 2,
                }
            )
        return nodes

    # ------------------------------------------------------------------
    # Ekran dogrulama
    # ------------------------------------------------------------------
    def detect_screen(self) -> Tuple[bool, str]:
        """
        Beklenen ekranda olup olmadigimizi anlamaya calisir.

        Donus: (uygun_mu, aciklama)
        Not: Snapchat basliklari surumden surume degistigi icin bu kontrol
        'kesin' degil, 'uyarici' niteliktedir. Bekleyen buton bulunuyorsa
        baslik eslesmese de calismaya devam edilir.
        """
        xml = self.dump()
        nodes = self._nodes(xml)
        if not nodes:
            return False, "Ekran okunamadi"

        # 1) Baslik metinlerinden biri var mi?
        for node in nodes:
            for field in (node["text"], node["desc"]):
                if field and contains_any(field, self.ui.screen_titles):
                    return True, f"Ekran basligi eslesti: '{field}'"

        # 2) Baslik yoksa bile bekleyen buton varsa dogru yerdeyiz.
        pending = self._extract_pending(nodes)
        if pending:
            return True, f"Baslik eslesmedi ama {len(pending)} bekleyen buton bulundu"

        return False, "Bekleyen istek ekraninda gorunmuyoruz"

    # ------------------------------------------------------------------
    # Bekleyen butonlari bulma
    # ------------------------------------------------------------------
    def find_pending(self) -> List[PendingElement]:
        """Ekrandaki tum bekleyen istek butonlarini yukaridan asagiya siralı dondurur."""
        xml = self.dump()
        nodes = self._nodes(xml)
        elements = self._extract_pending(nodes)

        if self.run.save_hierarchy:
            self.save_debug_dump(prefix="scan", xml=xml)

        return elements

    def _extract_pending(self, nodes: List[Dict]) -> List[PendingElement]:
        """
        Dugum listesinden bekleyen butonlari suzer ve her birine
        ayni satirdaki kullanici adini eslestirir.
        """
        candidates: List[PendingElement] = []

        for node in nodes:
            # Buton yazisi hem 'text' hem 'content-desc' alaninda olabilir.
            label = node["text"] or node["desc"]
            if not label:
                continue
            if not matches_any(label, self.ui.pending_labels):
                continue

            # Cok kucuk parcalari ele (ornek: tek harflik artiklar).
            if node["width"] < self.ui.min_button_width:
                continue
            if node["height"] < self.ui.min_button_height:
                continue

            row_label = self._find_row_name(node, nodes)

            candidates.append(
                PendingElement(
                    text=label,
                    bounds=node["bounds"],
                    resource_id=node["resource_id"],
                    row_label=row_label,
                )
            )

        # Ayni satirda birden fazla eslesme olursa (ic ice dugumler) tekilleştir.
        unique: Dict[str, PendingElement] = {}
        for element in candidates:
            row_key = str(element.bounds[1] // 20)   # dikey konuma gore grupla
            if row_key not in unique:
                unique[row_key] = element

        # Yukaridan asagiya sirala: liste sirasi bozulmasin.
        result = sorted(unique.values(), key=lambda e: e.bounds[1])
        return result

    def find_person_rows(self) -> List[PendingElement]:
        """
        Kisi listesi ekranindaki satirlari dondurur (profil akisi icin).

        find_pending() ile farki: orada satirin sagindaki "Bekliyor" butonu
        araniyor. Bazi Snapchat surumlerinde oyle bir buton yok, satirda
        sadece kisinin adi var ve istegi geri cekmek icin profile girmek
        gerekiyor. Bu fonksiyon o satirlarin kendisini tespit eder.

        Isim gibi gorunmeyen metinler (baslik, sekme adi, buton yazisi)
        elenir; geriye kalanlar yukaridan asagiya siralanir.
        """
        xml = self.dump()
        nodes = self._nodes(xml)

        if self.run.save_hierarchy:
            self.save_debug_dump(prefix="rows", xml=xml)

        noise = (
            self.ui.pending_labels
            + self.ui.confirm_labels
            + self.ui.dismiss_labels
            + self.ui.screen_titles
            + self.ui.manage_friendship_labels
            + self.ui.remove_friend_labels
        )

        rows: List[PendingElement] = []
        for node in nodes:
            text = node["text"] or node["desc"]
            if not text or len(text) > 40:
                continue
            if matches_any(text, noise):
                continue
            # Isim satiri, tek harflik artiklardan ve ince ayiriclardan buyuk olmali.
            if node["height"] < self.ui.min_button_height:
                continue
            rows.append(
                PendingElement(
                    text=text,
                    bounds=node["bounds"],
                    resource_id=node["resource_id"],
                    row_label=text,
                )
            )

        # Ic ice dugumler ayni satiri birden fazla uretebilir; dikey konuma
        # gore tekillestir.
        unique: Dict[str, PendingElement] = {}
        for element in rows:
            row_key = str(element.bounds[1] // 20)
            if row_key not in unique:
                unique[row_key] = element

        return sorted(unique.values(), key=lambda e: e.bounds[1])

    def _find_row_name(self, button: Dict, nodes: List[Dict]) -> str:
        """
        Butonun solunda, ayni yatay bantta duran metni bulur.
        Bu genellikle kullanici adi veya goruntulenen isimdir.

        Eslestirme kurallari:
          - Dikey merkezi butonunkinden en fazla yarim satir uzakta olmali
          - Butonun solunda kalmali
          - Butonun kendi yazisi veya baska bir durum etiketi olmamali
        """
        b_left, b_top, _, b_bottom = button["bounds"]
        b_cy = button["cy"]
        row_height = max(30, b_bottom - b_top)

        best_text = ""
        best_distance = 10 ** 9

        for node in nodes:
            text = node["text"] or node["desc"]
            if not text or len(text) > 40:
                continue
            # Butonun kendi metnini veya durum etiketlerini isim sanma.
            if matches_any(text, self.ui.pending_labels):
                continue
            if matches_any(text, self.ui.confirm_labels + self.ui.dismiss_labels):
                continue

            n_left, _, n_right, _ = node["bounds"]
            if n_right > b_left:            # butonun solunda degil
                continue
            if abs(node["cy"] - b_cy) > row_height:   # ayni satirda degil
                continue

            distance = b_left - n_right
            if distance < best_distance:
                best_distance = distance
                best_text = text

        return best_text

    # ------------------------------------------------------------------
    # Hata ayiklama ciktilari
    # ------------------------------------------------------------------
    def save_debug_dump(self, prefix: str = "dump", xml: Optional[str] = None) -> Optional[Path]:
        """
        Arayuz XML'ini ve ekran goruntusunu diske kaydeder.
        Bot beklemedigin bir davranis gosterirse bu dosyalari incele:
        butonun gercek metni ve resource-id degeri burada gorunur.
        """
        try:
            folder = Path(self.run.debug_dir)
            folder.mkdir(parents=True, exist_ok=True)
            stamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3]

            xml_path = folder / f"{prefix}_{stamp}.xml"
            xml_path.write_text(xml or self._last_xml or self.dump(), encoding="utf-8")

            try:
                self.device.screenshot(str(folder / f"{prefix}_{stamp}.png"))
            except Exception:  # noqa: BLE001 - ekran goruntusu olmasa da olur
                pass

            self.logger.debug(f"Hata ayiklama dokumu kaydedildi: {xml_path}")
            return xml_path
        except Exception as exc:  # noqa: BLE001
            self.logger.debug(f"Dokum kaydedilemedi: {exc}")
            return None

    def list_all_texts(self, limit: int = 60) -> List[str]:
        """
        Ekrandaki tum okunabilir metinleri listeler.
        config.py icindeki etiket listelerini kendi Snapchat surumune gore
        duzenlerken bu cikti yol gostericidir.
        """
        nodes = self._nodes(self.dump())
        texts = []
        for node in nodes:
            value = node["text"] or node["desc"]
            if value and value not in texts:
                texts.append(value)
            if len(texts) >= limit:
                break
        return texts
