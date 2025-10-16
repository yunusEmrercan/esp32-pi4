# Raspberry Pi / ESP32 Kontrol Sistemi Dökümantasyonu

## 1. Genel Bakış

Bu Python programı, bir Raspberry Pi ve bağlı ESP32 cihazı arasında haberleşme sağlayarak:

* QR kod ve RFID okuma,
* Röle kontrolü (yıkama, köpük, osmos, cila vb.),
* Özel QR komutları ile Raspberry Pi’yi kapatma veya yeniden başlatma,
* Tüm işlemlerin loglanması

işlevlerini gerçekleştirir.

---

## 2. Gereksinimler

* **Python 3.x**
* **GPIO Zero** kütüphanesi: Röle kontrolü için

```bash
pip install gpiozero
```

* **Serial kütüphanesi**: Seri port iletişimi için

```bash
pip install pyserial
```

* ESP32 ve QR cihazları için USB bağlantısı
* RFID okuyucu (HID) `/dev/hidraw0` üzerinden çalışır
* Raspberry Pi üzerinde çalıştırılacaksa `sudo` yetkisi gerekir (shutdown/reboot komutları için)

---

## 3. Log Ayarları

Program, tüm işlemleri `system.log` dosyasına kaydeder.

* **Log formatı:** `tarih - seviye - mesaj`
* **Seviye:** INFO, WARNING, ERROR

```python
logging.basicConfig(
    filename="system.log",
    filemode="a",
    format="%(asctime)s - %(levelname)s - %(message)s",
    level=logging.INFO,
    encoding="utf-8"
)
```

---

## 4. Röle Tanımları

| Röle Adı     | GPIO Pin |
| ------------ | -------- |
| yikama       | 17       |
| kopuk        | 27       |
| renkli_kopuk | 22       |
| osmos        | 10       |
| cila         | 16       |
| QR_Rele      | 5        |

Röleler `OutputDevice` sınıfı ile `active_high=False` olarak tanımlanır ve başlangıçta kapalıdır (`initial_value=False`).

---

## 5. Port Bulma Fonksiyonları

* **ESP32:** `/dev/ttyUSB*`
* **QR cihazı:** `/dev/ttyACM*`

Fonksiyonlar ilk uygun portu döner veya `None`.

```python
def find_esp_port(): ...
def find_qr_port(): ...
```

---

## 6. ESP32 Bağlantısı

* `connect_esp()` fonksiyonu ile ESP32 seri port üzerinden bağlanılır.
* Başarılı bağlantıda ESP32’ye başlangıç mesajı gönderilir:

```json
{"status": true, "start": true}
```

---

## 7. QR Kod Okuma

* `read_qr()` fonksiyonu QR cihazından 1 saniyelik süre içinde veri okur.
* Okunan veri `decode().strip()` ile temizlenir.
* Hata durumunda loglanır ve `None` döner.

---

## 8. RFID Okuma

* HID cihazı `/dev/hidraw0` üzerinden okunur.
* 7 saniye süreli deneme ile kart verisi alınır.
* Keycode mapping `KEYS` dict ile ASCII karaktere çevrilir.
* Okunan değer return edilir veya hata durumunda `None`.

```python
def read_rfid(timeout=7): ...
```

---

## 9. ESP32’ye Veri Gönderme

* `send_to_esp(data)` fonksiyonu ile ESP32’ye JSON veya string veri gönderilir.
* Hata veya bağlantı yoksa loglanır.

```python
send_to_esp({'qr_id': '12345', 'status': True})
```

---

## 10. Röle Kontrol

* `activate_rele(name, duration)` ile belirtilen röle belirtilen süre açılır ve sonra kapatılır.
* Hata durumunda ESP32’ye `status: False` mesajı gönderilir.

---

## 11. Ana Dinleme Döngüsü

* `main_loop()` sürekli olarak QR ve RFID okur.
* Özel QR komutları:

  * `systemd:shutdown` → Raspberry Pi kapatılır
  * `systemd:reboot` → Raspberry Pi yeniden başlatılır
* Diğer QR veya RFID verileri ESP32’ye gönderilir ve röle tetikleme fonksiyonu çağrılır.

```python
if qr_data.lower() == "systemd:shutdown":
    os.system("sudo shutdown now")
elif qr_data.lower() == "systemd:reboot":
    os.system("sudo reboot")
```

---

## 12. ESP32 Response Bekleme

* `wait_response_and_activate_rele()` fonksiyonu:

  * ESP32’den JSON yanıt bekler
  * `{ "status": true, "rele": "yikama", "time": 60 }` şeklinde gelirse ilgili röle tetiklenir
  * Maksimum 7 saniye bekler
  * JSON parse hataları loglanır

---

## 13. Program Başlatma

```python
if __name__ == "__main__":
    logging.info("Sistem başlatıldı")
    try:
        main_loop()
    except KeyboardInterrupt:
        logging.info("Sistem durduruldu")
        running = False
```

* Ctrl+C ile durdurulabilir
* Log dosyasında kapanma kaydı tutulur

---

## 14. Özet Akış

1. ESP32 ve QR cihazı portları bulunur
2. ESP32’ye bağlantı sağlanır
3. Ana döngü QR ve RFID okur
4. Özel QR komutları kontrol edilir (`shutdown`, `reboot`)
5. Normal QR veya RFID verisi ESP32’ye gönderilir
6. ESP32’den gelen cevap ile röle tetiklenir
7. Tüm işlemler loglanır
