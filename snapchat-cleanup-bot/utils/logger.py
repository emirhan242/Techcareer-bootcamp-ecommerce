"""
utils/logger.py
---------------
Renkli ve zaman damgali basit log altyapisi.
Hem konsola hem de 'run.log' dosyasina yazar; boylece bot uzun sure
calistiktan sonra neyin ne zaman yapildigini geriye donuk inceleyebilirsin.
"""

import logging
import sys
from pathlib import Path


# ANSI renk kodlari (Windows 10+ terminalleri de destekler)
_COLORS = {
    "DEBUG": "\033[90m",     # gri
    "INFO": "\033[96m",      # acik mavi
    "WARNING": "\033[93m",   # sari
    "ERROR": "\033[91m",     # kirmizi
    "CRITICAL": "\033[95m",  # mor
}
_RESET = "\033[0m"


class _ColorFormatter(logging.Formatter):
    """Sadece konsol ciktisina renk ekleyen formatlayici."""

    def format(self, record: logging.LogRecord) -> str:
        raw = super().format(record)
        color = _COLORS.get(record.levelname, "")
        return f"{color}{raw}{_RESET}" if color else raw


def get_logger(name: str = "snapbot", log_file: str = "run.log") -> logging.Logger:
    """
    Verilen isimde bir logger dondurur.
    Ayni isimle tekrar cagrilirsa yeni handler eklemez (log tekrarini onler).
    """
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger

    logger.setLevel(logging.DEBUG)
    logger.propagate = False

    fmt = "[%(asctime)s] %(levelname)-7s | %(name)s | %(message)s"
    datefmt = "%H:%M:%S"

    # 1) Konsol handler'i (renkli, INFO ve ustu)
    console = logging.StreamHandler(sys.stdout)
    console.setLevel(logging.INFO)
    console.setFormatter(_ColorFormatter(fmt, datefmt=datefmt))
    logger.addHandler(console)

    # 2) Dosya handler'i (renksiz, DEBUG dahil her sey)
    try:
        parent = Path(log_file).parent
        if str(parent) not in ("", "."):
            parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(logging.Formatter(fmt, datefmt="%Y-%m-%d %H:%M:%S"))
        logger.addHandler(file_handler)
    except OSError as exc:
        # Dosyaya yazamiyorsak bot yine de calismaya devam etsin.
        logger.warning("Log dosyasi acilamadi (%s). Sadece konsola yazilacak.", exc)

    return logger


def banner(logger: logging.Logger, text: str) -> None:
    """Asamalar arasinda gorsel ayirici basar."""
    line = "=" * 62
    logger.info(line)
    logger.info(text)
    logger.info(line)
