import serial
import glob
import time
import json
import logging
from threading import Thread, Event
from gpiozero import OutputDevice
import os 

# -------------------- LOG AYARLARI --------------------
logging.basicConfig(
    filename="system.log",
    filemode="a",
    format="%(asctime)s - %(levelname)s - %(message)s",
    level=logging.INFO,
    encoding="utf-8"
)

# -------------------- RELE PINLERİ --------------------
RELE_PINS = {
    "yikama": 17,
    "kopuk": 27,
    "renkli_kopuk": 22,
    "osmos": 10,
    "cila": 16,
    "QR_Rele": 5
}

reles = {name: OutputDevice(pin, active_high=False, initial_value=False) for name, pin in RELE_PINS.items()}

# -------------------- GLOBAL DURUMLAR --------------------
esp_serial = None
qr_port_path = None
esp_port_path = None
esp_found_event = Event()
device_lock = Event()  # 7 saniyelik bloklama
running = True

# -------------------- PORT BULMA FONKSİYONLARI --------------------
def find_esp_port():
    global esp_port_path
    ports = glob.glob("/dev/ttyUSB*")
    return ports[0] if ports else None

def find_qr_port():
    global qr_port_path
    ports = glob.glob("/dev/ttyACM*")
    return ports[0] if ports else None

# -------------------- ESP32 BAĞLANTI FONKSİYONU --------------------
def connect_esp():
    global esp_serial
    while running:
        port = find_esp_port()
        if port:
            try:
                esp_serial = serial.Serial(port, baudrate=9600, timeout=0.1)
                logging.info(f"ESP32 bağlandı: {port}")
                esp_found_event.set()
                # ESP32'ye başlangıç mesajı
                send_to_esp({'status': True, 'start': True})
                return
            except Exception as e:
                logging.error(f"ESP32 bağlanamadı: {e}")
        else:
            logging.info("ESP32 bulunamadı, tekrar aranıyor...")
        time.sleep(2)

# -------------------- QR KOD OKUMA --------------------
def read_qr():
    try:
        ser = serial.Serial(qr_port_path, baudrate=9600, timeout=0.1)
        data = b""
        start = time.time()
        while time.time() - start < 1:  # 1 saniyelik deneme periyodu
            if ser.in_waiting > 0:
                data += ser.read(ser.in_waiting)
                if b'\n' in data:
                    break
            time.sleep(0.01)
        ser.close()
        if not data:
            return None
        return data.decode(errors="ignore").strip()
    except Exception as e:
        logging.error(f"QR okuma hatası: {e}")
        return None

# -------------------- RFID OKUMA --------------------
KEYS = {
    4: 'a', 5: 'b', 6: 'c', 7: 'd', 8: 'e',
    9: 'f', 10: 'g', 11: 'h', 12: 'i', 13: 'j',
    14: 'k', 15: 'l', 16: 'm', 17: 'n', 18: 'o',
    19: 'p', 20: 'q', 21: 'r', 22: 's', 23: 't',
    24: 'u', 25: 'v', 26: 'w', 27: 'x', 28: 'y',
    29: 'z', 30: '1', 31: '2', 32: '3', 33: '4',
    34: '5', 35: '6', 36: '7', 37: '8', 38: '9',
    39: '0', 40: '\n', 44: ' ', 45: '-', 55: '.'
}

def parse_keycodes(buffer):
    return ''.join(KEYS.get(b, '') for b in buffer).strip()

def read_rfid(timeout=7):
    try:
        with open("/dev/hidraw0", "rb") as rfid_file:
            buffer = b""
            end = time.time() + timeout
            while time.time() < end:
                raw = rfid_file.read(8)
                code = raw[2]
                if code == 0:
                    continue
                if code == 40:
                    return parse_keycodes(buffer)
                else:
                    buffer += bytes([code])
    except Exception as e:
        logging.error(f"RFID hatası: {e}")
    return None

# -------------------- ESP32'YE VERİ GÖNDERME --------------------
def send_to_esp(data):
    global esp_serial
    if not esp_serial:
        logging.warning("ESP32 bulunamadı, veri gönderilemedi.")
        return
    try:
        if isinstance(data, dict):
            message = json.dumps(data)
        else:
            message = str(data)
        esp_serial.write((message + "\n").encode())
        logging.info(f"ESP32'ye gönderildi: {message}")
    except Exception as e:
        logging.error(f"ESP32'ye veri gönderilemedi: {e}")

# -------------------- RELE KONTROL --------------------
def activate_rele(name, duration):
    rele = reles.get(name)
    if not rele:
        logging.error(f"Rele bulunamadı: {name}")
        send_to_esp({'status': False, 'message': f'{name} rele bulunamadı'})
        return
    try:
        logging.info(f"{name} rölesi açıldı ({duration}s)")
        rele.on()
        time.sleep(duration)
        rele.off()
        logging.info(f"{name} rölesi kapandı")
    except Exception as e:
        logging.error(f"Rele hatası: {e}")
        send_to_esp({'status': False, 'message': str(e)})

# -------------------- ANA DİNLEME DÖNGÜSÜ --------------------
def main_loop():
    global qr_port_path
    while running:
        if not esp_found_event.is_set():
            connect_esp()
        if not qr_port_path:
            qr_port_path = find_qr_port()
            if qr_port_path:
                logging.info(f"QR port bulundu: {qr_port_path}")
        if not esp_found_event.is_set() or not qr_port_path:
            time.sleep(2)
            continue

        if device_lock.is_set():
            time.sleep(0.1)
            continue

        qr_data = read_qr()
        rfid_data = read_rfid(timeout=0.1)

        if qr_data:
            # Özel QR komutlarını kontrol et
            if qr_data.lower() == "systemd:shutdown":
                logging.info("Özel QR: systemd:shutdown algılandı. Raspberry Pi kapatılıyor...")
                os.system("sudo shutdown now")
                break  # döngüyü durdur
            elif qr_data.lower() == "systemd:reboot":
                logging.info("Özel QR: systemd:reboot algılandı. Raspberry Pi yeniden başlatılıyor...")
                os.system("sudo reboot")
                break  # döngüyü durdur

            device_lock.set()
            send_to_esp({'qr_id': qr_data, 'status': True})
            logging.info(f"QR okundu: {qr_data}")
            wait_response_and_activate_rele()

        elif rfid_data:
            device_lock.set()
            send_to_esp({'kart_id': rfid_data, 'status': True})
            logging.info(f"RFID okundu: {rfid_data}")
            wait_response_and_activate_rele()

        time.sleep(0.01)

# -------------------- RESPONSE BEKLEME --------------------
def wait_response_and_activate_rele():
    """ESP32'den gelecek response beklenir ve rele tetiklenir"""
    timeout = 7  # saniye
    start = time.time()
    while time.time() - start < timeout:
        try:
            if esp_serial.in_waiting > 0:
                line = esp_serial.readline().decode(errors='ignore').strip()
                logging.info(f"ESP32 veri geldi: {line}")
                try:
                    resp = json.loads(line)
                    if resp.get('status') and 'rele' in resp:
                        duration = resp.get('time', 66)
                        activate_rele(resp['rele'], duration)
                        break
                except Exception:
                    logging.warning(f"Geçersiz JSON: {line}")
        except Exception as e:
            logging.error(f"ESP32 okuma hatası: {e}")
        time.sleep(0.05)
    device_lock.clear()

# -------------------- PROGRAM BAŞLATMA --------------------
if __name__ == "__main__":
    logging.info("Sistem başlatıldı")
    try:
        main_loop()
    except KeyboardInterrupt:
        logging.info("Sistem durduruldu")
        running = False
