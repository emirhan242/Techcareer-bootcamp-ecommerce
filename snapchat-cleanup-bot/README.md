# Snapchat Bekleyen İstek Temizleyici

Snapchat'te gönderilmiş ama henüz kabul edilmemiş (bekleyen) arkadaşlık
isteklerini, Android emülatörü üzerinden ADB ile toplu olarak iptal eden
modüler bir otomasyon aracı.

## Önce okunması gereken uyarı

Snapchat kullanım şartları üçüncü parti otomasyona izin vermez. Bu araç
kendi hesabında, kendi gönderdiğin istekleri geri çekmek için tasarlandı;
yine de hesabın geçici veya kalıcı olarak kısıtlanma riski her zaman vardır.
Ana hesabını riske atmak istemiyorsan önce ikincil bir hesapta dene.
Varsayılan ayarlar bilinçli olarak yavaştır, bunları hızlandırma.

---

## Mimari

Proje iki katmana ayrıldı. **Skill**'ler tek bir işi yapan, durum tutmayan
yapı taşları. **Agent**'lar bu yapı taşlarını sırayla kullanan karar
katmanı. Böylece Snapchat arayüzü değiştiğinde sadece ilgili skill
güncelleniyor, akış mantığına dokunmuyorsun.

| Katman | Dosya | Görevi |
|---|---|---|
| Agent | `agents/environment_agent.py` | ADB, emülatör ve Snapchat kontrolü |
| Agent | `agents/ui_parser_agent.py` | Ekranı XML olarak okuyup butonları bulma |
| Agent | `agents/action_agent.py` | Tıklama, kaydırma ve zamanlama döngüsü |
| Skill | `skills/adb_connect.py` | Cihaza bağlanma |
| Skill | `skills/find_and_cancel_requests.py` | İstek bulma ve iptal etme |
| Skill | `skills/human_like_scroll.py` | Doğal kaydırma hareketi |
| Skill | `skills/random_delay_and_cooldown.py` | Bekleme ve mola mantığı |

### Klasör yapısı

```
snapchat-cleanup-bot/
├── main.py                              # Giriş noktası
├── config.py                            # Tüm ayarlar
├── requirements.txt
├── README.md
├── agents/
│   ├── __init__.py
│   ├── environment_agent.py
│   ├── ui_parser_agent.py
│   └── action_agent.py
├── skills/
│   ├── __init__.py
│   ├── adb_connect.py
│   ├── find_and_cancel_requests.py
│   ├── human_like_scroll.py
│   └── random_delay_and_cooldown.py
├── utils/
│   ├── __init__.py
│   └── logger.py
└── tests/
    ├── __init__.py
    ├── fake_device.py                   # Sahte cihaz simülasyonu
    └── test_offline.py                  # Emülatörsüz doğrulama testleri
```

---

## Emülatör mü, gerçek telefon mu?

Aşağıdaki kurulum emülatör içindir. Botu **kendi telefonunda** (USB,
kablosuz veya Termux ile tamamen telefon üzerinde) çalıştırmak istiyorsan
[MOBILE.md](MOBILE.md) dosyasına bak — orası daha kısa, çünkü emülatör
kurulumu gerekmiyor.

## Kurulum

### 1. Python paketleri

```bash
cd snapchat-cleanup-bot
python -m venv .venv

# Windows
.venv\Scripts\activate
# macOS / Linux
source .venv/bin/activate

pip install -r requirements.txt
```

### 2. Android Platform Tools (adb)

`adb` komutunun PATH'te olması gerekiyor.

Windows:
1. https://developer.android.com/tools/releases/platform-tools adresinden indir.
2. `C:\platform-tools` klasörüne çıkart.
3. Sistem Ortam Değişkenleri > Path > Yeni > `C:\platform-tools` ekle.
4. Yeni bir terminal aç ve doğrula:

```bash
adb version
```

macOS / Linux:

```bash
brew install android-platform-tools     # macOS
sudo apt install adb                    # Debian / Ubuntu
```

### 3. Emülatör ayarları

**LDPlayer:**
1. Ayarlar (üst sağdaki üç çizgi) > Diğer ayarlar.
2. **ADB hata ayıklama** seçeneğini "Yerel bağlantıya izin ver" yap.
3. Çözünürlüğü telefon moduna al: 540x960 veya 720x1280, DPI 240.
4. Emülatörü yeniden başlat.
5. Varsayılan ADB portu: `127.0.0.1:5555`

**BlueStacks 5:**
1. Ayarlar > Gelişmiş > **Android hata ayıklama köprüsü (ADB)** açık.
2. Aynı ekranda yazan port numarasını not al (genelde 5555, bazen 5565/5585).
3. Ayarlar > Ekran > Telefon (Portrait) modunu seç.

Bağlantıyı doğrula:

```bash
adb connect 127.0.0.1:5555
adb devices
```

Çıktıda cihazın `device` durumunda görünmesi gerekiyor. `offline` yazıyorsa:

```bash
adb kill-server
adb start-server
adb connect 127.0.0.1:5555
```

### 4. Snapchat hazırlığı

