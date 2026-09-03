"""
agents/action_agent.py
----------------------
AGENT: ActionAgent

Sorumlulugu: Tum dongunun yonetimi. UIParserAgent'in bulduklarini
find_and_cancel_requests skill'ine verir, PaceController ile hiz sinirini
uygular, liste bitene veya limitlere ulasilana kadar kaydirmaya devam eder.

Durma kosullari (hangisi once gerceklesirse):
    - max_cancellations limitine ulasildi
    - max_runtime_seconds suresi doldu
    - Ust uste max_empty_scrolls kez yeni istek bulunamadi (liste bitti)
    - Kullanici Ctrl+C ile durdurdu
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Set

from skills.find_and_cancel_requests import CancelStats, find_and_cancel_requests
from skills.human_like_scroll import human_like_scroll
from skills.random_delay_and_cooldown import PaceController, random_delay


@dataclass
class RunResult:
    """Calisma sonucu ozeti."""

    cancelled: int = 0
    failed: int = 0
    skipped: int = 0
    scrolls: int = 0
    rounds: int = 0
    elapsed: float = 0.0
    stop_reason: str = ""
    processed: Set[str] = field(default_factory=set)


class ActionAgent:
    """Tiklama, kaydirma ve zamanlama mantigini yuruten ajan."""

    def __init__(self, device, parser, config, logger):
        self.device = device
        self.parser = parser                 # UIParserAgent
        self.ui = config.ui
        self.timing = config.timing
        self.run = config.run
        self.logger = logger

        # Hiz kontrolcusu: 2-5 sn bekleme, 15 islemde bir 45 sn mola.
        self.pace = PaceController(
            click_delay=(self.timing.click_delay_min, self.timing.click_delay_max),
            cooldown_every=self.timing.cooldown_every,
            cooldown_seconds=self.timing.cooldown_seconds,
            logger=logger,
        )

        # Ayni kaydi iki kez islememek icin kimlik kumesi.
        self.processed: Set[str] = set()

    # ------------------------------------------------------------------
    def _budget_left(self, done: int) -> int:
        """Kalan islem hakki. 0 limitsiz demek, o durumda buyuk bir sayi doner."""
        if self.run.max_cancellations <= 0:
            return 10 ** 9
        return max(0, self.run.max_cancellations - done)

    # ------------------------------------------------------------------
    def execute(self) -> RunResult:
        """Ana dongu."""
        result = RunResult()
        started = time.time()
        empty_streak = 0

        if self.run.dry_run:
            self.logger.warning(
                "DENEME MODU ACIK (dry_run=True). Hicbir tiklama yapilmayacak, "
                "sadece ne yapilacagi loglanacak."
            )

        try:
            while True:
                result.rounds += 1

                # --- Durma kosulu: sure limiti ---
                elapsed = time.time() - started
                if self.run.max_runtime_seconds > 0 and elapsed > self.run.max_runtime_seconds:
                    result.stop_reason = "Sure limiti doldu"
                    break

                # --- Durma kosulu: islem limiti ---
                budget = self._budget_left(result.cancelled)
                if budget <= 0:
                    result.stop_reason = (
                        f"Islem limitine ulasildi ({self.run.max_cancellations})"
                    )
                    break

                # --- Ekrani tara ve bulunanlari iptal et ---
                # Profil akisinda satirin sagindaki buton yerine satirin
                # kendisi hedefleniyor, o yuzden tarayici da degisiyor.
                scan = (
                    self.parser.find_person_rows
                    if self.run.profile_flow
                    else self.parser.find_pending
                )

                stats: CancelStats = find_and_cancel_requests(
                    device=self.device,
                    find_pending=scan,
                    ui_config=self.ui,
                    logger=self.logger,
                    dry_run=self.run.dry_run,
                    dialog_wait=self.timing.dialog_wait,
                    on_action=self.pace.after_action,
                    already_processed=self.processed,
                    remaining_budget=budget,
                    profile_flow=self.run.profile_flow,
                    profile_waits=(
                        self.timing.profile_open_wait,
                        self.timing.profile_step_wait,
                        self.timing.profile_back_wait,
                    ),
                )

                result.cancelled += stats.cancelled
                result.failed += stats.failed
                result.skipped += stats.skipped
                result.processed |= stats.processed_keys

                # --- Bu turda yeni bir sey yapildi mi? ---
                if stats.cancelled == 0 and stats.failed == 0:
                    empty_streak += 1
                    self.logger.info(
                        f"Yeni istek bulunamadi ({empty_streak}/{self.run.max_empty_scrolls})"
                    )
                else:
                    empty_streak = 0
                    self.logger.info(
                        f"Tur {result.rounds} ozeti: {stats} | "
                        f"toplam iptal: {result.cancelled}"
                    )

                # --- Durma kosulu: liste bitti ---
                if empty_streak >= self.run.max_empty_scrolls:
                    result.stop_reason = "Listenin sonuna ulasildi"
                    break

                # --- Asagi kaydir ---
                human_like_scroll(self.device, direction="down", logger=self.logger)
                result.scrolls += 1

                # Kaydirma sonrasi listenin oturmasini bekle.
                random_delay(
                    self.timing.scroll_settle_min,
                    self.timing.scroll_settle_max,
                    logger=self.logger,
                    reason="kaydirma sonrasi",
                )

        except KeyboardInterrupt:
            result.stop_reason = "Kullanici durdurdu (Ctrl+C)"
            self.logger.warning("Ctrl+C algilandi, guvenli sekilde durduruluyor...")

        except Exception as exc:  # noqa: BLE001 - beklenmedik hatada dokum al
            result.stop_reason = f"Beklenmedik hata: {exc}"
            self.logger.error(f"Hata olustu: {exc}", exc_info=True)
            self.parser.save_debug_dump(prefix="error")

        result.elapsed = time.time() - started
        return result

    # ------------------------------------------------------------------
    def report(self, result: RunResult) -> None:
        """Calisma sonucunu okunabilir bicimde loglar."""
        minutes = result.elapsed / 60.0
        self.logger.info("=" * 62)
        self.logger.info("CALISMA OZETI")
        self.logger.info("=" * 62)
        self.logger.info(f"  Durma nedeni     : {result.stop_reason or 'bilinmiyor'}")
        self.logger.info(f"  Iptal edilen     : {result.cancelled}")
        self.logger.info(f"  Basarisiz        : {result.failed}")
        self.logger.info(f"  Atlanan (tekrar) : {result.skipped}")
        self.logger.info(f"  Tur / kaydirma   : {result.rounds} / {result.scrolls}")
        self.logger.info(f"  Gecen sure       : {minutes:.1f} dakika")
        self.logger.info(f"  {self.pace.summary()}")
        if self.run.dry_run:
            self.logger.warning(
                "  NOT: Deneme modunda calisildi, gercekte hicbir istek iptal edilmedi."
            )
        self.logger.info("=" * 62)
