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
    # Cihaz adresi.
    #
    #   "auto"                -> bagli tek cihazi otomatik sec (ONERILEN)
    #                            Hem USB telefonda hem emulatorde calisir.
    #   "127.0.0.1:5555"      -> LDPlayer / BlueStacks
    #   "127.0.0.1:21503"     -> MEmu
    #   "R58M12ABCDE"         -> USB ile bagli fiziksel telefon (adb devices)
    #   "192.168.1.42:39123"  -> Kablosuz hata ayiklama ile telefon
    #
    # Komut satirindan --serial ile de gecici olarak degistirebilirsin.
    serial: str = "auto"

    # TCP/IP uzerinden 'adb connect' calistirilsin mi?
    # Serial icinde ":" yoksa (USB cihaz) bu ayar zaten atlanir,
    # yani "auto" veya USB seri numarasi ile ugrasmana gerek yok.
    use_tcp_connect: bool = True

    # Calisma boyunca ekranin kapanmasi engellensin mi?
    # Fiziksel telefonda True olmali: ekran kapanirsa bot arayuzu okuyamaz.
    keep_screen_awake: bool = True

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
        "Vazgec", "Vazgeç", "Kapat", "Geri", "Tamamlandi", "Tamamlandı", "Bitti",
        "Cancel", "Close", "Dismiss", "Not Now", "Simdi Degil", "Şimdi Değil",
        "Done",
    ])

    # Bekleyen istekler ekranini bulmak icin aranan baslik metinleri.
    screen_titles: List[str] = field(default_factory=lambda: [
        "Bekleyen Istekler", "Bekleyen İstekler", "Gonderilen Istekler",
        "Gönderilen İstekler", "Arkadas Ekle", "Arkadaş Ekle", "Arkadaslarim",
        "Arkadaşlarım", "Hizli Ekle", "Hızlı Ekle",
        "En Son Eklenenler", "En Son Eklediklerim", "Son Eklenenler",
        "Pending Requests", "Sent Requests", "Add Friends", "My Friends",
        "Quick Add", "Recently Added",
    ])

    # Bir elemanin "tiklanabilir buton" sayilmasi icin gereken minimum
    # genislik/yukseklik (piksel). Cok kucuk metin parcalarini eler.
    min_button_width: int = 40
    min_button_height: int = 30

    # -- Profil akisi (bazi Snapchat surumleri) ---------------------------
    # Bazi surumlerde liste ekraninda "Bekliyor" butonu hic yok. Istegi geri
    # cekmek icin kisinin profiline girip menuden ilerlemek gerekiyor:
    #   liste > kisi > "Arkadasligi Yonet" > "Arkadasi Sil" > onay
    # Asagidaki listeler o akistaki buton yazilarini tanimlar.

    # Profildeki menuyu acan buton.
    manage_friendship_labels: List[str] = field(default_factory=lambda: [
        "Arkadasligi Yonet", "Arkadaşlığı Yönet", "Arkadasligi yonet",
        "Manage Friendship", "Manage",
    ])

    # Menu icindeki silme/geri cekme butonu.
    remove_friend_labels: List[str] = field(default_factory=lambda: [
        "Arkadasi Sil", "Arkadaşı Sil", "Arkadasi Kaldir", "Arkadaşı Kaldır",
        "Arkadasliktan Cikar", "Arkadaşlıktan Çıkar", "Istegi Geri Cek",
        "İsteği Geri Çek",
        "Remove Friend", "Unadd", "Cancel Request", "Remove",
    ])

    # DIKKAT - GUVENLIK KAPISI.
    # "En Son Eklenenler" listesinde hem istegi kabul etmis arkadaslar hem de
    # hala bekleyenler yan yana duruyor. Ikisi de ayni menuden siliniyor, yani
    # ayrim yapmadan calisan bir bot gercek arkadaslari da siler.
    # Bot bu yuzden profili actiktan sonra asagidaki isaretlerden birini
    # gormeden SILMEZ; goremezse geri cikip o kisiyi atlar.
    # Kendi Snapchat surumundeki gercek yaziyi ogrenmek icin:
    #     python main.py --inspect-profile
    # komutunu calistir, profil ekranindaki tum metinleri listeler.
    profile_pending_markers: List[str] = field(default_factory=lambda: [
        "Bekliyor", "Beklemede", "Istek Gonderildi", "İstek Gönderildi",
        "Eklendi", "Davet Gonderildi", "Davet Gönderildi",
        "Pending", "Requested", "Request Sent", "Added",
    ])

    # Guvenlik kapisi kapatilabilir ama VARSAYILAN OLARAK ACIK kalmali.
    # False yapmak "listedeki herkesi sil" demektir.
    require_pending_marker: bool = True

    # -- "En Son Eklenenler" listesine gitme ------------------------------
    # Snapchat "Arkadas Ekle" ekraninda aciliyor; bekleyen istekler orada
    # degil, sag ustteki uc nokta menusunun altindaki listede duruyor.

    # Hedef listenin basligi. Bot bunu gorurse dogru ekranda sayar.
    recent_list_titles: List[str] = field(default_factory=lambda: [
        "En Son Eklenenler", "En Son Eklediklerim", "Son Eklenenler",
        "Recently Added",
    ])

    # Uc nokta menusunu acan butonun content-desc / text degeri.
    # Ikon oldugu icin yazisi yok, erisilebilirlik etiketiyle bulunuyor.
    # Kendi surumundeki degeri ogrenmek icin: python main.py --scan
    overflow_button_labels: List[str] = field(default_factory=lambda: [
        "Daha Fazla", "Daha fazla", "Diger", "Diğer", "Menu", "Menü",
        "Secenekler", "Seçenekler", "More", "More options", "Options",
        "Overflow",
    ])

    # Uc nokta menusunde hedef listeyi acan satir.
    recent_list_menu_labels: List[str] = field(default_factory=lambda: [
        "En Son Eklediğim Arkadaşlar", "En Son Ekledigim Arkadaslar",
        "En Son Eklenenler", "Son Eklenenler",
        "Recently Added", "Recently Added Friends",
    ])


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

    # -- Profil akisi beklemeleri (--profile-flow) ------------------------
    # Profil ekraninin acilmasi icin beklenecek sure.
    profile_open_wait: float = 2.0

    # Menu / buton gecisleri arasinda beklenecek sure.
    profile_step_wait: float = 1.0

    # Geri tusundan sonra ekranin oturmasi icin beklenecek sure.
    profile_back_wait: float = 0.8


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

    # Liste ekraninda "Bekliyor" butonu olmayan Snapchat surumleri icin
    # profil akisini kullan (liste > kisi > Arkadasligi Yonet > Arkadasi Sil).
    # --profile-flow ile acilir.
    profile_flow: bool = False


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
