#!/usr/bin/env bash
# Termux'ta telefonu kendi kendine ADB'ye baglar.
#
# Kullanim:
#   ./tools/termux_connect.sh                      # sadece baglan (eslesme zaten yapilmissa)
#   ./tools/termux_connect.sh 37529 219263         # once eslestir, sonra baglan
#
# Ikinci kullanimda argumanlar telefondaki "Cihazi eslesme kodu ile esle"
# penceresindeki PORT ve KOD. O pencere komut calisirken ACIK kalmali,
# kapaninca kod gecersiz olur.

set -u

PAIR_PORT="${1:-}"
PAIR_CODE="${2:-}"

log() { printf '%s\n' "$*"; }

if ! command -v adb >/dev/null 2>&1; then
    log "HATA: adb bulunamadi. Once: pkg install android-tools"
    exit 1
fi

# Telefonun kendi adresleri. Kablosuz hata ayiklama bazi cihazlarda
# yalnizca Wi-Fi arayuzune baglaniyor, bazilarinda loopback'e de cevap
# veriyor. Ikisini de deneriz.
wifi_ip() {
    ip -4 addr show 2>/dev/null \
        | awk '/inet /{print $2}' \
        | cut -d/ -f1 \
        | grep -v '^127\.' \
        | head -n 1
}

IP="$(wifi_ip)"
HOSTS="127.0.0.1"
[ -n "$IP" ] && HOSTS="$IP 127.0.0.1"

log "== adb sunucusu yeniden baslatiliyor"
adb kill-server >/dev/null 2>&1
adb start-server >/dev/null 2>&1

if [ -n "$PAIR_PORT" ]; then
    if [ -z "$PAIR_CODE" ]; then
        log "HATA: port verdin ama kodu vermedin."
        log "Kullanim: $0 <port> <kod>"
        exit 1
    fi
    log "== eslestirme deneniyor (port $PAIR_PORT)"
    paired=0
    for h in $HOSTS; do
        log "-- adb pair $h:$PAIR_PORT"
        if adb pair "$h:$PAIR_PORT" "$PAIR_CODE" 2>&1 | tee /dev/stderr | grep -qi "Successfully paired"; then
            paired=1
            break
        fi
    done
    if [ "$paired" -ne 1 ]; then
        log ""
        log "Eslestirme basarisiz. En sik sebep: eslestirme penceresi kapandi."
        log "Pencere komut calisirken acik kalmali. Bolunmus ekran kullan"
        log "veya Termux:Float eklentisini kur, sonra YENI port ve kodla"
        log "tekrar dene (her acilista degisiyor)."
        exit 1
    fi
fi

# Baglanti portu eslestirme portundan farkli ve her seferinde degisiyor.
# mDNS ile bulmayi dene, bulamazsak kullanicidan isteriz.
log "== baglanti portu araniyor (mDNS)"
CONNECT_ADDR="$(adb mdns services 2>/dev/null \
    | awk '/_adb-tls-connect/{print $3}' \
    | head -n 1)"

if [ -n "$CONNECT_ADDR" ]; then
    log "-- bulundu: $CONNECT_ADDR"
    CANDIDATES="$CONNECT_ADDR"
    PORT="${CONNECT_ADDR##*:}"
    for h in $HOSTS; do
        CANDIDATES="$CANDIDATES $h:$PORT"
    done
else
    log "-- mDNS bir sey bulamadi."
    log ""
    log "Telefonda: Gelistirici secenekleri > Kablosuz hata ayiklama"
    log "ekranindaki 'IP adresi ve Baglanti noktasi' satirini oku ve"
    log "portu gir (ornek 39485):"
    printf 'Port: '
    read -r MANUAL_PORT
    [ -z "$MANUAL_PORT" ] && { log "Port verilmedi, cikiliyor."; exit 1; }
    CANDIDATES=""
    for h in $HOSTS; do
        CANDIDATES="$CANDIDATES $h:$MANUAL_PORT"
    done
fi

log "== baglaniliyor"
for addr in $CANDIDATES; do
    log "-- adb connect $addr"
    if adb connect "$addr" 2>&1 | tee /dev/stderr | grep -qiE "connected to"; then
        log ""
        log "== bagli cihazlar"
        adb devices
        log ""
        log "Simdi botu calistirabilirsin:"
        log "  python main.py --serial $addr --scan"
        exit 0
    fi
done

log ""
log "Baglanti kurulamadi. Kontrol listesi:"
log "  1. Kablosuz hata ayiklama hala acik mi?"
log "  2. Telefon Wi-Fi'a bagli mi? (mobil veri yetmiyor)"
log "  3. Ekrandaki port degismis olabilir, tekrar oku."
log "  4. Eslestirme hic yapilmadiysa once port+kod ile calistir:"
log "     $0 <eslestirme_portu> <kod>"
exit 1
