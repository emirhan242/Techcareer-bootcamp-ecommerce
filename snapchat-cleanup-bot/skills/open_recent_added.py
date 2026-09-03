"""
skills/open_recent_added.py
---------------------------
SKILL: open_recent_added

Gorevi: Snapchat'i "En Son Eklenenler" listesine getirmek.

Neden gerekli:
    Snapchat "Arkadas Ekle" ekraninda aciliyor. O ekranda gorunen kisiler
    ONERILER (yanlarinda sari "+ Ekle" butonu var), yani senin istek
    gonderdiklerin degil. Bekleyen istekler sag ustteki uc nokta menusunun
    altindaki "En Son Eklediğim Arkadaslar" listesinde duruyor.

    Bot yanlis ekranda calisirsa ya hicbir sey bulamaz ya da hic tanimadigi
    kisilere istek gonderir. Bu yuzden islem baslamadan once dogru listeye
    gecildigi dogrulanir.

Akis:
    1. Zaten hedef listede miyiz? Oyleyse dokunma.
    2. Degilsek uc nokta menusunu ac.
    3. Menuden "En Son Eklediğim Arkadaslar" satirina tikla.
    4. Basligi gorerek dogrula.
"""

from __future__ import annotations

import time
from typing import List, Optional, Tuple

from skills.find_and_cancel_requests import matches_any, screen_texts


def _clickable_nodes(device) -> List[dict]:
    """Ekrandaki tiklanabilir dugumleri sade bir sozluk listesi olarak dondurur."""
    from xml.etree import ElementTree
    import re

    try:
        root = ElementTree.fromstring(device.dump_hierarchy(compressed=True))
    except Exception:  # noqa: BLE001
        return []

    nodes = []
    for node in root.iter("node"):
        match = re.match(r"\[(\d+),(\d+)\]\[(\d+),(\d+)\]", node.get("bounds", "") or "")
        if not match:
            continue
        left, top, right, bottom = (int(g) for g in match.groups())
        if right <= left or bottom <= top:
            continue
        nodes.append(
            {
                "text": (node.get("text") or "").strip(),
                "desc": (node.get("content-desc") or "").strip(),
                "clickable": node.get("clickable") == "true",
                "bounds": (left, top, right, bottom),
                "center": ((left + right) // 2, (top + bottom) // 2),
            }
        )
    return nodes


def on_recent_list(device, ui_config) -> bool:
    """Hedef listenin basligi ekranda mi?"""
    return any(
        matches_any(text, ui_config.recent_list_titles)
        for text in screen_texts(device)
    )


def _find_overflow_button(device, ui_config) -> Optional[Tuple[int, int]]:
    """
    Uc nokta menusunu acan butonu bulur.

    Once erisilebilirlik etiketiyle arar. Bulamazsa ekranin sag ust
    kosesindeki tiklanabilir, yazisiz dugumu aday olarak dondurur -
    uc nokta ikonu orada duruyor.
    """
    nodes = _clickable_nodes(device)

    for node in nodes:
        label = node["desc"] or node["text"]
        if label and matches_any(label, ui_config.overflow_button_labels):
            return node["center"]

    # Etiketle bulunamadi: sag ust koseye bak.
    if not nodes:
        return None
    width = max(n["bounds"][2] for n in nodes)
    height = max(n["bounds"][3] for n in nodes)

    candidates = [
        n for n in nodes
        if n["clickable"]
        and not (n["text"] or n["desc"])          # ikon: yazisi yok
        and n["bounds"][0] > width * 0.75         # sagda
        and n["bounds"][1] < height * 0.20        # ustte
    ]
    if not candidates:
        return None
    # Birden fazlaysa en sagdakini sec.
    return max(candidates, key=lambda n: n["bounds"][0])["center"]


def open_recent_added(
    device,
    ui_config,
    logger=None,
    menu_wait: float = 1.5,
    list_wait: float = 2.0,
) -> bool:
    """
    Snapchat'i "En Son Eklenenler" listesine getirir.
    Donus: hedef listede olundugu dogrulandiysa True.
    """
    log = logger.info if logger else print

    if on_recent_list(device, ui_config):
        log("Zaten 'En Son Eklenenler' listesindeyiz.")
        return True

    center = _find_overflow_button(device, ui_config)
    if center is None:
        if logger:
            logger.warning(
                "Uc nokta menu butonu bulunamadi. Listeyi elle ac "
                "(sag ust ... > 'En Son Eklediğim Arkadaslar') ve tekrar calistir."
            )
        return False

    log(f"Uc nokta menusu aciliyor: {center}")
    device.click(*center)
    time.sleep(menu_wait)

    # Menuden hedef satiri sec.
    for label in ui_config.recent_list_menu_labels:
        element = device(textMatches=f"(?i)^{_escape(label)}$")
        if element.exists:
            log(f"Menu satirina tiklaniyor: '{label}'")
            element.click()
            time.sleep(list_wait)
            break
    else:
        if logger:
            logger.warning(
                "Menude 'En Son Eklediğim Arkadaslar' satiri bulunamadi. "
                "Gercek yaziyi ogrenmek icin menu acikken: python main.py --scan"
            )
        return False

    if on_recent_list(device, ui_config):
        log("'En Son Eklenenler' listesi acildi.")
        return True

    if logger:
        logger.warning("Menuye tiklandi ama hedef liste dogrulanamadi.")
    return False


def _escape(text: str) -> str:
    import re
    return re.escape(text)
