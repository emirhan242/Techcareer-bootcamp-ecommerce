"""
skills/random_delay_and_cooldown.py
-----------------------------------
SKILL: random_delay_and_cooldown

Gorevi: Botun islem hizini sinirlamak. Iki amaci var:
  1. Snapchat sunucusuna saniyede onlarca istek gitmesini engellemek
     (hem hesap saglığı hem de sunucuya yuk bindirmemek icin).
  2. Islem araliklarini sabit degil degisken tutmak, cunku sabit araliklarla
     calisan bir dongu hem gercek disi hem de arayuz animasyonlari
     bitmeden tiklandigi icin hatali sonuc uretir.

Kurallar (config.TimingConfig uzerinden ayarlanir):
  - Her tiklama arasi 2-5 saniye rastgele bekleme.
  - Her 15 islemde bir 45 saniyelik uzun mola.
"""

from __future__ import annotations

import random
import time
from dataclasses import dataclass


def random_delay(min_seconds: float, max_seconds: float, logger=None, reason: str = "") -> float:
    """
    min-max araliginda rastgele bir sure bekler ve bekledigi sureyi dondurur.
    Duz uniform yerine 'ucgen dagilim' kullanilir: degerler ortalamaya yakin
    yogunlasir, uclar ise daha seyrek cikar. Bu, gercek bir kullanicinin
    tepki suresi dagilimina daha yakindir.
    """
    if max_seconds < min_seconds:
        min_seconds, max_seconds = max_seconds, min_seconds

    mid = (min_seconds + max_seconds) / 2.0
    delay = random.triangular(min_seconds, max_seconds, mid)

    if logger:
        suffix = f" ({reason})" if reason else ""
        logger.debug(f"Bekleniyor: {delay:.2f} sn{suffix}")

    time.sleep(delay)
    return delay


@dataclass
class PaceController:
    """
    Islem sayacini tutar ve ne zaman kisa bekleme, ne zaman uzun mola
    verilecegine karar verir.

    Kullanim:
        pace = PaceController(click_delay=(2.0, 5.0), cooldown_every=15,
                              cooldown_seconds=45.0, logger=log)
        for ...:
            islem_yap()
            pace.after_action()      # bekleme + gerekiyorsa mola
    """

    click_delay: tuple = (2.0, 5.0)
    cooldown_every: int = 15
    cooldown_seconds: float = 45.0
    logger: object = None

    # Dahili sayaclar (disaridan verilmez)
    action_count: int = 0
    cooldown_count: int = 0
    total_wait: float = 0.0

    def after_action(self) -> None:
        """
        Bir islem (tiklama) tamamlandiktan sonra cagrilir.
        Once sayaci artirir, sonra kisa bekleme yapar,
        esik doldiysa uzun molaya gecer.
        """
        self.action_count += 1

        # --- Kisa bekleme: her islemden sonra ---
        waited = random_delay(
            self.click_delay[0],
            self.click_delay[1],
            logger=self.logger,
            reason=f"islem #{self.action_count}",
        )
        self.total_wait += waited

        # --- Uzun mola: her N islemde bir ---
        if self.cooldown_every > 0 and self.action_count % self.cooldown_every == 0:
            self.long_cooldown()

    def long_cooldown(self) -> None:
        """
        Uzun molayi uygular. Sure, ayarlanan degerin %+-20'si kadar sapar
        (ornek: 45 sn ayarliysa 36-54 sn arasi bir deger).
        Mola sirasinda her 15 saniyede bir kalan sureyi loglar.
        """
        self.cooldown_count += 1
        jitter = random.uniform(0.8, 1.2)
        duration = self.cooldown_seconds * jitter

        if self.logger:
            self.logger.info(
                f"MOLA #{self.cooldown_count}: {self.action_count} islem tamamlandi. "
                f"{duration:.0f} saniye bekleniyor..."
            )

        remaining = duration
        step = 15.0
        while remaining > 0:
            chunk = min(step, remaining)
            time.sleep(chunk)
            remaining -= chunk
            if remaining > 1 and self.logger:
                self.logger.debug(f"Molaya devam... kalan {remaining:.0f} sn")

        self.total_wait += duration
        if self.logger:
            self.logger.info("Mola bitti, islemlere devam ediliyor.")

    def summary(self) -> str:
        """Calisma sonunda ozet satiri uretir."""
        return (
            f"Toplam islem: {self.action_count} | "
            f"Uzun mola sayisi: {self.cooldown_count} | "
            f"Beklemede gecen sure: {self.total_wait / 60.0:.1f} dakika"
        )
