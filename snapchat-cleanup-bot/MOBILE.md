# Fiziksel Telefonda Çalıştırma

Emülatör kurmadan, botu doğrudan kendi Android telefonunda çalıştırmanın
üç yolu var. Aşağıdakiler zorluk sırasına göre dizildi.

Önce genel not: uiautomator2 Android'in kendi test altyapısını (UiAutomator)
kullanıyor. Bu iPhone'da yok, dolayısıyla bu bot iOS'ta doğrudan çalışmaz.
Ayrıntı ve çözüm için aşağıdaki [iPhone kullanıyorsanız](#iphone-kullaniyorsaniz)
bölümüne bak.

---

## Yöntem A — PC + telefon, USB kablo (en kolay)

Python PC'de çalışır, tıklamalar kabloyla telefona gider. Emülatör kurmaya
gerek yok, Snapchat zaten telefonunda kurulu ve giriş yapılmış durumda.

### 1. Telefonda geliştirici seçeneklerini aç

1. Ayarlar > Telefon hakkında.
2. **Yapı numarası**na (Build number) arka arkaya 7 kez dokun.
   - Xiaomi/MIUI'de: Ayarlar > Telefon hakkında > **MIUI sürümü**.
   - Samsung'da: Ayarlar > Telefon hakkında > Yazılım bilgileri > Yapı numarası.
3. "Artık geliştiricisiniz" yazısını görünce geri dön.
4. Ayarlar > Sistem > **Geliştirici seçenekleri**ne gir.
5. **USB hata ayıklama**yı aç.
6. Xiaomi kullanıyorsan ek olarak **USB hata ayıklama (Güvenlik ayarları)**
   seçeneğini de aç. Bu kapalıyken bot tıklayamaz, sadece ekranı okur.

### 2. Telefonu bağla

Kabloyu tak. Telefonda "USB hata ayıklamaya izin verilsin mi?" penceresi
çıkacak. **Bu bilgisayardan her zaman izin ver** kutusunu işaretle ve onayla.

Kablonun veri aktarımı desteklediğinden emin ol. Bazı ucuz şarj kabloları
sadece güç taşır, o zaman telefon `adb devices` çıktısında hiç görünmez.

PC'de:

```bash
adb devices
```

Beklenen çıktı:

```
List of devices attached
R58M12ABCDE     device
```

`unauthorized` yazıyorsa telefondaki izin penceresini onaylamamışsındır.
Hiç görünmüyorsa kablo veya sürücü sorunu (Windows'ta cihazın OEM USB
sürücüsünü kur).

### 3. Çalıştır

Serial artık `auto` olduğu için hiçbir ayar dosyasına dokunman gerekmiyor:

```bash
python main.py --usb --scan          # tanı: ekranı oku, tıklama yok
python main.py --usb                 # deneme modu
python main.py --usb --live --max 30 # gerçek mod
```

Birden fazla cihaz bağlıysa (mesela hem telefon hem emülatör açıksa) bot
hangisini seçeceğini bilemez ve listeyi gösterip durur. O durumda seç:

```bash
python main.py --usb --serial R58M12ABCDE --live
```

---

## Yöntem B — PC + telefon, kablosuz (Android 11 ve üstü)

Kablo istemiyorsan. Telefon ve PC aynı Wi-Fi ağında olmalı.

### 1. Kablosuz hata ayıklamayı aç

Geliştirici seçenekleri > **Kablosuz hata ayıklama**yı aç.

### 2. Eşleştir

Aynı ekranda **Cihazı eşleştirme koduyla eşleştir**e dokun. Açılan pencerede
bir IP:PORT ve 6 haneli kod görünür. Pencere açıkken PC'de:

```bash
python main.py --pair 192.168.1.42:37215 123456 --scan
```

Dikkat: buradaki port **eşleştirme portu**dur, her seferinde değişir ve
pencere kapanınca geçersiz olur.

### 3. Bağlan

Eşleştirme bittikten sonra "Kablosuz hata ayıklama" ana ekranında farklı bir
IP:PORT yazar. Asıl bağlantı adresi budur:

```bash
python main.py --serial 192.168.1.42:39123 --live --max 30
```

Eşleştirmeyi bir kez yapman yeterli, sonraki seferlerde sadece `--serial`
ile bağlanırsın. Ama telefon yeniden başlarsa port değişir, tekrar bakman
gerekir.

---

## Yöntem C — Sadece telefon, PC yok (Termux)

Botu telefonun kendi üzerinde çalıştırmak. Android 11+ gerekiyor, root
gerekmiyor. Mantık şu: telefon kendi kendine ADB ile bağlanıyor
(`127.0.0.1`), Python da Termux içinde çalışıyor.

### 1. Termux kur

**Play Store'daki Termux'u kurma**, o sürüm yıllardır güncellenmiyor ve
paket kurulumu bozuk. F-Droid'den veya GitHub releases'ten kur:
https://github.com/termux/termux-app/releases

### 2. Paketleri kur

```bash
pkg update && pkg upgrade
pkg install python git android-tools
```

Sonra derlenmesi sorunlu olan iki kütüphaneyi pip yerine `pkg` ile kur.
`uiautomator2` içeride `lxml` istiyor, `lxml`i Termux'ta pip kaynaktan
derlemeye çalışır ve `libxml2 and libxslt development packages` hatasıyla
düşer. Hazır derlenmiş paketleri kurunca pip onları olduğu gibi kullanır:

```bash
pkg install libxml2 libxslt python-lxml python-pillow
```

Ardından botun kendi bağımlılıkları:

```bash
pip install uiautomator2 adbutils
```

Burada `pip install -r requirements.txt` kullanma; o dosya Pillow'u da pip
üzerinden kurmaya çalışır ve Termux'ta aynı derleme sorununa girersin.
Yukarıdaki iki komut aynı işi görüyor.

### 3. Projeyi indir

```bash
git clone https://github.com/emirhan242/Techcareer-bootcamp-ecommerce
cd Techcareer-bootcamp-ecommerce/snapchat-cleanup-bot
```

`cd` "No such file or directory" diyorsa bot kodu henüz `main`e merge
edilmemiş demektir, geliştirme dalını çek:

```bash
cd ~/Techcareer-bootcamp-ecommerce
git checkout claude/snapchat-cancel-pending-requests-uv1uk2
cd snapchat-cleanup-bot
```

### 4. Kablosuz hata ayıklamayı aç ve kendine bağlan

Geliştirici seçenekleri > **Kablosuz hata ayıklama** açık olsun.

Android bu özelliği yalnızca telefon bir **Wi-Fi ağına bağlıyken** açıyor;
sadece mobil veri varken seçenek gri kalır veya eşleştirme adresi vermez.
Etrafta ağ yoksa başka bir telefonun kişisel erişim noktasını açıp bu
telefonu ona bağlaman yeterli. O ağın internete çıkması gerekmiyor: bot
`127.0.0.1` üzerinden, yani telefonun kendi içinden bağlanıyor, Wi-Fi
sadece Android'in özelliği etkinleştirmesi için duruyor.

**Cihazı eşleştirme koduyla eşleştir**e dokun. Çıkan IP:PORT ve kodla,
Termux'ta (telefon kendi kendine eşleşiyor, IP yerine 127.0.0.1 yaz):

```bash
adb pair 127.0.0.1:37215 123456
```

Sonra "Kablosuz hata ayıklama" ana ekranındaki portla bağlan:

```bash
adb connect 127.0.0.1:39123
adb devices
```

Bir zorluk var: eşleştirme ekranını açıp Termux'a geçmen gerekiyor, ekran
değişince pencere kapanabiliyor. Bölünmüş ekran (split screen) kullanırsan
ikisini yan yana görürsün, iş çok kolaylaşır.

### 5. Çalıştır

```bash
python main.py --serial 127.0.0.1:39123 --scan
python main.py --serial 127.0.0.1:39123 --live --max 30
```

Termux'ta çalışırken Snapchat'i ön plana alman gerekiyor. Bot Snapchat'i
kendisi başlatır, ama Termux arka plana düşünce Android onu öldürebilir.
Bunu engellemek için Termux bildirimindeki **Acquire wakelock**a dokun ve
Ayarlar > Uygulamalar > Termux > Pil > **Kısıtlama yok** yap.

---

## Fiziksel telefonda dikkat edilecekler

**Ekran açık kalmalı.** Ekran kapanınca arayüz ağacı okunamaz ve bot yarıda
kalır. Bot bunu kendisi hallediyor: başlarken `svc power stayon` ile ekranı
açık tutuyor, iş bitince geri alıyor. Yine de telefonu şarja takılı tut,
ekran sürekli açık kalacağı için pil hızlı biter.

**Telefonu kullanma.** Bot çalışırken telefona dokunma, bildirim açma,
uygulama değiştirme. Ekran değişirse bot yanlış yere tıklayabilir. Bu yüzden
`--max` ile küçük partiler halinde çalıştırmak, telefonu bir kenara bırakıp
işini yapmaktan daha rahat.

**Bildirimler.** Gelen bir bildirim banner'ı listenin üstünü kapatabilir.
Rahatsız Etmeyin modunu açmak iyi olur.

**Otomatik döndürmeyi kapat.** Ekran yatay moda geçerse tüm koordinatlar
kayar.

**Ekran çözünürlüğü.** Kaydırma mantığı sabit piksel değil, ekran yüksekliği
oranı kullanıyor. Yani telefon çözünürlüğü ne olursa olsun çalışır, ayar
gerekmez.

**Snapchat'in arayüzü.** Emülatördeki ile telefondaki Snapchat sürümü farklı
olabilir, buton yazıları değişebilir. Bu yüzden her yeni cihazda önce
`--scan` çalıştır, algılanan etiketleri kontrol et.

---

## iPhone kullanıyorsanız

iOS'ta UiAutomator'ın karşılığı **XCUITest**, ona da ancak cihaza imzalanmış
bir test taşıyıcısı (**WebDriverAgent**) kurarak erişilebiliyor. Bu bir Mac,
Xcode ve Apple Developer hesabı gerektiriyor; ücretsiz hesapta imza 7 günde
bir düşüyor. Teknik olarak mümkün ama bu iş için ödenen bedel yüksek.

**Gerek yok, çünkü bekleyen istekler sunucu tarafında tutuluyor.** Hangi
cihazdan iptal ettiğin fark etmez. Yapılacak:

1. PC'de emülatörü kur (ana [README.md](README.md) kurulum bölümü).
2. Emülatördeki Snapchat'e **aynı hesapla** giriş yap.
3. Botu normal şekilde çalıştır.
4. İş bitince iPhone'daki Snapchat'i aşağı çekerek yenile — liste temizlenmiş
   olacak.

Yeni bir cihazdan giriş yaptığın için Snapchat SMS veya e-posta ile doğrulama
isteyebilir, iPhone'unu yanında tut. Emülatördeki oturumu işi bitince
kapatabilirsin.

İleride gerçekten iPhone üzerinde çalıştırmak istersen mimari buna hazır:
skill'ler `device` nesnesini dışarıdan alıyor ve ondan yalnızca `info`,
`dump_hierarchy()`, `click(x, y)`, `swipe_points()` ve `device(textMatches=...)`
bekliyor. `facebook-wda` kütüphanesini bu arayüze çeviren bir adaptör yazmak
yeterli; `find_and_cancel_requests` ve `human_like_scroll` hiç değişmez.
Snapchat'in iOS bundle kimliği `com.toyopagroup.picaboo`.

---

## Sorun giderme

**`Bagli cihaz bulunamadi`**
`adb devices` çalıştır. Boşsa: USB hata ayıklama kapalı, kablo veri
taşımıyor veya izin penceresi onaylanmamış.

**Cihaz `unauthorized` görünüyor**
Telefondaki "USB hata ayıklamaya izin ver" penceresini onayla. Pencere
çıkmıyorsa Geliştirici seçenekleri > **USB hata ayıklama yetkilerini sıfırla**
yapıp kabloyu tekrar tak.

**Bot ekranı okuyor ama tıklamıyor (Xiaomi/Redmi/POCO)**
Geliştirici seçenekleri > **USB hata ayıklama (Güvenlik ayarları)** kapalı.
Bunu açmak için telefonda bir Mi hesabıyla giriş yapmış olman gerekiyor.

**`uiautomator2 baglantisi kurulamadi`**
Cihaza ATX agent kurulamamış. Çalıştır:

```bash
python -m uiautomator2 init
```

Bazı telefonlarda "bilinmeyen kaynaklardan uygulama yükleme" izni gerekir.

**Kablosuz hata ayıklama seçeneği gri / açılmıyor**
Telefon Wi-Fi'a bağlı değil. Mobil veri bu özellik için yetmiyor. Herhangi
bir Wi-Fi ağına (başka bir telefonun erişim noktası dahil) bağlan, seçenek
açılacaktır.

**Termux'ta `adb: command not found`**
`pkg install android-tools` çalıştır.

**Termux'ta `Failed to build lxml` / `libxml2 and libxslt development
packages are installed`**
pip lxml'i kaynaktan derlemeye çalışıyor. Hazır paketleri kur, sonra pip'i
tekrar çalıştır:

```bash
pkg install libxml2 libxslt python-lxml
pip install uiautomator2 adbutils
```

**Termux'ta `adb pair` başarısız**
Eşleştirme penceresi kapanmış olabilir, kod tek kullanımlık. Bölünmüş ekran
kullanarak pencereyi açık tutarken komutu yaz.

**Bot çalışırken Termux donuyor / kapanıyor**
Wakelock al (Termux bildirimindeki "Acquire wakelock") ve pil optimizasyonunu
Termux için kapat.
