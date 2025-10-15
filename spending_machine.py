import glob, serial, time, logging
from threading import Thread, Event

logging.basicConfig(
    filename='raspberry.log',
    filemode='a',
    format='%(asctime)s - %(message)s - %(levelname)s',
    level=logging.INFO,
    encoding='utf-8'
)

# ---------------- USB Port Bulma ----------------
esp_flag = True
while esp_flag:
    try:
        usb_ports = glob.glob('/dev/ttyUSB*')
        if usb_ports:
            logging.info('[GLOB] Bağlanıyorum..')
            esp_flag = False
        else:
            logging.warning('[GLOB] USB Portu Bulamadım.')
            time.sleep(2)
    except Exception as e:
        logging.error(f"[GLOB] Aranırken hata: {e}")
        time.sleep(2)

selected_port = usb_ports[0]
logging.info(f'[GLOB] Seçilen Port: {selected_port}')


qr_flag = True
while qr_flag:
    try:
        qr_ports = glob.glob('/dev/ttyACM*')
        if qr_ports:
            logging.info('[GLOB] Bağlanıyorum..')
            qr_flag = False
        else:
            logging.warning('[GLOB] QR Portu Bulamadım.')
            time.sleep(2)
    except Exception as e:
        logging.error(f"[GLOB] Aranırken hata: {e}")
        time.sleep(2)

qr_port = qr_ports[0]
logging.info(f'[GLOB] Seçilen Port: {qr_port}')


# ---------------- ESP32 Seri Bağlantı ----------------
esp_serial = serial.Serial(selected_port, baudrate=9600, timeout=5)

def send_to_esp(message):
    try:
        esp_serial.write((message + "\n").encode())
        logging.info(f"[ESP] Gönderildi: {message}")
    except Exception as e:
        logging.warning(f"[ESP] Mesaj Gönderilemedi: {e}")

# ---------------- RFID Yardımcı Fonksiyonları ----------------
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

def clean_buffer_str(s):
    uuid_len = 36
    if len(s) >= 2 * uuid_len:
        first = s[:uuid_len]
        second = s[uuid_len:uuid_len*2]
        if first == second:
            s = s[uuid_len:]
    return s

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
                if code == 40:  # Enter tuşu
                    card = parse_keycodes(buffer)
                    return clean_buffer_str(card)
                else:
                    buffer += bytes([code])
    except Exception as e:
        logging.warning(f"[RFID] Hata: {e}")
    return None

# ---------------- QR Kod Okuma ----------------
def read_qr_uart(port=qr_port, baudrate=9600, timeout=5):
    try:
        ser = serial.Serial(port, baudrate=baudrate, timeout=0.1)
        logging.info("[UART] QR portu açıldı, veri bekleniyor...")
        start_time = time.time()
        qr_data = b""

        while time.time() - start_time < timeout:
            if ser.in_waiting > 0:
                qr_data += ser.read(ser.in_waiting)
                if b'\n' in qr_data:
                    break
            time.sleep(0.05)

        ser.close()

        if not qr_data:
            return None
        return qr_data.decode(errors="ignore").strip()

    except Exception as e:
        logging.warning(f"[QR] Hata: {e}")
        return None

# ---------------- Ana Döngü ----------------
def main_loop():
    logging.info("[SİSTEM] RFID ve QR okuma başlatıldı.")
    mode = "RFID"  # Varsayılan mod

    while True:
        # ESP32'den gelen mesajı kontrol et
        if esp_serial.in_waiting > 0:
            try:
                data = esp_serial.readline().decode(errors='ignore').strip()
                if data.startswith("MODE:"):
                    mode = data.split(":")[1].upper()
                    logging.info(f"[ESP] Mod değişti: {mode}")
            except Exception as e:
                logging.warning(f"[ESP] Veri okunamadı: {e}")

        # Mod durumuna göre okuma yap
        if mode == "RFID":
            rfid_data = read_rfid(timeout=5)
            print('RFID')
            if rfid_data:
                logging.info(f"[RFID] Kart Okundu: {rfid_data}")
                send_to_esp(f"RFID:{rfid_data}")

        elif mode == "QR":
            print('QR')
            qr_data = read_qr_uart(timeout=1)
            if qr_data:
                logging.info(f"[QR] QR Okundu: {qr_data}")
                send_to_esp(f"QR:{qr_data}")

        time.sleep(0.1)  # CPU yükünü azalt


if __name__ == "__main__":
    main_loop()
