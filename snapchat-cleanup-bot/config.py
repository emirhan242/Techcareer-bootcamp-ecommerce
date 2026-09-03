"""
config.py
---------
Tum ayarlar tek yerde. Kod icine sabit deger yazmak yerine burayi duzenle.
Snapchat arayuzu surumden surume degistigi icin "etiket" listeleri
genis tutuldu (Turkce + Ingilizce karsiliklar birlikte).
"""

from dataclasses import dataclass, field
from typing import List


# ---------------------------------------------------------------------------
# 1) CIHAZ / BAGLANTI AYARLARI
# ---------------------------------------------------------------------------
@dataclass
class DeviceConfig:
    # Emulator ADB adresi.
    #   LDPlayer   -> 127.0.0.1:5555
    #   BlueStacks -> 127.0.0.1:5555 (veya 5565 / 5585)
    #   MEmu       -> 127.0.0.1:21503
    # Fiziksel telefon kullaniyorsan buraya "adb devices" ciktisindaki
    # seri numarasini yaz (ornek: "R58M12ABCDE").
    serial: str = "127.0.0.1:5555"

    # TCP/IP uzerinden baglanilacak mi? Fiziksel USB cihazda False yap.
    use_tcp_connect: bool = True

    # Snapchat paket adi. Klon/beta surumlerde farkli olabilir.
    package_name: str = "com.snapchat.android"

    # uiautomator2 servisi baslarken beklenecek maksimum sure (saniye).
    connect_timeout: float = 60.0


# ---------------------------------------------------------------------------
# 2) ARAYUZ ETIKETLERI (UI SELECTORS)
# ---------------------------------------------------------------------------
@dataclass
class UIConfig:
    # "Bekleyen istek" satirini tanimlayan buton yazilari.
    # Snapchat'te istek gonderilmis kisinin yanindaki buton bu metinleri alir.
    pending_labels: List[str] = field(default_factory=lambda: [
        # Turkce
        "Bekliyor", "Beklemede", "Istek Gonderildi", "İstek Gönderildi",
        "Gonderildi", "Gönderildi", "Eklendi",
        # Ingilizce
        "Pending", "Requested", "Request Sent", "Added", "Added Me Back",
    ])

    # Iptal islemini onaylayan dialog butonlarinin yazilari.
    confirm_labels: List[str] = field(default_factory=lambda: [
        # Turkce
        "Istegi Iptal Et", "İsteği İptal Et", "Iptal Et", "İptal Et",
        "Arkadasi Kaldir", "Arkadaşı Kaldır", "Kaldir", "Kaldır",
        "Evet", "Tamam", "Sil",
        # Ingilizce
        "Cancel Request", "Remove Friend", "Remove", "Unadd",
        "Yes", "OK", "Confirm", "Delete",
    ])

    # Dialogu kapatmak icin kullanilan "vazgec" butonlari.
    # DIKKAT: Turkce'de "Iptal" hem onay hem vazgec anlamina gelebiliyor.
    # Bu yuzden onay listesinde "Iptal Et" (fiil), burada "Iptal" (tek basina) var.
    dismiss_labels: List[str] = field(default_factory=lambda: [
        "Vazgec", "Vazgeç", "Kapat", "Geri",
        "Cancel", "Close", "Dismiss", "Not Now", "Simdi Degil", "Şimdi Değil",
    ])

    # Bekleyen istekler ekranini bulmak icin aranan baslik metinleri.
    screen_titles: List[str] = field(default_factory=lambda: [
        "Bekleyen Istekler", "Bekleyen İstekler", "Gonderilen Istekler",
        "Gönderilen İstekler", "Arkadas Ekle", "Arkadaş Ekle", "Arkadaslarim",
        "Arkadaşlarım", "Hizli Ekle", "Hızlı Ekle",
        "Pending Requests", "Sent Requests", "Add Friends", "My Friends",
        "Quick Add",
    ])

    # Bir elemanin "tiklanabilir buton" sayilmasi icin gereken minimum
    # genislik/yukseklik (piksel). Cok kucuk metin parcalarini eler.
    min_button_width: int = 40
    min_button_height: int = 30


# ---------------------------------------------------------------------------
# 3) ZAMANLAMA / HIZ AYARLARI
# ---------------------------------------------------------------------------
@dataclass
class TimingConfig:
    # Iki tiklama arasi bekleme araligi (saniye).
    click_delay_min: float = 2.0
    click_delay_max: float = 5.0

    # Kac islemde bir uzun mola verilecek.
    cooldown_every: int = 15

    # Uzun mola suresi (saniye). Gercek sure bu degerin %+-20'si kadar sapar.
    cooldown_seconds: float = 45.0

    # Onay dialogunun ekrana gelmesi icin beklenecek sure.
    dialog_wait: float = 3.0

    # Kaydirma sonrasi ekranin oturmasi icin beklenecek sure araligi.
    scroll_settle_min: float = 0.8
    scroll_settle_max: float = 1.8


# ---------------------------------------------------------------------------
# 4) CALISMA / GUVENLIK LIMITLERI
# ---------------------------------------------------------------------------
@dataclass
class RunConfig:
    # True ise HICBIR tiklama yapilmaz, sadece ne yapacagi loglanir.
    # Ilk calistirmada mutlaka True birak ve loglari incele.
    dry_run: bool = True

    # Tek oturumda iptal edilecek maksimum istek sayisi.
    # 0 = limitsiz. Hesap guvenligi icin ilk gunlerde 50-100 arasi onerilir.
    max_cancellations: int = 50

    # Yeni istek bulunamadan ust uste kac kez kaydirilacak.
    # Bu sayiya ulasilinca listenin sonuna gelindigi varsayilir.
    max_empty_scrolls: int = 4

    # Toplam calisma suresi limiti (saniye). 0 = limitsiz.
    max_runtime_seconds: float = 3600.0

    # Ekran goruntusu / hierarchy dokumu kaydedilecek klasor (hata ayiklama).
    debug_dir: str = "debug_dumps"

    # Her adimda hierarchy dokumu kaydedilsin mi? (yavaslatir, sadece debug)
    save_hierarchy: bool = False


# ---------------------------------------------------------------------------
# 5) TEK BIR TOPLU AYAR NESNESI
# ---------------------------------------------------------------------------
@dataclass
class AppConfig:
    device: DeviceConfig = field(default_factory=DeviceConfig)
    ui: UIConfig = field(default_factory=UIConfig)
    timing: TimingConfig = field(default_factory=TimingConfig)
    run: RunConfig = field(default_factory=RunConfig)


# main.py bu nesneyi import eder.
CONFIG = AppConfig()
