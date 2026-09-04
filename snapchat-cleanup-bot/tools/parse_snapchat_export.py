"""
tools/parse_snapchat_export.py
------------------------------
Snapchat'in "Verilerim" (My Data) dokumunden bekleyen istek listesini cikarir.

Neden:
    Arayuz, bir kaydin bekleyen istek mi yoksa istegi kabul etmis bir arkadas
    mi oldugunu guvenilir sekilde soylemiyor. Ikisi ayni listede duruyor ve
    ayni menuden siliniyor. Tahmin etmek yerine kaynaga gidiyoruz: Snapchat
    bu ayrimi kendi veri dokumunde acikca veriyor.

Dokum nasil alinir:
    1. accounts.snapchat.com adresine giris yap
    2. "Verilerim" (My Data) > "Verilerimi Gonder"
    3. E-postana gelen zip dosyasini indir

Kullanim:
    python tools/parse_snapchat_export.py mydata.zip
    python tools/parse_snapchat_export.py json/friends.json
    python tools/parse_snapchat_export.py mydata.zip -o hedefler.txt

Cikti: her satirda bir isim iceren metin dosyasi. Bot bu dosyayi
--targets ile alir ve YALNIZCA icindeki kisilere dokunur.
"""

from __future__ import annotations

import argparse
import json
import sys
import zipfile
from pathlib import Path
from typing import Dict, Iterable, List, Set

# Bekleyen istekleri tutan bolumun adi surumden surume degisiyor
# ("Sent Friend Requests", "Bekleyen Arkadaslik Istekleri" ...). Bu yuzden
# bolum adini tam esitlikle degil, anahtar kelimelerle ariyoruz.
PENDING_HINTS = ("pending", "sent", "request", "bekleyen", "gonderilen", "istek")

# Ayni sekilde elenmesi gerekenler: kabul edilmis arkadaslar, silinenler,
# engellenenler. Bunlar hedef listeye ASLA girmemeli.
EXCLUDE_HINTS = ("deleted", "blocked", "silinen", "engellenen")

# Isim tasiyan alan adlari.
NAME_KEYS = ("username", "user_name", "display_name", "displayname", "name")


def _iter_sections(data) -> Iterable[tuple]:
    """JSON'daki (bolum_adi, kayitlar) ciftlerini dolasir."""
    if isinstance(data, dict):
        for key, value in data.items():
            if isinstance(value, list):
                yield key, value
            elif isinstance(value, dict):
                yield from _iter_sections(value)


def _names_from_entry(entry) -> List[str]:
    """Tek bir kayittan isim ve kullanici adini cikarir."""
    if isinstance(entry, str):
        return [entry.strip()] if entry.strip() else []
    if not isinstance(entry, dict):
        return []

    found = []
    for key, value in entry.items():
        if not isinstance(value, str) or not value.strip():
            continue
        if key.strip().lower().replace(" ", "_") in NAME_KEYS:
            found.append(value.strip())
    return found


def extract_pending(data) -> Dict[str, Set[str]]:
    """
    Dokumden bekleyen istekleri cikarir.
    Donus: {bolum_adi: {isimler}}
    """
    result: Dict[str, Set[str]] = {}

    for section, entries in _iter_sections(data):
        label = section.lower()
        if any(bad in label for bad in EXCLUDE_HINTS):
            continue
        if not any(hint in label for hint in PENDING_HINTS):
            continue

        names: Set[str] = set()
        for entry in entries:
            names.update(_names_from_entry(entry))
        if names:
            result[section] = names

    return result


def load_json(path: Path) -> dict:
    """friends.json'u dogrudan ya da zip icinden okur."""
    if path.suffix.lower() == ".zip":
        with zipfile.ZipFile(path) as archive:
            candidates = [
                name for name in archive.namelist()
                if name.lower().endswith("friends.json")
            ]
            if not candidates:
                raise SystemExit(
                    f"{path} icinde friends.json bulunamadi.\n"
                    "Zip'in icindekiler:\n  "
                    + "\n  ".join(archive.namelist()[:20])
                )
            with archive.open(candidates[0]) as handle:
                return json.load(handle)

    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Snapchat veri dokumunden bekleyen istek listesi cikarir."
    )
    parser.add_argument("path", help="mydata.zip veya friends.json yolu")
    parser.add_argument(
        "-o", "--output", default="hedefler.txt",
        help="Yazilacak dosya (varsayilan: hedefler.txt)",
    )
    args = parser.parse_args()

    path = Path(args.path)
    if not path.exists():
        print(f"Dosya bulunamadi: {path}", file=sys.stderr)
        return 1

    data = load_json(path)
    sections = extract_pending(data)

    if not sections:
        print("Bekleyen istek bolumu bulunamadi.")
        print("Dokumdeki bolumler:")
        for name, entries in _iter_sections(data):
            print(f"  - {name}  ({len(entries)} kayit)")
        print()
        print("Yukaridakilerden hangisi bekleyen istekleri tutuyorsa,")
        print("adindaki bir kelimeyi PENDING_HINTS listesine ekle.")
        return 1

    all_names: Set[str] = set()
    for section, names in sections.items():
        print(f"{section}: {len(names)} isim")
        all_names |= names

    output = Path(args.output)
    output.write_text(
        "\n".join(sorted(all_names)) + "\n", encoding="utf-8"
    )
    print()
    print(f"{len(all_names)} isim yazildi -> {output}")
    print()
    print("Simdi once deneme modunda calistir:")
    print(f"  python main.py --profile-flow --targets {output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
