"""
skills/human_like_scroll.py
---------------------------
SKILL: human_like_scroll

Gorevi: Listeyi asagi (veya yukari) kaydirmak.

Neden duz 'device.swipe()' yetmiyor?
  - Duz swipe her seferinde ayni iki nokta arasinda, ayni surede calisir.
    Bu hem liste her defasinda tam ayni miktarda kaydigi icin bazi satirlarin
    atlanmasina yol acar, hem de parmak hareketi hic sapmadigi icin
    dogal degildir.
  - Burada bunun yerine: baslangic/bitis noktalari rastgelelestirilir,
    aradaki yol hafif egri (yay) cizilir ve hiz basta yavas - ortada hizli -
    sonda yavas olacak sekilde dagitilir (ease-in-out).

Disari acilan fonksiyonlar:
    human_like_scroll()  -> Tek bir dogal kaydirma yapar.
    scroll_to_top()      -> Listenin basina donmek icin birkac hizli kaydirma.
"""

from __future__ import annotations

import math
import random
import time
from typing import List, Tuple


def _ease_in_out(t: float) -> float:
    """
    0..1 araligindaki ilerlemeyi yumusatir.
    Sonuc: hareket basta yavas baslar, ortada hizlanir, sonda yavaslar.
    Gercek bir parmak hareketinin hiz profili boyledir.
    """
    return 0.5 - 0.5 * math.cos(math.pi * t)


def _build_path(
    start: Tuple[int, int],
    end: Tuple[int, int],
    steps: int,
    curvature: float,
) -> List[Tuple[int, int]]:
    """
    Baslangic ve bitis noktasi arasinda, hafif yay cizen ve
    her adimda 1-2 piksel titreyen bir nokta listesi uretir.

    curvature: yayin ne kadar bukulecegi (piksel). 0 = duz cizgi.
    """
    x0, y0 = start
    x1, y1 = end

    # Yayin hangi yone bukulecegini rastgele sec (sola veya saga).
    bend = random.choice([-1, 1]) * curvature

    path: List[Tuple[int, int]] = []
    for i in range(steps + 1):
        raw_t = i / steps
        t = _ease_in_out(raw_t)          # hiz profili

        # Dogrusal ilerleme
        x = x0 + (x1 - x0) * t
        y = y0 + (y1 - y0) * t

        # Yay sapmasi: yolun ortasinda maksimum, uclarda sifir.
        x += bend * math.sin(math.pi * raw_t)

        # Mikro titreme: gercek parmakta her zaman +-1-2 piksel oynama olur.
        x += random.uniform(-1.5, 1.5)
        y += random.uniform(-1.5, 1.5)

        path.append((int(x), int(y)))

    return path


def human_like_scroll(
    device,
    direction: str = "down",
    distance_ratio: float = None,
    logger=None,
) -> None:
    """
    Ekrani dogal bir sekilde kaydirir.

    device          : uiautomator2 Device nesnesi
    direction       : "down" (listede asagi in) veya "up"
    distance_ratio  : Ekran yuksekliginin yuzde kaci kadar kaydirilacagi.
                      None birakilirsa 0.35-0.60 arasi rastgele secilir.
                      Kucuk deger = daha az satir atlama riski.
    """
    info = device.info
    width = info["displayWidth"]
    height = info["displayHeight"]

    # --- Kaydirma mesafesi ---
    if distance_ratio is None:
        distance_ratio = random.uniform(0.35, 0.60)
    distance = int(height * distance_ratio)

    # --- Baslangic X: ekran ortasina yakin ama tam ortasi degil ---
    # Tam merkez (width/2) her seferinde kullanilirsa mekanik gorunur.
    center_x = width // 2
    start_x = center_x + random.randint(-width // 8, width // 8)

    # --- Baslangic/bitis Y ---
    # Ust ve alt %15'lik bantlardan uzak dur: oralarda durum cubugu,
    # gezinme cubugu ve "bildirim panelini asagi cek" jesti var.
    safe_top = int(height * 0.20)
    safe_bottom = int(height * 0.80)

    if direction == "down":
        # Listede asagi inmek icin parmak yukari dogru surunur.
        start_y = random.randint(safe_bottom - 40, safe_bottom)
        end_y = max(safe_top, start_y - distance)
    else:
        start_y = random.randint(safe_top, safe_top + 40)
        end_y = min(safe_bottom, start_y + distance)

    end_x = start_x + random.randint(-25, 25)   # parmak asla dik inmez

    # --- Yol ve sure ---
    steps = random.randint(14, 26)              # ne kadar cok adim, o kadar puruzsuz
    duration_ms = random.randint(280, 620)      # toplam surukleme suresi
    path = _build_path((start_x, start_y), (end_x, end_y), steps, curvature=random.uniform(4, 14))

    if logger:
        logger.debug(
            f"Kaydirma: {direction} | ({start_x},{start_y}) -> ({end_x},{end_y}) | "
            f"{distance}px | {duration_ms}ms | {steps} adim"
        )

    # --- Hareketi uygula ---
    # swipe_points nokta basina saniye cinsinden gecikme ister.
    per_step = (duration_ms / 1000.0) / max(1, len(path))
    try:
        device.swipe_points(path, per_step)
    except Exception:  # noqa: BLE001 - eski u2 surumlerinde swipe_points olmayabilir
        # Yedek yontem: klasik swipe (yay ve titreme olmadan).
        if logger:
            logger.debug("swipe_points calismadi, klasik swipe'a dusuluyor.")
        device.swipe(start_x, start_y, end_x, end_y, duration=duration_ms / 1000.0)

    # Listenin atalet (fling) hareketi bitene kadar kisa bir bekleme.
    time.sleep(random.uniform(0.15, 0.45))


def scroll_to_top(device, times: int = 6, logger=None) -> None:
    """
    Listenin en basina donmek icin ust uste hizli kaydirmalar yapar.
    Bot yeniden baslatildiginda veya bir tur bittiginde kullanilir.
    """
    if logger:
        logger.info("Listenin basina donuluyor...")
    for _ in range(times):
        human_like_scroll(device, direction="up", distance_ratio=0.7, logger=logger)
        time.sleep(0.2)