1. Emülatör içindeki Play Store'dan Snapchat'i kur.
2. Hesabına giriş yap ve uygulamayı en az bir kez elle aç.
3. uiautomator2 servisini cihaza kur:

```bash
python -m uiautomator2 init
```

---

## Kullanım

Üç adımı sırayla uygula. İlk çalıştırmada doğrudan `--live` kullanma.

### Adım 1: Tanı modu

Emülatörde bekleyen istekler listesini ekrana getir, sonra:

```bash
python main.py --scan
```

Bu komut hiçbir şeye tıklamaz. Ekrandaki tüm yazıları listeler ve hangi
kayıtları "bekleyen istek" olarak algıladığını gösterir.

Eğer hiçbir şey bulamazsa: çıktıdaki metin listesinden istek butonunun
gerçek yazısını bul ve `config.py` içindeki `UIConfig.pending_labels`
listesine ekle. Aynısı onay penceresi butonu için `confirm_labels` ile
geçerli.

### Adım 2: Deneme modu

```bash
python main.py
```

Bot listeyi baştan sona gezer, her adımda ne yapacağını loglar ama hiçbir
yere tıklamaz. Logları oku, doğru kişileri hedeflediğinden emin ol.

### Adım 3: Gerçek mod

```bash
python main.py --live --max 30
```

`--max` ile oturum başına iptal sayısını sınırla. İlk gün 20-30, sorun
çıkmazsa sonraki günlerde kademeli olarak artır. Tek seferde yüzlerce
işlem yapmak yerine güne yayman daha güvenli.

### Tüm seçenekler

| Seçenek | Açıklama |
|---|---|
| `--scan` | Sadece ekranı okur, hiçbir işlem yapmaz |
| `--live` | Gerçek mod. Verilmezse asla tıklama yapılmaz |
| `--max N` | Bu oturumda en fazla N istek iptal et (`0` = limitsiz) |
| `--serial ADRES` | Cihaz adresi, örnek `127.0.0.1:5565` |
| `--debug` | Her taramada arayüz XML'i ve ekran görüntüsü kaydeder |
| `--yes` | Gerçek moddaki onay sorusunu atlar |
| `--usb` | Fiziksel telefon USB ile bağlı, `adb connect` adımını atlar |
| `--pair ADRES KOD` | Android 11+ kablosuz hata ayıklama eşleştirmesi |

Çalışmayı istediğin an `Ctrl+C` ile durdurabilirsin, bot o ana kadarki
özeti yazdırıp güvenli şekilde kapanır.

---

## Ayarlar

Tüm ayarlar `config.py` içinde. Sık değiştirilenler:

| Ayar | Varsayılan | Ne işe yarar |
|---|---|---|
| `DeviceConfig.serial` | `auto` | Cihaz adresi. `auto` bağlı tek cihazı seçer |
| `DeviceConfig.keep_screen_awake` | `True` | Çalışırken ekranın kapanmasını engeller |
| `TimingConfig.click_delay_min/max` | 2.0 / 5.0 sn | Tıklamalar arası bekleme |
| `TimingConfig.cooldown_every` | 15 | Kaç işlemde bir mola |
| `TimingConfig.cooldown_seconds` | 45.0 sn | Mola süresi |
| `RunConfig.max_cancellations` | 50 | Oturum başına iptal limiti |
| `RunConfig.max_empty_scrolls` | 4 | Kaç boş kaydırmadan sonra dursun |

---

## Testler

Emülatör olmadan, sahte bir cihaz üzerinde tüm mantığı doğrular:

```bash
python -m tests.test_offline
```

Ayrıştırma, deneme modu, onay penceresi olan ve olmayan iptal akışları,
işlem limiti, İngilizce arayüz ve boş liste durumu test edilir.

---

## Sorun giderme

**`adb bulunamadı`**
Platform Tools kurulmamış veya PATH'te değil. Alternatif olarak
`skills/adb_connect.py` içindeki `_COMMON_ADB_PATHS` listesine kendi
`adb.exe` yolunu ekle.

**`127.0.0.1:5555 adresine bağlanılamadı`**
Emülatör kapalı, ADB hata ayıklama ayarı kapalı veya port farklı.
`adb devices` çıktısındaki adresi `--serial` ile ver.

**Cihaz `offline` görünüyor**
Emülatörün kendi adb sürümü ile sistemdeki sürüm çakışıyor.
`adb kill-server && adb start-server` çalıştır, sonra tekrar bağlan.

**Bot hiçbir istek bulamıyor**
Snapchat arayüzü güncellenmiş olabilir. `--scan` çalıştır, çıktıdaki
gerçek buton yazısını `config.py > UIConfig.pending_labels` listesine ekle.

**Tıklıyor ama "doğrulanamadı" diyor**
Onay penceresinin buton yazısı listede yok. `--debug` ile çalıştır,
`debug_dumps/` klasöründeki XML dosyasından gerçek yazıyı bul ve
`confirm_labels` listesine ekle.

**Liste ortasında takılıyor**
`RunConfig.max_empty_scrolls` değerini artır veya
`TimingConfig.scroll_settle_max` süresini uzat. Yavaş emülatörlerde
liste, kaydırma bitmeden okunuyor olabilir.
