# 📘 ESP32 - Raspberry Pi Seri Haberleşme Dokümantasyonu

## 🧠 Genel Bakış
Bu sistem, **Raspberry Pi 4** ve **ESP32** arasında seri haberleşme protokolü üzerinden veri alışverişini sağlar.  
Amaç: **Yükleme Otomatı** gibi cihazlarda QR kod, RFID, röle kontrolü ve işlem takibini senkron biçimde yürütmektir.

---

## ⚙️ Donanım Bileşenleri

| Cihaz | Görev |
|-------|--------|
| **Raspberry Pi 4** | Ana kontrolcü, API bağlantısı, QR & RFID okuma işlemleri |
| **ESP32** | Röle kontrolü, süre yönetimi, geri bildirim sinyalleri |

Bağlantı:  
🔌 USB-Serial (örneğin `/dev/ttyUSB0`)  
Baud Rate: **115200**

---

## 🔁 Veri Akış Yapısı

### 🔹 Raspberry Pi → ESP32
Raspberry Pi, ESP32’ye kontrol verilerini JSON formatında gönderir.

#### Örnek Gönderim
```json
{"qr_id": 123123}
```

> Bu komut, belirli bir QR kimliği ile işlem başlatıldığını belirtir.

---

### 🔹 ESP32 → Raspberry Pi
ESP32, röle pin ve süresini belirterek geri dönüş yapar:

#### Örnek Yanıt
```json
{"relepin": 1, "süre": 60}
```

> ESP32, `relepin=1` numaralı röleyi **60 saniye** boyunca aktif tutacaktır.

---

### 🔹 Süre Bitiminde ESP32’den Gelen Son Mesaj
```json
{"program": false}
```

> Bu mesaj, işlemin tamamlandığını ve rölenin kapatıldığını bildirir.

---

## 🔒 Röle Kilitleme Mekanizması

Sistem, güvenlik amacıyla röle tetikleme komutu alındığında dış müdahaleyi engeller.

### Kurallar:
1. ESP32 bir **röle tetikleme verisi** (örnek: `{"relepin": 1, "süre": 60}`) aldığında,
2. Röle **60 saniye boyunca aktif kalır**.
3. Bu sürenin üzerine **+1 saniye ek güvenlik süresi** eklenir.
4. Bu 61 saniyelik süre boyunca ESP32 **dışarıdan başka veri almaz**.
5. Süre dolduğunda kilit kaldırılır ve sistem tekrar veri alabilir hale gelir.

---

## 🧩 Veri Formatı Kuralları

| Alan | Tip | Açıklama |
|------|-----|----------|
| `qr_id` | int | Raspberry Pi’den gönderilen işlem kimliği |
| `relepin` | int | ESP32’deki röle pin numarası |
| `süre` | int | Rölenin aktif kalma süresi (saniye) |
| `program` | bool | İşlemin bitişini bildirir |

---

## 🧠 Sistem Akış Özeti

1. Raspberry Pi QR kod veya RFID’den gelen bilgiyi işler.  
2. Bilgiyi JSON olarak ESP32’ye yollar (`{"qr_id": 123123}`).  
3. ESP32 gelen komutu değerlendirir ve uygun röleyi tetikler.  
4. Röle aktif kaldığı sürede başka komut alınmaz (kilit).  
5. Süre sonunda ESP32, röleyi kapatır ve `{"program": false}` mesajını gönderir.  
6. Raspberry Pi bu mesajı alır, işlemi tamamlar ve loglar.

---

## 📡 Seri Haberleşme Özellikleri

| Parametre | Değer |
|------------|--------|
| **Baud Rate** | 115200 |
| **Veri Formatı** | JSON |
| **Timeout** | 1 saniye |
| **Bağlantı Türü** | USB Serial (`/dev/ttyUSB*`) |

---

## 🪵 Loglama
Raspberry Pi tarafında tüm haberleşmeler `raspberry.log` dosyasına kaydedilir.

### Örnek Log Çıktısı:
```
2025-10-16 22:15:01 - Raspberry → ESP32: {"qr_id": 123123}
2025-10-16 22:15:02 - ESP32 → Raspberry: {"relepin": 1, "süre": 60}
2025-10-16 22:16:03 - ESP32 → Raspberry: {"program": false}
```

---

## 🧰 Geliştirme Notları
- Tüm veri anahtarları küçük harflerle yazılmalıdır (`qr_id`, `relepin`, `süre`).
- Raspberry Pi, ESP32 bağlantısını başlatmadan önce port varlığını kontrol eder.
- ESP32 üzerindeki röle aktifken gelen tüm yeni veriler **yok sayılır**.
- Bağlantı kesilirse sistem otomatik yeniden bağlanma denemesi yapabilir.

---

## 📅 Sürüm Bilgisi
**Sürüm:** 1.0.0  
**Yayın Tarihi:** 17.10.2025  
**Hazırlayan:** 🧑‍💻 *Yunus Emre Ercân 
